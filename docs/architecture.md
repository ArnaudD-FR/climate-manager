# Climate Manager — Architecture Reference

> Keep this document current. Refresh it before completing every milestone.

## Overview

Climate Manager is a Home Assistant custom integration with two layers:

- **Python backend** (`custom_components/climate_manager/`) — all control logic,
  persistence, schedule evaluation, and WebSocket API. Since Phase 16 the
  control logic is organised as a **domain model** (`EvalContext`, `Zone`/
  `ZoneMode`, `Person`/`PersonMode`, `Room`, `TRV`/`TRVGroup`); the coordinator
  builds this object graph and delegates each evaluation cycle to it.
- **Frontend panel** (`frontend/`) — Lit 3 / TypeScript SPA compiled to a single
  `custom_components/climate_manager/www/panel.js` bundle

The two layers communicate exclusively over HA's WebSocket API. No REST
endpoints are used.

---

## Python Backend

### Entry point — `__init__.py`

`async_setup_entry` wires the integration in order:

1. Construct `ClimateManagerStore` and load merged config
2. Run discovery (rooms, persons, room sensors)
3. Assign all to `entry.runtime_data` (typed `ClimateManagerData` dataclass)
4. Wire preheat `Store` and load persisted samples
5. Construct `ClimateManagerCoordinator` and run immediate evaluation (restart
   recovery — INFRA-03)
6. Register minute-polling scheduler via `async_track_time_interval`
7. Register 19 WebSocket commands via `cm_ws.async_register_commands`
8. Serve `www/` directory as static path (`cache_headers=False`)
9. Register sidebar panel via `panel_custom.async_register_panel`
10. Register entity/device registry listeners for live room re-discovery

`async_unload_entry` cancels the scheduler and registry listeners before
unloading platforms.

`ClimateManagerData` is a typed dataclass stored on `entry.runtime_data`. The
global `hass.data` dict is never used.

---

### Configuration schema — `const.py`

Single source of truth for all constants and `DEFAULT_CONFIG`.

| Concept             | Values                                                         |
| ------------------- | -------------------------------------------------------------- |
| Zone modes          | `off`, `time_program`, `time_program_presences`                |
| Period temperatures | `frost_protection`, `reduced`, `normal`, `comfort`             |
| Presence modes      | `scheduled`, `force_present`, `force_absent`, `ha`, `calendar` |

**Zone model**: Default Zone (room has no `zone_id`) + custom zones (UUID string
keys in `config["zones"]`). Sparse — never store `zone_id: null`. The mode is a
property of the **zone**, not the room — Phase 15 (D-07) removed room-level
modes entirely; every room follows its owning zone's mode and schedule.

Default temperatures: frost=5°C, reduced=18°C, normal=20°C, comfort=22°C.

---

### Storage — `storage.py`

`ClimateManagerStore` wraps `homeassistant.helpers.storage.Store`.

- **Key**: `climate_manager`, schema version 2
- **Load**: sparse-merge stored data over `DEFAULT_CONFIG` deep copy;
  `period_temperatures` merges key-by-key; `rooms`/`persons`/`zones` replace
  wholesale. Post-merge fills any empty day with default schedule periods. Runs
  field migrations (presence mode renames, `preheat_lead_minutes` →
  `wakeup_advance_minutes`).
- **Save**: calls `validate_zone_assignment()` before every write.

Preheat convergence samples persist separately under key
`climate_manager_preheat` (a bare `Store`, not `ClimateManagerStore`).

---

### Control loop — `coordinator.py`

Since Phase 16 the coordinator is a thin orchestrator over the domain model (see
[Domain model](#domain-model) below). It owns two responsibilities: building the
object graph and driving each evaluation cycle.

**`_build_domain_objects(config)`** constructs the `Zone` / `Person` / `Room` /
`TRVGroup` graph from `runtime_config`. It is called on first evaluate and again
whenever a WS handler changes the config — detected by a cheap structural
**fingerprint** (`_config_fingerprint`); an unchanged fingerprint skips the
rebuild. On rebuild, anti-spam log state is **carried forward** from the old
objects (`Zone._current_period`/`_current_mode_name`, `Person._last_home`) so a
config edit does not replay log lines.

`ClimateManagerCoordinator.async_evaluate()` runs every minute and on startup:

```text
1. now = dt_util.now(); rebuild domain objects if fingerprint changed
2. ctx = EvalContext(now, hass, period_temperatures)   # per-cycle cache
3. for zone in zones: await zone.evaluate(ctx)
     → ZoneMode.evaluate resolves the period and, for each room,
       await room.apply_setpoint(period, temp, ctx)
         → TRVGroup.push → TRV.push_temperature (anti-flap + manual-hold)
     → Zone emits OBS-01 INFO log on (period, mode) change
4. for person not yet in ctx._presence_cache: await person.evaluate(ctx)
     → Person emits OBS-01 INFO log on home/away flip
5. _check_ha_tracker_warnings (persistent notifications)
6. snapshot status fields: _last_room_periods (per-room), _last_zone_periods,
   _last_present_persons
7. per-room calibration pass (Room.calibrate_trvs) if calibration_enabled
8. per-room pre-heat pass (Room.compute_preheat)
9. Fire climate_manager_status_update bus event
```

**Anti-flap push** (`TRV.push_temperature`): skip if `last_pushed == desired`.
**Manual-override hold** (D-03): if the TRV reports a setpoint ≠ last pushed, a
user adjusted it manually — hold until the next period transition. **Pre-heat**
(`Room.compute_preheat`): triggers early heating ahead of the next occupied time
(`schedule.next_occupied_at` for scheduled persons, else the next zone
setpoint-increase). Lead time is learned (average of the last 5 convergence
samples) and bounded by `preheat_max_lead_minutes` (default 120 min). Skipped
when the room is already at/above the upcoming setpoint
(`current_temp ≥ upcoming − PREHEAT_CONVERGENCE_THRESHOLD`). **Calibration**
(`Room.calibrate_trvs`): incremental offset toward the room reference sensor.
Tado X Radiator Valve X uses the device-based offset call; other TRVs use
entity-based. Clamped ±5°C with a threshold guard to avoid jitter.

---

### Domain model

The control logic lives in five collaborating object families. Each `*Mode` base
class is a plain class (not an ABC) holding a `weakref` back-link to its owner;
unimplemented overloads raise `assert False`.

| File              | Classes                                                                  | Role                                                                                                                                       |
| ----------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `eval_context.py` | `EvalContext`                                                            | Per-cycle cache passed through the whole call chain: `now`, `period_temperatures`, lazy `_calendar_cache`, `_presence_cache` (D-02)        |
| `zone.py`         | `Zone`, `ZoneModeOff`, `ZoneModeTimeProgram`, `ZoneModeProgramPresences` | Resolves the active period; pushes setpoints to its rooms; emits the `zone` OBS-01 log on `(period, mode)` change                          |
| `person.py`       | `Person`, `PersonModeScheduled/HA/Calendar/ForcePresent/ForceAbsent`     | Evaluates presence (cached in `ctx`); emits the `presence` OBS-01 log on home/away flip and on user mode change                            |
| `room.py`         | `Room`                                                                   | Owns `_trv_groups`, `assigned_persons`, per-room pre-heat/calibration state, `_last_period` (status badge); `apply_setpoint`/`apply_off`   |
| `trv.py`          | `TRV`, `TRVGroup`                                                        | `TRVGroup` is assembled once (resolving `matter_mappings` + boiler filter); `TRV` owns `last_pushed` anti-flap and the `heating` DEBUG log |

`ZoneModeProgramPresences` resolves an effective period **per room** (empty room
→ reduced; occupied → schedule via `compute_occupied_temp`), so each `Room`
tracks its own `_last_period` for the status badge rather than a single
zone-level value. `TRVGroup.from_room_config` applies `is_trv_entity` so
boiler/HVAC entities (`max_temp > 45 °C`) are never push targets, and dedups
Matter entities already covered by a `tado_x` mapping.

#### OBS-01 structured log traces

Emitted at `INFO` (heating at `DEBUG`) under
`custom_components.climate_manager.*`. Each family is anti-spammed — it logs
only on a real state change, never every tick.

| Logger            | Format                                                                                 | Fires on                                          |
| ----------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `zone`            | `zone \| zone=<name> state=<old>[<mode>]→<new>[<mode>] reason=<why>`                   | period or mode change (`time_program:` / `user:`) |
| `presence`        | `presence \| person=<name> home=<bool> reason=<mode>` / `mode=<old>→<new> reason=user` | `_last_home` flip / user mode change              |
| `heating` (DEBUG) | `heating \| room=<name> temp=<T>°C zone=<name> slot=<period>`                          | setpoint actually pushed to a TRV                 |

To surface these, set `custom_components.climate_manager: info` (or `debug`)
under `logger:` in `configuration.yaml` — custom integrations are filtered at
`WARNING` by default.

---

### Discovery — `discovery.py`

| Function                  | Returns                                            |
| ------------------------- | -------------------------------------------------- |
| `discover_rooms()`        | `{area_id: [climate_entity_ids]}`                  |
| `discover_persons()`      | `[person.* entity_ids]`                            |
| `discover_room_sensors()` | `{area_id: {"temperature": eid, "humidity": eid}}` |

Registry listeners (`entity_registry_updated`, `device_registry_updated`) re-run
discovery live when climate entities are created/removed or a device's area
assignment changes.

---

### TRV control — `trv.py`

| Function                                            | Purpose                                                                                                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `set_trv_temperature(hass, entity_id, temp)`        | Step 1: ensure `hvac_mode=heat`; Step 2: `set_temperature`. Two-step workaround for Tado X Matter auto mode.                                      |
| `set_trv_off(hass, entity_id)`                      | `set_hvac_mode=off`                                                                                                                               |
| `set_trv_offset(hass, entity_id, offset)`           | Entity-based temperature offset calibration                                                                                                       |
| `set_trv_offset_by_device(hass, device_id, offset)` | Tado X Radiator Valve X device-based calibration                                                                                                  |
| `supports_hvac_off(hass, entity_id)`                | Inspects `hvac_modes` attribute                                                                                                                   |
| `supports_offset_calibration(hass, entity_id)`      | Checks `temperature_offset` attribute                                                                                                             |
| `is_trv_entity(hass, entity_id)`                    | True for room TRVs; False for boiler/HVAC entities (`max_temp > 45 °C`). Applied in `TRVGroup.from_room_config` and every status/calibration path |
| `get_tado_valve_devices(hass, area_id)`             | Returns Tado X Radiator Valve X devices in an area                                                                                                |

The module also defines the `TRV` and `TRVGroup` domain classes (see
[Domain model](#domain-model)). `TRVGroup` is assembled once per room and holds
the resolved push targets; `TRV.push_temperature` wraps the two-call sequence
with the anti-flap guard, manual-override hold, and the `heating` DEBUG log. The
free functions above remain the low-level service-call layer the classes call
into.

---

### Schedule evaluation — `schedule.py`

Pure Python — no HA imports. All async HA calls stay in `coordinator.py`.

| Function                                               | Purpose                                            |
| ------------------------------------------------------ | -------------------------------------------------- |
| `evaluate_schedule(program, now)`                      | Active period mode at the given time               |
| `resolve_presence(person_config, now, ...)`            | Evaluates person schedule → present/absent         |
| `resolve_calendar_presence(events, ...)`               | Calendar-based presence with gap handling          |
| `compute_occupied_temp(program, now, is_present, ...)` | PERSON-07/08/09 rules (occupied window, sandwich)  |
| `next_occupied_at(person_config, ...)`                 | Next scheduled "present" transition (for pre-heat) |
| `validate_daily_program(program)`                      | Validates a 7-day program before mutation          |

These are pure helpers; the per-mode dispatch lives in `person.py`'s
`PersonMode` subclasses (Phase 16), which call into them:

- `PersonModeHA` — reads HA `person.*` entity state directly (`== "home"`)
- `PersonModeCalendar` — resolves via `ctx.calendar_events()` +
  `resolve_calendar_presence()`
- `PersonModeScheduled` — `resolve_presence()`
- `PersonModeForcePresent` / `PersonModeForceAbsent` — constant `True` / `False`

---

### WebSocket API — `websocket.py`

19 commands registered under `climate_manager/` prefix. All handlers access
state via the config-entry closure (never `hass.data[DOMAIN]`).

**Write pattern**: mutate `runtime_config` → `store.async_save()` →
`send_result` → `coordinator.async_evaluate()` (background task).
`set_zone_mode` / `set_person_config` additionally call `change_mode()` on the
live domain object (captured **before** the `await`) so the OBS-01 user-driven
log fires before the rebuild. The Default Zone is addressed by the sentinel
`zone_id="default"` (writes `default_zone.*`); `set_global_mode` /
`reset_time_program` / `reset_room_to_*` were removed in Phases 14–15.

| Category    | Commands                                                                                                                             |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Read        | `get_status`, `get_config`, `get_calibration_status`                                                                                 |
| Global      | `set_period_temperatures`, `set_time_program`, `reset_period_temperatures`                                                           |
| Room        | `set_room_config`                                                                                                                    |
| Person      | `set_person_config`                                                                                                                  |
| Zone        | `create_zone`, `rename_zone`, `set_zone_mode`, `set_zone_preheat`, `delete_zone`, `set_zone_time_program`, `reset_zone_time_program` |
| Calibration | `set_calibration_config`                                                                                                             |
| Matter      | `set_matter_mapping`, `suggest_matter_mappings`                                                                                      |
| Push        | `subscribe_status`                                                                                                                   |

`subscribe_status` registers a listener for `climate_manager_status_update` bus
events and pushes the status payload to the panel connection on each coordinator
cycle.

---

## Frontend Panel

### Build toolchain — `frontend/`

| File             | Purpose                                                        |
| ---------------- | -------------------------------------------------------------- |
| `vite.config.ts` | Bundles to `../custom_components/climate_manager/www/panel.js` |
| `tsconfig.json`  | TypeScript 5 config                                            |
| `package.json`   | Lit 3 + home-assistant-js-websocket deps                       |

Lit is bundled into `panel.js` — no dependency on HA's own Lit instance.

### Panel registration

- Static URL: `/climate_manager_panel` → `www/` directory
- Component name: `climate-manager-panel` (must match `customElements.define`)
- Registered via `panel_custom.async_register_panel` in `async_setup_entry`
- `manifest.json` declares `["http", "frontend", "panel_custom"]` as
  dependencies

### Source structure — `frontend/src/`

| File/component                                 | Role                                                                                                   |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `panel.ts`                                     | Root `<climate-manager-panel>` element; receives `hass` from HA; owns tab routing                      |
| `ws-client.ts`                                 | Typed WS helpers (thin wrappers over `hass.connection`)                                                |
| `types.ts`                                     | TypeScript interfaces for all WS message shapes (`ClimateConfig`, `StatusPayload`, `RoomStatus`, etc.) |
| `toast.ts`                                     | Global toast notification utility                                                                      |
| `shared-styles.ts`                             | Shared CSS design tokens                                                                               |
| `components/rooms-tab.ts` + `room-card.ts`     | Per-room config and schedule editor                                                                    |
| `components/zone-tab.ts`                       | Zone management (create/rename/delete/mode/schedule)                                                   |
| `components/persons-tab.ts` + `person-card.ts` | Person presence config and schedule editor                                                             |
| `components/global-settings-tab.ts`            | Global mode, period temps, calibration                                                                 |
| `components/presence-mode.ts`                  | Presence mode selector widget                                                                          |
| `components/time-bar.ts`                       | Interactive weekly schedule bar (drag to resize periods)                                               |
| `components/week-parity.ts`                    | Even/odd week selector for biweekly schedules                                                          |
| `components/search-picker.ts`                  | Entity/area search dropdown                                                                            |

HA native elements broken in HA 2026.x:

- `ha-select` — use native `<select>` instead
- `ha-tabs` / `paper-tab` — use CSS button tabs + manual panel header
- `ha-textfield` — use native `<input type="number">` with label + suffix span

---

## Data flow

```text
HA event loop (1 min tick)
  → coordinator.async_evaluate()
      → EvalContext(now, …)                    # per-cycle cache
      → zone.evaluate(ctx)                      # resolve period per room
          → room.apply_setpoint(period, temp)  # → TRVGroup.push → TRV
      → person.evaluate(ctx)                    # presence (cached)
      → OBS-01 INFO logs on state change
      → hass.bus.async_fire(status_update)    # notify subscribed panels

Panel (initial load)
  → climate_manager/get_config               # full config snapshot
  → climate_manager/subscribe_status         # register live push

Panel (mutation)
  → climate_manager/set_*
      → store.async_save()
      → coordinator.async_evaluate()         # immediate re-evaluation
                                             # → status_update pushed
```

---

## Key design decisions

| Decision                                     | Rationale                                                                                                                            |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `entry.runtime_data` typed dataclass         | No global `hass.data` dict; auto-cleaned on unload                                                                                   |
| Anti-flap push + manual override hold        | Avoids redundant TRV calls; respects manual adjustments                                                                              |
| Sparse storage model                         | Absent keys fall back to `DEFAULT_CONFIG`; forward-compatible                                                                        |
| Zone model (absent `zone_id` = Default Zone) | ZONE-04: room belongs to at most one zone by structure                                                                               |
| Domain model + fingerprint rebuild           | Coordinator delegates to `Zone`/`Person`/`Room`/`TRV` objects; rebuilt only when config changes; anti-spam log state carried forward |
| `EvalContext` per cycle                      | One object threads `now` + calendar/presence caches through the call chain (D-02)                                                    |
| OBS-01 anti-spammed logs                     | `zone`/`presence`/`heating` lines fire only on real state changes                                                                    |
| Pre-heat learned lead                        | Average of last 5 convergence samples per room; bounded by max lead; skipped when room already warm                                  |
| Calendar cache per cycle                     | One `get_events` call per unique calendar entity per minute tick                                                                     |
| WebSocket over REST                          | Session already established; no auth token management from JS                                                                        |
| Lit bundled in panel.js                      | Avoids HA Lit version conflicts; larger bundle is acceptable trade-off                                                               |
