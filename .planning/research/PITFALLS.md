# Pitfalls

**Project:** Climate Manager — v1.1 Heating Zones (adding zone layer to existing
global + per-room system) **Researched:** 2026-05-26 **Confidence:** HIGH for
storage/migration pitfalls (codebase directly inspected); HIGH for
evaluation-order pitfalls (coordinator logic reviewed); MEDIUM for UI complexity
pitfalls (pattern-based, not empirically tested)

---

## Critical Pitfalls (rewrites or silent failures if missed)

### C1 — Evaluation order not explicitly defined → inconsistent behaviour under edge cases

**What goes wrong:** Zone mode is supposed to override global, and per-room mode
is supposed to override zone. But this three-level hierarchy (global → zone →
room) is only correct if the coordinator implements it as a strict, explicitly
coded chain — not as a series of independent checks. If zone evaluation and room
override evaluation are written as separate conditional branches rather than a
single resolution pass, edge cases will produce wrong temperatures: e.g. a room
in a zone with mode `off` but also `room_mode=custom` — which wins? If the code
isn't explicit, the answer depends on iteration order.

**Why it happens:** The v1.0 coordinator has two modes that already compose
global and per-room. Adding a third level is tempting to bolt on as "check zone
first, then fall through" without defining every combination formally.

**Consequences:** Some rooms heat when they shouldn't (zone=off, room=custom
wins incorrectly). Silent — no error, no log, just wrong temperature.

**Prevention:** Define the full resolution matrix before writing code. The
correct v1.1 contract is:

1. If room has `room_mode=frost_protection` → frost always (room wins over
   everything)
2. Else if room is in a zone → use zone's mode and zone's time_program (zone
   overrides global)
3. Else → use global mode and global time_program (unzoned rooms, existing v1.0
   path)
4. Presence overrides apply after schedule resolution, but only if the effective
   mode includes presences

Encode this as a single `_resolve_room_program(room_id, config)` helper that
returns `(mode, daily_program)` — never inline the resolution across multiple
branches.

**Detection:** Write a unit test for each combination: room=frost in a zone with
mode=off; room=custom in a zone with mode=time_program; unzoned room with global
mode=off.

**Phase:** Backend evaluation (zone evaluation phase)

---

### C2 — Data migration: existing rooms have no `zone_id` → silent KeyError or wrong fallback

**What goes wrong:** The v1.0 storage schema has no `zones` key and no `zone_id`
on rooms. When v1.1 first loads, `config["zones"]` raises `KeyError` or returns
`None` unless the load path seeds the key. If code does `room_config["zone_id"]`
anywhere without a `.get()` default, it crashes on every existing room on first
upgrade load.

**Why it happens:** The sparse-merge loader in `storage.py` overlays stored
values onto `DEFAULT_CONFIG`. If `DEFAULT_CONFIG` is not updated to include
`"zones": {}`, existing installs load without the key. Any code that relies on
the key existing (even a `.get()` on the wrong dict) will fail.

**Consequences:** Integration fails to load on upgrade. User sees integration
broken on first HA restart after update. Recovery requires manual `.storage`
file editing.

**Prevention:**

- Add `"zones": {}` to `DEFAULT_CONFIG` in `const.py` before writing any
  zone-aware coordinator code
- `async_load` in `storage.py` already deep-copies `DEFAULT_CONFIG` and overlays
  stored values — no changes to the merge logic are needed, but the key must
  exist in the default
- Rooms do not need a `zone_id` field — zone membership is stored on the zone
  object (`zone["room_ids"]`), not on the room. This avoids needing to migrate
  every room entry.
- Add an `async_load` migration block (like the existing person mode migration)
  that detects `"zones" not in stored` and seeds it as `{}`

**Detection:** Load the current v1.0 `.storage` file in a test with the v1.1
`ClimateManagerStore`. Assert that `config["zones"]` is `{}` and no rooms have a
`zone_id` key.

**Phase:** Storage schema update (first task of zone milestone)

---

### C3 — Zone deletion leaves orphaned room references → rooms silently revert to global with no warning

**What goes wrong:** If a zone is deleted and its `room_ids` list is not cleaned
up from the zone object (already gone), or if rooms internally stored a
`zone_id` reference, those rooms would silently fall back to global — with no
indication in the UI that their zone association was removed. The user has no
way to know their zone schedule is no longer active.

**Why it happens:** Deletion handlers often remove the primary object but skip
reference cleanup. If zone membership is stored on rooms (`room["zone_id"]`),
deleting the zone leaves stale `zone_id` values in every affected room's config.

**Consequences:** Rooms that were zone-controlled silently revert to the global
schedule. No error. User notices rooms heating differently but has no
diagnostic.

**Prevention:**

- Store zone membership exclusively on the zone object
  (`zone["room_ids"] = [...]`), never on the room. This means zone deletion is
  self-contained: delete the zone dict, no room config needs touching.
- On zone delete, trigger `coordinator.async_evaluate()` immediately so affected
  rooms adopt the correct fallback temperature at once — not on the next minute
  tick.
- UI: after zone delete, display a toast "Zone deleted — X rooms now follow
  global schedule" listing the affected room names.

**Detection:** Test: create zone with 2 rooms, delete zone, assert rooms
evaluate against global program on next tick.

**Phase:** Zone CRUD backend + UI

---

### C4 — Presence + zone mode interaction: zone `off` silently disables presence heating

**What goes wrong:** If a zone's mode is `off`, presence-based heating should
also be suppressed for rooms in that zone (otherwise a present person re-heats a
room that the zone owner explicitly turned off). But if the presence override is
applied after zone mode in the evaluation chain without an explicit zone-off
guard, present persons will keep heating zone-off rooms.

Conversely: if zone mode is `time_program` (not `time_program_presences`),
presence overrides should NOT apply to that zone's rooms even if the global mode
is `time_program_presences`. A zone defines its own independent mode — including
whether presence heating applies.

**Why it happens:** The v1.0 coordinator applies presence overrides in a second
pass over all rooms without inspecting the room's governing mode. Adding zones
without updating that pass creates a gap.

**Consequences:**

- Zone `off` rooms heat for present persons (privacy/energy violation)
- Zone `time_program` rooms heat unexpectedly when global mode is
  `time_program_presences`

**Prevention:** The zone's own mode field governs presence behaviour for its
rooms, independently of global mode. The resolution must be: "what mode governs
this room?" and then "does that mode include presences?" — not "does the global
mode include presences?"

Presence override pass must check effective mode per room, not global mode.

**Detection:** Test: global mode=`time_program_presences`, zone mode=`off`,
person present in zone room. Assert frost protection temperature, not
presence-elevated temperature.

**Phase:** Backend evaluation

---

### C5 — Storage schema version not bumped → corrupted config on rollback

**What goes wrong:** If zones are added to `DEFAULT_CONFIG` without bumping
`STORAGE_VERSION`, a user who rolls back to v1.0 will load a config with an
unexpected `zones` key. v1.0's loader does a shallow merge — it won't crash, but
the `zones` key will persist in storage silently. More critically: if v1.1 makes
a breaking schema change (e.g. renames a key) without a version bump, the v1.0
migration path in `async_load` won't run.

**Why it happens:** `STORAGE_VERSION = 2` in `const.py`. If v1.1 adds zones as
purely additive (new key, existing keys unchanged), there is an argument for not
bumping. But any rename or structural change without a bump silently breaks
existing installs.

**Consequences:** Silent data corruption. Wrong temperatures applied. Difficult
to diagnose.

**Prevention:**

- If zone addition is purely additive (new `zones: {}` key only), do not bump
  the version — the sparse merge loader handles new keys gracefully
- If any existing key is renamed or restructured, bump to `STORAGE_VERSION = 3`
  and add a migration block in `async_load`
- Never rename existing schema keys without a version bump + migration block

**Detection:** Load a v1.0 `.storage` JSON with a v1.1 store. Assert all
existing fields round-trip correctly. Assert `zones` appears with default value.

**Phase:** Storage schema update

---

## Moderate Pitfalls (quality gate or logic bugs)

### M1 — Zone mode `off` vs global mode `off` — same string, different semantics, same coordinator branch

**What goes wrong:** Both global mode and zone mode use `"off"` as the string
value. The coordinator `MODE_OFF` branch in v1.0 sends frost protection to ALL
rooms. If zone mode is naively stored as the same `"off"` string, code like
`if zone_config.get("mode") == MODE_OFF` works — but the handling must be
different: global `off` → all rooms get frost; zone `off` → only that zone's
rooms get frost, other rooms unaffected.

If the coordinator's `MODE_OFF` top-level branch is reused for zones without
narrowing to zone-specific rooms, zones with mode `off` will accidentally freeze
rooms in other zones.

**Prevention:** Keep the global-mode `MODE_OFF` branch as-is for all-rooms
frost. Zone `off` must be handled inside the per-room resolution loop, not as a
top-level early exit. Use a `_resolve_room_program` helper that returns
`(mode, daily_program)` per room — zone mode `off` returns `(MODE_OFF, None)`
for that room's entry, handled locally.

**Phase:** Backend evaluation

---

### M2 — WebSocket command proliferation — zone CRUD adds 4+ new commands on top of 11 existing

**What goes wrong:** v1.0 has 11 WebSocket commands. Zone CRUD needs at minimum:
`create_zone`, `update_zone`, `delete_zone`, `set_zone_room_assignments`. That
is 15+ commands. If zone config is also editable (zone mode, zone time program),
add `set_zone_mode` and `set_zone_time_program`. At 17+ commands the
`async_register_commands` function and the WS schema become hard to maintain and
the panel's `ClimateManagerWS` client class grows proportionally.

**Why it happens:** Each feature gets its own bespoke command because copy-paste
from existing patterns is easy.

**Prevention:**

- Consider a single `set_zone_config` command (analogous to `set_room_config`)
  that sparse-merges into `zones[zone_id]` — covers mode, time_program,
  room_ids, name in one handler
- Consider a `delete_zone` command that also accepts a list of `room_ids` to
  reassign (or simply removes the zone and lets rooms fall back to global)
- Resist adding `get_zone_config` if `get_config` already returns the full
  `zones` dict — it does, as it returns `runtime_config` wholesale

**Phase:** Zone CRUD backend

---

### M3 — `_last_room_periods` status tracking misses zone-governed rooms — incorrect active period shown in UI

**What goes wrong:** The coordinator's `_last_room_periods` dict tracks the
active period per room for the status push. In v1.0, a room not in
`_last_room_periods` falls back to `self._last_active_period` (the global
period). After v1.1, a room governed by a zone has its own period (from the
zone's time program), which may differ from the global period. If the zone
evaluation doesn't write into `_last_room_periods`, the UI will show the wrong
period label for zone-governed rooms.

**Prevention:** Zone evaluation must write
`room_periods[area_id] = zone_period_mode` for every zone-governed room, just as
per-room custom programs do in v1.0. The status build loop in
`_build_status_payload` already uses
`_last_room_periods.get(area_id, self._last_active_period)` — no change needed
there, only the evaluation write path needs updating.

**Phase:** Backend evaluation

---

### M4 — Zone time program reset copies global program — user expects zone default, gets global program

**What goes wrong:** v1.0 has a `reset_room_to_global_program` command that
deep-copies the global time program into the room. For zones, a "reset zone to
defaults" button would logically copy the global time program. But if the user
has customised the global program heavily, the zone inherits a non-neutral
schedule. The user might expect a "fresh" default weekday/weekend schedule (the
backend constant), not a copy of whatever the global is.

**Prevention:** A zone's "reset" command should copy `_DEFAULT_DAILY_PROGRAM`
(the module constant), not the current `global_time_program`. Clearly label the
button "Reset to factory default" not "Copy global program". This is the
opposite of the room reset UX — rooms explicitly inherit from global, zones are
independent.

**Phase:** Zone CRUD UI + backend

---

### M5 — Person room associations span zones — presence heating bypasses zone mode

**What goes wrong:** A person has `room_ids = ["bedroom", "kitchen"]`. Bedroom
is in Zone A (mode=`time_program`), kitchen is unzoned. In
`MODE_TIME_PROGRAM_PRESENCES`, the coordinator's presence pass iterates over
person room_ids without inspecting zone mode. Zone A has no presence mode — so
bedroom gets presence-heated even though Zone A was configured as `time_program`
(not `time_program_presences`).

**Why it happens:** The person room_ids list and the zone membership list are
independently keyed — no join is performed in v1.0 because zones don't exist.

**Prevention:** Same fix as C4 — the resolution must be per-room, asking "does
the governing mode for this room include presences?" before applying
`compute_occupied_temp`. The presence pass (Step 2 in
`_evaluate_time_program_presences`) must gate on the room's effective mode, not
the global mode.

**Phase:** Backend evaluation

---

### M6 — Zone deletion + person room associations → stale room_ids cause no-op presence heating

**What goes wrong:** A person has `room_ids = ["bedroom"]`. Bedroom was in Zone
A. Zone A is deleted, bedroom still exists (falls back to global). The person's
`room_ids` is untouched — presence heating for bedroom continues normally. This
is actually correct behaviour, but: if bedroom's HA area was also deleted (user
cleaned up HA areas), the person's `room_ids` contains a stale area_id. The
coordinator already silently skips unknown area_ids
(`if area_id not in rooms: continue`), so no crash — but the person appears to
have a room association that does nothing.

**Prevention:** This is a v1.0 issue too, not introduced by zones. Log a debug
warning when a person's `room_ids` contains an area_id not in
`self._data.rooms`. No correction needed at runtime, but the warning surfaces
the stale config.

**Phase:** Backend evaluation (low priority — existing behaviour, zones don't
worsen it)

---

### M7 — UI: three-level config hierarchy causes cognitive overload if zones tab is a peer of Global/Rooms/Persons

**What goes wrong:** The current panel has three tabs: Global Settings, Rooms,
Persons. Adding a fourth Zones tab that is a peer of Rooms creates confusion
about what controls what. A user seeing a room in the Rooms tab with its own
custom schedule, and the same room in the Zones tab with a zone schedule, will
not understand which one applies.

**Why it happens:** Tabs are the simplest UI extension — just add one more. But
the hierarchy (zone governs room unless room overrides) is not visible in a flat
tab structure.

**Prevention:**

- Zones tab shows zone config (mode, time program) and the list of rooms
  assigned to the zone
- Room card in the Rooms tab shows the badge "In zone: [Zone Name]" when a room
  is zone-governed, making the override hierarchy visible at the room level
- Room card's time-program section shows "Governed by zone [Name]" when the room
  inherits the zone schedule, with an option to override at room level
  (room_mode=custom) — same pattern as "Governed by global" in v1.0
- Do not show both zone schedule and room schedule simultaneously — only show
  the applicable one with a clear label

**Phase:** Zone UI

---

## Minor Pitfalls (correctness / maintainability)

### m1 — `zone_id` as UUID vs user-readable slug

Zone IDs that are UUIDs (`"a3f2b1..."`) are opaque in `.storage` files and in
WebSocket payloads — hard to debug. User-assigned names as IDs
(`"zone_kitchen"`) clash if the user renames. Use a short random slug (e.g.
`"zone_abc123"`) or a sequential integer string (`"zone_1"`, `"zone_2"`)
generated on create. Keep it stable — never derive from the name.

### m2 — Zones with empty `room_ids` are valid but confusing

A zone can exist with no rooms assigned yet. The coordinator must not crash on
an empty `room_ids` list. The UI should show an "empty zone" badge and not hide
the zone. Empty zones are a normal transient state (create zone, then assign
rooms).

### m3 — Zone `time_program` not seeded with defaults on creation → evaluates as frost on first tick

When a zone is created, its `time_program` is `{}` if not seeded.
`evaluate_schedule({}, now)` returns `PERIOD_FROST_PROTECTION` (T-03-01
fallback). A newly created zone will immediately push frost protection to its
rooms until the user configures the schedule. Mitigation: seed new zones with a
copy of `_DEFAULT_DAILY_PROGRAM` on creation, or set zone `mode=off` by default
until the user activates it.

### m4 — `reset_room_to_global_program` WS command needs equivalent for zones

The existing `reset_room_to_global_program` command deep-copies
global_time_program into a room. Zone users will expect a "reset zone to
default" command. This should copy `_DEFAULT_DAILY_PROGRAM`, not
`global_time_program` (see M4 above). Document this asymmetry in code comments.

### m5 — Zone name stored in zone config, not HA area registry

Zone names are custom strings chosen by the user, not HA area names. Unlike
rooms (which reuse HA area names from the registry), zones are a Climate Manager
concept with no HA registry counterpart. Store the name in the zone config dict
(`zone["name"]`). Do not attempt to create HA areas for zones — the integration
does not own the area registry.

---

## Phase-Specific Warnings

| Phase Topic           | Likely Pitfall                                             | Mitigation                                                                       |
| --------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Storage schema update | C2 — missing `zones: {}` in DEFAULT_CONFIG                 | Add to DEFAULT_CONFIG first, before any coordinator changes                      |
| Storage schema update | C5 — version bump decision                                 | Additive-only → no bump; any rename → bump to v3 + migration                     |
| Zone CRUD backend     | C3 — room references on zone delete                        | Store membership on zone, not room; trigger evaluate on delete                   |
| Zone CRUD backend     | M2 — WebSocket command proliferation                       | One `set_zone_config` + `delete_zone` + `create_zone` — avoid per-field commands |
| Backend evaluation    | C1 — evaluation order not explicit                         | Write `_resolve_room_program()` helper first, test the full matrix               |
| Backend evaluation    | C4 / M5 — presence ignores zone mode                       | Presence pass gates on effective mode, not global mode                           |
| Backend evaluation    | M1 — zone off vs global off same string                    | Zone off handled inside per-room loop, not as top-level branch                   |
| Backend evaluation    | M3 — `_last_room_periods` not updated for zone rooms       | Zone evaluation writes `room_periods[area_id]` same as custom room evaluation    |
| Zone CRUD UI          | M4 — zone reset copies wrong program                       | "Reset" copies `_DEFAULT_DAILY_PROGRAM`, not current global                      |
| Zone CRUD UI          | m3 — new zone has empty schedule                           | Seed with `_DEFAULT_DAILY_PROGRAM` or default to `mode=off` on creation          |
| Zone UI               | M7 — three-level hierarchy invisible in flat tab structure | Room card shows "In zone: X" badge; room schedule section shows governing source |

---

## Open Questions

- Should zone mode include a `time_program_presences` option independently of
  global mode? If yes, the person presence pass becomes significantly more
  complex — every room needs its own effective mode lookup. If no, zone presence
  behaviour always mirrors global. Simpler to start: zone mode =
  `off | time_program | time_program_presences`, same enum as global.
- Can a room be in multiple zones? Almost certainly not in v1.1 — one zone per
  room, or no zone (global). Enforce at save time in `set_zone_config`.
- Should unzoned rooms be visible in the Zones tab as "Global (unassigned)" or
  only in the Rooms tab? Answer affects whether the Zones tab needs to list all
  rooms or only assigned ones.
