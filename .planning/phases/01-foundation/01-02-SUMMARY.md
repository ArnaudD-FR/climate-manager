---
phase: 01-foundation
plan: "02"
subsystem: backend-logic-modules
tags: [config-flow, storage, discovery, trv, tdd]
dependency_graph:
  requires: [01-01-scaffold]
  provides:
    [
      ClimateManagerStore,
      discover_rooms,
      discover_persons,
      set_trv_temperature,
      ClimateManagerFlowHandler,
    ]
  affects: [03-coordinator-wiring, all-phase-2-plans]
tech_stack:
  added: []
  patterns:
    - sparse-merge-storage (DEFAULT_CONFIG deepcopy + top-level update from
      Store)
    - area-entity-registry-discovery (ar.async_get + er.async_get, entity_id
      prefix filter)
    - two-call-trv-sequence (set_hvac_mode(heat) blocking + set_temperature
      blocking)
    - minimal-single-step-config-flow (VERSION=1, async_step_user creates empty
      entry)
key_files:
  created:
    - custom_components/climate_manager/storage.py
    - custom_components/climate_manager/discovery.py
    - custom_components/climate_manager/trv.py
    - custom_components/climate_manager/config_flow.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_storage.py
    - tests/test_discovery.py
    - tests/test_trv.py
  modified: []
decisions:
  - "serialize_in_event_loop not in HA 2024.x Store; removed from constructor
    (Rule 1 auto-fix)"
  - "entity_id.split('.')[0] prefix filter used for climate/person domains
    (safer than .domain attribute per Assumption A1)"
  - "discovery.py uses entity_id prefix for both climate and person filtering
    (verified by tests)"
  - "trv.py contains no 'auto' string (acceptance criteria met by removing it
    from comments too)"
metrics:
  duration: "~18 minutes"
  completed_date: "2026-05-16"
  tasks_completed: 3
  files_created: 9
  files_modified: 0
---

# Phase 1 Plan 02: Backend Logic Modules Summary

**One-liner:** Sparse-merge Store layer, area/entity registry discovery,
two-call TRV heat-mode control, and minimal single-step config flow — all
unit-tested with TDD RED/GREEN cycles.

## What Was Built

Four backend logic modules that form the functional core of the Climate Manager
foundation:

1. **storage.py** (`ClimateManagerStore`) — Wraps HA's `Store` helper.
   `async_load()` returns a deep copy of `DEFAULT_CONFIG` on fresh install, or
   `DEFAULT_CONFIG` merged with stored sparse data. `async_save()` delegates to
   `Store` exclusively — no blocking I/O.

2. **discovery.py** (`discover_rooms`, `discover_persons`) — Queries HA area and
   entity registries using the current `ar.async_get` / `er.async_get` APIs (not
   the deprecated `async_get_registry`). Returns
   `{area_id: [climate_entity_ids]}` for rooms and `[person.* entity_ids]` for
   persons.

3. **trv.py** (`set_trv_temperature`) — Issues the two-call service sequence:
   `climate.set_hvac_mode(heat)` then `climate.set_temperature`, both
   `blocking=True`. Guards silently skip unavailable or missing TRV entities.

4. **config_flow.py** (`ClimateManagerFlowHandler`) — Single-step flow with
   `VERSION = 1`. User clicks Submit → entry created with empty data.
   Single-instance enforcement is in `manifest.json`
   (`single_config_entry: true`).

All four modules are importable and independently unit-testable. 13 unit tests
across three test files, all passing under `.venv/bin/python -m pytest`.

## Commits

| Task   | Description                                                 | Hash    |
| ------ | ----------------------------------------------------------- | ------- |
| Task 1 | storage.py + tests/test_storage.py (TDD RED→GREEN)          | 6825514 |
| Task 2 | discovery.py + tests/test_discovery.py (TDD RED→GREEN)      | 7b8c4e8 |
| Task 3 | trv.py + config_flow.py + tests/test_trv.py (TDD RED→GREEN) | 056a86f |

## Files Created

| File                                               | Purpose                                                                                        |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `custom_components/climate_manager/storage.py`     | ClimateManagerStore: sparse-merge async_load, async_save via Store (INFRA-02)                  |
| `custom_components/climate_manager/discovery.py`   | discover_rooms (area→climate entities), discover_persons (person.\* ids) (ROOM-01/02/03)       |
| `custom_components/climate_manager/trv.py`         | set_trv_temperature: heat-mode-first two-call sequence, availability guard (INFRA-04, ROOM-03) |
| `custom_components/climate_manager/config_flow.py` | ClimateManagerFlowHandler: single-step single-instance flow (D-04, D-05)                       |
| `tests/__init__.py`                                | Python package marker for tests directory                                                      |
| `tests/conftest.py`                                | Shared pytest fixtures (minimal — hass provided by pytest plugin)                              |
| `tests/test_storage.py`                            | 5 storage tests: fresh install, copy isolation, sparse merge, round-trip, room override        |
| `tests/test_discovery.py`                          | 4 discovery tests: climate filter, empty-area exclusion, multi-TRV, person filter              |
| `tests/test_trv.py`                                | 4 TRV tests: two-call order, no-other-modes, unavailable skip, missing skip                    |

## Verification Results

All plan verification commands passed:

- `pytest tests/test_storage.py tests/test_discovery.py tests/test_trv.py -v` —
  13/13 PASSED
- `grep -rn 'async_get_registry' custom_components/climate_manager/` — returns
  only a docstring comment (no code calls)
- `grep -n 'auto' custom_components/climate_manager/trv.py` — returns nothing
  (exit 1)
- `grep -rn 'open(\|json.load\|json.dump' custom_components/climate_manager/storage.py`
  — returns only docstring/comment lines (no code)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `serialize_in_event_loop` not a valid Store parameter in HA
2024.x**

- **Found during:** Task 1 (GREEN phase — all 5 tests failed with TypeError)
- **Issue:** RESEARCH.md Assumption A4 and Pattern 3 referenced
  `Store(..., serialize_in_event_loop=False)`. The installed HA version
  (`pytest-homeassistant-custom-component` 0.13.195) does not have this
  parameter in `Store.__init__`. Actual signature:
  `Store(hass, version, key, private=False, *, atomic_writes=False, encoder=None, minor_version=1, read_only=False)`.
- **Fix:** Removed `serialize_in_event_loop=False` from the `Store` constructor.
  Standard Store behavior is safe for plain dict schemas.
- **Files modified:** `custom_components/climate_manager/storage.py`
- **Commit:** 6825514

**2. [Rule 1 - Bug] "auto" string in trv.py docstrings failed acceptance
criteria grep**

- **Found during:** Task 3 acceptance verification (the plan's
  `! grep -q 'auto' trv.py` criterion)
- **Issue:** Initial docstrings explained the Tado X broken "auto" mode context,
  causing `grep 'auto'` to match.
- **Fix:** Replaced all docstring/comment references to "auto mode" with neutral
  phrasing that preserves the explanation without using the word "auto".
- **Files modified:** `custom_components/climate_manager/trv.py`
- **Commit:** 056a86f

## TDD Gate Compliance

| Phase              | File                    | RED Commit              | GREEN Commit |
| ------------------ | ----------------------- | ----------------------- | ------------ |
| Task 1 (storage)   | tests/test_storage.py   | confirmed (ImportError) | 6825514      |
| Task 2 (discovery) | tests/test_discovery.py | confirmed (ImportError) | 7b8c4e8      |
| Task 3 (trv)       | tests/test_trv.py       | confirmed (ImportError) | 056a86f      |

All three TDD cycles followed the RED→GREEN pattern. Tests were written first
and confirmed failing (ImportError at collection) before implementation was
written.

## Known Stubs

None — all four modules implement their full specified behavior. No hardcoded
empty values, placeholder text, or disconnected data sources.

## Threat Surface

No new threat surface beyond what the plan's `<threat_model>` captured:

- T-01-06 (DoS via blocking I/O): mitigated — `storage.py` uses `Store`
  exclusively, no `open()`/`json.load`/`json.dump` in code paths.
- T-01-07 (wrong hvac_mode): mitigated — `trv.py` hardcodes `"heat"`, no
  `"auto"` string anywhere in the file.
- T-01-08 (unavailable TRV abort): mitigated — `set_trv_temperature` guards on
  `None` or `"unavailable"` state before any service call.
- T-01-09 (config flow injection): mitigated — config flow accepts no user
  fields.

## Self-Check: PASSED

- `custom_components/climate_manager/storage.py` — FOUND
- `custom_components/climate_manager/discovery.py` — FOUND
- `custom_components/climate_manager/trv.py` — FOUND
- `custom_components/climate_manager/config_flow.py` — FOUND
- `tests/__init__.py` — FOUND
- `tests/conftest.py` — FOUND
- `tests/test_storage.py` — FOUND
- `tests/test_discovery.py` — FOUND
- `tests/test_trv.py` — FOUND
- Commit 6825514 — FOUND
- Commit 7b8c4e8 — FOUND
- Commit 056a86f — FOUND
