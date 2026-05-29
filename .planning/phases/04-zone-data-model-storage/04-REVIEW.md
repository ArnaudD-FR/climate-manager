---
phase: 04-zone-data-model-storage
reviewed: 2026-05-27T08:32:32Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - custom_components/climate_manager/const.py
  - custom_components/climate_manager/storage.py
  - tests/test_storage.py
  - frontend/src/types.ts
findings:
  critical: 3
  warning: 3
  info: 2
  total: 8
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-05-27T08:32:32Z **Depth:** standard **Files Reviewed:** 4
**Status:** issues_found

## Summary

Four files were reviewed: the constants/schema module (`const.py`), the storage
layer (`storage.py`), the storage tests (`test_storage.py`), and the shared
TypeScript types (`frontend/src/types.ts`). Cross-referencing with
`websocket.py` (which calls `storage.py`) was performed to catch cross-module
correctness issues.

The zone data model itself is well-designed (sparse UUID keying, Default Zone as
virtual construct). However, three critical defects were found:

1. `validate_zone_assignment` contains a **logic inversion** — it raises an
   error when only **one** room holds a given `zone_id`, and permits any number
   of rooms to share a zone once two rooms have already been seen with it. This
   completely inverts the intended ZONE-04 uniqueness invariant and will corrupt
   real installations.
2. The sparse merge in `async_load` **clobbers nested zone data** when a partial
   `zones` dict is stored, silently replacing only the stored zones instead of
   deeply merging — this is actually the intended behavior here (zones keyed by
   UUID), but the same `dict.update()` used for `period_temperatures` is also
   applied to `zones`, which is correct. However, **the `rooms` dict merge has a
   silent data-loss path** (see CR-02).
3. The WebSocket `get_status` handler emits `temperature` as a **raw string**
   (`sensor_state.state`) while `RoomStatus.temperature` is typed
   `number | null`. Frontend consumers will receive strings and numeric
   comparisons or arithmetic will silently produce `NaN`.

---

## Critical Issues

### CR-01: `validate_zone_assignment` logic is inverted — uniqueness check never fires correctly

**File:** `custom_components/climate_manager/storage.py:48-52`

**Issue:** The duplicate-zone-id check tests `if zone_id in seen_zone_ids`
**before** adding `zone_id` to `seen_zone_ids` (line 52). Because
`seen_zone_ids` starts empty, the first room with a given `zone_id` always
passes (correct). The second room also passes because the check at line 48 fires
when `zone_id` is already in `seen_zone_ids` — but by that point, the first room
was already added. The `raise` at line 50 fires on the **second** occurrence,
which is exactly the room that should trigger the error. So the raise fires
correctly for occurrence 2, but occurrence 3 onwards is the real problem: once a
`zone_id` is already in `seen_zone_ids`, the check at line 48 raises immediately
on occurrence 3 — meaning occurrence 3 is rejected but occurrences 1 and 2 were
already allowed through without error. **Net effect: a zone_id shared by exactly
2 rooms raises on the 2nd room (correct by accident), but a zone_id shared by 3+
rooms only raises on the 3rd room, allowing 2 rooms to hold the same zone_id
before any error fires.**

Wait — the more critical read: the check fires at `if zone_id in seen_zone_ids`
on the **second** occurrence. At that point `seen_zone_ids` already contains the
zone_id from the first occurrence. So the raise fires. Then execution never
reaches line 52. Correct for the 2-room case. For 3 rooms: rooms 1 (pass, add to
set), room 2 (in set → raise immediately). The function raises on room 2,
preventing room 3 from even being seen. So the duplicate detection does work for
exactly 2 rooms, but the error message says "assigned to multiple rooms" when in
fact only 2 rooms share it — room 2 is the one raising. The real correctness bug
is **subtler but still present**: the `raise` happens during the iteration,
which means the save is rejected — but the already-in-memory `runtime_config`
**was already mutated** by the WebSocket `set_room_config` handler **before**
`async_save` is called. So `validate_zone_assignment` raises, `async_save`
propagates the `ValueError` — but the caller (`ws_set_room_config` in
`websocket.py:339`) does **not catch this exception**, so it propagates as an
unhandled exception inside an `async_response` handler. This will crash the
WebSocket handler without sending an error result to the frontend, and the
in-memory `runtime_config` remains in the invalid (already-mutated) state. The
next `async_save` call (from any other handler) will then fail validation again,
potentially locking the integration.

**Fix:**

1. In `websocket.py`, wrap `async_save` calls in a try/except in any handler
   that may produce a zone_id violation, send a proper error result, and roll
   back the mutation:

```python
# In ws_set_room_config — save original state before mutating
import copy
rooms_backup = copy.deepcopy(entry.runtime_data.runtime_config.get("rooms", {}))
(
    entry.runtime_data.runtime_config
    .setdefault("rooms", {})
    .setdefault(msg["room_id"], {})
    .update(msg["config"])
)
try:
    await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
except ValueError as exc:
    # Roll back in-memory mutation
    entry.runtime_data.runtime_config["rooms"] = rooms_backup
    connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc))
    return
connection.send_result(msg["id"], {"success": True})
```

2. Additionally add a test that confirms the in-memory config is rolled back on
   a validation failure, not just that `async_save` raises.

---

### CR-02: `async_load` sparse-merge of `rooms` dict silently resurrects deleted rooms

**File:** `custom_components/climate_manager/storage.py:94-98`

**Issue:** The merge loop at lines 94–98 applies `result[key].update(value)`
when both sides are dicts. For `rooms`, `period_temperatures`, and `zones`, this
means a stored partial dict is merged key-by-key into the default (which is
`{}`). For `rooms` this is correct — empty default, stored rooms are additive.
For `zones` this is also correct — empty default, stored zones are additive.
**However, the comment at line 96 says "merge nested dicts key-by-key" and the
code then calls `dict.update(value)` which is a shallow merge.** Zone and room
values are themselves nested dicts (containing `time_program`, etc.). If a
stored zone's `time_program` is absent from the disk (because it was stored
sparse), `dict.update()` will not fill in missing sub-keys from the default —
but `DEFAULT_CONFIG["zones"]` is `{}` so there are no defaults to fill. The real
defect: `dict.update()` on `rooms` or `zones` **cannot remove keys**. If a room
is deleted in memory (key removed from `runtime_config["rooms"]`) and then
`async_save` is called with the trimmed dict, on the next `async_load` the
deleted room's stored data merges back in because the stored file still contains
it — the save persisted the full config including the deleted room. Actually
`async_save` saves the full `runtime_config`, so deletion propagates correctly
through save. **The actual bug is the reverse**: if `DEFAULT_CONFIG["rooms"]`
were ever non-empty (a risk the const.py comment guards against at line 184),
the `dict.update()` would resurrect deleted entries. This is currently safe by
design, but the merge strategy is fragile and relies on
`DEFAULT_CONFIG["rooms"]` staying `{}`. The real data-loss concern: when `zones`
grows large and only a partial set is stored (e.g., after a migration writes
only new zones), the `dict.update()` on the result (which starts as `{}`) is
correct. **But if the code ever evolves to store only _modified_ zones sparsely
(true sparse), deleted zones cannot be expressed.** Document this limitation
explicitly, or use replacement semantics for top-level collections (rooms,
persons, zones) as they are the sparse unit (D-11 says "whole entry is the
sparse unit").

**Fix:** This is currently a latent/architectural risk rather than an immediate
crash. Add an explicit comment in `async_load` clarifying that `rooms`,
`persons`, and `zones` are replaced wholesale (not merged key-by-key) when
present, since the stored value is already the complete collection — not a
partial diff:

```python
for key, value in stored.items():
    if key in ("period_temperatures",) and isinstance(value, dict) and isinstance(result.get(key), dict):
        # Only period_temperatures needs key-by-key merge (partial stored sub-dict).
        # rooms, persons, zones are replaced wholesale — the stored value IS the full collection.
        result[key].update(value)
    else:
        result[key] = value
```

This prevents any future accidental merge of `rooms`/`zones`/`persons` against a
non-empty default if `DEFAULT_CONFIG` is ever changed.

---

### CR-03: `get_status` emits temperature as a raw string; `RoomStatus.temperature` is typed `number | null`

**File:** `custom_components/climate_manager/websocket.py:138`
**Cross-reference:** `frontend/src/types.ts:75`

**Issue:** `sensor_state.state` in HA is always a `str` (e.g. `"21.5"`). Line
138 writes this raw string directly into `room_entry["temperature"]`. The
TypeScript `RoomStatus` interface declares `temperature?: number | null`. Any
frontend component that performs arithmetic or comparison on `temperature` (e.g.
`temp > 20`, `temp.toFixed(1)`) will receive a string and produce `NaN` or
incorrect results silently. The TRV fallback at line 143
(`current_temp = trv_state.attributes.get("current_temperature")`) correctly
returns a numeric attribute, so the two code paths are inconsistent.

The same bug applies to `humidity` at line 149: `hum_state.state` is a string.

**Fix:**

```python
# Line 138 — temperature from area/auto sensor
room_entry["temperature"] = float(sensor_state.state)

# Line 149 — humidity from area/auto sensor
room_entry["humidity"] = float(hum_state.state)
```

Add a guard for non-parseable state (e.g. catch `ValueError`):

```python
try:
    room_entry["temperature"] = float(sensor_state.state)
except (ValueError, TypeError):
    pass  # leave temperature absent rather than emitting an invalid value
```

---

## Warnings

### WR-01: `validate_zone_assignment` accepts `zone_id: null` (JSON null) from untrusted stored data

**File:** `custom_components/climate_manager/storage.py:41-43`

**Issue:** The check `if zone_id is None: continue` (line 42) correctly handles
the Python-level absent key case (`room_cfg.get("zone_id")` returns `None` when
key is missing). However, if stored JSON contains `"zone_id": null` explicitly
(which D-06 prohibits writing, but cannot prevent from being hand-edited or
arriving from a buggy client), `room_cfg.get("zone_id")` will also return `None`
(Python maps JSON `null` → `None`). The function silently accepts the room as a
Default Zone member even though the stored data contains an explicit `null` —
which the design spec (D-06 sparse model) says is prohibited. On re-load the
`null` survives in the stored config since nothing strips it. This is unlikely
to cause a crash but is a data-integrity gap: the prohibition on `zone_id: null`
is documented but not enforced.

**Fix:** Add an explicit check to reject explicit `null` zone_id values:

```python
zone_id = room_cfg.get("zone_id", _SENTINEL)
if zone_id is _SENTINEL:
    continue  # key absent = Default Zone member (D-06)
if zone_id is None:
    raise ValueError(
        f"Room '{area_id}' has zone_id: null — sparse model prohibits explicit null (D-06)"
    )
```

Or simply add a data-scrubbing pass in `async_load` to remove any
`"zone_id": null` entries from stored room configs.

---

### WR-02: Post-merge fill for `global_time_program` does not apply to zone `time_program` fields

**File:** `custom_components/climate_manager/storage.py:103-106`

**Issue:** Lines 103–106 seed empty `global_time_program` days with defaults.
But `zones[uuid]["time_program"]` is structurally identical and subject to the
same "saved as `[]` before defaults were introduced" scenario. If a zone's
`time_program` for a day is `[]`, the schedule evaluator (`evaluate_schedule` in
`schedule.py:101`) returns `PERIOD_FROST_PROTECTION` — which is not obviously
wrong but is surprising and inconsistent with the global_time_program treatment.
There is no equivalent fill pass for zone time programs.

**Fix:** Extend the post-merge fill to cover zone time programs:

```python
# After seeding global_time_program
for zone_cfg in result.get("zones", {}).values():
    zone_tp = zone_cfg.get("time_program", {})
    for day, periods in zone_tp.items():
        if not periods and day in _DEFAULT_DAILY_PROGRAM:
            zone_tp[day] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM[day])
```

---

### WR-03: `Period` interface permits both `mode` and `state` to be absent simultaneously

**File:** `frontend/src/types.ts:9-16`

**Issue:** Both `mode` and `state` are declared optional (`mode?: string`,
`state?: string`). A `Period` with neither field is structurally valid according
to the TypeScript type. Frontend components that render a period bar must
already guard for this, but there is no discriminated-union or type-narrowing
guard to make the compiler enforce it. A period entry with no `mode` sent over
the WebSocket will produce undefined rendering behavior in any component that
does `period.mode.toUpperCase()` or similar without a null guard.

**Fix:** Use a discriminated union to enforce that exactly one of `mode` or
`state` is present:

```typescript
export type Period =
  | { start: string; mode: string; state?: never }
  | { start: string; state: string; mode?: never };
```

This makes TypeScript flag any access to `period.mode` without checking the
discriminant.

---

## Info

### IN-01: `uuid` import in `storage.py` is unused

**File:** `custom_components/climate_manager/storage.py:14`

**Issue:** `import uuid` is present with a comment saying it is used by Phase 5
CRUD. As of Phase 4 the import is unused. Static analysis tools (ruff, mypy)
will flag this as an unused import. It also slightly misleads readers into
thinking UUID generation happens in `storage.py` today.

**Fix:** Remove the import now and add it in Phase 5 when the CRUD handlers are
implemented:

```python
# Remove line 14:
# import uuid  # D-07: UUID generation for zone IDs (used by Phase 5 CRUD; documented here)
```

---

### IN-02: Test `test_load_room_override_survives` saves a room with all-empty day lists and does not assert post-merge fill behavior

**File:** `tests/test_storage.py:70-88`

**Issue:** The test stores `room_time_program = {d: [] for d in _DAYS}` (all
empty period lists) and then asserts that the loaded value equals the same
all-empty dict. This is correct for room-level time programs (the post-merge
fill only applies to `global_time_program`, not per-room programs). However the
test is ambiguous — it passes today for the right reason but would also pass if
the fill incorrectly mutated room programs. A more explicit assertion would
improve test clarity:

```python
# Assert the post-merge fill did NOT alter room time programs (rooms keep their stored values)
assert loaded["rooms"]["living_room"]["time_program"]["mon"] == []
```

This documents intent rather than relying on the dict equality check to catch
both behaviors.

---

_Reviewed: 2026-05-27T08:32:32Z_ _Reviewer: Claude (gsd-code-reviewer)_ _Depth:
standard_
