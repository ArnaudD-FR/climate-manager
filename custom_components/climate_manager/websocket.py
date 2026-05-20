"""Climate Manager WebSocket command handlers.

Registers 8 WebSocket commands for the panel ↔ backend protocol:
- get_status: returns global_mode, active_period, present_persons, rooms_status
- get_config: returns full runtime_config
- set_global_mode: mutates global_mode, persists, re-evaluates
- set_period_temperatures: updates all 4 period temperatures
- set_time_program: validates and persists the global per-day program
- set_room_config: sparse-merges into rooms[room_id]
- set_person_config: sparse-merges into persons[person_id]
- subscribe_status: registers a push listener in connection.subscriptions

All handlers access state via the entry closure (never hass.data[DOMAIN]).
Write handlers follow the write-then-evaluate pattern:
  mutate runtime_config → store.async_save → coordinator.async_evaluate → send_result.

Security:
- T-03-04: vol.In/vol.Coerce schema gates reject invalid payloads before handler runs
- T-03-05: validate_daily_program gate rejects partial programs before any save
- T-03-06: HA WebSocket auth gate handles unauthenticated access (not our concern)
- T-03-07: get_status reads only configured sensor entity IDs; every hass.states.get
           result is guarded for None before reading state
- T-03-09: write handlers mutate only targeted sub-keys; DEFAULT_CONFIG never imported
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

if TYPE_CHECKING:
    from . import ClimateManagerConfigEntry

from .const import (
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
)
from .schedule import validate_daily_program

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
    websocket_api.async_register_command(hass, _make_ws_set_period_temperatures(entry))
    websocket_api.async_register_command(hass, _make_ws_set_time_program(entry))
    websocket_api.async_register_command(hass, _make_ws_set_room_config(entry))
    websocket_api.async_register_command(hass, _make_ws_set_person_config(entry))
    websocket_api.async_register_command(hass, _make_ws_subscribe_status(entry))


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

        # Build per-room status list
        from homeassistant.helpers import area_registry as ar  # noqa: PLC0415
        _area_reg = ar.async_get(hass)

        rooms_status = []
        room_configs = runtime_config.get("rooms", {})
        for area_id, entity_ids in rooms.items():
            room_cfg = room_configs.get(area_id, {})
            _area = _area_reg.async_get_area(area_id)
            room_entry: dict = {
                "area_id": area_id,
                "name": _area.name if _area else area_id,
                "entity_ids": entity_ids,
            }

            # Temperature: from configured temperature_sensor, else first TRV's current_temperature
            temp_sensor = room_cfg.get("temperature_sensor")
            if temp_sensor:
                sensor_state = hass.states.get(temp_sensor)
                if sensor_state is not None:
                    room_entry["temperature"] = sensor_state.state
            elif entity_ids:
                trv_state = hass.states.get(entity_ids[0])
                if trv_state is not None:
                    current_temp = trv_state.attributes.get("current_temperature")
                    if current_temp is not None:
                        room_entry["temperature"] = current_temp

            # Humidity: only if humidity_sensor is configured
            humidity_sensor = room_cfg.get("humidity_sensor")
            if humidity_sensor:
                hum_state = hass.states.get(humidity_sensor)
                if hum_state is not None:
                    room_entry["humidity"] = hum_state.state

            # Active period for this room (from coordinator's last result)
            room_entry["active_period"] = active_period

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
        """Return full runtime_config unchanged."""
        connection.send_result(msg["id"], entry.runtime_data.runtime_config)

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
        await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
        await entry.runtime_data.coordinator.async_evaluate()
        connection.send_result(msg["id"], {"success": True})

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
        period_temps = entry.runtime_data.runtime_config.setdefault("period_temperatures", {})
        for key, value in temps.items():
            period_temps[key] = value
        await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
        await entry.runtime_data.coordinator.async_evaluate()
        connection.send_result(msg["id"], {"success": True})

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
            connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, err)
            return  # T-03-05: return BEFORE save/evaluate

        entry.runtime_data.runtime_config["global_time_program"] = msg["program"]
        await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
        await entry.runtime_data.coordinator.async_evaluate()
        connection.send_result(msg["id"], {"success": True})

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
        """
        (
            entry.runtime_data.runtime_config
            .setdefault("rooms", {})
            .setdefault(msg["room_id"], {})
            .update(msg["config"])
        )
        await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
        await entry.runtime_data.coordinator.async_evaluate()
        connection.send_result(msg["id"], {"success": True})

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
        (
            entry.runtime_data.runtime_config
            .setdefault("persons", {})
            .setdefault(msg["person_id"], {})
            .update(msg["config"])
        )
        await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
        await entry.runtime_data.coordinator.async_evaluate()
        connection.send_result(msg["id"], {"success": True})

    return ws_set_person_config


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
