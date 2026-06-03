---
phase: 13-matter-tado-x-real-time-calibration
plan: 02
subsystem: websocket
tags:
  - home-assistant
  - matter
  - tado-x
  - websocket
  - calibration
  - entity-registry

# Dependency graph
requires:
  - phase: 13-matter-tado-x-real-time-calibration
    plan: 01
    provides: "_async_refresh_matter_listeners method + _matter_cal_listeners\
      \ lifecycle"
provides:
  - "set_matter_mapping WS command: D-15 sparse mapping persistence\
    \ with D-16 atomic listener refresh (MCALIB-01)"
  - "get_config extension: matter_entities + tado_x_entities derived\
    \ lists (A2 Option A/C, T-13-06)"
affects:
  - "13-matter-tado-x-real-time-calibration plan 03 (frontend pairing UI\
    \ — consumes matter_entities + tado_x_entities from get_config)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-15: set_matter_mapping factory — mutate sparse dict → pop when\
      \ empty (never store []) → persist → send_result → async_create_task\
      \ listener refresh"
    - "A2 Option A/C: derive matter_entities + tado_x_entities in get_config\
      \ via entity registry platform check, merged into NEW payload dict\
      \ (no runtime_config mutation)"
    - "T-13-04 / Pitfall 7: filter matter_entity_ids to climate.* strings\
      \ before storage"

key-files:
  created: []
  modified:
    - custom_components/climate_manager/websocket.py
    - tests/test_websocket.py

key-decisions:
  - "A2 Option A/C chosen: backend derives matter_entities and tado_x_entities\
    \ from entity registry in get_config — frontend has no direct registry\
    \ access so backend must surface platform info"
  - "D-15/D-16 atomic pattern: persist first, send_result, then\
    \ hass.async_create_task(_async_refresh_matter_listeners) — same\
    \ ordering as set_global_mode (mutate→persist→result→action)"
  - "T-13-06 no-pollution: derived entity lists merged into new payload\
    \ dict, never written to runtime_config (mirrors D-25 climate_entities\
    \ invariant established in Phase 03)"

# Metrics
duration: 4min
completed: 2026-06-03
---

# Phase 13 Plan 02: set_matter_mapping WS Command + get_config Extension

**`set_matter_mapping` WS command with D-15 sparse persistence + D-16\
 listener refresh, and `get_config` extended to surface `matter_entities`\
 + `tado_x_entities` derived lists via entity registry platform checks.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-03T14:42Z
- **Completed:** 2026-06-03T14:46Z
- **Tasks:** 2 (Task 1 TDD RED→GREEN; Task 2 auto with tests)
- **Files modified:** 2

## Accomplishments

- Implemented `_make_ws_set_matter_mapping` factory in websocket.py:
  - Filters `matter_entity_ids` to `climate.*` strings (T-13-04 / Pitfall 7)
  - Sparse D-01 model: stores mapping when non-empty, pops key when empty
    (never stores `[]`)
  - Persists via `store.async_save` then `connection.send_result`
  - D-16: schedules `coordinator._async_refresh_matter_listeners()` via
    `hass.async_create_task` after persist
  - Registered in `async_register_commands` alongside existing commands
- Extended `_make_ws_get_config` to derive `matter_entities` and
  `tado_x_entities` from entity registry (platform == "matter" /
  "tado_x"), merged into NEW payload dict — `runtime_config` never
  mutated (T-13-06 / D-25 invariant)
- 7 new tests (4 Task 1 + 3 Task 2), full suite 240 tests passing

## Task Commits

1. **Task 1: set_matter_mapping WS command** (TDD)
   - `6b69de8` test(13-02): add failing tests for set_matter_mapping (RED)
   - `dd6dbde` feat(13-02): implement set_matter_mapping WS command (GREEN)

2. **Task 2: get_config extension** (auto + 3 behavior tests)
   - `6e7266e` feat(13-02): extend get_config with matter_entities +
     tado_x_entities (A2 Option A/C)

## Files Created/Modified

- `custom_components/climate_manager/websocket.py` — Added
  `_make_ws_set_matter_mapping` factory + registration; extended
  `_make_ws_get_config` with `matter_entities` / `tado_x_entities`
  derived lists; updated module docstring and security notes
- `tests/test_websocket.py` — Added 7 new tests covering D-15 sparse
  mapping, D-01 pop behavior, T-13-04 input filtering, D-16 listener
  refresh trigger, A2 Option A/C entity list derivation, and T-13-06
  no-storage-pollution invariant

## Decisions Made

- **A2 Option A/C (backend-derived entity lists):** frontend cannot
  access the HA entity registry directly, so `get_config` now derives
  `matter_entities` and `tado_x_entities` by iterating
  `entity_reg.entities.values()` and filtering by `platform`. These are
  merged into a new payload dict so `runtime_config` is never mutated.
- **Single iteration of climate_reg_entries:** refactored `get_config`
  to build `climate_reg_entries` list once, then derive all three sorted
  lists from it — avoids three separate iterations of
  `entity_reg.entities.values()`.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints or auth paths introduced. All mitigations from
the plan's `<threat_model>` implemented:

| Flag | File | Description |
|------|------|-------------|
| T-13-04 mitigated | websocket.py | `matter_entity_ids` filtered to
  `climate.*` before storage |
| T-13-06 mitigated | websocket.py | derived entity lists in new payload
  dict only; `runtime_config` never mutated |

## Self-Check: PASSED

- `custom_components/climate_manager/websocket.py` exists with
  `_make_ws_set_matter_mapping` and extended `_make_ws_get_config`
- `tests/test_websocket.py` exists with 7 new tests
- Commits `6b69de8`, `dd6dbde`, `6e7266e` exist in git log
- 240 tests passing, `make lint` clean

---

*Phase: 13-matter-tado-x-real-time-calibration*
*Completed: 2026-06-03*
