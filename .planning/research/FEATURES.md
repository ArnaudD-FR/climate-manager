# Features

**Project:** Climate Manager — v1.1 Heating Zones **Researched:** 2026-05-26
**Confidence:** HIGH (system internals), MEDIUM (zone UI patterns from
commercial systems)

---

## Context

This document covers features for the v1.1 "Heating Zones" milestone only. v1.0
features (global mode, time programs, per-room overrides, persons, full panel)
are already shipped and are dependencies, not in-scope work. References to
existing code use the actual source filenames.

**Core concept being added:** A zone is a named group of rooms that runs its own
mode and weekly schedule, independently from the global configuration. Rooms not
in any zone continue to fall back to global. Zones override global, not
individual room configs — a room's own `room_mode=custom` override can still
exist within a zone.

---

## Table Stakes

Features users must have for zones to be usable at all. Missing = zones are
incomplete.

| Feature                                                                   | Why Expected                                                                          | Complexity | Notes                                                                                         |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------- |
| Zone CRUD — create named zone                                             | Can't use a feature that doesn't exist yet                                            | Low        | Name is the only required field at creation; mode + schedule can be set later                 |
| Zone CRUD — rename zone                                                   | Names are always wrong first draft                                                    | Low        | Inline rename, immediate persistence                                                          |
| Zone CRUD — delete zone                                                   | Zones created for experiments or restructuring need removal                           | Low        | Delete unassigns all rooms; rooms fall back to global — no data loss                          |
| Zone mode — Off / Time program / Time program & presences                 | Zones exist to run independently from global; mode is what makes them independent     | Low        | Same three values as global mode; persisted per zone                                          |
| Zone time program — own weekly schedule                                   | A zone with no schedule is just a label; this is the core value                       | Medium     | Same per-day structure as global_time_program; reuses existing evaluate_schedule()            |
| Room assignment — assign room to a zone                                   | Without this, zones are disconnected from the actual rooms                            | Low        | One room belongs to at most one zone (exclusive assignment)                                   |
| Room assignment — unassign room from zone                                 | Users need to move rooms or leave them at global                                      | Low        | Dropping back to global must be explicit and reversible                                       |
| Backend evaluation — zone takes precedence over global for assigned rooms | This is the entire point of zones                                                     | Medium     | coordinator.py must branch: zone config > global before room_mode evaluation                  |
| Zone status in panel — show which zone each room belongs to               | Without visual indication, users can't tell what's doing what                         | Low        | Zone name badge on room card is sufficient                                                    |
| Default zone schedule seeded from global                                  | New zones start empty; a pre-populated schedule prevents a blank-screen on first open | Low        | Deep-copy global_time_program at zone creation (same pattern as reset_room_to_global_program) |

---

## Differentiators

Features that make zones genuinely useful beyond the minimum viable
implementation.

| Feature                                                              | Value Proposition                                                                                 | Complexity | Notes                                                                                            |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------ |
| Zone mode shown in zone card header                                  | Instant visible status — don't make user open zone to see mode                                    | Low        | Same mode chip already on global settings; reuse component                                       |
| Zone list summary — room count and active period per zone            | Scannable at a glance; avoids opening each zone                                                   | Low        | Derived from runtime evaluation data already in coordinator.\_last_room_periods                  |
| Room assignment via room card (assign/unassign from within the room) | Natural location — user is already looking at a room when they want to zone it                    | Medium     | Needs dropdown of existing zone names + "none (global)" option; triggers set_zone_config WS call |
| Zone assignment visible on Rooms tab without entering zone detail    | Zones are orthogonal to rooms; rooms tab is where users go to manage rooms                        | Low        | Zone name badge or chip on room card; low implementation cost                                    |
| "Reset zone schedule to global" action                               | Zones often start as copies of global then diverge; reset shortcut saves re-entering the schedule | Low        | Deep-copy pattern already in ws_reset_room_to_global_program; replicate for zones                |
| Zone evaluation order shown in UI                                    | With multiple zones, users wonder "which config wins for this room?"                              | Low        | A room in a zone always uses zone config; show "Zone: Bathrooms" in status                       |

---

## Anti-Features

Explicitly out of scope for v1.1.

| Anti-Feature                                                                            | Why Avoid                                                                                 | What to Do Instead                                                                                   |
| --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Zones nested inside zones (hierarchical zones)                                          | Exponential conflict-resolution complexity; no household use case requires it             | Flat list of zones is sufficient; use zone naming conventions for grouping                           |
| Per-zone person presence associations                                                   | Persons are already associated to rooms; a zone inheriting those associations is implicit | Persons remain room-scoped; zone mode TIME_PROGRAM_PRESENCES already works through room associations |
| Zone priority ordering (zone A overrides zone B)                                        | A room can only be in one zone — priority ordering is meaningless                         | Enforce exclusive room-zone membership; no priority needed                                           |
| Zone-level period temperatures (different Frost/Reduced/Normal/Comfort values per zone) | Each zone having its own temperature scale multiplies configuration surface 4x per zone   | Global period temperatures continue to apply; zones only override mode + schedule                    |
| Zone creation from global mode switch                                                   | Global mode is a different concept (master on/off); conflating them causes confusion      | Zones tab is separate from global settings; different UX path                                        |
| "Copy zone" shortcut                                                                    | Nice-to-have but zones rarely need identical copies                                       | Manual re-creation is acceptable for v1.1                                                            |
| Zone-specific frost protection temperature                                              | Already covered by global period_temperatures[frost_protection]                           | No per-zone temperature scale                                                                        |

---

## Feature Dependencies

```
Zones feature (v1.1)
  └─→ Depends on: global_time_program structure (already exists — same schema)
  └─→ Depends on: evaluate_schedule() in schedule.py (already exists — no changes needed)
  └─→ Depends on: coordinator.py evaluation loop (must be extended, not replaced)
  └─→ Depends on: storage.py sparse-merge pattern (zones dict follows same pattern as rooms/persons)
  └─→ Depends on: websocket.py WS command factory pattern (new zone commands follow same pattern)

Zone CRUD (create/rename/delete)
  └─→ Storage: new "zones" key in DEFAULT_CONFIG, keyed by zone_id (UUID or slug)
  └─→ WS commands: create_zone, update_zone, delete_zone
  └─→ UI: Zones tab in panel with zone list

Zone mode
  └─→ Stored in zone config alongside zone schedule
  └─→ Backend: coordinator evaluates zone mode before global mode for zone-assigned rooms

Zone time program
  └─→ Same DailyProgram type (Record<day, Period[]>); reuses existing time-bar component
  └─→ Seeded at creation with copy of global_time_program (reuse reset_room_to_global pattern)

Room assignment to zone
  └─→ Stored in zone config as room_ids list (parallel to person.room_ids pattern)
  └─→ Must enforce exclusive membership: assign to zone B removes from zone A
  └─→ WS command: set_zone_config carries room_ids
  └─→ UI: assignable from within zone detail OR from room card

Backend evaluation order (coordinator.py)
  For each room at each tick:
    1. Find zone for this room (if any) → evaluate zone mode + zone schedule
    2. No zone → evaluate global mode + global schedule (existing logic, unchanged)
    3. Room-level mode (room_mode=frost / custom) → evaluated after zone/global mode decision,
       because room mode overrides temperature within the scheduling context, not the mode itself.
       Existing semantics: room_mode=frost overrides regardless; room_mode=custom replaces schedule
       source. These continue to work within zone context.

Zone status for status payload
  └─→ coordinator._build_status_payload() must include zone membership per room
  └─→ WS get_status response gains zone_name field per room (used by room card badge)
```

---

## User Flows

### Create Zone

1. User opens Zones tab (new tab in panel, same nav bar)
2. Taps "Add zone" button (consistent with how HA Areas or similar panels
   present creation)
3. Name field inline (not a modal) — types "Bathrooms", taps confirm
4. Zone card appears in list: name, mode selector, room count (0), "Edit
   schedule" button
5. User sets mode (e.g., Time program) directly in zone card header
6. User taps "Edit schedule" — opens time-bar editor pre-filled with global
   schedule copy
7. User assigns rooms: from zone detail, taps "Add rooms" → checklist of
   unassigned rooms

### Assign Room to Zone

- **From zone detail:** checklist of rooms not yet in any zone; multi-select,
  save
- **From room card (Rooms tab):** zone selector dropdown showing existing zone
  names + "None (global)"
- Assigning to a new zone automatically removes from previous zone (exclusive
  membership enforced client-side before save)

### Delete Zone

1. User taps delete icon on zone card
2. Confirmation: "Rooms in this zone will return to global settings"
3. On confirm: zone removed from config, all room_ids cleared, coordinator
   re-evaluates
4. Room cards lose zone badge, resume global behavior

### Rename Zone

1. User taps zone name in zone card header
2. Inline edit field — type new name, confirm with Enter or blur
3. WS call persists immediately; UI reflects new name

---

## Edge Cases

**Room in deleted zone** When a zone is deleted, rooms that were in it have no
zone assignment. Coordinator must handle this gracefully — rooms fall through to
global evaluation on the next tick. No orphaned zone_id references should remain
in room configs (rooms are not stored per-zone in room config; zone owns the
room_id list).

**Zone with no rooms** Allowed — user creates zone, hasn't assigned rooms yet.
Empty zone card shows "0 rooms". No coordinator impact (no rooms to evaluate).

**Zone with Time program & presences mode** Person-room associations are defined
on person config, not on zones. A room in a zone using TIME_PROGRAM_PRESENCES
mode works identically to the same mode at global level — persons associated
with that room via their room_ids still apply their presence override within the
zone's schedule. No new configuration needed; existing presence logic in
\_evaluate_time_program_presences() must be called with the zone's daily_program
instead of global when the room belongs to a zone.

**Room with room_mode=custom inside a zone** Room-level custom schedule
overrides the zone's schedule source. Zone mode (on/off/time-program/etc.) still
applies. This is consistent with v1.0 semantics where room_mode=custom overrides
the schedule source at the room level.

**Room with room_mode=frost inside a zone** Frost mode is unconditional — it
overrides both zone and global. Consistent with v1.0 behavior.

**HA restart with zones configured** Zones are stored in the same Store as the
rest of the config. On startup, coordinator reads zone assignments and evaluates
zone-aware temperatures before the first push. No new restart logic needed
beyond including zones in the evaluation pass.

---

## MVP Recommendation

For v1.1, ship in this priority order:

1. Zone CRUD (create/rename/delete) — backend + WS commands + Zones tab with
   basic zone cards
2. Zone mode per zone — mode selector in zone card header, persisted, evaluated
   by coordinator
3. Zone time program — time-bar editor in zone detail, seeded from global on
   create
4. Room assignment — from zone detail with room checklist, zone badge on room
   card
5. Zone mode shown in room card status — which zone, which mode

Defer to a later quick-task or v1.2:

- Room assignment from within room card (lower priority; zone detail flow is
  sufficient for initial use)
- "Reset zone schedule to global" shortcut (easy to add post-v1.1)
- Zone list summary stats (active period per zone) — nice-to-have, not blocking

---

## Implementation Notes for Requirements Author

**Storage schema change:** Add `"zones": {}` key to DEFAULT_CONFIG in const.py.
Zone schema:

```python
{
  "<zone_id>": {
    "name": "<str>",
    "mode": "off" | "time_program" | "time_program_presences",
    "time_program": {per-day DailyProgram},
    "room_ids": ["<area_id>", ...]
  }
}
```

Zone IDs can be slugs derived from name (lowercase, hyphenated) or UUIDs. Slugs
are more debuggable. Risk: slug collision on rename. UUID avoids collision but
loses readability. Recommendation: use slug generated at creation time only
(rename does not re-slug; zone_id is immutable after creation).

**Coordinator change:** Before evaluating global mode for a room, check if the
room's area_id appears in any zone's room_ids list. If found, use that zone's
mode and time_program instead of global. The existing \_evaluate_time_program()
and \_evaluate_time_program_presences() logic can be reused with a different
daily_program source and mode — extract "resolve daily_program for area_id" as a
helper.

**WebSocket commands needed (new):**

- `climate_manager/create_zone` — creates zone, returns zone_id
- `climate_manager/update_zone` — update name, mode, time_program, room_ids
- `climate_manager/delete_zone` — removes zone, returns success
- `climate_manager/get_config` — already returns full config; just needs zones
  key in payload
- `climate_manager/get_status` — rooms_status entries gain `zone_id` and
  `zone_name` fields

**Frontend changes:**

- New "Zones" tab (4th tab in nav bar — or replace an existing tab if nav bar
  gets crowded)
- ZonesTab component with zone card list and "Add zone" button
- ZoneCard component (header with name, mode chip, room count; expandable body
  with time-bar + room list)
- Room assignment checklist (reuse search-picker.ts pattern already used for
  climate entity picker)
- Zone badge on RoomCard (zone name, small chip below room name)

**Dependency on existing components:**

- `time-bar.ts` — already handles DailyProgram; no changes needed for zone
  schedule editing
- `search-picker.ts` — room assignment checklist can reuse this component for
  area_id selection
- `ws-client.ts` — new zone WS commands follow same sendMessagePromise pattern;
  no structural change
- `ClimateConfig` type in types.ts — add `zones: Record<string, ZoneConfig>`
  field

---

## Sources

- Tado X zone help:
  https://help.tado.com/en/articles/8911771-how-does-tado-x-control-heating-zones-how-can-i-change-the-zone-controller-of-a-room
- HA community multi-zone heating:
  https://community.home-assistant.io/t/smart-heating-scheduler-for-home-assistant-extra-multi-zones-version/237966
- HA community multi-zone with scheduling:
  https://community.home-assistant.io/t/multi-zone-heating-with-scheduling/160280
- multizone_generic_thermostat HA component:
  https://github.com/tpacri/multizone_generic_thermostat
- Existing codebase: const.py, coordinator.py, schedule.py, websocket.py,
  storage.py, types.ts
