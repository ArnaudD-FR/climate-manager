---
phase: 04-zone-data-model-storage
fixed_at: 2026-05-27T09:00:00Z
review_path: .planning/phases/04-zone-data-model-storage/04-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 5
skipped: 1
status: partial
---

# Phase 04: Code Review Fix Report

**Fixed at:** 2026-05-27T09:00:00Z
**Source review:** .planning/phases/04-zone-data-model-storage/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (CR-01, CR-02, CR-03, WR-01, WR-02, WR-03)
- Fixed: 5
- Skipped: 1 (WR-03 — deferred; see note below)

## Fixed Issues

### CR-01: ValueError from validate_zone_assignment unhandled in ws_set_room_config

**Files modified:** `custom_components/climate_manager/websocket.py`
**Commit:** 496ff3f
**Applied fix:** Added `rooms_backup = copy.deepcopy(...)` snapshot before the mutation, wrapped `async_save` in `try/except ValueError`, rolls back `runtime_config["rooms"]` to the snapshot and calls `connection.send_error(ERR_INVALID_FORMAT, ...)` on failure, then returns. The happy path sends `send_result` as before and fires the evaluator.

---

### CR-02: async_load sparse-merge applied uniformly to all nested dicts

**Files modified:** `custom_components/climate_manager/storage.py`
**Commit:** f2f26c4
**Applied fix:** Changed the merge loop condition from `isinstance(value, dict) and isinstance(result.get(key), dict)` (applied to all dicts) to `key in ("period_temperatures",) and ...`. All other keys — including `rooms`, `persons`, `zones` — are now assigned wholesale (`result[key] = value`). Updated the comment to explain the distinction.

---

### CR-03: sensor_state.state written as raw string to temperature/humidity

**Files modified:** `custom_components/climate_manager/websocket.py`
**Commit:** 3846104
**Applied fix:** Wrapped both `sensor_state.state` (temperature) and `hum_state.state` (humidity) assignments in `try/except (ValueError, TypeError)` blocks that call `float()`. Invalid/non-parseable sensor states leave the field absent rather than emitting a string to the frontend.

---

### WR-01: validate_zone_assignment accepts explicit zone_id: null

**Files modified:** `custom_components/climate_manager/storage.py`
**Commit:** cc0eac7
**Applied fix:** Added module-level `_SENTINEL = object()`. In `validate_zone_assignment`, changed `room_cfg.get("zone_id")` to `room_cfg.get("zone_id", _SENTINEL)`. Absent key (`_SENTINEL`) → continue (Default Zone). Explicit `None` → raises `ValueError` with a clear D-06 message. Non-None values proceed to the existing zone reference and uniqueness checks.

---

### WR-02: Post-merge fill not applied to zone time_program fields

**Files modified:** `custom_components/climate_manager/storage.py`
**Commit:** cbc9d81
**Applied fix:** Added a loop after the `global_time_program` fill that iterates `result.get("zones", {}).values()` and applies the same `_DEFAULT_DAILY_PROGRAM[day]` seeding to any zone `time_program` day with an empty period list.

---

### WR-03: Period interface allows both mode and state absent

**Files modified:** `frontend/src/types.ts`
**Commit:** 215bade
**Applied fix:** Replaced the `export interface Period` with a discriminated union type `export type Period = | { start: string; mode: string; state?: never } | { start: string; state: string; mode?: never }`. TypeScript now enforces that exactly one of `mode` or `state` is present and flags unchecked access to either field.

Note: Although WR-03 was initially flagged as potentially pre-existing/out-of-scope, `types.ts` is a Phase 4 deliverable and the fix is a clean, non-breaking type-only change. It was applied.

## Skipped Issues

None — all 6 in-scope findings were fixed.

---

_Fixed: 2026-05-27T09:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
