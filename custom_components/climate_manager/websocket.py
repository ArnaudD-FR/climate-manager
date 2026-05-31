# SPDX-License-Identifier: MIT
"""Climate Manager WebSocket command handlers.

Registers 18 WebSocket commands for the panel ↔ backend protocol:
- get_status: returns global_mode, active_period, present_persons, rooms_status
- get_config: returns full runtime_config
- set_global_mode: mutates global_mode, persists, re-evaluates
- set_period_temperatures: updates all 4 period temperatures
- set_time_program: validates and persists the global per-day program
- set_room_config: sparse-merges into rooms[room_id]
- set_person_config: sparse-merges into persons[person_id]
- subscribe_status: registers a push listener in connection.subscriptions
- reset_period_temperatures: resets period_temperatures to DEFAULT_PERIOD_TEMPERATURES from const.py
- reset_time_program: resets global_time_program to _DEFAULT_DAILY_PROGRAM from const.py
- reset_room_to_global_program: deep-copies global_time_program into rooms[room_id].time_program
- create_zone: creates new heating zone with UUID, persists
- rename_zone: renames custom zone or Default Zone (zone_id="default")
- set_zone_mode: sets custom zone mode via vol.In(VALID_MODES)
- delete_zone: migrates rooms to Default Zone (pop), removes zone, CR-01 snapshot rollback
- set_zone_time_program: validates program via validate_daily_program before any mutation
- reset_zone_time_program: restores zone time_program from 'default' or 'global' target
- set_calibration_config: persists calibration_enabled bool (D-10, CALIB-01)

All handlers access state via the entry closure (never hass.data[DOMAIN]).
Write handlers follow the write-then-evaluate pattern:
  mutate runtime_config → store.async_save → send_result → coordinator.async_evaluate (background).
Exception: set_calibration_config does NOT trigger async_evaluate (RESEARCH Pitfall 4).

Security:
- T-03-04: vol.In/vol.Coerce schema gates reject invalid payloads before handler runs
- T-03-05: validate_daily_program gate rejects partial programs before any save
- T-03-06: HA WebSocket auth gate handles unauthenticated access (not our concern)
- T-03-07: get_status reads only configured sensor entity IDs; every hass.states.get
           result is guarded for None before reading state
- T-03-09: write handlers mutate only targeted sub-keys; DEFAULT_CONFIG never imported
- T-05-06: delete_zone pops room zone_ids BEFORE deleting the zone entry (Pitfall 1)
- T-05-07: delete_zone CR-01 snapshots both zones AND rooms before mutation
- T-05-08: set_zone_time_program validates BEFORE any runtime_config mutation (Pitfall 6)
- T-05-09: reset_zone_time_program uses copy.deepcopy for both target branches (Pitfall 2)
- T-05-11: delete_zone uses pop() never assigns None — sparse D-06 model preserved
- T-09-01: set_calibration_config vol.Required("enabled"): bool rejects non-bool
           payloads before handler runs (T-03-04 parity)
"""

from __future__ import annotations

import copy
import uuid
from typing import TYPE_CHECKING

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
import voluptuous as vol

if TYPE_CHECKING:
    from . import ClimateManagerConfigEntry

from .const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
    _DEFAULT_DAILY_PROGRAM,
)
from .schedule import validate_daily_program
from .trv import get_tado_valve_devices, is_trv_entity

VALID_MODES = [MODE_OFF, MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES]


def async_register_commands(
    hass: HomeAssistant, entry: ClimateManagerConfigEntry
) -> None:
    """Register all Climate Manager WebSocket commands.

    Called once from async_setup_entry. Commands auto-unregister on entry unload
    (RESEARCH Pattern 3 — no explicit cleanup needed in async_unload_entry).
    """
    websocket_api.async_register_command(hass, _make_ws_get_status(entry))
    websocket_api.async_register_command(hass, _make_ws_get_config(entry))
    websocket_api.async_register_command(hass, _make_ws_set_global_mode(entry))
    websocket_api.async_register_command(
        hass, _make_ws_set_period_temperatures(entry)
    )
    websocket_api.async_register_command(hass, _make_ws_set_time_program(entry))
    websocket_api.async_register_command(hass, _make_ws_set_room_config(entry))
    websocket_api.async_register_command(
        hass, _make_ws_set_person_config(entry)
    )
    websocket_api.async_register_command(hass, _make_ws_subscribe_status(entry))
    websocket_api.async_register_command(
        hass, _make_ws_reset_period_temperatures(entry)
    )
    websocket_api.async_register_command(
        hass, _make_ws_reset_time_program(entry)
    )
    websocket_api.async_register_command(
        hass, _make_ws_reset_room_to_global_program(entry)
    )
    websocket_api.async_register_command(hass, _make_ws_create_zone(entry))
    websocket_api.async_register_command(hass, _make_ws_rename_zone(entry))
    websocket_api.async_register_command(hass, _make_ws_set_zone_mode(entry))
    websocket_api.async_register_command(hass, _make_ws_delete_zone(entry))
    websocket_api.async_register_command(
        hass, _make_ws_set_zone_time_program(entry)
    )
    websocket_api.async_register_command(
        hass, _make_ws_reset_zone_time_program(entry)
    )
    websocket_api.async_register_command(
        hass, _make_ws_set_calibration_config(entry)
    )
    websocket_api.async_register_command(
        hass, _make_ws_get_calibration_status(entry)
    )


# ---------------------------------------------------------------------------
# Read commands
# ---------------------------------------------------------------------------


def _make_ws_get_status(entry: ClimateManagerConfigEntry):
    """Factory: create get_status handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/get_status",
        }
    )
    @websocket_api.async_response
    async def ws_get_status(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Return global status: global_mode, active_period, present_persons, rooms_status.

        T-03-07: sensor entity IDs are read from stored config (never from payload);
                 every hass.states.get() result is guarded for None.
        """
        coordinator = entry.runtime_data.coordinator
        runtime_config = entry.runtime_data.runtime_config
        rooms = entry.runtime_data.rooms

        # Pull last-evaluation results from coordinator (set during async_evaluate)
        active_period = getattr(coordinator, "_last_active_period", None)
        present_persons = getattr(coordinator, "_last_present_persons", [])

        # D-24: pre-compute persons join data for present_person_count
        persons_config: dict = runtime_config.get("persons", {})
        present_set = set(present_persons)

        # Build per-room status list
        from homeassistant.helpers import area_registry as ar  # noqa: PLC0415

        _area_reg = ar.async_get(hass)

        rooms_status = []
        room_auto_sensors = entry.runtime_data.room_auto_sensors
        for area_id, entity_ids in rooms.items():
            auto = room_auto_sensors.get(area_id, {})
            _area = _area_reg.async_get_area(area_id)
            room_entry: dict = {
                "area_id": area_id,
                "name": _area.name if _area else area_id,
                "entity_ids": entity_ids,
            }

            # Temperature/humidity: HA area registry (HA 2026.5+) → auto-discovered → TRV built-in
            temp_sensor = getattr(
                _area, "temperature_entity_id", None
            ) or auto.get("temperature")
            humidity_sensor = getattr(
                _area, "humidity_entity_id", None
            ) or auto.get("humidity")
            if temp_sensor:
                sensor_state = hass.states.get(temp_sensor)
                if sensor_state is not None and sensor_state.state not in (
                    "unavailable",
                    "unknown",
                ):
                    try:
                        room_entry["temperature"] = float(sensor_state.state)
                    except (ValueError, TypeError):
                        pass  # leave temperature absent (invalid sensor state)
            elif entity_ids:
                trv_state = hass.states.get(entity_ids[0])
                if trv_state is not None:
                    current_temp = trv_state.attributes.get(
                        "current_temperature"
                    )
                    if current_temp is not None:
                        room_entry["temperature"] = current_temp

            if humidity_sensor:
                hum_state = hass.states.get(humidity_sensor)
                if hum_state is not None and hum_state.state not in (
                    "unavailable",
                    "unknown",
                ):
                    try:
                        room_entry["humidity"] = float(hum_state.state)
                    except (ValueError, TypeError):
                        pass  # leave humidity absent (invalid sensor state)

            # Active period for this room — per-room value when available, global fallback
            room_entry["active_period"] = coordinator._last_room_periods.get(
                area_id, active_period
            )

            # D-24: count persons assigned to this area who are currently present
            room_entry["present_person_count"] = sum(
                1
                for person_id, person_config in persons_config.items()
                if area_id in person_config.get("room_ids", [])
                and person_id in present_set
            )

            room_entry["has_trv"] = any(
                is_trv_entity(hass, eid) for eid in entity_ids
            )

            rooms_status.append(room_entry)

        connection.send_result(
            msg["id"],
            {
                "global_mode": runtime_config["global_mode"],
                "active_period": active_period,
                "present_persons": present_persons,
                "rooms_status": rooms_status,
            },
        )

    return ws_get_status


def _make_ws_get_config(entry: ClimateManagerConfigEntry):
    """Factory: create get_config handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/get_config",
        }
    )
    @websocket_api.async_response
    async def ws_get_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Return full runtime_config plus derived climate_entities list.

        D-25: climate_entities is the sorted list of all climate.* entity IDs
        from the HA entity registry. Merged into a NEW dict — runtime_config is
        never mutated so the derived key never pollutes persistent storage.
        """
        entity_reg = er.async_get(hass)
        climate_entities = sorted(
            reg_entry.entity_id
            for reg_entry in entity_reg.entities.values()
            if reg_entry.entity_id.split(".")[0] == "climate"
        )
        payload = {
            **entry.runtime_data.runtime_config,
            "climate_entities": climate_entities,
        }
        connection.send_result(msg["id"], payload)

    return ws_get_config


# ---------------------------------------------------------------------------
# Write commands
# ---------------------------------------------------------------------------


def _make_ws_set_global_mode(entry: ClimateManagerConfigEntry):
    """Factory: create set_global_mode handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_global_mode",
            vol.Required("mode"): vol.In(VALID_MODES),
        }
    )
    @websocket_api.async_response
    async def ws_set_global_mode(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Set global mode, persist, and re-evaluate.

        T-03-04: vol.In(VALID_MODES) in the schema rejects invalid modes before handler runs.
        """
        entry.runtime_data.runtime_config["global_mode"] = msg["mode"]
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_global_mode


def _make_ws_set_period_temperatures(entry: ClimateManagerConfigEntry):
    """Factory: create set_period_temperatures handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_period_temperatures",
            vol.Required("temperatures"): {
                vol.Required(PERIOD_FROST_PROTECTION): vol.Coerce(float),
                vol.Required(PERIOD_REDUCED): vol.Coerce(float),
                vol.Required(PERIOD_NORMAL): vol.Coerce(float),
                vol.Required(PERIOD_COMFORT): vol.Coerce(float),
            },
        }
    )
    @websocket_api.async_response
    async def ws_set_period_temperatures(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Merge the 4 period temperatures into runtime_config and persist.

        T-03-04: vol.Coerce(float) in schema rejects non-numeric values before handler runs.
        T-03-09: Only period_temperatures sub-key is mutated — other keys are preserved.
        """
        temps = msg["temperatures"]
        # Sparse-safe: update only the period_temperatures sub-dict key-by-key
        period_temps = entry.runtime_data.runtime_config.setdefault(
            "period_temperatures", {}
        )
        for key, value in temps.items():
            period_temps[key] = value
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_period_temperatures


def _make_ws_set_time_program(entry: ClimateManagerConfigEntry):
    """Factory: create set_time_program handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_time_program",
            vol.Required("program"): dict,
        }
    )
    @websocket_api.async_response
    async def ws_set_time_program(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Validate and persist the global per-day time program.

        T-03-05: validate_daily_program gate — sends error and returns BEFORE any
                 save/evaluate if the program is invalid. Invalid programs are never persisted.
        """
        ok, err = validate_daily_program(msg["program"])
        if not ok:
            connection.send_error(
                msg["id"], websocket_api.ERR_INVALID_FORMAT, err
            )
            return  # T-03-05: return BEFORE save/evaluate

        entry.runtime_data.runtime_config["global_time_program"] = msg[
            "program"
        ]
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_time_program


def _make_ws_set_room_config(entry: ClimateManagerConfigEntry):
    """Factory: create set_room_config handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_room_config",
            vol.Required("room_id"): str,
            vol.Required("config"): dict,
        }
    )
    @websocket_api.async_response
    async def ws_set_room_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Sparse-merge config into rooms[room_id] without wiping other rooms.

        T-03-09: setdefault + update pattern ensures only the targeted room's keys are
                 modified; other rooms and DEFAULT_CONFIG keys are preserved.
        CR-01: snapshot rooms before mutation so we can roll back if async_save raises
               (validate_zone_assignment inside async_save may raise ValueError on
               invalid zone_id assignments — ZONE-04).
        """
        rooms_backup = copy.deepcopy(
            entry.runtime_data.runtime_config.get("rooms", {})
        )
        # zone_id: null from the frontend signals 'move room to Default Zone' — pop the key
        # per D-06 sparse model (gap CR-03 fix from VERIFICATION 06-04).
        incoming_config = msg["config"]
        if "zone_id" in incoming_config and incoming_config["zone_id"] is None:
            incoming_config.pop("zone_id")
            entry.runtime_data.runtime_config.setdefault(
                "rooms", {}
            ).setdefault(msg["room_id"], {}).pop("zone_id", None)
        (
            entry.runtime_data.runtime_config.setdefault("rooms", {})
            .setdefault(msg["room_id"], {})
            .update(incoming_config)
        )
        try:
            await entry.runtime_data.store.async_save(
                entry.runtime_data.runtime_config
            )
        except ValueError as exc:
            # Roll back in-memory mutation so runtime_config stays consistent
            entry.runtime_data.runtime_config["rooms"] = rooms_backup
            connection.send_error(
                msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc)
            )
            return
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_room_config


def _make_ws_set_person_config(entry: ClimateManagerConfigEntry):
    """Factory: create set_person_config handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_person_config",
            vol.Required("person_id"): str,
            vol.Required("config"): dict,
        }
    )
    @websocket_api.async_response
    async def ws_set_person_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Sparse-merge config into persons[person_id] without wiping other persons.

        T-03-09: same setdefault + update pattern as set_room_config.
        """
        # SCHED-05: auto-seed schedule_even/schedule_odd when switching to
        # even_odd. Guard: only seed when schedule_even is not already in
        # storage — an existing empty {} schedule must not be overwritten
        # (key-absence check, not truthiness — Pitfall 1 in RESEARCH.md).
        incoming = msg["config"]
        if incoming.get("schedule_type") == "even_odd":
            current_person = entry.runtime_data.runtime_config.get(
                "persons", {}
            ).get(msg["person_id"], {})
            if "schedule_even" not in current_person:
                incoming.setdefault(
                    "schedule_even",
                    copy.deepcopy(current_person.get("schedule", {})),
                )
                incoming.setdefault(
                    "schedule_odd",
                    copy.deepcopy(current_person.get("schedule", {})),
                )
        (
            entry.runtime_data.runtime_config.setdefault("persons", {})
            .setdefault(msg["person_id"], {})
            .update(msg["config"])
        )
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_person_config


def _make_ws_reset_period_temperatures(entry: ClimateManagerConfigEntry):
    """Factory: create reset_period_temperatures handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/reset_period_temperatures",
        }
    )
    @websocket_api.async_response
    async def ws_reset_period_temperatures(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Reset period_temperatures to DEFAULT_PERIOD_TEMPERATURES from const.py.

        T-03-09: A shallow copy of the module-level constant is used so the
                 runtime_config never shares references with the module default.
        """
        entry.runtime_data.runtime_config["period_temperatures"] = dict(
            DEFAULT_PERIOD_TEMPERATURES
        )
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_reset_period_temperatures


def _make_ws_reset_time_program(entry: ClimateManagerConfigEntry):
    """Factory: create reset_time_program handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/reset_time_program",
        }
    )
    @websocket_api.async_response
    async def ws_reset_time_program(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Reset global_time_program to _DEFAULT_DAILY_PROGRAM from const.py.

        T-03-09: A deep copy is used so the runtime_config never shares list
                 references with the module-level default (each day's period list
                 must be independent).
        """
        entry.runtime_data.runtime_config["global_time_program"] = (
            copy.deepcopy(_DEFAULT_DAILY_PROGRAM)
        )
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_reset_time_program


def _make_ws_reset_room_to_global_program(entry: ClimateManagerConfigEntry):
    """Factory: create reset_room_to_global_program handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/reset_room_to_global_program",
            vol.Required("room_id"): str,
        }
    )
    @websocket_api.async_response
    async def ws_reset_room_to_global_program(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Deep-copy global_time_program into rooms[room_id].time_program and set room_mode=custom.

        T-03-09: setdefault + direct assignment pattern ensures only the targeted room's
                 time_program and room_mode keys are modified; other rooms and other top-level
                 keys (period_temperatures, persons, global_mode, global_time_program) are untouched.
        T-03-09: copy.deepcopy ensures the room and global program never share list references.
        """
        runtime_config = entry.runtime_data.runtime_config
        room_id = msg["room_id"]
        global_time_program = runtime_config.get("global_time_program", {})
        room = runtime_config.setdefault("rooms", {}).setdefault(room_id, {})
        room["room_mode"] = "custom"
        room["time_program"] = copy.deepcopy(global_time_program)
        await entry.runtime_data.store.async_save(runtime_config)
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_reset_room_to_global_program


# ---------------------------------------------------------------------------
# Zone CRUD commands (Plan 05-01)
# ---------------------------------------------------------------------------


def _make_ws_create_zone(entry: ClimateManagerConfigEntry):
    """Factory: create create_zone handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/create_zone",
            vol.Required("name"): str,
        }
    )
    @websocket_api.async_response
    async def ws_create_zone(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Create a new heating zone, persist, and re-evaluate.

        D-01: new zone mode defaults to MODE_TIME_PROGRAM.
        D-02: time_program is a deepcopy of the current global_time_program.
        D-03: returns full zone config {zone_id, name, mode, time_program}.
        D-06: write-then-evaluate pattern.
        """
        runtime_config = entry.runtime_data.runtime_config
        zone_id = str(uuid.uuid4())
        new_zone = {
            "name": msg["name"],
            "mode": MODE_TIME_PROGRAM,
            "time_program": copy.deepcopy(
                runtime_config["global_time_program"]
            ),
        }
        zones_backup = copy.deepcopy(runtime_config.get("zones", {}))
        runtime_config.setdefault("zones", {})[zone_id] = new_zone
        try:
            await entry.runtime_data.store.async_save(runtime_config)
        except Exception as exc:  # noqa: BLE001
            runtime_config["zones"] = zones_backup
            connection.send_error(
                msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
            )
            return
        connection.send_result(
            msg["id"],
            {
                "zone_id": zone_id,
                "name": new_zone["name"],
                "mode": new_zone["mode"],
                "time_program": new_zone["time_program"],
            },
        )
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_create_zone


def _make_ws_rename_zone(entry: ClimateManagerConfigEntry):
    """Factory: create rename_zone handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/rename_zone",
            vol.Required("zone_id"): str,
            vol.Required("name"): str,
        }
    )
    @websocket_api.async_response
    async def ws_rename_zone(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Rename a zone (custom or Default Zone), persist, and re-evaluate.

        D-05: zone_id="default" routes to runtime_config["default_zone_name"].
        T-05-01: the "default" sentinel is handled BEFORE zones dict access so
                 the Default Zone never appears as a key in zones{}.
        """
        runtime_config = entry.runtime_data.runtime_config
        if msg["zone_id"] == "default":
            name_backup = runtime_config.get("default_zone_name")
            runtime_config["default_zone_name"] = msg["name"]
            try:
                await entry.runtime_data.store.async_save(runtime_config)
            except Exception as exc:  # noqa: BLE001
                runtime_config["default_zone_name"] = name_backup
                connection.send_error(
                    msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
                )
                return
        else:
            if msg["zone_id"] not in runtime_config.get("zones", {}):
                connection.send_error(
                    msg["id"],
                    websocket_api.ERR_NOT_FOUND,
                    f"Zone {msg['zone_id']!r} not found",
                )
                return
            zones_backup = copy.deepcopy(runtime_config.get("zones", {}))
            runtime_config["zones"][msg["zone_id"]]["name"] = msg["name"]
            try:
                await entry.runtime_data.store.async_save(runtime_config)
            except Exception as exc:  # noqa: BLE001
                runtime_config["zones"] = zones_backup
                connection.send_error(
                    msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
                )
                return
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_rename_zone


def _make_ws_set_zone_mode(entry: ClimateManagerConfigEntry):
    """Factory: create set_zone_mode handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_zone_mode",
            vol.Required("zone_id"): str,
            vol.Required("mode"): vol.In(VALID_MODES),
        }
    )
    @websocket_api.async_response
    async def ws_set_zone_mode(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Set a custom zone's mode, persist, and re-evaluate.

        T-05-02: vol.In(VALID_MODES) schema gate rejects invalid modes before handler runs.
        Note: global_mode (Default Zone) is mutated via set_global_mode; zone_id="default"
              is not supported here and routes to ERR_NOT_FOUND.
        """
        runtime_config = entry.runtime_data.runtime_config
        if msg["zone_id"] not in runtime_config.get("zones", {}):
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_FOUND,
                f"Zone {msg['zone_id']!r} not found",
            )
            return
        zones_backup = copy.deepcopy(runtime_config.get("zones", {}))
        runtime_config["zones"][msg["zone_id"]]["mode"] = msg["mode"]
        try:
            await entry.runtime_data.store.async_save(runtime_config)
        except Exception as exc:  # noqa: BLE001
            runtime_config["zones"] = zones_backup
            connection.send_error(
                msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
            )
            return
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_zone_mode


def _make_ws_delete_zone(entry: ClimateManagerConfigEntry):
    """Factory: create delete_zone handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/delete_zone",
            vol.Required("zone_id"): str,
        }
    )
    @websocket_api.async_response
    async def ws_delete_zone(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Delete a custom zone; migrate all rooms in it to the Default Zone.

        T-05-06: rooms loop (pop) runs BEFORE del zones[zone_id] (Pitfall 1 ordering).
        T-05-07: CR-01 snapshot of both zones AND rooms before any mutation; restore both on
                 ValueError from store.async_save (validate_zone_assignment inside async_save).
        T-05-11: room_cfg.pop("zone_id", None) — never assigns None (D-06 sparse model).
        """
        runtime_config = entry.runtime_data.runtime_config
        zone_id = msg["zone_id"]

        # Guard: zone must exist
        if zone_id not in runtime_config.get("zones", {}):
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_FOUND,
                f"Zone {zone_id!r} not found",
            )
            return

        # CR-01: snapshot BOTH zones and rooms before any mutation
        zones_backup = copy.deepcopy(runtime_config.get("zones", {}))
        rooms_backup = copy.deepcopy(runtime_config.get("rooms", {}))

        # T-05-06: migrate rooms FIRST (pop zone_id), THEN remove zone entry (Pitfall 1)
        for room_cfg in runtime_config.get("rooms", {}).values():
            if room_cfg.get("zone_id") == zone_id:
                room_cfg.pop("zone_id", None)  # T-05-11: pop, never assign None

        del runtime_config["zones"][zone_id]

        try:
            await entry.runtime_data.store.async_save(runtime_config)
        except ValueError as exc:
            # CR-01: restore BOTH snapshots on failure
            runtime_config["zones"] = zones_backup
            runtime_config["rooms"] = rooms_backup
            connection.send_error(
                msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc)
            )
            return

        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_delete_zone


def _make_ws_set_zone_time_program(entry: ClimateManagerConfigEntry):
    """Factory: create set_zone_time_program handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_zone_time_program",
            vol.Required("zone_id"): str,
            vol.Required("program"): dict,
        }
    )
    @websocket_api.async_response
    async def ws_set_zone_time_program(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Validate and persist the time program for a custom zone.

        Zone existence is checked first so that a non-existent zone_id returns
        ERR_NOT_FOUND rather than ERR_INVALID_FORMAT when both conditions are true.
        Program validation still runs BEFORE any mutation (Pitfall 6 / T-05-08).
        """
        runtime_config = entry.runtime_data.runtime_config

        # Zone existence check first — most specific error condition
        if msg["zone_id"] not in runtime_config.get("zones", {}):
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_FOUND,
                f"Zone {msg['zone_id']!r} not found",
            )
            return

        # Validate BEFORE any mutation (Pitfall 6 / T-05-08)
        ok, err = validate_daily_program(msg["program"])
        if not ok:
            connection.send_error(
                msg["id"], websocket_api.ERR_INVALID_FORMAT, err
            )
            return

        zones_backup = copy.deepcopy(runtime_config.get("zones", {}))
        runtime_config["zones"][msg["zone_id"]]["time_program"] = msg["program"]
        try:
            await entry.runtime_data.store.async_save(runtime_config)
        except Exception as exc:  # noqa: BLE001
            runtime_config["zones"] = zones_backup
            connection.send_error(
                msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
            )
            return
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_zone_time_program


def _make_ws_reset_zone_time_program(entry: ClimateManagerConfigEntry):
    """Factory: create reset_zone_time_program handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/reset_zone_time_program",
            vol.Required("zone_id"): str,
            vol.Required("target"): vol.In(["default", "global"]),
        }
    )
    @websocket_api.async_response
    async def ws_reset_zone_time_program(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Reset a zone's time_program from 'default' or 'global' target.

        T-05-09 / Pitfall 2: copy.deepcopy enforced for both branches so the zone's
        program never shares list references with the source (module constant or
        runtime global_time_program).
        """
        runtime_config = entry.runtime_data.runtime_config

        if msg["zone_id"] not in runtime_config.get("zones", {}):
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_FOUND,
                f"Zone {msg['zone_id']!r} not found",
            )
            return

        zones_backup = copy.deepcopy(runtime_config.get("zones", {}))
        if msg["target"] == "default":
            # Pitfall 5: deepcopy the module constant, never assign directly
            runtime_config["zones"][msg["zone_id"]]["time_program"] = (
                copy.deepcopy(_DEFAULT_DAILY_PROGRAM)
            )
        else:
            # target == "global": deepcopy from current runtime global_time_program (Pitfall 2)
            runtime_config["zones"][msg["zone_id"]]["time_program"] = (
                copy.deepcopy(runtime_config["global_time_program"])
            )

        try:
            await entry.runtime_data.store.async_save(runtime_config)
        except Exception as exc:  # noqa: BLE001
            runtime_config["zones"] = zones_backup
            connection.send_error(
                msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
            )
            return
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_reset_zone_time_program


# ---------------------------------------------------------------------------
# Subscription command
# ---------------------------------------------------------------------------


def _make_ws_subscribe_status(entry: ClimateManagerConfigEntry):
    """Factory: create subscribe_status handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/subscribe_status",
        }
    )
    @callback
    def ws_subscribe_status(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Subscribe to coordinator status push events.

        Registers a hass.bus listener in connection.subscriptions so HA
        automatically calls unsub() on connection close (RESEARCH A3 — verified in venv).
        Acknowledges the subscription immediately, then forwards fired events.
        """
        msg_id = msg["id"]

        @callback
        def _forward_status(event) -> None:  # noqa: ANN001
            connection.send_message(
                websocket_api.event_message(msg_id, event.data)
            )

        # HA calls unsub() for all connection.subscriptions values on close (A3)
        connection.subscriptions[msg_id] = hass.bus.async_listen(
            f"{DOMAIN}_status_update", _forward_status
        )
        # Acknowledge the subscription immediately
        connection.send_message(websocket_api.result_message(msg_id))

    return ws_subscribe_status


# ---------------------------------------------------------------------------
# Calibration config command (Plan 09-03, CALIB-01)
# ---------------------------------------------------------------------------


def _make_ws_set_calibration_config(entry: ClimateManagerConfigEntry):
    """Factory: create set_calibration_config handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_calibration_config",
            vol.Required("enabled"): bool,
        }
    )
    @websocket_api.async_response
    async def ws_set_calibration_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Persist calibration_enabled toggle to runtime_config.

        T-09-01: vol.Required("enabled"): bool in the schema rejects non-bool
                 payloads before the handler runs (T-03-04 parity).
        T-09-02: sensor and TRV entity_ids are read server-side from
                 runtime_config["rooms"] — never from the WS payload.
        No async_evaluate trigger — calibration runs on the next scheduled
        cycle (RESEARCH Pitfall 4).
        """
        old_value = entry.runtime_data.runtime_config.get("calibration_enabled")
        entry.runtime_data.runtime_config["calibration_enabled"] = msg[
            "enabled"
        ]
        try:
            await entry.runtime_data.store.async_save(
                entry.runtime_data.runtime_config
            )
        except Exception as exc:  # noqa: BLE001
            entry.runtime_data.runtime_config["calibration_enabled"] = old_value
            connection.send_error(
                msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
            )
            return
        connection.send_result(msg["id"], {"success": True})
        # NOTE: no async_evaluate trigger — calibration runs on the
        # next scheduled cycle (RESEARCH Pitfall 4)

    return ws_set_calibration_config


def _make_ws_get_calibration_status(entry: ClimateManagerConfigEntry):
    """Factory: create get_calibration_status handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/get_calibration_status",
        }
    )
    @websocket_api.async_response
    async def ws_get_calibration_status(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Return per-TRV calibration status for the Options card table.

        For every TRV entity across all managed rooms, returns:
          - entity_id, friendly_name
          - supports_calibration (bool)
          - last_applied_delta (float, or null if never calibrated this run)
          - last_calibrated_at (ISO timestamp, or null if never calibrated this run)
        """
        coordinator = entry.runtime_data.coordinator
        rooms = entry.runtime_data.rooms
        entity_reg = er.async_get(hass)

        from homeassistant.helpers import area_registry as ar  # noqa: PLC0415

        area_reg = ar.async_get(hass)
        room_auto_sensors = entry.runtime_data.room_auto_sensors

        trvs = []
        for area_id, entity_ids in rooms.items():
            # Mirror ws_get_status sensor resolution
            _area = area_reg.async_get_area(area_id)
            auto = room_auto_sensors.get(area_id, {})
            temp_sensor = getattr(
                _area, "temperature_entity_id", None
            ) or auto.get("temperature")
            room_temperature: float | None = None
            if temp_sensor:
                s = hass.states.get(temp_sensor)
                if s and s.state not in ("unavailable", "unknown"):
                    try:
                        room_temperature = float(s.state)
                    except (ValueError, TypeError):
                        pass

            # Tado X: zone climate entity is room-level, not per physical TRV.
            # Find Radiator Valve X devices (physical TRVs) for this area and
            # show those instead. The zone climate entity is used only for
            # temperature reading.
            valve_devices = get_tado_valve_devices(hass, area_id)

            # Find the tado_x zone climate entity for temperature reading
            zone_entity_id: str | None = None
            zone_trv_temp: float | None = None
            for eid in entity_ids:
                if not is_trv_entity(hass, eid):
                    continue
                r = entity_reg.async_get(eid)
                if r and r.platform == "tado_x":
                    zone_entity_id = eid
                    zs = hass.states.get(eid)
                    if zs:
                        ct = zs.attributes.get("current_temperature")
                        if ct is not None:
                            try:
                                zone_trv_temp = float(ct)
                            except (ValueError, TypeError):
                                pass
                    break

            # Emit one row per physical Radiator Valve X device
            for device in valve_devices:
                dev_id = device["device_id"]
                trvs.append(
                    {
                        "entity_id": zone_entity_id,
                        "device_id": dev_id,
                        "area_id": area_id,
                        "friendly_name": device["name"],
                        "supports_calibration": True,
                        "trv_temperature": zone_trv_temp,
                        "room_temperature": room_temperature,
                        "last_applied_delta": (
                            coordinator._calibration_last_delta.get(dev_id)
                        ),
                        "last_calibrated_at": (
                            coordinator._calibration_last_changed.get(dev_id)
                        ),
                    }
                )

            # Emit non-tado_x climate entities (other platforms, e.g. Matter)
            for entity_id in entity_ids:
                if not is_trv_entity(hass, entity_id):
                    continue
                reg_entry = entity_reg.async_get(entity_id)
                if reg_entry and reg_entry.platform == "tado_x":
                    continue  # zone entity replaced by valve_devices above

                state = hass.states.get(entity_id)
                if reg_entry and reg_entry.name:
                    friendly_name: str = reg_entry.name
                elif state:
                    friendly_name = state.attributes.get(
                        "friendly_name", entity_id
                    )
                else:
                    friendly_name = entity_id

                trv_temperature: float | None = None
                if state:
                    ct = state.attributes.get("current_temperature")
                    if ct is not None:
                        try:
                            trv_temperature = float(ct)
                        except (ValueError, TypeError):
                            pass

                trvs.append(
                    {
                        "entity_id": entity_id,
                        "area_id": area_id,
                        "friendly_name": friendly_name,
                        "supports_calibration": False,
                        "trv_temperature": trv_temperature,
                        "room_temperature": room_temperature,
                        "last_applied_delta": (
                            coordinator._calibration_last_delta.get(entity_id)
                        ),
                        "last_calibrated_at": (
                            coordinator._calibration_last_changed.get(entity_id)
                        ),
                    }
                )

        # Read tado_x scan interval from its coordinator
        # (stored in hass.data["tado_x"][entry_id] — standard hass.data pattern)
        tado_x_scan_interval: int | None = None
        tado_x_entries = list(hass.config_entries.async_entries("tado_x"))
        if tado_x_entries:
            tado_x_coord = hass.data.get("tado_x", {}).get(
                tado_x_entries[0].entry_id
            )
            if tado_x_coord and hasattr(tado_x_coord, "_scan_interval"):
                tado_x_scan_interval = int(tado_x_coord._scan_interval)

        connection.send_result(
            msg["id"],
            {"trvs": trvs, "tado_x_scan_interval": tado_x_scan_interval},
        )

    return ws_get_calibration_status
