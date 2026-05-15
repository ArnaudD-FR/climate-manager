# Architecture

**Project:** Climate Manager — Home Assistant Custom Integration
**Researched:** 2026-05-15
**Confidence:** HIGH

---

## Component Map

| Component | File | Responsibility | Communicates With |
|-----------|------|----------------|-------------------|
| Config Entry | `__init__.py`, `config_flow.py` | Integration install, entry point, lifecycle | HA core, all internal components |
| Storage | `storage.py` | Load/save JSON config; schema migrations | Coordinator, WebSocket handlers |
| Scheduling Engine | `scheduler.py` | Pure evaluation: room → temperature at time T | Coordinator only |
| Presence Engine | `presence.py` | Pure evaluation: person → present/absent at time T | Coordinator only |
| Coordinator | `coordinator.py` | Control loop, event listeners, TRV service calls | Storage, engines, HA services, HA event bus |
| WebSocket Handlers | `websocket.py` | CRUD API for frontend, triggers coordinator refresh | Storage, Coordinator |
| Frontend Panel | `frontend/` | Configuration UI (Lit + TypeScript + Vite) | WebSocket handlers only |
| Panel Registration | `panel.py` | Serve JS, register sidebar panel | HA frontend component |

---

## Architecture Layers

The canonical 5-layer stack for this integration:

```
┌─────────────────────────────────────────┐
│  Frontend Panel (Lit / TypeScript)      │  UI layer
├─────────────────────────────────────────┤
│  WebSocket Handlers                     │  API layer
├─────────────────────────────────────────┤
│  Coordinator (control loop)             │  Orchestration layer
├─────────────────────────────────────────┤
│  Scheduler + Presence engines           │  Pure logic layer
├─────────────────────────────────────────┤
│  Storage (JSON Store)                   │  Persistence layer
└─────────────────────────────────────────┘
```

Each layer has a single, testable responsibility. The Scheduler and Presence engines are pure Python — no HA dependencies — making them fully unit-testable without a running HA instance.

---

## Data Flow

**Config write (user saves changes in UI):**
```
User action → WS handler → Storage.save → Coordinator.refresh → Scheduler → TRV service call
```

**Scheduled period transition:**
```
async_track_point_in_time fires → Coordinator evaluates all rooms → TRV service calls → reschedule next boundary
```

**Presence change:**
```
person.* state_changed event → Coordinator evaluates affected rooms only → TRV service calls
```

**Panel startup:**
```
Panel element mounts → 3 sendMessagePromise calls (get_config, get_rooms, get_persons) → render
```

**HA restart recovery:**
```
async_added_to_hass → evaluate schedule for current datetime → push correct temp to all TRVs immediately
```

---

## Data Model (Storage JSON)

```json
{
  "version": 1,
  "global_mode": "time_program",
  "period_modes": {
    "frost_protection": 7.0,
    "reduced": 18.0,
    "normal": 20.0,
    "comfort": 22.0
  },
  "global_time_program": {
    "weekday_groups": [
      {
        "weekdays": [0, 1, 2, 3, 4],
        "periods": [
          {"start_time": "06:00", "mode": "normal"},
          {"start_time": "22:00", "mode": "reduced"}
        ]
      },
      {
        "weekdays": [5, 6],
        "periods": [
          {"start_time": "08:00", "mode": "comfort"},
          {"start_time": "23:00", "mode": "reduced"}
        ]
      }
    ]
  },
  "rooms": {
    "<room_id>": {
      "name": "Living Room",
      "climate_entity_ids": ["climate.living_room_trv"],
      "time_program": null
    }
  },
  "persons": {
    "<person_entity_id>": {
      "mode": "schedule",
      "associated_room_ids": ["<room_id>"],
      "schedule": {
        "weekday_groups": [
          {
            "weekdays": [0, 1, 2, 3, 4],
            "periods": [
              {"start_time": "08:00", "present": false},
              {"start_time": "18:00", "present": true}
            ]
          }
        ]
      }
    }
  }
}
```

Notes:
- `time_program: null` on a room means it inherits the global time program
- Weekday integers follow ISO (0 = Monday, 6 = Sunday)
- `persons[id].mode` is `schedule | present | absent`
- Storage uses HA `Store` helper — written to `.storage/climate_manager`

---

## Key Implementation Patterns

**Schedule evaluation — use `async_track_point_in_time`, not `async_track_time_interval`**

Fire the evaluator exactly at the next period boundary — not every N seconds. Polling causes unnecessary TRV service calls every N seconds; point-in-time scheduling is constant-overhead regardless of room count.

**Presence tracking — use `async_track_state_change_event`**

`async_track_state_change` is deprecated since HA 2024 and removed in 2025.5. Use the `_event` variant. On presence change, only re-evaluate rooms associated with that person.

**TRV control — two sequential service calls**

```python
# Step 1: Ensure heat mode
await hass.services.async_call(
    "climate", "set_hvac_mode",
    {"entity_id": entity_id, "hvac_mode": "heat"},
    blocking=True,
)
# Step 2: Set target temperature
await hass.services.async_call(
    "climate", "set_temperature",
    {"entity_id": entity_id, "temperature": target_temp},
    blocking=True,
)
```

**WebSocket API — batch commands, not per-field**

Register `climate_mgr/get_config`, `climate_mgr/set_config`, `climate_mgr/get_rooms`, `climate_mgr/set_room`, `climate_mgr/get_persons`, `climate_mgr/set_person`. Batch mutations to avoid per-keystroke TRV writes.

**Storage — two layers**

- `ConfigEntry.options` (via OptionsFlow): integration-level settings shown in HA Integrations UI
- `homeassistant.helpers.storage.Store`: complex schedule/room/person data structures

**Anti-pattern:** Do not use `hass.data[DOMAIN]` as a persistence layer — in-memory only, lost on restart.

---

## Suggested Build Order

```
Phase 1 — Foundation
  manifest.json, const.py, __init__.py skeleton, config_flow.py (minimal),
  Storage layer with schema and load/save, HACS structure

Phase 2 — Scheduling Engine (pure Python, unit-testable without HA)
  scheduler.py + presence.py + unit tests

Phase 3 — Coordinator and TRV Control  ← critical path
  coordinator.py: startup evaluation, point-in-time scheduling,
  presence event listener, TRV service calls
  Validate end-to-end with real TRVs before proceeding

Phase 4 — WebSocket API
  websocket.py: register climate_mgr/* commands (get/set config, rooms, persons)

Phase 5 — Frontend Panel
  Lit + TypeScript + Vite, panel registration, 3-section UI

Phase 6 — HA Services (optional convenience)
  climate_manager.set_mode for use in automations
```

**Build order rationale:** Phase 3 must be validated with real TRVs before Phase 4 begins. The WebSocket API shape depends on what the coordinator actually needs; discovering a coordinator flaw mid-frontend forces both layers to change simultaneously.

---

## Open Questions / Phase Flags

- **Phase 5 (Frontend):** Confirm whether `frontend.async_register_panel()` requires the JS file to be in `www/` relative to the integration directory or the HA config `www/`. Official docs suggest integration `www/` is mounted at `/api/climate_manager/static/` — verify exact path and registration signature against current HA source.
- **Phase 3 (Coordinator):** Verify `async_track_point_in_time` behaviour across DST transitions. HA uses `dt_util.now()` which is timezone-aware — confirm the scheduled callback fires at the correct local time after a clock change.
- **Phase 4 (WebSocket):** Confirm voluptuous schema requirements for WebSocket handler registration in latest HA.
