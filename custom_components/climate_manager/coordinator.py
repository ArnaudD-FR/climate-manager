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

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
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
            for entity_ids in rooms.values():
                for entity_id in entity_ids:
                    try:
                        await self._push_if_changed(entity_id, desired_temp)
                    except Exception:  # noqa: BLE001
                        _LOGGER.warning(
                            "Failed to push temperature to %s in MODE_OFF", entity_id
                        )

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

    async def _evaluate_time_program(
        self,
        now: datetime,
        config: dict,
        period_temperatures: dict[str, float],
        rooms: dict[str, list[str]],
    ) -> None:
        """Push scheduled temperatures for all rooms (MODE_TIME_PROGRAM).

        Per-room override takes precedence over the global time program (SCHED-05).
        """
        global_weekday_groups = config["global_time_program"]["weekday_groups"]
        room_configs: dict = config.get("rooms", {})

        for area_id, entity_ids in rooms.items():
            # Resolve weekday_groups: room override else global
            room_weekday_groups = (
                room_configs.get(area_id, {})
                .get("time_program", {})
                .get("weekday_groups")
            )
            weekday_groups = room_weekday_groups if room_weekday_groups else global_weekday_groups

            period_mode = evaluate_schedule(weekday_groups, now)
            desired_temp = period_temperatures[period_mode]

            for entity_id in entity_ids:
                try:
                    await self._push_if_changed(entity_id, desired_temp)
                except Exception:  # noqa: BLE001
                    _LOGGER.warning(
                        "Failed to push temperature to %s in MODE_TIME_PROGRAM", entity_id
                    )

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
        3. Present-person-wins rule: if a room already has a warmer temperature
           from a present person, an absent person cannot lower it for this tick.
        4. Push each room's final desired_temp to its TRVs.
        """
        global_weekday_groups: list[dict] = config["global_time_program"]["weekday_groups"]
        room_configs: dict = config.get("rooms", {})
        persons_config: dict = config.get("persons", {})

        # Step 1: baseline — time-program temp for every managed room
        desired_temps: dict[str, float] = {}
        for area_id in rooms:
            room_weekday_groups = (
                room_configs.get(area_id, {})
                .get("time_program", {})
                .get("weekday_groups")
            )
            weekday_groups = room_weekday_groups if room_weekday_groups else global_weekday_groups
            period_mode = evaluate_schedule(weekday_groups, now)
            desired_temps[area_id] = period_temperatures[period_mode]

        # Step 2: apply presence overrides per person
        for person_id, person_config in persons_config.items():
            room_ids: list[str] = person_config.get("room_ids", [])
            if not room_ids:
                # D-07/D-08: no room associations → skip silently
                continue

            is_present = resolve_presence(person_config, now)

            for area_id in room_ids:
                if area_id not in rooms:
                    # Person references an area not managed by this integration
                    continue

                # Resolve weekday_groups for this room
                room_weekday_groups = (
                    room_configs.get(area_id, {})
                    .get("time_program", {})
                    .get("weekday_groups")
                )
                weekday_groups = (
                    room_weekday_groups if room_weekday_groups else global_weekday_groups
                )

                occupied_temp = compute_occupied_temp(
                    weekday_groups, now, is_present, period_temperatures
                )

                # Step 3: present-person-wins rule — a present person can only raise
                # the temperature, never let an absent person lower what a present
                # person already set for this room within this tick.
                if is_present:
                    # Present: override unconditionally (raise to occupied-window temp)
                    desired_temps[area_id] = occupied_temp
                else:
                    # Absent: only lower if no present person has already set a higher temp.
                    # Compare against current desired_temp: if it was already set by a
                    # present person (occupied_temp for absent is PERIOD_REDUCED), do not
                    # overwrite with the lower Reduced temperature.
                    current = desired_temps[area_id]
                    if occupied_temp < current:
                        # Check whether a present person could have set `current`:
                        # if current == time-program baseline, absent person may lower it.
                        # if current > time-program baseline, a present person raised it — hold.
                        room_weekday_groups2 = (
                            room_configs.get(area_id, {})
                            .get("time_program", {})
                            .get("weekday_groups")
                        )
                        wg2 = room_weekday_groups2 if room_weekday_groups2 else global_weekday_groups
                        period_mode2 = evaluate_schedule(wg2, now)
                        baseline = period_temperatures[period_mode2]
                        if current <= baseline:
                            # No present person has raised it yet — absent person can lower
                            desired_temps[area_id] = occupied_temp
                        # else: a present person raised it — keep the higher temp

        # Step 4: push each room's resolved temperature to its TRVs
        for area_id, entity_ids in rooms.items():
            desired_temp = desired_temps[area_id]
            for entity_id in entity_ids:
                try:
                    await self._push_if_changed(entity_id, desired_temp)
                except Exception:  # noqa: BLE001
                    _LOGGER.warning(
                        "Failed to push temperature to %s in MODE_TIME_PROGRAM_PRESENCES",
                        entity_id,
                    )

    async def _push_if_changed(self, entity_id: str, desired_temp: float) -> None:
        """Push temperature to TRV only if it differs from the last pushed value.

        D-02: push-on-change — skip if already at desired temp (last == desired_temp).
        D-03: manual override hold — if TRV reports a temp different from last pushed,
              the user adjusted it manually → skip this tick. Hold lifts automatically
              at the next period transition (desired_temp will then differ from last).
        Pitfall 3: on startup last=None → override hold is bypassed, push always fires.
        Pitfall 6: reads attributes["temperature"] (setpoint), not the measured room temp.
        """
        last = self._last_pushed.get(entity_id)

        # D-02: push-on-change — skip if already at desired temp
        if last is not None and last == desired_temp:
            return

        # D-03: manual override hold — only active when we have a prior push record
        if last is not None:
            state = self._hass.states.get(entity_id)
            if state is not None:
                # ATTR_TEMPERATURE = "temperature" — the thermostat setpoint (Pitfall 6)
                reported = state.attributes.get("temperature")
                # Guard: reported may be None (TRV hasn't synced) or int (Pitfall 3)
                if reported is not None and float(reported) != last:
                    # User adjusted manually — hold until next period transition
                    return

        await set_trv_temperature(self._hass, entity_id, desired_temp)
        self._last_pushed[entity_id] = desired_temp
