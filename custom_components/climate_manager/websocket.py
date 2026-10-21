# SPDX-License-Identifier: MIT
"""Climate Manager WebSocket command handlers.

Registers 20 WebSocket commands for the panel ↔ backend protocol:
- get_status: delegates to coordinator._build_status_payload() (D-07)
- get_config: returns full runtime_config plus derived climate_entities,
  matter_entities, and pairable_entities lists (A2 Option A/C), and the
  boiler_candidates list (boiler.boiler_candidates)
- set_period_temperatures: updates all 4 period temperatures
- set_time_program: validates and persists the global per-day program
- set_room_config: sparse-merges into rooms[room_id]
- set_person_config: sparse-merges into persons[person_id]
- subscribe_status: registers a push listener in connection.subscriptions
- reset_period_temperatures: resets period_temperatures to DEFAULT_PERIOD_TEMPERATURES
- create_zone: creates new heating zone with UUID, persists; seeds time_program
  from default_zone.time_program (Pitfall 1)
- rename_zone: renames custom zone or Default Zone (zone_id="default" → default_zone.name)
- set_zone_mode: sets zone mode via vol.In(VALID_MODES); zone_id="default" writes
  default_zone.mode (D-08)
- set_zone_preheat: sets preheat_enabled at zone scope (GAP-01; zone_id="default"
  writes default_zone.preheat_enabled — D-11)
- delete_zone: migrates rooms to Default Zone (pop), removes zone, CR-01 snapshot
  rollback
- set_zone_time_program: validates program via validate_daily_program before any
  mutation
- reset_zone_time_program: restores zone time_program from 'default' or 'global'
  target; zone_id="default" resets default_zone.time_program (D-09)
- set_calibration_config: persists calibration_enabled bool (D-10, CALIB-01)
- set_matter_mapping: persists sparse matter_mappings[entity_id] and
  triggers coordinator listener refresh (D-15/D-16, MCALIB-01/02)
- suggest_matter_mappings: returns the vendors' auto-detected Matter
  pairings (read-only, no mutation)
- set_boiler_config: sets or clears the controlled boiler (climate, switch
  or input_boolean) and its min on/off durations

Removed in Phase 15 (D-06):
- reset_room_to_default_zone_program: rooms no longer have independent
  schedules; all rooms follow their zone exclusively

Removed in Phase 14 (D-08/D-09):
- set_global_mode: use set_zone_mode(zone_id="default") instead
- reset_time_program: use reset_zone_time_program(zone_id="default") instead

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
- T-13-04: set_matter_mapping filters matter_entity_ids to climate.* strings
           before storage (Pitfall 7 — non-climate entity_ids silently dropped)
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

from .boiler import boiler_candidates
from .const import (
    BOILER_DOMAINS,
    BOILER_MAX_MIN_MINUTES,
    DEFAULT_BOILER_MIN_OFF_MINUTES,
    DEFAULT_BOILER_MIN_ON_MINUTES,
    DEFAULT_BOILER_OFF_HVAC_MODE,
    DEFAULT_BOILER_ON_HVAC_MODE,
    DEFAULT_PERIOD_TEMPERATURES,
    DOMAIN,
    MODE_TIME_PROGRAM,
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
    PREHEAT_BOOST_FACTOR_MAX,
    VALID_MODES,
    _DEFAULT_DAILY_PROGRAM,
)
from .schedule import validate_daily_program
from .trv import is_trv_entity
from .vendors import cloud_polling, pairable_entities, suggest_mappings


def _friendly_name(hass: HomeAssistant, entity_id: str) -> str:
    """Registry name, else the state's friendly_name, else entity_id."""
    reg = er.async_get(hass).async_get(entity_id)
    if reg is not None and reg.name:
        return reg.name
    state = hass.states.get(entity_id)
    if state is not None:
        return state.attributes.get("friendly_name", entity_id)
    return entity_id


def _current_temperature(hass: HomeAssistant, entity_id: str) -> float | None:
    """current_temperature attribute of a climate entity, if numeric."""
    state = hass.states.get(entity_id)
    value = state.attributes.get("current_temperature") if state else None
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def async_register_commands(
    hass: HomeAssistant, entry: ClimateManagerConfigEntry
) -> None:
    """Register all Climate Manager WebSocket commands.

    Called once from async_setup_entry. Commands auto-unregister on entry unload
    (RESEARCH Pattern 3 — no explicit cleanup needed in async_unload_entry).
    """
    websocket_api.async_register_command(hass, _make_ws_get_status(entry))
    websocket_api.async_register_command(hass, _make_ws_get_config(entry))
    # D-08: set_global_mode removed; set_zone_mode handles zone_id="default"
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
    # D-09: reset_time_program removed; reset_zone_time_program handles
    # zone_id="default"
    # D-06 (Phase 15): reset_room_to_default_zone_program removed; rooms follow
    # their zone exclusively
    websocket_api.async_register_command(hass, _make_ws_create_zone(entry))
    websocket_api.async_register_command(hass, _make_ws_rename_zone(entry))
    websocket_api.async_register_command(hass, _make_ws_set_zone_mode(entry))
    websocket_api.async_register_command(hass, _make_ws_set_zone_preheat(entry))
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
    websocket_api.async_register_command(
        hass, _make_ws_set_matter_mapping(entry)
    )
    websocket_api.async_register_command(
        hass, _make_ws_suggest_matter_mappings(entry)
    )
    websocket_api.async_register_command(
        hass, _make_ws_set_boiler_config(entry)
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
        """Return global status delegating to coordinator._build_status_payload().

        D-07 (Phase 14): ws_get_status delegates to _build_status_payload()
        eliminating the sensor-read duplication. The payload includes:
        - zones: {default: {mode, active_period}, <uuid>: {mode, active_period}}
        - present_persons: list of present person entity_ids
        - rooms_status: per-room entries with sensor data, preheat fields

        T-03-07: sensor entity IDs are read from stored config (never from
                 payload); every hass.states.get() result is guarded for None
                 inside _build_status_payload.
        """
        coordinator = entry.runtime_data.coordinator
        payload = coordinator._build_status_payload()
        connection.send_result(msg["id"], payload)

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
        """Return full runtime_config plus derived entity lists.

        D-25: climate_entities is the sorted list of all climate.* entity IDs
        from the HA entity registry. A2 Option A/C: matter_entities and
        pairable_entities are derived subsets filtered by entity registry
        platform. All three are merged into a NEW dict — runtime_config is
        never mutated so derived keys never pollute persistent storage
        (T-13-06).
        """
        entity_reg = er.async_get(hass)
        climate_reg_entries = [
            reg_entry
            for reg_entry in entity_reg.entities.values()
            if reg_entry.entity_id.split(".")[0] == "climate"
        ]
        climate_entities = sorted(e.entity_id for e in climate_reg_entries)
        # A2 Option A/C: derive platform-filtered lists from entity registry.
        # Merged into a NEW payload dict — runtime_config never mutated so
        # these derived keys never pollute persistent storage (T-13-06/D-25).
        matter_entities = sorted(
            e.entity_id for e in climate_reg_entries if e.platform == "matter"
        )
        # Entities a vendor can pair with Matter entities.
        pairable = pairable_entities(
            hass, [e.entity_id for e in climate_reg_entries]
        )
        payload = {
            **entry.runtime_data.runtime_config,
            "boiler_candidates": boiler_candidates(hass),
            "climate_entities": climate_entities,
            "matter_entities": matter_entities,
            "pairable_entities": pairable,
        }
        connection.send_result(msg["id"], payload)

    return ws_get_config


# ---------------------------------------------------------------------------
# Write commands
# ---------------------------------------------------------------------------


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

        # Phase 14 (D-01): the default zone time program lives under
        # default_zone["time_program"] (flat key removed in D-01).
        entry.runtime_data.runtime_config["default_zone"]["time_program"] = msg[
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

        T-03-09: setdefault + update pattern ensures only the targeted room's
                 keys are modified; other rooms and DEFAULT_CONFIG keys are
                 preserved.
        CR-01: snapshot rooms before mutation so we can roll back if
               async_save raises (validate_zone_assignment inside async_save
               may raise ValueError on invalid zone_id assignments — ZONE-04).
        GAP-01: preheat_enabled moved to zone scope; this command no longer
                accepts or persists preheat_enabled on the room. Use
                set_zone_preheat to toggle the enable flag.
        """
        rooms_backup = copy.deepcopy(
            entry.runtime_data.runtime_config.get("rooms", {})
        )
        # zone_id: null from the frontend signals 'move room to Default Zone'
        # — pop the key per D-06 sparse model (gap CR-03 fix from VERIFY 06).
        incoming_config = msg["config"]
        if "zone_id" in incoming_config and incoming_config["zone_id"] is None:
            incoming_config.pop("zone_id")
            entry.runtime_data.runtime_config.setdefault(
                "rooms", {}
            ).setdefault(msg["room_id"], {}).pop("zone_id", None)
        # D-01 / T-12-06: validate sparse room preheat keys before persist.
        # preheat_max_lead_minutes must be an int in [0, 480]; drop otherwise.
        if "preheat_max_lead_minutes" in incoming_config:
            val = incoming_config["preheat_max_lead_minutes"]
            if not (
                isinstance(val, int)
                and not isinstance(val, bool)
                and 0 <= val <= 480
            ):
                incoming_config.pop("preheat_max_lead_minutes")
        # preheat_boost_factor must be a number in [0, 5]; drop otherwise.
        if "preheat_boost_factor" in incoming_config:
            val = incoming_config["preheat_boost_factor"]
            if not (
                isinstance(val, (int, float))
                and not isinstance(val, bool)
                and 0 <= val <= PREHEAT_BOOST_FACTOR_MAX
            ):
                incoming_config.pop("preheat_boost_factor")
        # GAP-01: preheat_enabled is no longer a valid room key; silently drop
        # it so legacy callers don't persist the deprecated room-level flag.
        incoming_config.pop("preheat_enabled", None)
        # Phase 15 (D-07): room_mode is no longer a valid room key; silently
        # drop it so legacy callers or residual frontend sends don't
        # persist the field.
        incoming_config.pop("room_mode", None)
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
        """Sparse-merge config into persons[person_id].

        Accepted keys (all optional, additive sparse-merge per D-09):
          mode: str
          room_ids: list[str]
          schedule / schedule_even / schedule_odd: DailyProgram
          schedule_type: "single" | "even_odd"
          calendar_config: {
            "entity_id": str,       # must start with "calendar." (T-11-06)
            "event_means": "absent" | "present",
          }
          wakeup_advance_minutes: int (0-480, clamped; D-02)

        T-03-09: same setdefault + update pattern as set_room_config.
        """
        # SCHED-05: auto-seed schedule_even/schedule_odd when switching to
        # even_odd. Guard: only seed when schedule_even is not already in
        # storage — an existing empty {} schedule must not be overwritten
        # (key-absence check, not truthiness — Pitfall 1 in RESEARCH.md).
        incoming = dict(msg["config"])
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
        # T-11-06 (ASVS V5): reject calendar_config whose entity_id does
        # not start with "calendar." — prevents persisting or calling
        # unintended entity targets (_prefetch_calendars prefix-checks
        # too, but validate here at the trust boundary).
        if "calendar_config" in incoming:
            cal_cfg = incoming["calendar_config"]
            eid = (
                cal_cfg.get("entity_id", "")
                if isinstance(cal_cfg, dict)
                else ""
            )
            event_means = (
                cal_cfg.get("event_means", "absent")
                if isinstance(cal_cfg, dict)
                else "absent"
            )
            if not (isinstance(eid, str) and eid.startswith("calendar.")):
                incoming.pop("calendar_config")
            elif event_means not in ("absent", "present"):
                # T-11-06 (WR-03): reject invalid event_means values to
                # prevent silent inversion of presence logic in schedule.py.
                incoming.pop("calendar_config")
            else:
                # Validate gap_handling and gap_threshold_minutes.
                # Sparse model: only normalize keys the client explicitly sent.
                if "gap_handling" in cal_cfg:
                    gap = cal_cfg["gap_handling"]
                    if gap not in ("exact", "day_span", "threshold"):
                        cal_cfg.pop("gap_handling")
                        cal_cfg.pop("gap_threshold_minutes", None)
                    elif gap == "threshold":
                        try:
                            thr = int(cal_cfg.get("gap_threshold_minutes", 30))
                            cal_cfg["gap_threshold_minutes"] = max(
                                0, min(480, thr)
                            )
                        except (TypeError, ValueError):
                            cal_cfg["gap_threshold_minutes"] = 30
                    else:
                        cal_cfg.pop("gap_threshold_minutes", None)
                else:
                    cal_cfg.pop("gap_threshold_minutes", None)
        # D-02: legacy preheat_lead_minutes → wakeup_advance_minutes rename.
        # Map old key to new key so existing clients keep working.
        if "preheat_lead_minutes" in incoming:
            incoming["wakeup_advance_minutes"] = incoming.pop(
                "preheat_lead_minutes"
            )
        # T-12-07: clamp wakeup_advance_minutes to [0, 480]; drop if invalid.
        if "wakeup_advance_minutes" in incoming:
            val = incoming["wakeup_advance_minutes"]
            if (
                isinstance(val, int)
                and not isinstance(val, bool)
                and 0 <= val <= 480
            ):
                pass  # valid — keep
            else:
                incoming.pop("wakeup_advance_minutes")
        (
            entry.runtime_data.runtime_config.setdefault("persons", {})
            .setdefault(msg["person_id"], {})
            .update(incoming)
        )
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        # Emit OBS-01 mode-change log on the live Person when mode changes.
        if "mode" in incoming:
            coord = entry.runtime_data.coordinator
            live_person = coord._persons.get(msg["person_id"])
            if live_person is not None:
                live_person.change_mode(incoming["mode"])
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
        D-02: time_program is a deepcopy of the current default_zone program.
        D-03: returns full zone config {zone_id, name, mode, time_program}.
        D-06: write-then-evaluate pattern.
        Pitfall 1 (Phase 14): seed from default_zone["time_program"], not
        from the old flat key (removed in D-01).
        """
        runtime_config = entry.runtime_data.runtime_config
        zone_id = str(uuid.uuid4())
        new_zone = {
            "name": msg["name"],
            "mode": MODE_TIME_PROGRAM,
            "time_program": copy.deepcopy(
                runtime_config["default_zone"]["time_program"]
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

        D-11 (Phase 14): zone_id="default" routes to
        runtime_config["default_zone"]["name"] (not the old flat
        default_zone_name key).
        T-05-01: the "default" sentinel is handled BEFORE zones dict access so
                 the Default Zone never appears as a key in zones{}.
        """
        runtime_config = entry.runtime_data.runtime_config
        if msg["zone_id"] == "default":
            name_backup = runtime_config["default_zone"].get("name")
            runtime_config["default_zone"]["name"] = msg["name"]
            try:
                await entry.runtime_data.store.async_save(runtime_config)
            except Exception as exc:  # noqa: BLE001
                runtime_config["default_zone"]["name"] = name_backup
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
        """Set a zone's mode (Default Zone or custom), persist, re-evaluate.

        D-08 (Phase 14): zone_id="default" is now supported — writes to
        runtime_config["default_zone"]["mode"] via T-05-01 sentinel pattern.
        T-05-02: vol.In(VALID_MODES) schema gate rejects invalid modes before
                 handler runs, regardless of zone_id value.
        T-14-05: sentinel check before zones dict lookup so Default Zone is
                 never confused with a custom zone UUID.
        Logic lives in coordinator.async_set_zone_mode (shared with the
        zone mode select entity).
        """
        try:
            await entry.runtime_data.coordinator.async_set_zone_mode(
                msg["zone_id"], msg["mode"]
            )
        except KeyError:
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_FOUND,
                f"Zone {msg['zone_id']!r} not found",
            )
            return
        except Exception as exc:  # noqa: BLE001
            connection.send_error(
                msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
            )
            return
        connection.send_result(msg["id"], {"success": True})

    return ws_set_zone_mode


def _make_ws_set_zone_preheat(entry: ClimateManagerConfigEntry):
    """Factory: create set_zone_preheat handler (GAP-01).

    Persists preheat_enabled at zone scope:
    - zone_id="default" → runtime_config["default_zone"]["preheat_enabled"]
      (D-11, Phase 14: was default_zone_preheat_enabled flat key)
    - custom zone_id    → runtime_config["zones"][zone_id]["preheat_enabled"]
    Modelled on _make_ws_rename_zone (dual-path default sentinel + CR-01
    snapshot/rollback).
    Security: T-12-11 — vol schema gates enabled:bool + zone_id:str;
    unknown custom zone_id returns ERR_NOT_FOUND; save failure rolls back.
    """

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_zone_preheat",
            vol.Required("zone_id"): str,
            vol.Required("enabled"): bool,
        }
    )
    @websocket_api.async_response
    async def ws_set_zone_preheat(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Set preheat_enabled on a zone (Default or custom), persist, re-eval.

        T-05-01 pattern: "default" sentinel handled BEFORE zones dict access
        so the Default Zone never appears as a key in zones{}.
        """
        runtime_config = entry.runtime_data.runtime_config
        enabled = bool(msg["enabled"])  # defensive; vol already type-guards
        if msg["zone_id"] == "default":
            # D-11 (Phase 14): write to default_zone sub-dict (was flat key)
            old_val = runtime_config["default_zone"].get("preheat_enabled")
            runtime_config["default_zone"]["preheat_enabled"] = enabled
            try:
                await entry.runtime_data.store.async_save(runtime_config)
            except Exception as exc:  # noqa: BLE001
                runtime_config["default_zone"]["preheat_enabled"] = old_val
                connection.send_error(
                    msg["id"],
                    websocket_api.ERR_UNKNOWN_ERROR,
                    str(exc),
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
            runtime_config["zones"][msg["zone_id"]]["preheat_enabled"] = enabled
            try:
                await entry.runtime_data.store.async_save(runtime_config)
            except Exception as exc:  # noqa: BLE001
                runtime_config["zones"] = zones_backup
                connection.send_error(
                    msg["id"],
                    websocket_api.ERR_UNKNOWN_ERROR,
                    str(exc),
                )
                return
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_zone_preheat


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
        """Validate and persist the time program for a zone.

        Handles zone_id="default" as a sentinel for the Default Zone
        (D-09, T-05-01 pattern). Custom zone existence is checked first so
        that a non-existent zone_id returns ERR_NOT_FOUND rather than
        ERR_INVALID_FORMAT when both conditions are true.
        Program validation runs BEFORE any mutation (Pitfall 6 / T-05-08).
        """
        runtime_config = entry.runtime_data.runtime_config

        # Validate BEFORE any mutation (Pitfall 6 / T-05-08)
        ok, err = validate_daily_program(msg["program"])
        if not ok:
            connection.send_error(
                msg["id"], websocket_api.ERR_INVALID_FORMAT, err
            )
            return

        if msg["zone_id"] == "default":
            dz_backup = copy.deepcopy(
                runtime_config["default_zone"]["time_program"]
            )
            runtime_config["default_zone"]["time_program"] = msg["program"]
            try:
                await entry.runtime_data.store.async_save(runtime_config)
            except Exception as exc:  # noqa: BLE001
                runtime_config["default_zone"]["time_program"] = dz_backup
                connection.send_error(
                    msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
                )
                return
            connection.send_result(msg["id"], {"success": True})
            hass.async_create_task(
                entry.runtime_data.coordinator.async_evaluate()
            )
            return

        # Custom zone — existence check first (most specific error)
        if msg["zone_id"] not in runtime_config.get("zones", {}):
            connection.send_error(
                msg["id"],
                websocket_api.ERR_NOT_FOUND,
                f"Zone {msg['zone_id']!r} not found",
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

        D-09 (Phase 14): zone_id="default" is now supported — resets
        default_zone.time_program to _DEFAULT_DAILY_PROGRAM for both target
        values (there is no separate "global" source after Phase 14 migration).
        T-05-01: sentinel check before zones dict lookup (T-14-05 pattern).
        T-05-09 / Pitfall 2: copy.deepcopy enforced for all branches so the
        zone's program never shares list references with the source (module
        constant or default_zone.time_program).
        """
        runtime_config = entry.runtime_data.runtime_config

        if msg["zone_id"] == "default":
            # D-09: Default Zone sentinel — reset default_zone.time_program.
            # Both target="default" and target="global" reset to the module
            # constant (after Phase 14 there is no separate global source).
            zones_backup = copy.deepcopy(runtime_config.get("default_zone", {}))
            runtime_config["default_zone"]["time_program"] = copy.deepcopy(
                _DEFAULT_DAILY_PROGRAM
            )
            try:
                await entry.runtime_data.store.async_save(runtime_config)
            except Exception as exc:  # noqa: BLE001
                runtime_config["default_zone"] = zones_backup
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
            if msg["target"] == "default":
                # Pitfall 5: deepcopy the module constant, never assign directly
                runtime_config["zones"][msg["zone_id"]]["time_program"] = (
                    copy.deepcopy(_DEFAULT_DAILY_PROGRAM)
                )
            else:
                # target == "global": deepcopy from default_zone.time_program
                # (Phase 14 D-09: flat key removed; default_zone is the source)
                runtime_config["zones"][msg["zone_id"]]["time_program"] = (
                    copy.deepcopy(
                        runtime_config["default_zone"]["time_program"]
                    )
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
          - last_calibrated_at (ISO timestamp, or null if never calibrated this run)
        """
        coordinator = entry.runtime_data.coordinator
        rooms = entry.runtime_data.rooms

        from homeassistant.helpers import area_registry as ar  # noqa: PLC0415

        area_reg = ar.async_get(hass)
        room_auto_sensors = entry.runtime_data.room_auto_sensors
        # Matter valves paired with another entity are calibrated through
        # its rows (same dedup set as TRVGroup).
        matter_mappings: dict[str, list[str]] = (
            entry.runtime_data.runtime_config.get("matter_mappings", {})
        )
        grouped_matter: frozenset[str] = frozenset(
            eid for eids in matter_mappings.values() for eid in eids
        )

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

            # Calibratable offsets, as the vendors resolve them (one row per
            # physical valve when the brand calibrates per device).
            calibrator = coordinator.calibrator if coordinator else None
            targets = calibrator.targets(area_id) if calibrator else []
            covered: set[str] = set()
            for target in targets:
                covered.update(
                    eid
                    for eid in (target.entity_id, target.temp_entity_id)
                    if eid is not None
                )
                trvs.append(
                    {
                        "entity_id": target.entity_id or target.temp_entity_id,
                        "device_id": target.device_id,
                        "area_id": area_id,
                        "friendly_name": (
                            target.name
                            if target.device_id is not None
                            else _friendly_name(hass, target.key)
                        ),
                        "supports_calibration": True,
                        "vendor": target.vendor.label,
                        "trv_temperature": _current_temperature(
                            hass, target.temp_entity_id
                        ),
                        "room_temperature": room_temperature,
                        "current_offset": calibrator.current_offset(target),
                        "last_calibrated_at": calibrator.last_changed.get(
                            target.key
                        ),
                    }
                )

            # TRVs no vendor can calibrate
            for entity_id in entity_ids:
                if not is_trv_entity(hass, entity_id):
                    continue
                if entity_id in covered or entity_id in grouped_matter:
                    continue  # shown via its calibration row
                trvs.append(
                    {
                        "entity_id": entity_id,
                        "device_id": None,
                        "area_id": area_id,
                        "friendly_name": _friendly_name(hass, entity_id),
                        "supports_calibration": False,
                        "vendor": None,
                        "trv_temperature": _current_temperature(
                            hass, entity_id
                        ),
                        "room_temperature": room_temperature,
                        "current_offset": None,
                        "last_calibrated_at": None,
                    }
                )

        connection.send_result(
            msg["id"],
            {
                "trvs": trvs,
                "cloud_polling": cloud_polling(hass),
            },
        )

    return ws_get_calibration_status


def _make_ws_set_matter_mapping(entry: ClimateManagerConfigEntry):
    """Factory: create set_matter_mapping handler.

    D-15/D-16: persists the sparse matter_mappings config and triggers
    atomic listener refresh in the coordinator.
    Security: T-13-04 — filter matter_entity_ids to climate.* only
    (Pitfall 7) before storage; non-climate entity_ids silently dropped.
    """

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_matter_mapping",
            vol.Required("entity_id"): str,
            vol.Required("matter_entity_ids"): list,
        }
    )
    @websocket_api.async_response
    async def ws_set_matter_mapping(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Store or remove the Matter entities paired with an entity.

        T-13-04: filter matter_entity_ids to climate.* strings only before
        storing (Pitfall 7 — rejects sensor.* and other non-climate domains).
        D-01 sparse model: empty filtered list pops the key (never stored
        as []).  D-16: refresh coordinator listeners atomically after persist.
        """
        matter_eids = [
            e
            for e in msg["matter_entity_ids"]
            if isinstance(e, str) and e.startswith("climate.")
        ]
        mappings = entry.runtime_data.runtime_config.setdefault(
            "matter_mappings", {}
        )
        if matter_eids:
            mappings[msg["entity_id"]] = matter_eids
        else:
            # D-01 sparse: absent key = no mapping; never store []
            mappings.pop(msg["entity_id"], None)
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        # D-16: refresh listeners atomically with config change
        coordinator = entry.runtime_data.coordinator
        if coordinator is not None:
            hass.async_create_task(
                coordinator._async_refresh_calibration_listeners()
            )

    return ws_set_matter_mapping


def _make_ws_suggest_matter_mappings(
    entry: ClimateManagerConfigEntry,
):
    """Factory: create suggest_matter_mappings handler."""

    @websocket_api.websocket_command(
        {vol.Required("type"): f"{DOMAIN}/suggest_matter_mappings"}
    )
    @websocket_api.async_response
    async def ws_suggest_matter_mappings(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Return the vendors' suggested Matter pairings (read-only)."""
        result = suggest_mappings(hass)
        connection.send_result(msg["id"], {"mappings": result})

    return ws_suggest_matter_mappings


# ---------------------------------------------------------------------------
# Boiler config command
# ---------------------------------------------------------------------------


def _boiler_config_error(hass: HomeAssistant, msg: dict) -> str | None:
    """Validate a set_boiler_config payload against the live entity."""
    entity_id = msg["entity_id"]
    if entity_id.split(".", 1)[0] not in BOILER_DOMAINS:
        return f"Boiler must be one of: {', '.join(BOILER_DOMAINS)}"
    state = hass.states.get(entity_id)
    if state is None:
        return f"Unknown entity: {entity_id}"
    if not entity_id.startswith("climate."):
        return None
    hvac_modes = state.attributes.get("hvac_modes") or []
    for key in ("on_hvac_mode", "off_hvac_mode"):
        mode = msg.get(key)
        if mode is not None and mode not in hvac_modes:
            return f"{mode} is not a hvac mode of {entity_id}"
    return None


def _make_ws_set_boiler_config(entry: ClimateManagerConfigEntry):
    """Factory: create set_boiler_config handler."""

    minutes = vol.All(int, vol.Range(min=0, max=BOILER_MAX_MIN_MINUTES))

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_boiler_config",
            vol.Required("entity_id"): vol.Any(None, str),
            vol.Optional("on_hvac_mode"): str,
            vol.Optional("off_hvac_mode"): str,
            vol.Optional("min_on_minutes"): minutes,
            vol.Optional("min_off_minutes"): minutes,
        }
    )
    @websocket_api.async_response
    async def ws_set_boiler_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Set (entity_id) or clear (entity_id=None) the boiler.

        The hvac modes only apply to a climate entity and must be among its
        hvac_modes. Rolls back runtime_config if the save fails.
        """
        config = entry.runtime_data.runtime_config
        old_value = copy.deepcopy(config.get("boiler"))
        if msg["entity_id"] is None:
            config.pop("boiler", None)
        else:
            error = _boiler_config_error(hass, msg)
            if error is not None:
                connection.send_error(
                    msg["id"], websocket_api.ERR_INVALID_FORMAT, error
                )
                return
            boiler = {
                "entity_id": msg["entity_id"],
                "min_on_minutes": msg.get(
                    "min_on_minutes", DEFAULT_BOILER_MIN_ON_MINUTES
                ),
                "min_off_minutes": msg.get(
                    "min_off_minutes", DEFAULT_BOILER_MIN_OFF_MINUTES
                ),
            }
            if msg["entity_id"].startswith("climate."):
                boiler["on_hvac_mode"] = msg.get(
                    "on_hvac_mode", DEFAULT_BOILER_ON_HVAC_MODE
                )
                boiler["off_hvac_mode"] = msg.get(
                    "off_hvac_mode", DEFAULT_BOILER_OFF_HVAC_MODE
                )
            config["boiler"] = boiler
        try:
            await entry.runtime_data.store.async_save(config)
        except Exception as exc:  # noqa: BLE001
            if old_value is None:
                config.pop("boiler", None)
            else:
                config["boiler"] = old_value
            connection.send_error(
                msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
            )
            return
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_boiler_config
