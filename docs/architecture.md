# Climate Manager — Architecture Reference

> Keep this document current. Refresh it before completing every milestone.

## Overview

Climate Manager is a Home Assistant custom integration with two layers:

- **Python backend** (`custom_components/climate_manager/`) — all control logic,
  persistence, schedule evaluation, and WebSocket API
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
7. Register 18 WebSocket commands via `cm_ws.async_register_commands`
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
| Global modes        | `off`, `time_program`, `time_program_presences`                |
| Period temperatures | `frost_protection`, `reduced`, `normal`, `comfort`             |
| Room modes          | `global`, `frost_protection`, `custom`                         |
| Presence modes      | `scheduled`, `force_present`, `force_absent`, `ha`, `calendar` |

**Zone model**: Default Zone (room has no `zone_id`) + custom zones (UUID string
keys in `config["zones"]`). Sparse — never store `zone_id: null`.

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

`ClimateManagerCoordinator.async_evaluate()` runs every minute and on startup:

```text
1. Reset calendar cache; prefetch calendar events (async, parallel)
2. Compute present persons
3. Check HA tracker warnings (persistent notifications)
4. PASS 1 — _compute_desired_temps
   Priority: frost_protection room_mode > zone MODE_OFF
           > custom room schedule > zone schedule
5. PASS 2 — _apply_presence_overrides
   Only for time_program_presences zones; mutates desired_temps in place
6. _push_temperatures
   push-on-change + manual override hold + off-capable TRV support
7. _async_calibrate (if calibration_enabled)
8. _async_preheat (per room)
9. Fire climate_manager_status_update bus event
```

**Push-on-change** (`_push_if_changed`): skip if `_last_pushed == desired`.
**Manual override hold** (D-03): if TRV reports a setpoint ≠ last pushed, a user
adjusted it manually — hold until the next period transition. **Pre-heat**
(`_async_preheat_room`): triggers early heating based on a learned lead time
(average of last 5 convergence samples). Bounded by `preheat_max_lead_minutes`
(default 120 min). Samples recorded on convergence; discarded if period starts
before room reaches target. **Calibration** (`_async_calibrate`): incremental
offset toward room reference sensor. Tado X Radiator Valve X uses device-based
offset call; other TRVs use entity-based. Clamped ±5°C. Threshold guard avoids
jitter.

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

| Function                                            | Purpose                                                                                                      |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `set_trv_temperature(hass, entity_id, temp)`        | Step 1: ensure `hvac_mode=heat`; Step 2: `set_temperature`. Two-step workaround for Tado X Matter auto mode. |
| `set_trv_off(hass, entity_id)`                      | `set_hvac_mode=off`                                                                                          |
| `set_trv_offset(hass, entity_id, offset)`           | Entity-based temperature offset calibration                                                                  |
| `set_trv_offset_by_device(hass, device_id, offset)` | Tado X Radiator Valve X device-based calibration                                                             |
| `supports_hvac_off(hass, entity_id)`                | Inspects `hvac_modes` attribute                                                                              |
| `supports_offset_calibration(hass, entity_id)`      | Checks `temperature_offset` attribute                                                                        |
| `is_trv_entity(hass, entity_id)`                    | Guards against non-climate entities in discovered rooms                                                      |
| `get_tado_valve_devices(hass, area_id)`             | Returns Tado X Radiator Valve X devices in an area                                                           |

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

Person presence modes at evaluation time:

- `ha` — reads HA `person.*` entity state directly (`== "home"`)
- `calendar` — resolves from prefetched `_calendar_cache`
- `scheduled` / `force_present` / `force_absent` — `resolve_presence()`

---

### WebSocket API — `websocket.py`

18 commands registered under `climate_manager/` prefix. All handlers access
state via the config-entry closure (never `hass.data[DOMAIN]`).

**Write pattern**: mutate `runtime_config` → `store.async_save()` →
`send_result` → `coordinator.async_evaluate()` (background task).

| Category    | Commands                                                                                                            |
| ----------- | ------------------------------------------------------------------------------------------------------------------- |
| Read        | `get_status`, `get_config`, `get_calibration_status`                                                                |
| Global      | `set_global_mode`, `set_period_temperatures`, `set_time_program`, `reset_period_temperatures`, `reset_time_program` |
| Room        | `set_room_config`, `reset_room_to_global_program`                                                                   |
| Person      | `set_person_config`                                                                                                 |
| Zone        | `create_zone`, `rename_zone`, `set_zone_mode`, `delete_zone`, `set_zone_time_program`, `reset_zone_time_program`    |
| Calibration | `set_calibration_config`                                                                                            |
| Push        | `subscribe_status`                                                                                                  |

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
      → schedule.evaluate_schedule()          # compute desired temps
      → trv.set_trv_temperature()             # push to TRVs
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

| Decision                                     | Rationale                                                              |
| -------------------------------------------- | ---------------------------------------------------------------------- |
| `entry.runtime_data` typed dataclass         | No global `hass.data` dict; auto-cleaned on unload                     |
| Push-on-change + manual override hold        | Avoids redundant TRV calls; respects manual adjustments                |
| Sparse storage model                         | Absent keys fall back to `DEFAULT_CONFIG`; forward-compatible          |
| Zone model (absent `zone_id` = Default Zone) | ZONE-04: room belongs to at most one zone by structure                 |
| Two-pass evaluation (PASS 1 + PASS 2)        | Presence override is cleanly separated from schedule baseline          |
| Pre-heat learned lead                        | Average of last 5 convergence samples per room; bounded by max lead    |
| Calendar cache per cycle                     | One `get_events` call per unique calendar entity per minute tick       |
| WebSocket over REST                          | Session already established; no auth token management from JS          |
| Lit bundled in panel.js                      | Avoids HA Lit version conflicts; larger bundle is acceptable trade-off |
