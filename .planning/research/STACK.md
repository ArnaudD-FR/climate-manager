# Technology Stack

**Project:** Climate Manager — v1.1 Heating Zones
**Researched:** 2026-05-26
**Overall confidence:** HIGH — analysis based on direct inspection of the existing codebase

---

## Verdict: No New Libraries Required

Every capability the zones feature needs is already present in the installed stack.
The additions are purely data-model, logic, and UI work within the existing tools.

---

## Existing Stack (Unchanged)

### Python Backend

| Technology | Version | Purpose | Status for Zones |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Integration language | No change |
| `homeassistant.helpers.storage.Store` | HA 2026.x | Persistent config (schedule data) | Schema extension only — add `"zones": {}` top-level key to `DEFAULT_CONFIG` in `const.py` |
| `homeassistant.components.websocket_api` | HA 2026.x | Panel ↔ backend protocol | Add ~5 new command handlers in `websocket.py` using the existing factory pattern |
| `homeassistant.helpers.event.async_track_time_interval` | HA 2026.x | Periodic schedule evaluation | No change — coordinator already polls every minute |
| `voluptuous` | (HA-bundled) | WebSocket payload validation | Add zone_id str schema to new WS handlers; same pattern as `room_id` today |

### Frontend Panel

| Technology | Version | Purpose | Status for Zones |
|------------|---------|---------|-----------------|
| Lit 3.x | ^3 | Web component framework | Add new `<climate-manager-zones-tab>` and `<climate-manager-zone-card>` components |
| TypeScript 5.x | ^5 | Type safety | Extend `types.ts` with `ZoneConfig`, `ZoneStatus` interfaces; update `ClimateConfig` |
| Vite 5.x | ^5 | Build tool | No change — single-file build pipeline unchanged |
| `home-assistant-js-websocket` | latest | WS client in panel | Extend `WsClient` class with zone CRUD methods; no library change |

---

## What Changes (Data Model + Logic Only)

### Storage schema extension (`const.py`)

Add one top-level key to `DEFAULT_CONFIG`:

```python
"zones": {}   # sparse: zone_id → { name, mode, time_program }
```

Zone sub-schema per entry:
```python
{
  "zone_id": {
    "name": str,                    # user-visible name
    "mode": str,                    # "off" | "time_program" | "time_program_presences"
    "time_program": DailyProgram,   # same per-day dict as global_time_program
  }
}
```

Room schema extension — add one optional key to each room config entry:
```python
"zone_id": str | None   # foreign key into zones dict; None = unassigned (falls back to global)
```

Bump `STORAGE_VERSION` from 2 → 3 to signal migration. Add migration block in `ClimateManagerStore.async_load()` that populates `"zones": {}` and sets `"zone_id": None` on all existing rooms — a no-op that produces a valid v3 schema from any v2 store.

### Coordinator logic extension (`coordinator.py`)

The evaluation order becomes: room zone config → global config. Concretely, in both `_evaluate_time_program` and `_evaluate_time_program_presences`, before selecting `daily_program`:

1. Look up the room's `zone_id`.
2. If a zone exists and its mode is not `MODE_OFF`, resolve `daily_program` from the zone's `time_program`.
3. If the zone mode is `MODE_OFF`, push frost protection (same as global MODE_OFF path).
4. If no zone is assigned, fall through to existing global logic (no behavior change for unassigned rooms).

This is a localized change inside the existing per-room loops — no new abstractions needed.

### Status payload extension (`coordinator.py` + `websocket.py`)

`get_status` and `subscribe_status` push `zones_status` alongside `rooms_status` — a list of `{ zone_id, name, mode, active_period }` entries for live UI feedback.

### New WebSocket commands (`websocket.py`)

Five new commands follow the existing factory pattern exactly:

| Command | Direction | Description |
|---------|-----------|-------------|
| `climate_manager/create_zone` | Write | Create a named zone with default mode + program |
| `climate_manager/update_zone` | Write | Rename, change mode, or update time program |
| `climate_manager/delete_zone` | Write | Remove zone; clear `zone_id` from all assigned rooms |
| `climate_manager/assign_room_zone` | Write | Set `rooms[room_id].zone_id` |
| `climate_manager/get_zones` | Read | Return full `zones` dict (already in `get_config`, but explicit getter for convenience) |

All five: `mutate runtime_config → store.async_save → send_result → coordinator.async_evaluate` — identical write pattern to existing handlers.

### New TypeScript types (`types.ts`)

```typescript
export interface ZoneConfig {
  name: string;
  mode: string;
  time_program?: DailyProgram;
}

export interface ClimateConfig {
  // ... existing fields unchanged ...
  zones: Record<string, ZoneConfig>;   // ADD: zone_id → config
}

// Extend RoomConfig:
export interface RoomConfig {
  room_mode?: "global" | "frost_protection" | "custom";
  time_program?: DailyProgram | null;
  zone_id?: string | null;              // ADD: zone assignment
}
```

### New frontend components

Two new Lit components following the exact structure of `rooms-tab.ts` and `room-card.ts`:

- `zones-tab.ts` — tab container: zone list + "Create zone" action; no new UI patterns
- `zone-card.ts` — per-zone card: name, mode picker, time-bar for zone program, room assignment list

The existing `<climate-manager-time-bar>` component is reused unchanged for zone programs. The existing mode picker UI in `global-settings-tab.ts` is reused for zone mode.

`WsClient` (`ws-client.ts`) gets five new typed methods matching the five new WS commands — same `sendMessagePromise` pattern.

---

## Alternatives Considered

| Decision | Chosen | Alternative | Why Not |
|----------|--------|-------------|---------|
| Zone storage location | Extend existing Store key | Separate `Store` instance per zone | Single `Store.async_save` call persists the entire config atomically; separate stores complicate cross-key consistency (e.g. delete_zone must also update rooms) |
| Zone ID scheme | UUID string generated at create time | HA area registry re-use | Zones are not HA areas; they are virtual groups. Using area IDs would couple zone existence to HA area lifecycle |
| Frontend zone UI | New tab (peer to Rooms / Persons) | Inline section within Rooms tab | Zones have their own time program and mode — needs the same screen real-estate as Rooms; embedding in the rooms tab would cause cramped UI |
| STORAGE_VERSION bump | Yes — 2 → 3 | Skip migration | The migration is trivial (add empty `zones: {}`, touch nothing else) and prevents any async_load code from crashing on a missing key |

---

## What NOT to Add

- No new PyPI packages — the integration has zero external deps; this feature must not introduce any.
- No separate WebSocket subscription for zones — zones are low-frequency config data; they are served via `get_config` on load and after any mutation.
- No HA area registry coupling for zones — zones are integration-internal groups; they do not map to HA areas.
- No dedicated zone evaluation engine class — zone evaluation is 5–10 lines inside the existing coordinator loops; extracting it into a new module would be premature abstraction.

---

## Sources

- Direct codebase inspection: `const.py`, `storage.py`, `coordinator.py`, `websocket.py`, `schedule.py`, `frontend/src/types.ts`, `frontend/src/ws-client.ts`, `frontend/package.json`
- Existing pattern reference: room CRUD (set_room_config, reset_room_to_global_program) and person CRUD (set_person_config) handlers in websocket.py
