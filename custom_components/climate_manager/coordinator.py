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
- SCHED-05: per-room time program override (room_mode=custom) wins over zone schedule
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

        # Presence list computed once — used for PASS 2 and status reporting.
        self._last_present_persons = self._compute_present_persons(config, now)

        desired_temps: dict[str, float] = {}
        room_periods: dict[str, str] = {}
        present_locked_rooms: set[str] = set()
        frost_locked_rooms: set[str] = set()
        mode_off_rooms: set[str] = set()

        # PASS 1: baseline temperature per room via zone resolution + room_mode short-circuit.
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
                continue

            if room_mode == ROOM_MODE_CUSTOM:
                # EVAL-05 / D-20: custom room schedule wins over zone resolution
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

            # Room follows its zone (D-09)
            zone_mode, zone_time_program = self._resolve_zone_config(
                area_id, config
            )

            if zone_mode == MODE_OFF:
                # EVAL-01: zone off → frost protection
                desired_temps[area_id] = period_temperatures[
                    PERIOD_FROST_PROTECTION
                ]
                room_periods[area_id] = PERIOD_FROST_PROTECTION
                frost_locked_rooms.add(area_id)
                mode_off_rooms.add(area_id)

            elif zone_mode in (MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES):
                # EVAL-02 baseline (or EVAL-03 baseline before PASS 2 presence override)
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

        # PASS 2: presence override for zones with mode=time_program_presences (EVAL-03).
        # All configured persons considered — not scoped to zone members (D-11).
        for person_id, person_config in config.get("persons", {}).items():
            room_ids: list[str] = person_config.get("room_ids", [])
            if not room_ids:
                continue

            is_present = resolve_presence(person_config, now)

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
                    zone_program_for_room, now, is_present, period_temperatures
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

        self._last_room_periods = room_periods

        # Pitfall 7: _last_active_period reflects Default Zone for backward-compat with status payload.
        global_mode = config["global_mode"]
        self._last_active_period = (
            evaluate_schedule(config["global_time_program"], now)
            if global_mode != MODE_OFF
            else None
        )

        # Push pass — off-capable TRVs in mode_off_rooms use _push_off_safely.
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

        self._hass.bus.async_fire(
            f"{DOMAIN}_status_update",
            self._build_status_payload(),
        )

        # Calibration pass — D-01: runs after push pass and status fire.
        await self._async_calibrate(config)

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
        rooms = self._data.rooms
        tasks = []
        for area_id, entity_ids in rooms.items():
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
                            config,
                        )
                    )
            else:
                for entity_id in entity_ids:
                    if is_trv_entity(self._hass, entity_id):
                        tasks.append(
                            self._async_calibrate_room(
                                area_id, entity_id, config
                            )
                        )
        await asyncio.gather(*tasks)

    async def _async_calibrate_tado_device(
        self,
        area_id: str,
        device_id: str,
        zone_entity_id: str | None,
        config: dict,
    ) -> None:
        """Calibrate one Tado X Radiator Valve X device toward its room sensor.

        Uses device_id for the offset call (tado_x service requirement) and
        zone_entity_id for temperature reading (no per-TRV temp entity).
        Tracks offset increments in _calibration_last_offset so successive
        calls accumulate correctly despite the device not exposing its offset.
        """
        sensor_entity_id = (
            config.get("rooms", {}).get(area_id, {}).get("temperature_sensor")
        )
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
        new_offset = max(
            -_OFFSET_CLAMP, min(_OFFSET_CLAMP, existing_offset + delta)
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
        self, area_id: str, entity_id: str, config: dict
    ) -> None:
        """Calibrate one TRV toward its room's reference sensor.

        Silently returns when any guard condition fails (CALIB-03/05, D-07/08,
        Pitfalls 2/5).
        """
        # CALIB-05, D-14: manual temperature_sensor config only
        sensor_entity_id = (
            config.get("rooms", {}).get(area_id, {}).get("temperature_sensor")
        )
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
            else:
                # scheduled, force_present, force_absent, or unknown → delegate to resolve_presence
                if resolve_presence(person_config, now):
                    present.append(person_id)
        return present

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
