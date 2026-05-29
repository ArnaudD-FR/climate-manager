# Architecture Patterns: Multi-Zone Heating Integration

**Domain:** HA custom integration — adding zone-level scheduling to an existing
coordinator-based control loop **Researched:** 2026-05-26 **Confidence:** HIGH —
derived entirely from reading the production codebase, not from external sources

---

## Existing Architecture Snapshot

Before proposing changes, here is the precise shape of the current system so
integration points are unambiguous.

### Data flow (v1.0)

```
HA startup / 1-min tick
  └─ coordinator.async_evaluate()
       ├─ reads runtime_config (global_mode, period_temperatures, global_time_program, rooms, persons)
       ├─ per room:
       │    global_mode=OFF → frost temp
       │    global_mode=TIME_PROGRAM →
       │        room_mode=frost_protection → frost temp
       │        room_mode=custom           → evaluate room time_program
       │        room_mode=global (default) → evaluate global_time_program
       │    global_mode=TIME_PROGRAM_PRESENCES →
       │        baseline = same as TIME_PROGRAM per room
       │        per person: compute_occupied_temp() → override baseline if person assigned to room
       └─ push changed temps → set_hvac_mode(heat) + set_temperature() per TRV entity
```

### Storage schema (v2, const.py DEFAULT_CONFIG)

```python
{
  "version": 2,
  "global_mode": "time_program",
  "period_temperatures": { "frost_protection": 5.0, "reduced": 18.0, "normal": 20.0, "comfort": 22.0 },
  "global_time_program": { "mon": [...], "tue": [...], ..., "sun": [...] },
  "rooms": {
    "<area_id>": {
      "room_mode": "global" | "frost_protection" | "custom",
      "time_program": { "mon": [...], ..., "sun": [...] }  # only when room_mode=custom
    }
  },
  "persons": {
    "person.<name>": {
      "mode": "scheduled" | "force_present" | "force_absent" | "ha",
      "room_ids": ["<area_id>", ...],
      "schedule": { "mon": [...], ..., "sun": [...] }
    }
  }
}
```

### Current component inventory

| File                                   | Role                                                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `const.py`                             | Domain constants + DEFAULT_CONFIG + default daily programs                                                    |
| `storage.py`                           | ClimateManagerStore — sparse-merge load, async_save                                                           |
| `coordinator.py`                       | ClimateManagerCoordinator — evaluate loop, per-room temp resolution, TRV push, status build                   |
| `schedule.py`                          | Pure evaluation functions: evaluate_schedule, resolve_presence, compute_occupied_temp, validate_daily_program |
| `websocket.py`                         | 11 WS command factories registered via async_register_commands                                                |
| `__init__.py`                          | async_setup_entry + ClimateManagerData dataclass                                                              |
| `frontend/src/types.ts`                | TypeScript interfaces: ClimateConfig, RoomConfig, StatusPayload, DailyProgram                                 |
| `frontend/src/ws-client.ts`            | WsClient class — one method per WS command                                                                    |
| `frontend/src/main.ts`                 | ClimateManagerPanel root element — tab shell, config/status loading                                           |
| `frontend/src/components/rooms-tab.ts` | Rooms tab — groups by floor, renders room-card                                                                |

---

## Zone Integration Design

### Guiding principle

Zones slot into the existing evaluation cascade as a new layer between global
and per-room. The cascade becomes:

```
global_mode=OFF           → frost temp (unchanged)
global_mode=TIME_PROGRAM  →
  room_mode=frost_protection → frost temp (unchanged)
  room_mode=custom           → room time_program (unchanged)
  room_mode=global:
    room has zone_id?
      YES → zone_mode=off               → frost temp
            zone_mode=time_program      → evaluate zone time_program
            zone_mode=time_program_presences → evaluate zone time_program as baseline + presence
      NO  → evaluate global_time_program (unchanged)
global_mode=TIME_PROGRAM_PRESENCES → same as above with presence overlay
```

Note: room_mode=custom always wins — it bypasses both zone and global programs.
This preserves existing room override semantics exactly.

---

## New Data Model

### Zones sub-schema

```python
# Added to DEFAULT_CONFIG:
"zones": {}

# Populated structure:
"zones": {
  "<zone_id>": {              # zone_id = slugified name, e.g. "upstairs"
    "name": "Upstairs",       # user-provided display name
    "mode": "time_program",   # "off" | "time_program" | "time_program_presences"
    "time_program": {         # same DailyProgram shape as global_time_program
      "mon": [...], ..., "sun": [...]
    }
  }
}
```

### Room schema extension

```python
# Extended room sub-schema (new key only):
"rooms": {
  "<area_id>": {
    "room_mode": "global" | "frost_protection" | "custom",  # unchanged
    "time_program": { ... },                                  # unchanged
    "zone_id": "<zone_id>" | None                            # NEW — absent = no zone
  }
}
```

### Storage version bump

STORAGE_VERSION must increment to 3. The async_load migration path in storage.py
already handles unknown keys gracefully (stored-wins sparse merge), so a fresh
`zones` dict defaulting to `{}` is safe without an explicit migration block.
Only the version integer needs bumping in both the constant and the Store
constructor.

### Why zone_id lives on the room, not on the zone

Storing a `room_ids` list on the zone (mirroring person.room_ids) creates a
two-way consistency problem: zone CRUD must scan and update all room refs, and
delete_zone must clean them up atomically. Storing `zone_id` on the room makes
room-to-zone assignment a single key write and keeps zone config self-contained.
Membership is derived by scanning `rooms[area_id]["zone_id"]` at evaluation
time, which is O(rooms) and already inside the existing O(rooms) loop — zero
cost.

---

## Component Boundaries: New vs Modified

### Backend

| Component        | Change           | What changes                                                                                                                                                                          |
| ---------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `const.py`       | **MODIFIED**     | Add zone mode constants, add `"zones": {}` to DEFAULT_CONFIG, bump STORAGE_VERSION to 3                                                                                               |
| `storage.py`     | **MODIFIED**     | Bump version integer in Store constructor; no migration logic required                                                                                                                |
| `coordinator.py` | **MODIFIED**     | Add zone resolution inside room_mode=global branch of both `_evaluate_time_program` and `_evaluate_time_program_presences`; add `zone_id` to rooms entries in `_build_status_payload` |
| `schedule.py`    | **NOT MODIFIED** | `evaluate_schedule` already accepts any DailyProgram dict; zone programs use it unchanged                                                                                             |
| `websocket.py`   | **MODIFIED**     | Register 5 new commands; existing 11 commands unchanged                                                                                                                               |
| `__init__.py`    | **NOT MODIFIED** | ClimateManagerData requires no new fields — zones live in runtime_config                                                                                                              |

### Frontend

| Component                           | Change           | What changes                                                                                                   |
| ----------------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------- |
| `types.ts`                          | **MODIFIED**     | Add `ZoneConfig` interface; add `zones` key to `ClimateConfig`; add `zone_id` to `RoomConfig` and `RoomStatus` |
| `ws-client.ts`                      | **MODIFIED**     | Add 5 new methods mirroring new WS commands                                                                    |
| `main.ts`                           | **MODIFIED**     | Add "Zones" tab button; render `<climate-manager-zones-tab>`                                                   |
| `components/zones-tab.ts`           | **NEW**          | Zone list + create form + empty state                                                                          |
| `components/zone-card.ts`           | **NEW**          | Single zone editor: name input, mode select, time-bar, delete button                                           |
| `components/room-card.ts`           | **MODIFIED**     | Add zone assignment selector in expanded view                                                                  |
| `components/rooms-tab.ts`           | **NOT MODIFIED** | No structural change needed; room-card handles zone display internally                                         |
| `components/global-settings-tab.ts` | **NOT MODIFIED** | No zone content needed here                                                                                    |
| `components/persons-tab.ts`         | **NOT MODIFIED** | Person-room associations unchanged by zones                                                                    |

---

## New WebSocket Commands

5 new commands. All follow the existing factory pattern in websocket.py (closure
over `entry`, `@websocket_api.async_response`, `vol` schema, write-then-evaluate
pattern).

```
climate_manager/get_zones
  → Returns: { zones: Record<zone_id, ZoneConfig> }
  Read-only snapshot. Thin — get_config already returns zones once the key
  is in DEFAULT_CONFIG, so this command is only needed if lazy-loading zones
  separately. Can be omitted if zones are always included in get_config.

climate_manager/set_zone
  Payload: { zone_id: str, config: { name?: str, mode?: str, time_program?: dict } }
  → { success: true }
  Creates or updates a zone. setdefault + update pattern (T-03-09).
  If time_program present, validate via validate_daily_program before save.

climate_manager/delete_zone
  Payload: { zone_id: str }
  → { success: true }
  Removes zone from zones dict AND clears zone_id from all rooms that
  reference this zone (inline scan of runtime_config["rooms"]).
  Both mutations in one save — atomic from the store's perspective.

climate_manager/set_zone_program
  Payload: { zone_id: str, program: DailyProgram }
  → { success: true }
  Dedicated time-program-only update (mirrors set_time_program pattern).
  Validates with validate_daily_program before save.

climate_manager/set_room_zone
  Payload: { room_id: str, zone_id: str | null }
  → { success: true }
  Sets or clears zone_id on rooms[room_id]. A dedicated command keeps the
  intent explicit and avoids the panel constructing room config deltas.
```

Note: `get_config` already returns the full runtime_config including the new
`zones` key once it is added to DEFAULT_CONFIG. No change to the get_config
handler is needed. The `get_zones` command is optional; it is worth adding only
if zones need to be fetched independently (e.g. for lazy-loading). For v1.1,
including zones in get_config is sufficient.

---

## Coordinator Modification Detail

The zone lookup is inserted inside the `room_mode=global` path in both
`_evaluate_time_program` and `_evaluate_time_program_presences`. The current
single-line assignment:

```python
daily_program = global_daily_program
```

becomes:

```python
zone_id = room_config.get("zone_id")
zone_cfg = config.get("zones", {}).get(zone_id) if zone_id else None
if zone_cfg:
    zone_mode = zone_cfg.get("mode", MODE_TIME_PROGRAM)
    if zone_mode == MODE_OFF:
        desired_temp = period_temperatures[PERIOD_FROST_PROTECTION]
        room_periods[area_id] = PERIOD_FROST_PROTECTION
        pushes.extend(
            (entity_id, desired_temp)
            for entity_id in entity_ids
            if is_trv_entity(self._hass, entity_id)
        )
        continue  # skip schedule evaluation for this room
    zone_program = zone_cfg.get("time_program")
    daily_program = zone_program if zone_program else global_daily_program
    # zone_mode stored for presence-override gate in time_program_presences pass
else:
    daily_program = global_daily_program
    zone_mode = None
```

For the presence-overlay pass in `_evaluate_time_program_presences`, whether a
room participates in presence override depends on the effective mode governing
it:

- Zone absent → uses global_mode to decide (existing behavior)
- Zone present with `mode=time_program_presences` → participates in presence
  override
- Zone present with `mode=time_program` → skips presence override even if
  global_mode is time_program_presences

This is implemented by passing `zone_mode` (or `None`) alongside `daily_program`
through the baseline step, then gating the presence-override step on
`zone_mode != MODE_TIME_PROGRAM` (when a zone is active).

### Status payload extension

```python
room_entry["zone_id"] = room_configs.get(area_id, {}).get("zone_id")
```

Added to `_build_status_payload` for all room entries. Allows the frontend to
display zone membership without a separate config fetch.

---

## TypeScript Types

```typescript
export interface ZoneConfig {
  name: string;
  mode: "off" | "time_program" | "time_program_presences";
  time_program: DailyProgram;
}

// ClimateConfig extended (add one key):
export interface ClimateConfig {
  global_mode: string;
  period_temperatures: Record<string, number>;
  global_time_program: DailyProgram;
  rooms: Record<string, RoomConfig>;
  persons: Record<string, PersonConfig>;
  zones: Record<string, ZoneConfig>; // NEW
  climate_entities: string[];
}

// RoomConfig extended (add one key):
export interface RoomConfig {
  room_mode?: "global" | "frost_protection" | "custom";
  time_program?: DailyProgram | null;
  zone_id?: string | null; // NEW
}

// RoomStatus extended (add one key):
export interface RoomStatus {
  area_id: string;
  name: string;
  entity_ids?: string[];
  temperature?: number | null;
  humidity?: number | null;
  active_period?: string | null;
  present_person_count: number;
  has_trv?: boolean;
  zone_id?: string | null; // NEW
}
```

---

## Build Order

Dependencies are strict — each phase requires its predecessors to be complete.

### Phase 1: Data model (backend + frontend types)

Files: `const.py`, `storage.py`, `types.ts`

- Add zone mode constants to const.py
- Add `"zones": {}` to DEFAULT_CONFIG
- Bump STORAGE_VERSION to 3 in const.py and storage.py Store constructor
- Add ZoneConfig, extend ClimateConfig / RoomConfig / RoomStatus in types.ts

Gate: Existing install loads cleanly with `zones: {}` default. No existing tests
broken.

### Phase 2: WebSocket API

Files: `websocket.py`, `ws-client.ts`

- Implement set_zone, delete_zone, set_zone_program, set_room_zone in
  websocket.py
- Register all new commands in async_register_commands
- Add corresponding methods to WsClient

Gate: Zone CRUD verifiable via browser console or test without any UI or
coordinator changes.

### Phase 3: Coordinator zone evaluation

Files: `coordinator.py`

- Add zone resolution inside room_mode=global path of both evaluation methods
- Add zone_id to status payload rooms
- Handle zone_mode=off (frost branch) and zone time_program (daily_program
  override)
- Handle presence-override gating when zone_mode=time_program

Gate: Assign a room to a zone via WS, verify TRV receives zone temperature at
next tick (HA logs). Rooms without zone_id behave identically to v1.0.

### Phase 4: Zones tab UI

Files: `components/zones-tab.ts` (new), `components/zone-card.ts` (new),
`main.ts`

- Zones tab with zone list, create form (name + mode + default time-bar)
- Zone card with name edit, mode select, time-bar, delete
- Add Zones tab button to main.ts tab bar

Gate: Full zone CRUD from the panel UI. Time-bar edits save correctly.

### Phase 5: Room-to-zone assignment UI

Files: `components/room-card.ts`

- Add zone assignment select to expanded room card view
- Populated from `panelConfig.zones`; includes "None" option
- Calls `ws.setRoomZone(roomId, zoneId | null)` on change

Gate: Assign rooms to zones from the Rooms tab. Room card shows zone name.
Assignment survives page reload.

---

## Anti-Patterns to Avoid

### Storing room_ids on the zone object

Mirroring `person.room_ids` by adding `room_ids: list` to the zone. This creates
a two-way consistency problem requiring multi-key writes on every room
assignment change and on zone delete. Zone_id on the room is the correct model
for a one-to-many relationship where the "many" side holds the foreign key.

### Adding a zone evaluation function to schedule.py

Zone programs use the same DailyProgram structure and `evaluate_schedule()`
function as global and room programs. A wrapper is pure indirection with no
abstraction value.

### Separate period temperature values per zone

Zones share the global period_temperatures. Zone time programs select period
modes; the temperature per mode is always global. Per-zone temperature overrides
are a v2+ concern.

### Using zone_id as a display name

zone_id is a stable slug used as a dict key; `name` is the display string. The
frontend must always display `zones[zone_id].name`, never zone_id itself. When
the user renames a zone, only the `name` key changes — zone_id stays stable so
room assignments don't need updating.

---

## Open Questions

1. **Zone mode vs global mode interaction for presence:** If a room is in a zone
   with `mode=time_program` and the global mode is `time_program_presences`,
   should persons still override that room? The design above says NO (zone
   mode=time_program opts out of presence). Confirm with user before
   implementing Phase 3 to avoid a costly coordinator rewrite.

2. **Zone ID generation:** The frontend generates zone*id as a slug from the
   user's name. A safe formula: `name.toLowerCase().replace(/\s+/g,
   "*").replace(/[^a-z0-9_]/g, "")`. The backend treats zone_id as an opaque
   string key. Confirm this is acceptable; alternatively the backend generates a
   UUID-style ID on set_zone if zone_id is absent.

3. **delete_zone atomicity:** Clearing `zone_id` from all affected rooms plus
   removing the zone must be a single `async_save` call. Test this explicitly —
   partial writes would leave dangling zone_id references that cause coordinator
   warnings.

4. **Zone time program default on create:** When a zone is created without a
   time_program, should it default to the global time program (deep-copied) or
   to the standard default weekday schedule? Defaulting to
   `_DEFAULT_DAILY_PROGRAM` (same as global default) is safest — avoids
   surprising behaviour if the user later changes the global program.
