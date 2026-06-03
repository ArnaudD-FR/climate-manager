---
phase: 14-default-zone-consolidation
plan: "01"
subsystem: storage
tags:
  - schema-migration
  - tdd
  - compat-shim
dependency_graph:
  requires: []
  provides:
    - default_zone key in DEFAULT_CONFIG (D-01)
    - legacy flat-key compat shim in storage.async_load (D-02/D-03)
  affects:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/storage.py
    - tests/test_storage.py
tech_stack:
  added: []
  patterns:
    - "Compat shim checks raw stored data (not merged result) to detect legacy
      format"
    - "Day-fill applied in both legacy and new-format load paths"
key_files:
  created: []
  modified:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/storage.py
    - tests/test_storage.py
decisions:
  - "D-01: DEFAULT_CONFIG uses single default_zone ZoneConfig; four old flat
    keys removed"
  - "D-02/D-03: lazy read-time compat shim in storage.async_load promotes
    legacy flat keys to default_zone on load"
  - "Shim guard checks raw stored dict (not merged result) — plan literal
    guard would fail with updated DEFAULT_CONFIG that always has default_zone"
metrics:
  duration_minutes: 7
  completed: "2026-06-03T21:37:46Z"
  tasks_completed: 2
  files_changed: 3
---

# Phase 14 Plan 01: Storage Schema Reshape Summary

Reshaped DEFAULT_CONFIG so the Default Zone is a single first-class
`default_zone: ZoneConfig` entry, and added a lazy read-time compat shim
that promotes the four legacy flat keys into `default_zone` on load.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Storage compat shim tests (RED) | 0aa2f47 | tests/test_storage.py |
| 2 | DEFAULT_CONFIG reshape + storage compat shim (GREEN) | c197891 | const.py, storage.py |

## What Was Built

- `const.py`: Removed `global_mode`, `global_time_program`, `default_zone_name`
  flat keys from `DEFAULT_CONFIG`. Added single `default_zone` key shaped as a
  full `ZoneConfig` with `name`, `mode`, `time_program`, `preheat_enabled`.
- `storage.py`: Removed the old `global_time_program` day-fill block.
  Added Phase 14 compat shim after the GAP-01 block. The shim detects old
  format via `"global_mode" in stored and "default_zone" not in stored` (guards
  against false-positive on new-format configs), then runs day-fill on the legacy
  time_program before absorbing it into `default_zone`. The else branch runs
  day-fill on `default_zone["time_program"]` for new-format configs.
- `tests/test_storage.py`: Updated 5 existing tests to assert on `default_zone`
  instead of flat keys. Added 2 new compat shim tests:
  `test_load_legacy_flat_keys_builds_default_zone` and
  `test_load_new_format_reads_default_zone_directly` with day-fill assertions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Compat shim guard checks `stored` not `result`**

- **Found during:** Task 2 GREEN phase
- **Issue:** The plan specified the literal guard
  `"global_mode" in result and "default_zone" not in result`. After
  DEFAULT_CONFIG gained a `default_zone` key, the merged `result` always has
  `default_zone` from defaults — the `"default_zone" not in result` condition
  is always False and the shim never fires.
- **Fix:** Changed the guard to check `"global_mode" in stored and
  "default_zone" not in stored` (raw stored data, not merged result). Legacy
  stored data never has `default_zone`; new-format stored data always has it.
  This correctly detects format without ambiguity.
- **Files modified:** `custom_components/climate_manager/storage.py`
- **Commit:** c197891

## Verification

- `pytest tests/test_storage.py`: 21 passed
- `grep -c '"global_mode"' const.py`: 0
- `grep -c '"default_zone"' const.py`: 1
- `make lint`: Passed

## Known Stubs

None — all tests pass and data flows correctly through the compat shim.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond
what is specified in the plan's threat model.

## Self-Check: PASSED

- tests/test_storage.py: exists and contains 21 tests
- custom_components/climate_manager/const.py: default_zone key present,
  global_mode absent
- custom_components/climate_manager/storage.py: compat shim at line 172
- Commits 0aa2f47 (RED) and c197891 (GREEN) exist in git log
