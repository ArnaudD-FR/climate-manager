# SPDX-License-Identifier: MIT
"""Climate Manager coordinator — the integration's control loop.

Evaluates each managed room independently against its zone (Default Zone or
custom zone) every minute and on HA startup, then pushes to TRVs only when
the target temperature changes.

Design decisions from CONTEXT.md / RESEARCH.md:
- D-01: Poll every minute via async_track_time_interval (caller registers this)
- D-02: Push-on-change only — _last_pushed dict tracks last pushed temp per entity
- D-03: Manual override hold — if TRV reports a temp different from last pushed,
         skip this entity this tick; hold lifts automatically at next period transition
- D-04: On HA restart _last_pushed is empty → startup push always fires (INFRA-03)
- D-07/D-08: global_mode is the Default Zone's mode — not a system-wide override.
         Rooms in custom zones follow their own zone's mode/schedule independently.
- D-09: Per-room algorithm: resolve zone → branch on zone.mode
- D-11: Presence evaluation for time_program_presences zones uses all configured
         persons (not scoped to zone members)

Requirements addressed:
- GLOBAL-01: Default Zone branches on global_mode (Off / Time program / Presences)
- GLOBAL-02: Default Zone MODE_OFF → frost protection; custom zones unaffected (D-08)
- GLOBAL-03: period_temperatures dict provides configurable temps per period mode
- SCHED-05: per-room time program override (room_mode=custom) wins over zone
            schedule when zone is active; zone MODE_OFF always overrides custom
- EVAL-01..05: per-zone independent evaluation via _resolve_zone_config
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
import statistics
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_PREHEAT_LEAD_MINUTES,
    DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
    PREHEAT_CONVERGENCE_THRESHOLD,
    PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD,
    PREHEAT_MAX_SAMPLES,
    PRESENCE_ABSENT,
    PRESENCE_CALENDAR,
    PRESENCE_HA,
    PRESENCE_PRESENT,
    ROOM_MODE_FROST,
    ROOM_MODE_CUSTOM,
)
from .schedule import (
    compute_occupied_temp,
    evaluate_schedule,
    next_occupied_at,
    next_setpoint_increase_at,
    resolve_calendar_presence,
    resolve_presence,
)
from .trv import (
    get_tado_valve_devices,
    is_trv_entity,
    set_trv_off,
    set_trv_offset,
    set_trv_offset_by_device,
    set_trv_temperature,
    supports_hvac_off,
    supports_offset_calibration,
)

if TYPE_CHECKING:
    from . import ClimateManagerData

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(minutes=1)
# Hardware-safe maximum for TRV temperature offset (±5°C for Tado X and most brands).
_OFFSET_CLAMP = 5.0


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
        # Widened to float | str to accommodate the "off" sentinel for off-capable TRVs.
        self._last_pushed: dict[str, float | str] = {}
        # Wave 2: track last evaluation results for status push and get_status WS command.
        self._last_active_period: str | None = None
        self._last_present_persons: list[str] = []
        # Per-room effective period (may differ from global in time_program_presences mode).
        self._last_room_periods: dict[str, str] = {}
        # Tracks when each TRV's offset was last changed by auto-calibration.
        self._calibration_last_changed: dict[str, str] = {}
        # Tracks the last delta applied per TRV (sensor_temp - current_temp).
        self._calibration_last_delta: dict[str, float] = {}
        # Tracks the last absolute offset written per Radiator Valve X device_id
        # (enables incremental adjustment — device doesn't expose current offset).
        self._calibration_last_offset: dict[str, float] = {}
        # Cancel callbacks for active ha-tracker watchers, keyed by notif_id.
        # One entry per person: person_state_cancel — dismisses the notification
        # immediately when device_trackers becomes non-empty again.
        # User dismissal is detected on the next tick by querying hass.data
        # directly (no event listener needed — more robust across HA versions).
        self._ha_tracker_listeners: dict[str, list] = {}
        # Per-cycle calendar event cache (D-13): maps entity_id → list of event
        # dicts. Reset at the start of every async_evaluate cycle. Never
        # persisted — populated fresh from calendar.get_events each cycle.
        self._calendar_cache: dict[str, list] = {}
        # D-04: tracks entity IDs for which the "unavailable" WARNING has
        # already been issued. Entry is added on first failure and removed
        # on the next successful fetch so the warning re-fires after recovery.
        self._calendar_warn_issued: set[str] = set()
        # Phase 12 pre-heat state (D-09, D-10).
        # _preheat_in_progress: active pre-heat entries per room.
        #   {area_id: {start_time: datetime, target_temp: float}}
        # _preheat_active: True while a pre-heat is in progress.
        # _preheat_target: temperature the room is pre-heating toward.
        # _preheat_suppressed: True when all persons are ha-mode (no schedule).
        # _frost_locked_rooms: snapshot from last _compute_desired_temps call
        #   (stored so _async_preheat_room can guard against it — T-12-03).
        self._preheat_in_progress: dict[str, dict] = {}
        self._preheat_active: dict[str, bool] = {}
        self._preheat_target: dict[str, float | None] = {}
        self._preheat_suppressed: dict[str, bool] = {}
        self._frost_locked_rooms: set[str] = set()

    async def async_evaluate(self, _utc_now: datetime | None = None) -> None:
        """Evaluate all managed rooms and push temperatures as needed.

        Each room is evaluated independently via _resolve_zone_config — there is no
        top-level global_mode branch. global_mode is the Default Zone's mode only (D-07/D-08).

        Called immediately after registration (INFRA-03 startup push) and then
        every minute by async_track_time_interval.

        The _utc_now argument is provided by async_track_time_interval but is
        deliberately ignored — it carries UTC time (Pitfall 2). Local wall-clock
        time is always derived from dt_util.now() (INFRA-05 / DST-safe).
        """
        now = dt_util.now()
        config = self._data.runtime_config
        period_temperatures: dict[str, float] = config["period_temperatures"]
        rooms: dict[str, list[str]] = self._data.rooms

        # D-13: reset cache each cycle, then prefetch all unique calendar
        # entity IDs referenced by persons or period states. This keeps the
        # async get_events call here (coordinator) and out of schedule.py
        # (D-05 — pure-Python contract maintained).
        self._calendar_cache = {}
        await self._prefetch_calendars(config, now)

        # Presence list computed once — used for PASS 2 and status reporting.
        self._last_present_persons = self._compute_present_persons(config, now)

        # Warn via persistent notification when an ha-mode person has no tracker.
        self._check_ha_tracker_warnings(config)

        desired_temps, room_periods, frost_locked_rooms, mode_off_rooms = (
            self._compute_desired_temps(config, rooms, period_temperatures, now)
        )
        # T-12-03: snapshot frost_locked_rooms for the pre-heat pass guard.
        self._frost_locked_rooms = frost_locked_rooms

        self._apply_presence_overrides(
            config,
            rooms,
            desired_temps,
            room_periods,
            frost_locked_rooms,
            period_temperatures,
            now,
        )

        self._last_room_periods = room_periods

        # Pitfall 7: _last_active_period reflects Default Zone for backward-compat.
        global_mode = config["global_mode"]
        self._last_active_period = (
            evaluate_schedule(config["global_time_program"], now)
            if global_mode != MODE_OFF
            else None
        )

        await self._push_temperatures(rooms, desired_temps, mode_off_rooms)

        # Calibration pass — D-01: runs after push pass.
        await self._async_calibrate(config)

        # Pre-heat pass (PREHEAT-02/03/04) — runs after calibrate so frost
        # lock state is stable; status fire AFTER so preheat_active is current.
        await self._async_preheat(config)

        # RESEARCH Open Question 1: fire status AFTER preheat pass so the
        # panel receives up-to-date preheat_active / preheat_suppressed in
        # the same cycle that triggered the preheat (avoids one-cycle lag).
        self._hass.bus.async_fire(
            f"{DOMAIN}_status_update",
            self._build_status_payload(),
        )

    async def _prefetch_calendars(self, config: dict, now: datetime) -> None:
        """Fetch get_events for all unique calendar entity IDs in config.

        Populates self._calendar_cache (entity_id → list of event dicts).
        Called at the top of each async_evaluate cycle after the cache reset.

        D-13: one get_events call per unique entity_id per cycle (dedup via
        set). D-04: HomeAssistantError → WARNING issued once per unavailable
        entity (suppressed on subsequent failures; re-fires after recovery).
        Empty-list fallback keeps the person as absent. D-05: keeps async
        HA service call here (coordinator) so schedule.py stays pure Python.

        Security — T-11-03: entity_id must start with 'calendar.' before
        being used as a service target (ASVS V5 input validation).
        """
        entity_ids: set[str] = set()

        for person_config in config.get("persons", {}).values():
            # Calendar-mode persons: read entity_id from calendar_config
            if person_config.get("mode") == PRESENCE_CALENDAR:
                eid = (person_config.get("calendar_config") or {}).get(
                    "entity_id"
                )
                if eid and eid.startswith("calendar."):
                    entity_ids.add(eid)

            # Scheduled-mode persons: scan periods for state="calendar"
            for schedule_key in (
                "schedule",
                "schedule_even",
                "schedule_odd",
            ):
                for day_periods in (
                    person_config.get(schedule_key) or {}
                ).values():
                    for period in day_periods:
                        if period.get("state") == "calendar":
                            eid = (period.get("calendar_config") or {}).get(
                                "entity_id"
                            )
                            if eid and eid.startswith("calendar."):
                                entity_ids.add(eid)

        async def _fetch_one(eid: str) -> None:
            """Fetch events for one entity and store in _calendar_cache."""
            try:
                result = await self._hass.services.async_call(
                    "calendar",
                    "get_events",
                    service_data={
                        "start_date_time": now,
                        "end_date_time": now + timedelta(hours=24),
                    },
                    target={"entity_id": eid},
                    blocking=True,
                    return_response=True,
                )
                # Landmine 2: entity service response is keyed by entity_id
                events = (result or {}).get(eid, {}).get("events", [])
                self._calendar_cache[eid] = events
                # D-04: clear warn-issued flag so the warning re-fires if
                # the entity becomes unavailable again after recovery.
                self._calendar_warn_issued.discard(eid)
            except HomeAssistantError:
                # D-04: log WARNING once per unavailable entity; suppress
                # repeated failures to avoid log spam (one WARNING per minute
                # with a 1-minute poll interval). Re-fires after recovery.
                if eid not in self._calendar_warn_issued:
                    _LOGGER.warning(
                        "Calendar entity %s unavailable — falling back to"
                        " absent (further failures will be suppressed"
                        " until recovery)",
                        eid,
                    )
                    self._calendar_warn_issued.add(eid)
                self._calendar_cache[eid] = []

        await asyncio.gather(*[_fetch_one(eid) for eid in entity_ids])

    def _compute_desired_temps(
        self,
        config: dict,
        rooms: dict[str, list[str]],
        period_temperatures: dict[str, float],
        now: datetime,
    ) -> tuple[dict[str, float], dict[str, str], set[str], set[str]]:
        """PASS 1 — baseline temperature per room.

        Returns (desired_temps, room_periods, frost_locked_rooms, mode_off_rooms).

        Priority order (highest to lowest):
        1. frost_protection room_mode — wins unconditionally (EVAL-05 / D-20)
        2. Zone MODE_OFF — always overrides, even custom room schedules (EVAL-01)
        3. Custom room schedule (room_mode=custom) — wins over zone schedule
           when the zone is active (SCHED-05 / EVAL-05)
        4. Zone schedule (time_program / time_program_presences) — baseline
        """
        desired_temps: dict[str, float] = {}
        room_periods: dict[str, str] = {}
        frost_locked_rooms: set[str] = set()
        mode_off_rooms: set[str] = set()

        for area_id in rooms:
            room_config = config.get("rooms", {}).get(area_id, {})
            room_mode = room_config.get("room_mode", "global")

            if room_mode == ROOM_MODE_FROST:
                # EVAL-05 / D-20: frost_protection room_mode wins unconditionally
                desired_temps[area_id] = period_temperatures[
                    PERIOD_FROST_PROTECTION
                ]
                room_periods[area_id] = PERIOD_FROST_PROTECTION
                frost_locked_rooms.add(area_id)
                mode_off_rooms.add(area_id)
                continue

            # Resolve zone mode for this room — needed for both custom and
            # global room modes (EVAL-01: zone OFF always wins).
            zone_mode, zone_time_program = self._resolve_zone_config(
                area_id, config
            )

            if zone_mode == MODE_OFF:
                # EVAL-01: zone off → frost protection for all rooms in the
                # zone, including those with a custom schedule (SCHED-05 only
                # overrides the schedule selection, not the zone power state).
                desired_temps[area_id] = period_temperatures[
                    PERIOD_FROST_PROTECTION
                ]
                room_periods[area_id] = PERIOD_FROST_PROTECTION
                frost_locked_rooms.add(area_id)
                mode_off_rooms.add(area_id)
                continue

            if room_mode == ROOM_MODE_CUSTOM:
                # EVAL-05 / SCHED-05: custom room schedule wins over the zone
                # schedule when the zone is active (zone OFF is handled above).
                room_program = (
                    room_config.get("time_program")
                    or config["global_time_program"]
                )
                period_mode = evaluate_schedule(room_program, now)
                temp = period_temperatures.get(period_mode)
                if temp is None:
                    _LOGGER.warning(
                        "Unknown period mode %r for area %s — skipping",
                        period_mode,
                        area_id,
                    )
                    continue
                desired_temps[area_id] = temp
                room_periods[area_id] = period_mode
                continue

            # Room follows its zone schedule (D-09)
            if zone_mode in (MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES):
                # EVAL-02 baseline (or EVAL-03 baseline before PASS 2)
                period_mode = evaluate_schedule(zone_time_program, now)
                temp = period_temperatures.get(period_mode)
                if temp is None:
                    _LOGGER.warning(
                        "Unknown period mode %r for area %s — skipping",
                        period_mode,
                        area_id,
                    )
                    continue
                desired_temps[area_id] = temp
                room_periods[area_id] = period_mode

            else:
                _LOGGER.warning(
                    "Unknown zone_mode %r for area %s — skipping",
                    zone_mode,
                    area_id,
                )

        return desired_temps, room_periods, frost_locked_rooms, mode_off_rooms

    def _apply_presence_overrides(
        self,
        config: dict,
        rooms: dict[str, list[str]],
        desired_temps: dict[str, float],
        room_periods: dict[str, str],
        frost_locked_rooms: set[str],
        period_temperatures: dict[str, float],
        now: datetime,
    ) -> None:
        """PASS 2 — presence override for time_program_presences zones (EVAL-03).

        Mutates desired_temps and room_periods in place.
        All configured persons are considered — not scoped to zone members (D-11).
        """
        present_locked_rooms: set[str] = set()

        for _person_id, person_config in config.get("persons", {}).items():
            room_ids: list[str] = person_config.get("room_ids", [])
            if not room_ids:
                continue

            # Landmine 5: _apply_presence_overrides also drives room temps —
            # must resolve presence the same way as _compute_present_persons
            # so calendar-mode persons and calendar period states are consistent.
            if person_config.get("mode") == PRESENCE_HA:
                state_obj = self._hass.states.get(_person_id)
                is_present = state_obj is not None and state_obj.state == "home"
            elif person_config.get("mode") == PRESENCE_CALENDAR:
                cal_cfg = person_config.get("calendar_config") or {}
                eid = cal_cfg.get("entity_id", "")
                events = self._calendar_cache.get(eid, [])
                # D-02: read wakeup_advance_minutes (renamed from
                # preheat_lead_minutes); fallback chain supports both old
                # and new key names during migration window.
                preheat = person_config.get(
                    "wakeup_advance_minutes",
                    person_config.get(
                        "preheat_lead_minutes",
                        DEFAULT_PREHEAT_LEAD_MINUTES,
                    ),
                )
                is_present = resolve_calendar_presence(
                    events,
                    cal_cfg.get("event_means", "absent"),
                    now,
                    gap_handling=cal_cfg.get("gap_handling", "exact"),
                    gap_threshold_minutes=cal_cfg.get(
                        "gap_threshold_minutes", 0
                    ),
                    preheat_lead_minutes=preheat,
                    start_of_local_day=dt_util.start_of_local_day,
                )
            else:
                is_present = resolve_presence(
                    person_config,
                    now,
                    calendar_cache=self._calendar_cache,
                    start_of_local_day=dt_util.start_of_local_day,
                )

            for area_id in room_ids:
                if area_id not in rooms:
                    continue
                if area_id in frost_locked_rooms:
                    # frost / zone.mode=off — presence cannot raise
                    continue

                room_config = config.get("rooms", {}).get(area_id, {})
                if room_config.get("room_mode", "global") == ROOM_MODE_CUSTOM:
                    # Custom room schedule wins; preserved v1.0 behavior
                    continue

                # Presence override applies only when zone mode is time_program_presences
                zone_mode_for_room, zone_program_for_room = (
                    self._resolve_zone_config(area_id, config)
                )
                if zone_mode_for_room != MODE_TIME_PROGRAM_PRESENCES:
                    continue

                occupied_temp, occupied_period = compute_occupied_temp(
                    zone_program_for_room,
                    now,
                    is_present,
                    period_temperatures,
                )

                if is_present:
                    if area_id in present_locked_rooms:
                        if occupied_temp > desired_temps.get(area_id, 0):
                            desired_temps[area_id] = occupied_temp
                            room_periods[area_id] = occupied_period
                    else:
                        desired_temps[area_id] = occupied_temp
                        room_periods[area_id] = occupied_period
                        present_locked_rooms.add(area_id)
                else:
                    if area_id not in present_locked_rooms:
                        desired_temps[area_id] = occupied_temp
                        room_periods[area_id] = occupied_period

    async def _push_temperatures(
        self,
        rooms: dict[str, list[str]],
        desired_temps: dict[str, float],
        mode_off_rooms: set[str],
    ) -> None:
        """Push pass — off-capable TRVs in mode_off_rooms use _push_off_safely."""
        await asyncio.gather(
            *(
                (
                    self._push_off_safely(entity_id, desired_temps[area_id])
                    if supports_hvac_off(self._hass, entity_id)
                    else self._push_safely(
                        entity_id, desired_temps[area_id], "ZONE_EVAL_OFF"
                    )
                )
                if area_id in mode_off_rooms
                else self._push_safely(
                    entity_id, desired_temps[area_id], "ZONE_EVAL"
                )
                for area_id, entity_ids in rooms.items()
                for entity_id in entity_ids
                if area_id in desired_temps
                and is_trv_entity(self._hass, entity_id)
            )
        )

    async def _async_preheat(self, config: dict) -> None:
        """Pre-heat pass — trigger early heating for enabled rooms (PREHEAT-02/03).

        Mirrors _async_calibrate: concurrent gather over all rooms, each room
        handled by _async_preheat_room. Each room persists its own sample on
        convergence (T-12-05 — bounded write rate; save only when a sample
        is added).
        """
        rooms = self._data.rooms
        now = dt_util.now()
        tasks = [
            self._async_preheat_room(area_id, config, now) for area_id in rooms
        ]
        await asyncio.gather(*tasks)

    async def _async_preheat_room(
        self,
        area_id: str,
        config: dict,
        now: datetime,
    ) -> None:
        """Pre-heat logic for a single room (D-04, D-07, D-08, D-09).

        Guard order (D-09):
        1. If not preheat_enabled → clear state and return.
        2. CONVERGENCE check: in-progress entry exists and TRV
           current_temperature has reached target → record sample.
        3. DISCARD check: in-progress entry exists and now >= next_occupied
           (or no next_occupied) → discard without recording.
        4. TRIGGER: compute next_occupied_at (earliest non-None across
           assigned persons), determine learned lead, fire set_temperature
           if inside the lead window and room is not already warm
           (T-12-03: skip if frost-locked).

        Security T-12-03: _frost_locked_rooms checked before any
        set_temperature call.
        """
        room_config = (config.get("rooms") or {}).get(area_id, {})
        # GAP-01: preheat_enabled moved from per-room to per-zone scope.
        # Rooms with no zone_id read default_zone_preheat_enabled (Option A).
        # Dangling zone_id falls back identically (defense-in-depth, T-12-12).
        zone_id = room_config.get("zone_id")
        if zone_id is None:
            preheat_enabled = config.get("default_zone_preheat_enabled", False)
        else:
            zone = config.get("zones", {}).get(zone_id)
            if zone is None:
                preheat_enabled = config.get(
                    "default_zone_preheat_enabled", False
                )
            else:
                preheat_enabled = zone.get("preheat_enabled", False)

        if not preheat_enabled:
            self._preheat_active[area_id] = False
            self._preheat_suppressed[area_id] = False
            self._preheat_in_progress.pop(area_id, None)
            return

        preheat_max_lead = room_config.get(
            "preheat_max_lead_minutes", DEFAULT_PREHEAT_MAX_LEAD_MINUTES
        )

        # Read current_temperature from the first TRV in the room.
        # Pitfall 5: use attributes["current_temperature"] (measured temp),
        # NOT attributes["temperature"] (setpoint).
        entity_ids = self._data.rooms.get(area_id, [])
        trv_entity_id: str | None = next(
            (eid for eid in entity_ids if is_trv_entity(self._hass, eid)),
            None,
        )
        current_temp: float | None = None
        if trv_entity_id:
            state = self._hass.states.get(trv_entity_id)
            if state is not None and state.state not in (
                "unavailable",
                "unknown",
            ):
                raw = state.attributes.get("current_temperature")
                if raw is not None:
                    try:
                        current_temp = float(raw)
                    except (ValueError, TypeError):
                        pass

        # ----------------------------------------------------------------
        # Step 1: CONVERGENCE check (D-09)
        # ----------------------------------------------------------------
        in_progress = self._preheat_in_progress.get(area_id)
        if in_progress is not None and current_temp is not None:
            target_temp: float = in_progress["target_temp"]
            if current_temp >= target_temp - PREHEAT_CONVERGENCE_THRESHOLD:
                # Target reached — record valid sample (D-07).
                # WR-03: skip zero-duration samples (same-tick convergence)
                # to avoid biasing the learned-lead average toward zero.
                start_time: datetime = in_progress["start_time"]
                duration_min = int((now - start_time).total_seconds() / 60)
                if duration_min < 1:
                    del self._preheat_in_progress[area_id]
                    return
                samples = self._data.preheat_samples.setdefault(area_id, [])
                samples.append(
                    {
                        "duration_minutes": duration_min,
                        "timestamp": now.isoformat(),
                    }
                )
                # Keep only last PREHEAT_MAX_SAMPLES (D-06)
                if len(samples) > PREHEAT_MAX_SAMPLES:
                    self._data.preheat_samples[area_id] = samples[
                        -PREHEAT_MAX_SAMPLES:
                    ]
                del self._preheat_in_progress[area_id]
                self._preheat_active[area_id] = False
                # Persist on sample change (T-12-05 — bounded write rate).
                if self._data.preheat_store is not None:
                    await self._data.preheat_store.async_save(
                        self._data.preheat_samples
                    )
                # Return; trigger logic not needed this cycle.
                return

        # ----------------------------------------------------------------
        # Step 2: compute trigger time.
        #
        # Priority: if any assigned person is currently absent AND has a
        # predictable schedule, use their earliest next arrival. This ensures
        # pre-heat fires just before the person comes home, not at an arbitrary
        # zone period boundary (e.g. Lucie absent until 18:00 → trigger at 16:00
        # with 120 min lead, not at the 11:30 Comfort boundary).
        #
        # Fallback: when all persons are already present or have unpredictable
        # modes (HA / force), use next_setpoint_increase_at from the zone
        # program — the room is occupied so heat based on schedule.
        # ----------------------------------------------------------------
        persons_cfg_step2: dict = config.get("persons", {})
        assigned_step2 = [
            pc
            for pc in persons_cfg_step2.values()
            if area_id in pc.get("room_ids", [])
        ]
        unpredictable = {PRESENCE_HA, PRESENCE_PRESENT, PRESENCE_ABSENT}

        next_arrival: datetime | None = None
        for pc in assigned_step2:
            if pc.get("mode") in unpredictable:
                continue
            currently_present = resolve_presence(
                pc, now, self._calendar_cache, dt_util.start_of_local_day
            )
            if currently_present:
                continue  # already home — no arrival to pre-heat for
            candidate = next_occupied_at(
                pc, now, self._calendar_cache, dt_util.start_of_local_day
            )
            if candidate is not None:
                if next_arrival is None or candidate < next_arrival:
                    next_arrival = candidate

        room_cfg_step2 = config.get("rooms", {}).get(area_id, {})
        if room_cfg_step2.get("room_mode") == ROOM_MODE_CUSTOM:
            tp_step2 = room_cfg_step2.get("time_program") or config.get(
                "global_time_program", {}
            )
        else:
            _, tp_step2 = self._resolve_zone_config(area_id, config)
        period_temperatures_step2: dict[str, float] = config.get(
            "period_temperatures", {}
        )

        if next_arrival is not None:
            next_occupied: datetime | None = next_arrival
        else:
            next_occupied = next_setpoint_increase_at(
                tp_step2, period_temperatures_step2, now
            )

        # ----------------------------------------------------------------
        # Step 3: DISCARD check (D-07 / D-09)
        # ----------------------------------------------------------------
        in_progress = self._preheat_in_progress.get(area_id)
        if in_progress is not None:
            if next_occupied is None or now >= next_occupied:
                # Period started before convergence → discard (D-07)
                del self._preheat_in_progress[area_id]
                self._preheat_active[area_id] = False
                # Fall through to suppressed/inactive reporting below

        # ----------------------------------------------------------------
        # Step 4: TRIGGER (D-08, T-12-03)
        # ----------------------------------------------------------------
        # Suppressed when no higher-temp period exists in the 7-day lookahead,
        # OR when the zone is in time_program_presences mode and every assigned
        # person is unpredictable (HA / force_present / force_absent) — in that
        # mode, heating depends on presence, and we can't predict arrival.
        zone_mode_ph, _ = self._resolve_zone_config(area_id, config)
        persons_config: dict = config.get("persons", {})
        assigned_persons = [
            pc
            for pc in persons_config.values()
            if area_id in pc.get("room_ids", [])
        ]
        unpredictable_modes = {PRESENCE_HA, PRESENCE_PRESENT, PRESENCE_ABSENT}
        presence_suppressed = (
            zone_mode_ph == MODE_TIME_PROGRAM_PRESENCES
            and bool(assigned_persons)
            and all(
                pc.get("mode") in unpredictable_modes for pc in assigned_persons
            )
        )
        self._preheat_suppressed[area_id] = (
            next_occupied is None or presence_suppressed
        )

        if (
            next_occupied is None
            or presence_suppressed
            or area_id in self._frost_locked_rooms
        ):
            self._preheat_active[area_id] = False
            return

        # D-08: compute learned lead. Bootstrap (< threshold samples) uses
        # preheat_max_lead so the user-configured cap is respected from the
        # first cycle. DEFAULT_PREHEAT_LEAD_MINUTES is only the fallback when
        # no preheat_max_lead_minutes is configured at all.
        samples = self._data.preheat_samples.get(area_id, [])
        if len(samples) >= PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD:
            avg = statistics.mean(s["duration_minutes"] for s in samples)
            learned_lead = min(avg, preheat_max_lead)
        else:
            learned_lead = preheat_max_lead

        trigger_start = next_occupied - timedelta(minutes=learned_lead)

        if not (trigger_start <= now < next_occupied):
            # Outside lead window
            self._preheat_active[area_id] = False
            return

        # Determine the upcoming setpoint (the period's temperature at
        # next_occupied). CR-02: for room_mode=custom rooms, use the room's
        # own time_program rather than the zone program so the pre-heat target
        # matches what _compute_desired_temps will push after the period starts.
        room_cfg = config.get("rooms", {}).get(area_id, {})
        if room_cfg.get("room_mode") == ROOM_MODE_CUSTOM:
            time_program = room_cfg.get("time_program") or config.get(
                "global_time_program", {}
            )
        else:
            _, time_program = self._resolve_zone_config(area_id, config)
        period_temperatures: dict[str, float] = config.get(
            "period_temperatures", {}
        )
        upcoming_period = evaluate_schedule(time_program, next_occupied)
        upcoming_setpoint = period_temperatures.get(upcoming_period)
        if upcoming_setpoint is None:
            self._preheat_active[area_id] = False
            return

        # Guard: if room already warm, no need to pre-heat
        if (
            current_temp is not None
            and current_temp
            >= upcoming_setpoint - PREHEAT_CONVERGENCE_THRESHOLD
        ):
            self._preheat_active[area_id] = False
            return

        # Fire set_temperature for all TRVs in the room
        if area_id not in self._preheat_in_progress:
            for entity_id in entity_ids:
                if is_trv_entity(self._hass, entity_id):
                    await self._push_safely(
                        entity_id,
                        upcoming_setpoint,
                        "PREHEAT",
                    )
            self._preheat_in_progress[area_id] = {
                "start_time": now,
                "target_temp": upcoming_setpoint,
            }

        self._preheat_active[area_id] = True
        self._preheat_target[area_id] = upcoming_setpoint

    async def _async_calibrate(self, config: dict) -> None:
        """Offset-calibrate all compatible TRVs toward their room sensors.

        For rooms with Tado X Radiator Valve X devices, calibration is
        device_id-based (tado_x.set_temperature_offset takes device_id).
        For other rooms, entity-based calibration is used as before.

        D-04: Returns immediately when calibration_enabled is False.
        D-03: Concurrent gather over all rooms, same pattern as push pass.
        """
        if not config.get("calibration_enabled", False):
            return
        from homeassistant.helpers import area_registry as ar  # noqa: PLC0415

        area_reg = ar.async_get(self._hass)
        rooms = self._data.rooms
        tasks = []
        for area_id, entity_ids in rooms.items():
            # Resolve room sensor: area registry (HA 2026.5+) → auto-discovered
            # → rooms_config explicit override (used in tests and manual config)
            _area = area_reg.async_get_area(area_id)
            sensor_entity_id = (
                getattr(_area, "temperature_entity_id", None)
                or self._data.room_auto_sensors.get(area_id, {}).get(
                    "temperature"
                )
                or config.get("rooms", {})
                .get(area_id, {})
                .get("temperature_sensor")
            )
            valve_devices = get_tado_valve_devices(self._hass, area_id)
            if valve_devices:
                # Find zone climate entity for temperature reading
                zone_entity = next(
                    (
                        eid
                        for eid in entity_ids
                        if is_trv_entity(self._hass, eid)
                    ),
                    None,
                )
                for device in valve_devices:
                    tasks.append(
                        self._async_calibrate_tado_device(
                            area_id,
                            device["device_id"],
                            zone_entity,
                            sensor_entity_id,
                            config,
                        )
                    )
            else:
                for entity_id in entity_ids:
                    if is_trv_entity(self._hass, entity_id):
                        tasks.append(
                            self._async_calibrate_room(
                                area_id, entity_id, sensor_entity_id, config
                            )
                        )
        await asyncio.gather(*tasks)

    async def _async_calibrate_tado_device(
        self,
        area_id: str,
        device_id: str,
        zone_entity_id: str | None,
        sensor_entity_id: str | None,
        config: dict,
    ) -> None:
        """Calibrate one Tado X Radiator Valve X device toward its room sensor.

        Uses device_id for the offset call (tado_x service requirement) and
        zone_entity_id for temperature reading (no per-TRV temp entity).
        Tracks offset increments in _calibration_last_offset so successive
        calls accumulate correctly despite the device not exposing its offset.
        """
        if not sensor_entity_id or not zone_entity_id:
            return

        state = self._hass.states.get(zone_entity_id)
        if state is None or state.state == "unavailable":
            return

        sensor_state = self._hass.states.get(sensor_entity_id)
        if sensor_state is None or sensor_state.state in (
            "unavailable",
            "unknown",
        ):
            return
        try:
            sensor_temp = float(sensor_state.state)
        except (ValueError, TypeError):
            return

        current_temp = state.attributes.get("current_temperature")
        if current_temp is None:
            return
        try:
            current_temp = float(current_temp)
        except (ValueError, TypeError):
            return

        delta = sensor_temp - current_temp
        threshold = config.get("calibration_threshold", 0.5)
        if abs(delta) <= threshold:
            return

        existing_offset = self._calibration_last_offset.get(device_id, 0.0)
        new_offset = round(
            max(-_OFFSET_CLAMP, min(_OFFSET_CLAMP, existing_offset + delta)),
            1,
        )

        try:
            await set_trv_offset_by_device(self._hass, device_id, new_offset)
            self._calibration_last_offset[device_id] = new_offset
            self._calibration_last_changed[device_id] = datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds")
            self._calibration_last_delta[device_id] = round(delta, 2)
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to apply offset %.1f to device %s",
                new_offset,
                device_id,
            )

    async def _async_calibrate_room(
        self,
        area_id: str,
        entity_id: str,
        sensor_entity_id: str | None,
        config: dict,
    ) -> None:
        """Calibrate one TRV toward its room's reference sensor.

        Silently returns when any guard condition fails (CALIB-03/05, D-07/08,
        Pitfalls 2/5).
        """
        if not sensor_entity_id:
            return

        # CALIB-03, D-08: capability guard (attribute-first)
        if not supports_offset_calibration(self._hass, entity_id):
            return

        # ROOM-03 parity: unavailable TRV
        state = self._hass.states.get(entity_id)
        if state is None or state.state == "unavailable":
            return

        # Pitfall 5: sensor state guard — catches "unavailable"/"unknown"
        sensor_state = self._hass.states.get(sensor_entity_id)
        if sensor_state is None or sensor_state.state in (
            "unavailable",
            "unknown",
        ):
            return
        try:
            sensor_temp = float(sensor_state.state)
        except (ValueError, TypeError):
            return

        # Pitfall 2: current_temperature may be None on startup
        current_temp = state.attributes.get("current_temperature")
        if current_temp is None:
            return
        try:
            current_temp = float(current_temp)
        except (ValueError, TypeError):
            return

        # D-05: delta formula
        delta = sensor_temp - current_temp

        # D-07: jitter guard
        threshold = config.get("calibration_threshold", 0.5)
        if abs(delta) <= threshold:
            return

        # D-06: incremental offset
        try:
            existing_offset = float(
                state.attributes.get("temperature_offset", 0.0)
            )
        except (ValueError, TypeError):
            existing_offset = 0.0
        new_offset = max(
            -_OFFSET_CLAMP, min(_OFFSET_CLAMP, existing_offset + delta)
        )

        try:
            await set_trv_offset(self._hass, entity_id, new_offset)
            self._calibration_last_changed[entity_id] = datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds")
            self._calibration_last_delta[entity_id] = round(delta, 2)
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to apply offset %.1f to %s", new_offset, entity_id
            )

    def _resolve_zone_config(
        self, area_id: str, config: dict
    ) -> tuple[str, dict]:
        """Return (mode, time_program) for a room based on its zone assignment.

        Rooms without a zone_id belong to the Default Zone (global_mode / global_time_program).
        Rooms with a dangling zone_id (zone deleted but room not updated) fall back to
        the Default Zone with a warning — defense in depth alongside validate_zone_assignment.
        """
        zone_id = config.get("rooms", {}).get(area_id, {}).get("zone_id")
        if zone_id is None:
            return (config["global_mode"], config["global_time_program"])
        zone = config.get("zones", {}).get(zone_id)
        if zone is None:
            _LOGGER.warning(
                "Room %s has unknown zone_id %r — using Default Zone",
                area_id,
                zone_id,
            )
            return (config["global_mode"], config["global_time_program"])
        return (zone["mode"], zone["time_program"])

    def _compute_present_persons(
        self, config: dict, now: datetime
    ) -> list[str]:
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
            elif person_config.get("mode") == PRESENCE_CALENDAR:
                # CAL-01: calendar-mode — resolve from prefetched cache (D-05)
                cal_cfg = person_config.get("calendar_config") or {}
                eid = cal_cfg.get("entity_id", "")
                events = self._calendar_cache.get(eid, [])
                # D-02: read wakeup_advance_minutes (renamed from
                # preheat_lead_minutes); fallback chain supports both old
                # and new key names during migration window.
                preheat = person_config.get(
                    "wakeup_advance_minutes",
                    person_config.get(
                        "preheat_lead_minutes",
                        DEFAULT_PREHEAT_LEAD_MINUTES,
                    ),
                )
                if resolve_calendar_presence(
                    events,
                    cal_cfg.get("event_means", "absent"),
                    now,
                    gap_handling=cal_cfg.get("gap_handling", "exact"),
                    gap_threshold_minutes=cal_cfg.get(
                        "gap_threshold_minutes", 0
                    ),
                    preheat_lead_minutes=preheat,
                    start_of_local_day=dt_util.start_of_local_day,
                ):
                    present.append(person_id)
            else:
                # scheduled, force_present, force_absent, or unknown →
                # delegate to resolve_presence; pass calendar_cache so period
                # state "calendar" periods resolve correctly (D-05, Landmine 5)
                if resolve_presence(
                    person_config,
                    now,
                    calendar_cache=self._calendar_cache,
                    start_of_local_day=dt_util.start_of_local_day,
                ):
                    present.append(person_id)
        return present

    def _dismiss_ha_tracker_notif(self, notif_id: str) -> None:
        """Cancel the tracker-restored watcher and dismiss the notification."""
        from homeassistant.components.persistent_notification import (  # noqa: PLC0415
            async_dismiss,
        )

        for cancel in self._ha_tracker_listeners.pop(notif_id, []):
            cancel()
        async_dismiss(self._hass, notif_id)

    def _check_ha_tracker_warnings(self, config: dict) -> None:
        """Create or dismiss persistent notifications for ha-mode persons.

        Runs on every tick. Notification existence is checked directly against
        hass.data["persistent_notification"] so user dismissals are detected
        on the next tick (≤1 min) and the notification is recreated — no event
        listener needed for dismissal detection.

        Tracker restoration: immediate via a per-person state-change listener
        registered once when the notification is first shown.
        """
        from homeassistant.components.persistent_notification import (  # noqa: PLC0415
            async_create,
        )
        from homeassistant.helpers.event import (  # noqa: PLC0415
            async_track_state_change_event,
        )

        pn_data = self._hass.data.get("persistent_notification", {})

        for person_id, person_cfg in config.get("persons", {}).items():
            notif_id = f"{DOMAIN}_ha_no_tracker_{person_id.replace('.', '_')}"
            mode_is_ha = person_cfg.get("mode") == PRESENCE_HA
            state_obj = self._hass.states.get(person_id)
            trackers = (
                state_obj.attributes.get("device_trackers", [])
                if state_obj is not None
                else []
            )
            has_trackers = isinstance(trackers, list) and len(trackers) > 0
            should_notify = mode_is_ha and not has_trackers

            if not should_notify:
                # Dismiss if shown and cancel any watcher.
                if isinstance(pn_data, dict) and notif_id in pn_data:
                    self._dismiss_ha_tracker_notif(notif_id)
                elif notif_id in self._ha_tracker_listeners:
                    for cancel in self._ha_tracker_listeners.pop(notif_id):
                        cancel()
                continue

            # Create or recreate when user dismissed (not in pn_data anymore).
            notif_present = isinstance(pn_data, dict) and notif_id in pn_data
            if not notif_present:
                name = (
                    state_obj.attributes.get("friendly_name", person_id)
                    if state_obj is not None
                    else person_id
                )
                slug = person_id.removeprefix("person.")
                async_create(
                    self._hass,
                    (
                        f"**{name}** is set to *HA home tracking* but has no "
                        f"device tracker linked in Home Assistant. Presence "
                        f"detection will not work until a device tracker is "
                        f"added.\n\n"
                        f"[Edit {name} in HA](/config/person/edit/{slug})"
                    ),
                    title="Climate Manager — HA Tracking",
                    notification_id=notif_id,
                )

            # Register the tracker-restored watcher only once per person.
            if notif_id not in self._ha_tracker_listeners:

                @callback
                def _on_tracker_restored(
                    event: object,
                    _notif_id: str = notif_id,
                ) -> None:
                    new_state = getattr(event, "data", {}).get("new_state")
                    if new_state is None:
                        return
                    t = new_state.attributes.get("device_trackers", [])
                    if isinstance(t, list) and len(t) > 0:
                        self._dismiss_ha_tracker_notif(_notif_id)

                self._ha_tracker_listeners[notif_id] = [
                    async_track_state_change_event(
                        self._hass, person_id, _on_tracker_restored
                    ),
                ]

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
                "active_period": self._last_room_periods.get(
                    area_id, self._last_active_period
                ),
                "entity_ids": entity_ids,
            }

            # D-24: count persons assigned to this area who are currently present
            room_entry["present_person_count"] = sum(
                1
                for person_id, person_config in persons_config.items()
                if area_id in person_config.get("room_ids", [])
                and person_id in present_set
            )

            # D-10 / PREHEAT-04: per-room pre-heat status fields.
            room_entry["preheat_active"] = self._preheat_active.get(
                area_id, False
            )
            room_entry["preheat_target"] = self._preheat_target.get(
                area_id, None
            )
            room_entry["preheat_suppressed"] = self._preheat_suppressed.get(
                area_id, False
            )

            auto = self._data.room_auto_sensors.get(area_id, {})

            # Temperature/humidity: HA area registry (HA 2026.5+) → auto-discovered → TRV built-in
            temp_sensor = getattr(
                _area, "temperature_entity_id", None
            ) or auto.get("temperature")
            humidity_sensor = getattr(
                _area, "humidity_entity_id", None
            ) or auto.get("humidity")
            if temp_sensor:
                sensor_state = self._hass.states.get(temp_sensor)
                if sensor_state is not None and sensor_state.state not in (
                    "unavailable",
                    "unknown",
                ):
                    try:
                        room_entry["temperature"] = float(sensor_state.state)
                    except (ValueError, TypeError):
                        pass  # leave temperature absent (invalid sensor state)
            elif entity_ids:
                trv_state = self._hass.states.get(entity_ids[0])
                if trv_state is not None:
                    current_temp = trv_state.attributes.get(
                        "current_temperature"
                    )
                    if current_temp is not None:
                        room_entry["temperature"] = current_temp

            if humidity_sensor:
                hum_state = self._hass.states.get(humidity_sensor)
                if hum_state is not None and hum_state.state not in (
                    "unavailable",
                    "unknown",
                ):
                    try:
                        room_entry["humidity"] = float(hum_state.state)
                    except (ValueError, TypeError):
                        pass  # leave humidity absent (invalid sensor state)

            room_entry["has_trv"] = any(
                is_trv_entity(self._hass, eid) for eid in entity_ids
            )

            rooms_status.append(room_entry)

        return {
            "global_mode": self._data.runtime_config["global_mode"],
            "active_period": self._last_active_period,
            "present_persons": self._last_present_persons,
            "rooms_status": rooms_status,
        }

    async def _push_safely(
        self, entity_id: str, desired_temp: float, context: str
    ) -> None:
        """Wrapper around _push_if_changed that logs exceptions instead of propagating them."""
        try:
            await self._push_if_changed(entity_id, desired_temp)
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to push temperature to %s in %s", entity_id, context
            )

    async def _push_off_safely(self, entity_id: str, frost_temp: float) -> None:
        """Pre-set frost setpoint then issue set_hvac_mode=off for an off-capable TRV in MODE_OFF.

        Two-step sequence: set_temperature(frost_temp) first, then set_hvac_mode=off.
        This ensures that when the TRV exits OFF it resumes at the frost setpoint rather
        than its previous arbitrary setpoint.

        Anti-flap guard: if _last_pushed already records "off" for this entity, skip both
        calls (same push-on-change parity as _push_if_changed).

        Error handling: if set_temperature raises, log a warning but still attempt
        set_hvac_mode=off (safety behavior preserved). If set_hvac_mode=off raises,
        do NOT set the sentinel (so the next tick will retry both calls).
        """
        state = self._hass.states.get(entity_id)
        if state is None or state.state == "unavailable":
            return

        if self._last_pushed.get(entity_id) == "off":
            return  # Anti-flap: already pushed off this evaluation cycle

        try:
            await set_trv_temperature(self._hass, entity_id, frost_temp)
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to pre-set frost temp on %s before MODE_OFF", entity_id
            )

        try:
            await set_trv_off(self._hass, entity_id)
            self._last_pushed[entity_id] = "off"
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Failed to push OFF to %s in MODE_OFF", entity_id)

    async def _push_if_changed(
        self, entity_id: str, desired_temp: float
    ) -> None:
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

        # Clear stale MODE_OFF sentinel: "off" is a string, not a temperature.
        # float(reported) != "off" is always True in Python 3, which would cause
        # the D-03 manual override hold to fire on every tick after MODE_OFF exit.
        if isinstance(last, str):
            last = None

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
