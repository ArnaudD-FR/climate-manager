"""Climate Manager coordinator — the integration's control loop.

Evaluates all managed rooms every minute and on HA startup, deriving the
desired temperature from the current global mode and time program, then
pushing to TRVs only when the target changes.

Design decisions from CONTEXT.md / RESEARCH.md:
- D-01: Poll every minute via async_track_time_interval (caller registers this)
- D-02: Push-on-change only — _last_pushed dict tracks last pushed temp per entity
- D-03: Manual override hold — if TRV reports a temp different from last pushed,
         skip this entity this tick; hold lifts automatically at next period transition
- D-04: On HA restart _last_pushed is empty → startup push always fires (INFRA-03)
- D-07/D-08: Persons with no room_ids are skipped silently
- D-09: Pure backend — no HA entities, no entity registration here

Requirements addressed:
- GLOBAL-01: branches on global mode (Off / Time program / Time program & presences)
- GLOBAL-02: MODE_OFF → frost protection temperature for all rooms
- GLOBAL-03: period_temperatures dict provides configurable temps per period mode
- SCHED-05: per-room time program override; falls back to global program if absent
- PERSON-06: persons have associated room_ids
- PERSON-07: present person → heat from first Normal/Comfort period to end of last
- PERSON-08: sandwiched Reduced/Frost in occupied window → hold preceding N/C temp
- PERSON-09: absent person → Reduced temperature
- INFRA-03: immediate push on HA startup before first tick
- INFRA-05: DST-safe — always calls dt_util.now(), never uses callback's UTC arg

Pitfalls mitigated:
- Pitfall 1: cancel callback stored externally on runtime_data and called on unload
- Pitfall 2: _utc_now arg ignored; dt_util.now() is the single time source
- Pitfall 3: last=None on startup bypasses override hold, ensuring startup push
- Pitfall 6: reads attributes["temperature"] (the setpoint), not the sensor reading
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
    PRESENCE_HA,
    ROOM_MODE_FROST,
    ROOM_MODE_CUSTOM,
)
from .schedule import compute_occupied_temp, evaluate_schedule, resolve_presence
from .trv import set_trv_temperature

if TYPE_CHECKING:
    from . import ClimateManagerData

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(minutes=1)


class ClimateManagerCoordinator:
    """Control loop: evaluates schedules every minute and pushes temps to TRVs.

    Created in async_setup_entry and stored on entry.runtime_data.coordinator.
    The minute-polling scheduler is registered by the caller (async_setup_entry)
    via async_track_time_interval — the cancel callback is stored on runtime_data
    and called in async_unload_entry (Pitfall 1 — no ghost listeners).
    """

    def __init__(self, hass: HomeAssistant, data: "ClimateManagerData") -> None:
        """Initialise the coordinator.

        Args:
            hass: The Home Assistant instance.
            data: The integration's runtime data (shared reference — mutations
                  from Phase 3 WebSocket handlers are visible on the next tick).
        """
        self._hass = hass
        self._data = data
        # Empty on construction → D-04: first async_evaluate is always a full push.
        self._last_pushed: dict[str, float] = {}
        # Wave 2: track last evaluation results for status push and get_status WS command.
        self._last_active_period: str | None = None
        self._last_present_persons: list[str] = []
        # Per-room effective period (may differ from global in time_program_presences mode).
        self._last_room_periods: dict[str, str] = {}

    async def async_evaluate(self, _utc_now: datetime | None = None) -> None:
        """Evaluate all managed rooms and push temperatures as needed.

        Called immediately after registration (INFRA-03 startup push) and then
        every minute by async_track_time_interval.

        The _utc_now argument is provided by async_track_time_interval but is
        deliberately ignored — it carries UTC time (Pitfall 2). Local wall-clock
        time is always derived from dt_util.now() (INFRA-05 / DST-safe).
        """
        # Single authoritative time source — DST-safe (Pitfall 2, INFRA-05)
        now = dt_util.now()
        config = self._data.runtime_config  # shared reference — never copy (Anti-pattern)
        global_mode = config["global_mode"]
        period_temperatures: dict[str, float] = config["period_temperatures"]
        rooms: dict[str, list[str]] = self._data.rooms  # {area_id: [entity_id, ...]}

        if global_mode == MODE_OFF:
            # GLOBAL-02: all TRVs → frost protection temperature
            desired_temp = period_temperatures[PERIOD_FROST_PROTECTION]
            await asyncio.gather(*(
                self._push_safely(entity_id, desired_temp, "MODE_OFF")
                for entity_ids in rooms.values()
                for entity_id in entity_ids
            ))
            # Wave 2: reset status tracking for MODE_OFF.
            # Active period is None (no schedule evaluated), but presence is still
            # computed for status display — mode only affects TRV control, not reporting.
            self._last_active_period = None
            self._last_present_persons = self._compute_present_persons(config, now)

        elif global_mode == MODE_TIME_PROGRAM:
            # SCHED-05: per-room override if defined, else global program
            await self._evaluate_time_program(now, config, period_temperatures, rooms)

        elif global_mode == MODE_TIME_PROGRAM_PRESENCES:
            # Open Question 1 recommendation: evaluate all rooms via their time program
            # first (unassociated rooms behave like MODE_TIME_PROGRAM), then apply
            # presence overrides for person-associated rooms.
            await self._evaluate_time_program_presences(
                now, config, period_temperatures, rooms
            )
        else:
            _LOGGER.warning("Unknown global_mode %r — no TRV commands issued", global_mode)

        # Wave 2: push updated status to all subscribed panel instances after every evaluation
        self._hass.bus.async_fire(
            f"{DOMAIN}_status_update",
            self._build_status_payload(),
        )

    def _compute_present_persons(self, config: dict, now: datetime) -> list[str]:
        """Return the list of person IDs currently present, regardless of global mode.

        Used for status reporting in all modes. Presence mode only affects TRV
        temperature control (MODE_TIME_PROGRAM_PRESENCES) — it never suppresses
        the presence state from the status display.

        Persons with mode=force_present always appear; force_absent always absent;
        scheduled is evaluated against the person's periodic schedule via resolve_presence().
        HA mode (D-21): mode='ha' delegates presence detection to HA's own person.*
        entity state — person is present iff hass.states.get(person_id).state == 'home'.
        All other HA states (not_home, unknown, unavailable, zone names, None) → absent.
        """
        persons_config: dict = config.get("persons", {})
        present: list[str] = []
        for person_id, person_config in persons_config.items():
            if person_config.get("mode") == PRESENCE_HA:
                # D-21: HA-mode — read person.* entity state from HA directly
                state_obj = self._hass.states.get(person_id)
                if state_obj is not None and state_obj.state == "home":
                    present.append(person_id)
            else:
                # scheduled, force_present, force_absent, or unknown → delegate to resolve_presence
                if resolve_presence(person_config, now):
                    present.append(person_id)
        return present

    async def _evaluate_time_program(
        self,
        now: datetime,
        config: dict,
        period_temperatures: dict[str, float],
        rooms: dict[str, list[str]],
    ) -> None:
        """Push scheduled temperatures for all rooms (MODE_TIME_PROGRAM).

        Per-room override takes precedence over the global time program (SCHED-05).
        Global time program IS the per-day dict directly (D-01).
        """
        global_daily_program: dict = config["global_time_program"]
        room_configs: dict = config.get("rooms", {})

        # Wave 2: track global active period for status push.
        # Present persons are computed for status display even though presence does
        # not influence TRV temperatures in this mode.
        global_period_mode = evaluate_schedule(global_daily_program, now)
        self._last_active_period = global_period_mode
        self._last_present_persons = self._compute_present_persons(config, now)

        pushes: list[tuple[str, float]] = []
        room_periods: dict[str, str] = {}
        for area_id, entity_ids in rooms.items():
            room_config = room_configs.get(area_id, {})
            room_mode = room_config.get("room_mode", "global")

            # D-20: branch on room_mode before schedule evaluation
            if room_mode == ROOM_MODE_FROST:
                # Frost protection: push frost temp directly, skip schedule evaluation
                desired_temp = period_temperatures[PERIOD_FROST_PROTECTION]
                room_periods[area_id] = PERIOD_FROST_PROTECTION
            else:
                # Resolve daily_program: custom room program else global (per-day dict, D-01)
                if room_mode == ROOM_MODE_CUSTOM:
                    room_daily_program = room_config.get("time_program")
                    daily_program = room_daily_program if room_daily_program else global_daily_program
                else:
                    # ROOM_MODE_GLOBAL or unknown → use global (default path, no behavior change)
                    daily_program = global_daily_program

                period_mode = evaluate_schedule(daily_program, now)
                desired_temp = period_temperatures.get(period_mode)
                if desired_temp is None:
                    _LOGGER.warning(
                        "Unknown period mode %r for area %s — skipping", period_mode, area_id
                    )
                    continue
                room_periods[area_id] = period_mode

            pushes.extend((entity_id, desired_temp) for entity_id in entity_ids)

        self._last_room_periods = room_periods

        await asyncio.gather(*(
            self._push_safely(eid, temp, "MODE_TIME_PROGRAM")
            for eid, temp in pushes
        ))

    async def _evaluate_time_program_presences(
        self,
        now: datetime,
        config: dict,
        period_temperatures: dict[str, float],
        rooms: dict[str, list[str]],
    ) -> None:
        """Push temperatures for all rooms, applying presence overrides (MODE_TIME_PROGRAM_PRESENCES).

        Algorithm (Open Question 1 recommendation, D-07):
        1. Compute time-program desired_temp for every managed room (baseline).
        2. For each person, resolve presence; for their room_ids, override the
           desired_temp via compute_occupied_temp (PERSON-06/07/08/09).
        3. Present-person-wins rule: once a present person sets a room's temp,
           that room is locked — an absent person cannot lower it within this tick.
           Uses a separate set to track present-locked rooms, ensuring the rule is
           order-independent regardless of person iteration order.
        4. Push each room's final desired_temp to its TRVs.

        Global time program IS the per-day dict directly (D-01).
        """
        global_daily_program: dict = config["global_time_program"]
        room_configs: dict = config.get("rooms", {})
        persons_config: dict = config.get("persons", {})

        # Step 1: baseline — time-program temp for every managed room
        desired_temps: dict[str, float] = {}
        room_periods: dict[str, str] = {}
        # Rooms with room_mode=frost_protection are locked at frost temp and skipped
        # during presence override (Step 2) — track them separately.
        frost_locked_rooms: set[str] = set()
        for area_id in rooms:
            room_config = room_configs.get(area_id, {})
            room_mode = room_config.get("room_mode", "global")

            # D-20: branch on room_mode before schedule evaluation
            if room_mode == ROOM_MODE_FROST:
                # Frost protection: hold at frost temp, skip schedule evaluation and presence
                desired_temps[area_id] = period_temperatures[PERIOD_FROST_PROTECTION]
                room_periods[area_id] = PERIOD_FROST_PROTECTION
                frost_locked_rooms.add(area_id)
            else:
                if room_mode == ROOM_MODE_CUSTOM:
                    room_daily_program = room_config.get("time_program")
                    daily_program = room_daily_program if room_daily_program else global_daily_program
                else:
                    daily_program = global_daily_program

                period_mode = evaluate_schedule(daily_program, now)
                desired_temp_baseline = period_temperatures.get(period_mode)
                if desired_temp_baseline is None:
                    _LOGGER.warning(
                        "Unknown period mode %r for area %s — skipping", period_mode, area_id
                    )
                    continue
                desired_temps[area_id] = desired_temp_baseline
                room_periods[area_id] = period_mode

        # Wave 2: track global active period for status push
        global_period_mode = evaluate_schedule(global_daily_program, now)
        self._last_active_period = global_period_mode
        # present_persons list is built during person iteration below
        present_persons_this_tick: list[str] = []

        # Step 3 tracking: rooms locked by a present person — absent persons cannot
        # lower the temperature for these rooms within this tick.
        present_locked_rooms: set[str] = set()

        # Step 2: apply presence overrides per person
        for _person_id, person_config in persons_config.items():
            room_ids: list[str] = person_config.get("room_ids", [])
            if not room_ids:
                # D-07/D-08: no room associations → skip silently
                continue

            is_present = resolve_presence(person_config, now)
            if is_present:
                present_persons_this_tick.append(_person_id)

            for area_id in room_ids:
                if area_id not in rooms:
                    # Person references an area not managed by this integration
                    continue

                # D-20: skip frost-locked rooms — room_mode overrides presence
                if area_id in frost_locked_rooms:
                    continue

                # Resolve daily_program for this room respecting room_mode (per-day dict, D-01)
                room_config = room_configs.get(area_id, {})
                room_mode = room_config.get("room_mode", "global")
                if room_mode == ROOM_MODE_CUSTOM:
                    room_daily_program = room_config.get("time_program")
                    daily_program = room_daily_program if room_daily_program else global_daily_program
                else:
                    daily_program = global_daily_program

                occupied_temp, occupied_period = compute_occupied_temp(
                    daily_program, now, is_present, period_temperatures
                )

                # Step 3: present-person-wins rule — order-independent.
                if is_present:
                    # Present person: set the occupied-window temp and lock the room.
                    # If another present person previously set a higher temp, keep that.
                    if area_id in present_locked_rooms:
                        # Room already locked by a prior present person — take the max
                        if occupied_temp > desired_temps[area_id]:
                            desired_temps[area_id] = occupied_temp
                            room_periods[area_id] = occupied_period
                    else:
                        desired_temps[area_id] = occupied_temp
                        room_periods[area_id] = occupied_period
                        present_locked_rooms.add(area_id)
                else:
                    # Absent person: only lower the temperature if no present person
                    # has already locked this room in this tick.
                    if area_id not in present_locked_rooms:
                        desired_temps[area_id] = occupied_temp
                        room_periods[area_id] = occupied_period

        # Wave 2: store resolved present persons list and per-room periods for status push
        self._last_present_persons = present_persons_this_tick
        self._last_room_periods = room_periods

        # Step 4: push each room's resolved temperature to its TRVs (parallel)
        await asyncio.gather(*(
            self._push_safely(entity_id, desired_temps[area_id], "MODE_TIME_PROGRAM_PRESENCES")
            for area_id, entity_ids in rooms.items()
            for entity_id in entity_ids
            if area_id in desired_temps
        ))

    def _build_status_payload(self) -> dict:
        """Build the status dict pushed to subscribed panel connections after each evaluation.

        Used by the Wave 2 subscribe_status WS command and the hass.bus event.
        Includes rooms_status so the Rooms tab populates from push events.
        """
        from homeassistant.helpers import area_registry as ar  # noqa: PLC0415
        _area_reg = ar.async_get(self._hass)

        # D-24: pre-compute persons join data for present_person_count
        persons_config: dict = self._data.runtime_config.get("persons", {})
        present_set = set(self._last_present_persons)

        rooms_status = []
        for area_id, entity_ids in self._data.rooms.items():
            _area = _area_reg.async_get_area(area_id)
            room_entry: dict = {
                "area_id": area_id,
                "name": _area.name if _area else area_id,
                "active_period": self._last_room_periods.get(area_id, self._last_active_period),
                "entity_ids": entity_ids,
            }

            # D-24: count persons assigned to this area who are currently present
            room_entry["present_person_count"] = sum(
                1
                for person_id, person_config in persons_config.items()
                if area_id in person_config.get("room_ids", []) and person_id in present_set
            )

            auto = self._data.room_auto_sensors.get(area_id, {})

            # Temperature/humidity: HA area registry (HA 2026.5+) → auto-discovered → TRV built-in
            temp_sensor = getattr(_area, "temperature_entity_id", None) or auto.get("temperature")
            humidity_sensor = getattr(_area, "humidity_entity_id", None) or auto.get("humidity")
            if temp_sensor:
                sensor_state = self._hass.states.get(temp_sensor)
                if sensor_state is not None and sensor_state.state not in ("unavailable", "unknown"):
                    room_entry["temperature"] = sensor_state.state
            elif entity_ids:
                trv_state = self._hass.states.get(entity_ids[0])
                if trv_state is not None:
                    current_temp = trv_state.attributes.get("current_temperature")
                    if current_temp is not None:
                        room_entry["temperature"] = current_temp

            if humidity_sensor:
                hum_state = self._hass.states.get(humidity_sensor)
                if hum_state is not None and hum_state.state not in ("unavailable", "unknown"):
                    room_entry["humidity"] = hum_state.state

            rooms_status.append(room_entry)

        return {
            "global_mode": self._data.runtime_config["global_mode"],
            "active_period": self._last_active_period,
            "present_persons": self._last_present_persons,
            "rooms_status": rooms_status,
        }

    async def _push_safely(self, entity_id: str, desired_temp: float, context: str) -> None:
        """Wrapper around _push_if_changed that logs exceptions instead of propagating them."""
        try:
            await self._push_if_changed(entity_id, desired_temp)
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Failed to push temperature to %s in %s", entity_id, context)

    async def _push_if_changed(self, entity_id: str, desired_temp: float) -> None:
        """Push temperature to TRV only if it differs from the last pushed value.

        D-02: push-on-change — skip if already at desired temp (last == desired_temp).
        D-03: manual override hold — if TRV reports a temp different from last pushed,
              the user adjusted it manually → skip this tick. Hold lifts automatically
              at the next period transition (desired_temp will then differ from last).
        Pitfall 3: on startup last=None → override hold is bypassed, push always fires.
        Pitfall 6: reads attributes["temperature"] (setpoint), not the measured room temp.
        """
        # WR-02: guard against removed or unavailable entities — skip completely
        # to avoid repeated no-op service calls every minute.
        state = self._hass.states.get(entity_id)
        if state is None or state.state == "unavailable":
            return

        last = self._last_pushed.get(entity_id)

        # D-02: push-on-change — skip if already at desired temp
        if last is not None and last == desired_temp:
            return

        # D-03: manual override hold — only active when we have a prior push record
        if last is not None:
            # state is already fetched and confirmed non-None/non-unavailable above
            # ATTR_TEMPERATURE = "temperature" — the thermostat setpoint (Pitfall 6)
            reported = state.attributes.get("temperature")
            # Guard: reported may be None (TRV hasn't synced) or int (Pitfall 3)
            if reported is not None and float(reported) != last:
                # User adjusted manually — hold until next period transition
                return

        await set_trv_temperature(self._hass, entity_id, desired_temp)
        self._last_pushed[entity_id] = desired_temp
