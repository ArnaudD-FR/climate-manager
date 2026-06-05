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
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    MODE_TIME_PROGRAM,
    PRESENCE_HA,
)
from .eval_context import EvalContext
from .person import Person
from .room import Room
from .trv import (
    TRV,
    TRVGroup,
    get_tado_valve_devices,
    is_trv_entity,
    set_trv_offset_by_device,
)
from .zone import Zone

if TYPE_CHECKING:
    from . import ClimateManagerData

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(minutes=1)
# Hardware-safe maximum for TRV temperature offset (±5°C for Tado X and most brands).
_OFFSET_CLAMP = 5.0
# Minimum time between calibration API calls per device to avoid 429s.
_CALIBRATION_MIN_INTERVAL = timedelta(minutes=5)


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
        # Expose data on hass so Room.compute_preheat / calibrate_trvs can read
        # runtime_config and preheat_samples without a coordinator reference.
        self._hass._climate_manager_data = self._data
        # D-09 domain objects — instantiated from config at init and rebuilt
        # on config change (fingerprint-based, T-16-13).
        self._zones: dict[str, Zone] = {}
        self._persons: dict[str, Person] = {}
        self._rooms: dict[str, Room] = {}
        # Fingerprint of the zones/persons/rooms config structure.
        # Compared each cycle; rebuild triggered on change (T-16-13).
        self._config_fingerprint: int = 0
        # Wave 2: track last evaluation results for status push and get_status WS command.
        self._last_active_period: str | None = None
        self._last_present_persons: list[str] = []
        # Per-room effective period (may differ from global in time_program_presences mode).
        self._last_room_periods: dict[str, str] = {}
        # D-05: per-zone active period dict — "default" plus one key per custom
        # zone UUID. Populated by async_evaluate; consumed by _build_status_payload.
        self._last_zone_periods: dict[str, str | None] = {}
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
        # D-04: tracks entity IDs for which the calendar "unavailable" WARNING
        # has already been issued. Entry is added on first failure and removed
        # on the next successful fetch so the warning re-fires after recovery.
        # Retained here (not migrated to EvalContext) so the suppression persists
        # across evaluation cycles (T-16-13 retention list).
        self._calendar_warn_issued: set[str] = set()
        # _frost_locked_rooms: snapshot from last zone evaluation pass.
        # Retained until consumed by Room (T-16-13 retention list).
        self._frost_locked_rooms: set[str] = set()
        # D-08 (Phase 13): cancel callbacks for Matter calibration
        # state_changed listeners. Keyed by entity_id (Matter or tado_x).
        # Single Callable per key — unlike _ha_tracker_listeners (list).
        # Cancel-all-then-rebuild via _async_refresh_matter_listeners().
        self._matter_cal_listeners: dict[str, Callable] = {}

        # Build initial domain object graph from config.
        self._build_domain_objects(data.runtime_config)

    # ------------------------------------------------------------------
    # D-09: Domain object graph construction
    # ------------------------------------------------------------------

    def _compute_config_fingerprint(self, config: dict) -> int:
        """Compute a cheap fingerprint of the zones/persons/rooms config.

        Used to detect WS-driven config mutations between ticks (T-16-13).
        Hash covers the three dicts that affect domain object graph structure.
        """
        key_parts = (
            repr(config.get("default_zone", {})),
            repr(config.get("zones", {})),
            repr(config.get("persons", {})),
            repr(config.get("rooms", {})),
        )
        return hash("".join(key_parts))

    def _build_domain_objects(self, config: dict) -> None:
        """Construct Zone/Person/Room/TRVGroup graphs from stored config.

        Called at __init__ and re-called when the config fingerprint changes
        (i.e. a WS handler mutated runtime_config between ticks — T-16-13).
        Domain objects are the SINGLE strong references so weakrefs in
        ZoneMode/PersonMode instances resolve correctly (Pitfall 1).

        Assembly order:
        1. Zones — default + each custom zone UUID.
        2. Persons — one per entry in config["persons"].
        3. Rooms — one per area_id in self._data.rooms; each room gets:
           a. TRVGroup via TRVGroup.from_room_config (Matter dedup — Pitfall 4).
           b. _zone wired to its owning Zone.
           c. assigned_persons populated from each person's room_ids.
        4. zone._rooms populated from Room objects.
        """
        matter_mappings: dict[str, list[str]] = config.get(
            "matter_mappings", {}
        )

        # -- Step 1: Zones ---------------------------------------------------
        dz_cfg = config.get("default_zone", {})
        default_zone = Zone(
            zone_id="default",
            hass=self._hass,
            initial_mode=dz_cfg.get("mode", MODE_TIME_PROGRAM),
            time_program=dz_cfg.get("time_program", {}),
            preheat_enabled=dz_cfg.get("preheat_enabled", False),
        )

        zones: dict[str, Zone] = {"default": default_zone}
        for zone_id, zone_cfg in config.get("zones", {}).items():
            zones[zone_id] = Zone(
                zone_id=zone_id,
                hass=self._hass,
                initial_mode=zone_cfg.get("mode", MODE_TIME_PROGRAM),
                time_program=zone_cfg.get("time_program", {}),
                preheat_enabled=zone_cfg.get("preheat_enabled", False),
            )

        # -- Step 2: Persons -------------------------------------------------
        persons: dict[str, Person] = {}
        for person_id, person_cfg in config.get("persons", {}).items():
            p = Person(
                person_id=person_id,
                hass=self._hass,
                person_config=person_cfg,
                room_ids=person_cfg.get("room_ids", []),
            )
            persons[person_id] = p

        # -- Step 3: Rooms + TRVGroups ---------------------------------------
        rooms: dict[str, Room] = {}
        for area_id, entity_ids in self._data.rooms.items():
            room_cfg = config.get("rooms", {}).get(area_id, {})
            zone_id = room_cfg.get("zone_id")
            owning_zone: Zone = (
                zones.get(zone_id, default_zone)
                if zone_id is not None
                else default_zone
            )

            room = Room(area_id=area_id, hass=self._hass)
            room._zone = owning_zone  # wire owning zone reference

            # Build TRVGroup from entity list + matter_mappings.
            # room_name and zone_name used for DEBUG log short names.
            group = TRVGroup.from_room_config(
                hass=self._hass,
                entity_ids=entity_ids,
                matter_mappings=matter_mappings,
                room_name=area_id,
                zone_name=owning_zone.zone_id,
            )
            room._trv_groups = [group]

            rooms[area_id] = room

        # Populate assigned_persons on each room (from person.room_ids).
        for person in persons.values():
            for area_id in person.room_ids:
                if area_id in rooms:
                    rooms[area_id].assigned_persons.append(person)

        # Populate zone._rooms from the assembled rooms.
        for zone in zones.values():
            zone._rooms = [
                room for room in rooms.values() if room._zone is zone
            ]

        # Carry forward anti-spam state from previous Zone/Person objects so a
        # config-triggered rebuild doesn't reset log-state and spam the log.
        for zone_id, zone in zones.items():
            old = self._zones.get(zone_id)
            if old is not None and old._current_period is not None:
                zone._current_period = old._current_period
                zone._current_mode_name = old._current_mode_name

        for person_id, person in persons.items():
            old_p = self._persons.get(person_id)
            if old_p is not None and old_p._last_home is not None:
                person._last_home = old_p._last_home

        # Commit the new graph (single atomic update — Pitfall 1).
        self._zones = zones
        self._persons = persons
        self._rooms = rooms
        self._config_fingerprint = self._compute_config_fingerprint(config)

    def _get_trv(self, entity_id: str) -> "TRV | None":
        """Return the TRV domain object for entity_id, or None if not found.

        Searches self._rooms for a TRV with the matching entity_id.
        Used by the event-driven calibration path.
        """
        for room in self._rooms.values():
            for group in room._trv_groups:
                for trv in group._trvs:
                    if trv.entity_id == entity_id:
                        return trv
        return None

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

        # T-16-13: rebuild domain objects when WS handler mutated runtime_config.
        # Fingerprint covers zones/persons/rooms structure; cheap hash comparison.
        new_fp = self._compute_config_fingerprint(config)
        if new_fp != self._config_fingerprint:
            self._build_domain_objects(config)

        # D-09: build one EvalContext per cycle (OBS-01 / RESEARCH D-02).
        ctx = EvalContext(
            now=now,
            hass=self._hass,
            period_temperatures=period_temperatures,
        )

        # Zone evaluation loop — each Zone delegates to its ZoneMode which
        # calls room.apply_setpoint → TRVGroup.push → TRV.push_temperature.
        # ZoneModeProgramPresences also evaluates Person.evaluate (cached in ctx).
        for zone in self._zones.values():
            await zone.evaluate(ctx)

        # Evaluate any persons not yet in ctx._presence_cache (those in
        # time_program zones are never called by zone.evaluate, but we still
        # need their presence state for status reporting — D-11 / INFRA-03).
        for person in self._persons.values():
            if person.person_id not in ctx._presence_cache:
                await person.evaluate(ctx)

        # Warn via persistent notification when an ha-mode person has no tracker.
        self._check_ha_tracker_warnings(config)

        # Update status-payload tracking fields from EvalContext (D-09).
        # _last_present_persons: list of person_ids where ctx returned True.
        self._last_present_persons = [
            pid for pid, home in ctx._presence_cache.items() if home
        ]

        # _last_room_periods: per-room effective period from the owning Zone.
        # In time_program_presences mode this is the last period returned by
        # ZoneModeProgramPresences.evaluate — same for all rooms in the zone.
        self._last_room_periods = {}
        for area_id, room in self._rooms.items():
            # Per-room period wins: in presence mode each room resolves its
            # own effective period (e.g. empty room → reduced) while the
            # zone-level _current_period only holds the last room's value.
            if room._last_period is not None:
                self._last_room_periods[area_id] = room._last_period
                continue
            zone = room._zone
            if zone is not None and zone._current_period is not None:
                self._last_room_periods[area_id] = zone._current_period

        # _last_active_period: Default Zone's current period (status fallback).
        default_zone = self._zones.get("default")
        self._last_active_period = (
            default_zone._current_period if default_zone is not None else None
        )

        # _last_zone_periods: per-zone current period dict (D-05).
        self._last_zone_periods = {
            zone_id: zone._current_period
            for zone_id, zone in self._zones.items()
        }

        # D-10 (Phase 13): register Matter calibration listeners on first
        # evaluate. Rooms are populated by async_setup_entry before
        # async_evaluate is called, so _matter_cal_listeners is always
        # built against current runtime_data.rooms.
        if not self._matter_cal_listeners:
            await self._async_refresh_matter_listeners()

        # Per-room preheat and calibration passes (D-09).
        # Room.compute_preheat owns all preheat state (D-06 migration).
        # _async_calibrate handles Tado X device-level calibration separately.
        for room in self._rooms.values():
            await room.compute_preheat(ctx)

        await self._async_calibrate(config, ctx)

        # RESEARCH Open Question 1: fire status AFTER preheat/calibrate passes
        # so the panel receives up-to-date preheat_active / preheat_suppressed
        # in the same cycle that triggered the preheat (avoids one-cycle lag).
        self._hass.bus.async_fire(
            f"{DOMAIN}_status_update",
            self._build_status_payload(),
        )

    def _resolve_room_sensor(self, area_id: str, config: dict) -> str | None:
        """Return the temperature sensor entity_id for a room.

        Resolution order (shared by _async_calibrate and
        _async_calibrate_for_room):
          1. area_reg.temperature_entity_id (HA 2026.5+ area registry)
          2. room_auto_sensors (discovered from device registry)
          3. rooms_config explicit override (test + manual config)
        """
        from homeassistant.helpers import area_registry as ar  # noqa: PLC0415

        area_reg = ar.async_get(self._hass)
        _area = area_reg.async_get_area(area_id)
        return (
            getattr(_area, "temperature_entity_id", None)
            or self._data.room_auto_sensors.get(area_id, {}).get("temperature")
            or config.get("rooms", {})
            .get(area_id, {})
            .get("temperature_sensor")
        )

    async def _async_calibrate(
        self,
        config: dict,
        ctx: "EvalContext | None" = None,
    ) -> None:
        """Offset-calibrate all compatible TRVs toward their room sensors.

        For rooms with Tado X Radiator Valve X devices, calibration is
        device_id-based (tado_x.set_temperature_offset takes device_id).
        For other rooms, delegates to Room.calibrate_trvs(ctx) (D-06 migration).

        D-04: Returns immediately when calibration_enabled is False.
        D-03: Concurrent gather over all rooms, same pattern as push pass.
        """
        if not config.get("calibration_enabled", False):
            return
        rooms = self._data.rooms
        tado_tasks = []
        generic_rooms = []
        for area_id, entity_ids in rooms.items():
            sensor_entity_id = self._resolve_room_sensor(area_id, config)
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
                    tado_tasks.append(
                        self._async_calibrate_tado_device(
                            area_id,
                            device["device_id"],
                            zone_entity,
                            sensor_entity_id,
                            config,
                        )
                    )
            else:
                generic_rooms.append(area_id)
        if tado_tasks:
            await asyncio.gather(*tado_tasks)
        # Generic entity calibration: delegated to Room.calibrate_trvs (D-06).
        if ctx is not None:
            generic_tasks = [
                self._rooms[area_id].calibrate_trvs(ctx)
                for area_id in generic_rooms
                if area_id in self._rooms
            ]
            if generic_tasks:
                await asyncio.gather(*generic_tasks)

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

        last_changed = self._calibration_last_changed.get(device_id)
        if last_changed:
            elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(
                last_changed
            )
            if elapsed < _CALIBRATION_MIN_INTERVAL:
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

    # -----------------------------------------------------------------------
    # Phase 13: Matter calibration listener lifecycle (D-08..D-11)
    # -----------------------------------------------------------------------

    @callback
    def _make_matter_cal_listener(self, area_id: str) -> Callable:
        """Factory: create a state_changed callback for an entity in area_id.

        D-09: only fires calibration when current_temperature changes.
        Guards old_state=None (Pitfall 5 — entity startup event).
        Schedules _async_calibrate_for_room via hass.async_create_task
        (listener is @callback; cannot await directly).
        """

        @callback
        def _on_state_changed(event: object) -> None:
            new_state = getattr(event, "data", {}).get("new_state")
            if new_state is None:
                return
            old_state = getattr(event, "data", {}).get("old_state")
            new_temp = (new_state.attributes or {}).get("current_temperature")
            old_temp = (
                (old_state.attributes or {}).get("current_temperature")
                if old_state is not None
                else None
            )
            if new_temp == old_temp:
                return
            self._hass.async_create_task(
                self._async_calibrate_for_room(area_id)
            )

        return _on_state_changed

    async def _async_refresh_matter_listeners(self) -> None:
        """Cancel all Matter calibration listeners and re-register.

        D-10: cancel-all-then-rebuild. Safe because WS commands are
        serialised on the HA event loop — no concurrent registration race.
        Listener scope per D-09:
          - mapped tado_x entity → no listener (Matter handles it)
          - mapped Matter entity → listener
          - unmapped tado_x entity → listener
          - unmapped Matter entity (not in any mapping value) → listener
        """
        from homeassistant.helpers import (  # noqa: PLC0415
            entity_registry as er,
        )
        from homeassistant.helpers.event import (  # noqa: PLC0415
            async_track_state_change_event,
        )

        # Cancel all existing listeners before rebuild (Pitfall 1)
        for cancel in self._matter_cal_listeners.values():
            cancel()
        self._matter_cal_listeners.clear()

        entity_reg = er.async_get(self._hass)
        config = self._data.runtime_config
        matter_mappings: dict[str, list[str]] = config.get(
            "matter_mappings", {}
        )
        # Build frozenset of all Matter entity_ids in any mapping value
        # (used to skip Matter entities already covered by a tado_x branch)
        matter_entity_set: frozenset[str] = frozenset(
            eid for eids in matter_mappings.values() for eid in eids
        )

        def _register(eid: str, aid: str) -> None:
            """Register once — skip if already tracked (idempotent)."""
            if eid in self._matter_cal_listeners:
                return
            cancel = async_track_state_change_event(
                self._hass,
                eid,
                self._make_matter_cal_listener(aid),
            )
            self._matter_cal_listeners[eid] = cancel

        for area_id, entity_ids in self._data.rooms.items():
            for entity_id in entity_ids:
                reg = entity_reg.async_get(entity_id)
                # When no registry entry exists, treat as generic entity
                platform = reg.platform if reg is not None else None
                if platform == "tado_x":
                    mapped = matter_mappings.get(entity_id)
                    if mapped:
                        # D-09: mapped tado_x → no listener on tado_x;
                        # each mapped Matter entity gets its own listener
                        for matter_eid in mapped:
                            _register(matter_eid, area_id)
                    else:
                        # D-09: unmapped tado_x → listener on tado_x entity
                        _register(entity_id, area_id)
                elif platform == "matter":
                    # D-09: unmapped Matter entity → listener
                    if entity_id not in matter_entity_set:
                        _register(entity_id, area_id)
                else:
                    # Generic TRV or unregistered entity → listener
                    _register(entity_id, area_id)

    async def _async_calibrate_for_room(self, area_id: str) -> None:
        """Run calibration for a single room (event-driven path).

        Called from the Matter calibration listener callback via
        hass.async_create_task. Mirrors the per-area body of _async_calibrate
        but scoped to one room and not gated by the full gather.

        Routing per mapping state (D-04..D-07):
          - mapped tado_x: calibrate via tado_x devices, delta from Matter entity
          - unmapped tado_x: existing _async_calibrate_tado_device path
          - unmapped Matter / generic: Room.calibrate_trvs (D-06 migration)
        """
        config = self._data.runtime_config
        if not config.get("calibration_enabled", False):
            return

        from homeassistant.helpers import (  # noqa: PLC0415
            entity_registry as er,
        )

        entity_reg = er.async_get(self._hass)
        entity_ids = self._data.rooms.get(area_id, [])
        sensor_entity_id = self._resolve_room_sensor(area_id, config)

        matter_mappings: dict[str, list[str]] = config.get(
            "matter_mappings", {}
        )
        matter_entity_set: frozenset[str] = frozenset(
            eid for eids in matter_mappings.values() for eid in eids
        )

        tado_tasks = []
        needs_generic_calibrate = False
        for entity_id in entity_ids:
            if not is_trv_entity(self._hass, entity_id):
                continue
            reg = entity_reg.async_get(entity_id)
            platform = reg.platform if reg is not None else None
            if platform == "tado_x":
                mapped = matter_mappings.get(entity_id)
                if mapped:
                    # D-04/D-05: use first Matter entity as temp source;
                    # resolve Tado X valve devices by area
                    matter_eid = mapped[0]
                    valve_devices = get_tado_valve_devices(self._hass, area_id)
                    if valve_devices:
                        for device in valve_devices:
                            tado_tasks.append(
                                self._async_calibrate_tado_device(
                                    area_id,
                                    device["device_id"],
                                    matter_eid,
                                    sensor_entity_id,
                                    config,
                                )
                            )
                    else:
                        # D-05 fallback: generic entity-based calibration
                        needs_generic_calibrate = True
                else:
                    # D-06: unmapped tado_x → existing device-based path
                    valve_devices = get_tado_valve_devices(self._hass, area_id)
                    if valve_devices:
                        zone_entity = next(
                            (
                                eid
                                for eid in entity_ids
                                if is_trv_entity(self._hass, eid)
                            ),
                            None,
                        )
                        for device in valve_devices:
                            tado_tasks.append(
                                self._async_calibrate_tado_device(
                                    area_id,
                                    device["device_id"],
                                    zone_entity,
                                    sensor_entity_id,
                                    config,
                                )
                            )
                    else:
                        needs_generic_calibrate = True
            elif platform == "matter":
                if entity_id not in matter_entity_set:
                    # D-07: unmapped Matter → generic entity-based calibration
                    needs_generic_calibrate = True
            else:
                # Generic TRV entity: entity-based calibration via Room
                needs_generic_calibrate = True

        if tado_tasks:
            await asyncio.gather(*tado_tasks)

        if needs_generic_calibrate:
            room = self._rooms.get(area_id)
            if room is not None:
                # Build a minimal EvalContext for the event-driven calibration path.
                ctx_calib = EvalContext(
                    now=dt_util.now(),
                    hass=self._hass,
                    period_temperatures=config.get("period_temperatures", {}),
                )
                await room.calibrate_trvs(ctx_calib)

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
            # State now lives on Room domain object (D-06 migration).
            _room_obj = self._rooms.get(area_id)
            room_entry["preheat_active"] = (
                _room_obj._preheat_active if _room_obj is not None else False
            )
            room_entry["preheat_target"] = (
                _room_obj._preheat_target if _room_obj is not None else None
            )
            room_entry["preheat_suppressed"] = (
                _room_obj._preheat_suppressed
                if _room_obj is not None
                else False
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

        config = self._data.runtime_config
        return {
            "zones": {
                "default": {
                    "mode": config["default_zone"]["mode"],
                    "active_period": self._last_zone_periods.get("default"),
                },
                **{
                    zone_id: {
                        "mode": zone["mode"],
                        "active_period": self._last_zone_periods.get(zone_id),
                    }
                    for zone_id, zone in config.get("zones", {}).items()
                },
            },
            "present_persons": self._last_present_persons,
            "rooms_status": rooms_status,
        }
