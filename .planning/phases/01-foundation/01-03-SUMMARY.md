---
phase: 01-foundation
plan: "03"
subsystem: integration-entry-point
tags: [setup-entry, runtime-data, smoke-test, tdd, foundation]
dependency_graph:
  requires: [01-01-scaffold, 01-02-backend-modules]
  provides: [async_setup_entry, async_unload_entry, ClimateManagerData, ClimateManagerConfigEntry, smoke-test]
  affects: [all-phase-2-plans, coordinator, phase-2-schedule-engine]
tech_stack:
  added: []
  patterns:
    - runtime-data-typed-dataclass (entry.runtime_data = ClimateManagerData, Pattern 2)
    - enable-custom-integrations-autouse (conftest.py autouse fixture for HA test harness)
key_files:
  created:
    - tests/test_init.py
  modified:
    - custom_components/climate_manager/__init__.py
    - tests/conftest.py
decisions:
  - "ClimateManagerData @dataclass fields: store, runtime_config, rooms, persons — minimal, typed, auto-cleaned on unload"
  - "type alias ClimateManagerConfigEntry = ConfigEntry[ClimateManagerData] — modern Pattern 2 typed runtime_data"
  - "async_setup_entry calls store.async_load + discover_rooms + discover_persons — all three wired at setup"
  - "global hass.data dict intentionally absent — all state on entry.runtime_data (T-01-11)"
  - "conftest.py enable_custom_integrations autouse fixture required for integration not found fix (Rule 3)"
metrics:
  duration: "~5 minutes"
  completed_date: "2026-05-16"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
---

# Phase 1 Plan 03: Integration Entry Point Wiring Summary

**One-liner:** Fully loadable HA integration with Store+discovery wired into typed entry.runtime_data dataclass, proven by 5 smoke tests reaching "loaded" state (18 total tests green).

## What Was Built

The integration entry point (`__init__.py`) replaced the plan-01 placeholder with full setup and unload implementations. This is the foundation spine that ties together all prior work:

1. **`ClimateManagerData` dataclass** — Typed container for in-memory integration state: `store`, `runtime_config`, `rooms`, `persons`. Stored exclusively on `entry.runtime_data` (modern Pattern 2); the global `hass.data` dict is never used.

2. **`ClimateManagerConfigEntry`** — Type alias `ConfigEntry[ClimateManagerData]` for typed access to `entry.runtime_data` throughout the codebase.

3. **`async_setup_entry`** — Constructs `ClimateManagerStore`, calls `async_load()`, runs `discover_rooms()` and `discover_persons()`, then sets `entry.runtime_data`. No coordinator, scheduler, or time-interval listener started (Phase 2 scope).

4. **`async_unload_entry`** — Delegates to `hass.config_entries.async_unload_platforms(entry, PLATFORMS)`. Required even with empty PLATFORMS to mark the integration as reloadable (Pitfall 1, T-01-10).

5. **`tests/conftest.py`** — Updated with `enable_custom_integrations` autouse fixture enabling custom integrations to load in the test harness (was missing, causing "Integration not found" failures).

6. **`tests/test_init.py`** — 5 smoke tests: "loaded" state assertion, runtime_data populated, runtime_config equals DEFAULT_CONFIG on fresh install, unload returns True, hass.data not used.

## Commits

| Task | Description | Hash |
|------|-------------|------|
| Task 1+2 RED | Failing smoke tests for async_setup_entry and runtime_data | 3e70303 |
| Task 1+2 GREEN | Implement __init__.py + conftest.py autouse fixture | 71d2cf5 |

## Files Modified

| File | Change |
|------|--------|
| `custom_components/climate_manager/__init__.py` | Full replacement: ClimateManagerData dataclass, ClimateManagerConfigEntry alias, async_setup_entry, async_unload_entry |
| `tests/conftest.py` | Added enable_custom_integrations autouse fixture (required for integration to load in tests) |
| `tests/test_init.py` | Created: 5 smoke tests asserting loaded state, runtime_data fields, unload, no hass.data usage |

## Verification Results

All plan verification commands passed:

- `.venv/bin/python -m pytest tests/ -v` — 18/18 PASSED (storage x5, discovery x4, trv x4, init x5)
- `entry.state.value == "loaded"` confirmed by `test_setup_entry_reaches_loaded_state`
- `grep -n 'hass.data\[' __init__.py` returns nothing
- `grep -n 'async_unload_entry' __init__.py` returns match at line 83
- Syntax check: `ast.parse(open('__init__.py').read())` prints "syntax OK"

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] conftest.py missing enable_custom_integrations autouse fixture**
- **Found during:** Task 2 (GREEN phase — integration failed to load with "Integration not found")
- **Issue:** The wave 2 conftest.py had only a comment about `enable_custom_integrations` being available but never actually requested it in an autouse fixture. Without the autouse fixture, tests using `hass.config_entries.async_setup()` fail because HA's test harness blocks loading from `custom_components/`. Error: `Setup failed for 'climate_manager': Integration not found.`
- **Fix:** Added `@pytest.fixture(autouse=True) def auto_enable_custom_integrations(enable_custom_integrations)` to `tests/conftest.py`. This is the canonical pattern from RESEARCH.md Pattern 6.
- **Files modified:** `tests/conftest.py`
- **Commit:** 71d2cf5

**2. [Rule 1 - Bug] Docstring text contained hass.data pattern matched by acceptance criteria grep**
- **Found during:** Task 1 acceptance verification
- **Issue:** The module docstring and dataclass docstring mentioned `hass.data[DOMAIN]` to explain the anti-pattern being avoided. The acceptance criteria grep `! grep -q 'hass.data\['` matched these docstring lines, causing the check to fail.
- **Fix:** Rewrote docstring references to use "global hass.data dict" instead of the literal bracket notation.
- **Files modified:** `custom_components/climate_manager/__init__.py`
- **Commit:** 71d2cf5

## TDD Gate Compliance

| Phase | File | RED Commit | GREEN Commit |
|-------|------|------------|--------------|
| Task 1+2 (init + conftest) | tests/test_init.py | 3e70303 (ImportError) | 71d2cf5 |

TDD RED/GREEN cycle followed: tests written first, confirmed failing with `ImportError: cannot import name 'ClimateManagerData'`, then implementation written to pass.

## Known Stubs

None. `async_setup_entry` fully implements store loading, room discovery, and person discovery. `entry.runtime_data` is populated with live (test-environment) data on every call. No hardcoded empty values flow to any output.

## Threat Surface

No new threat surface beyond what the plan's `<threat_model>` captured:

- T-01-10 (DoS via ghost listeners): mitigated — `async_unload_entry` exists and is tested to return True; no scheduled callbacks started in Phase 1.
- T-01-11 (Tampering via hass.data global state): mitigated — the global hass.data dict is never written by this integration; acceptance criteria grep and `test_hass_data_domain_not_used` both confirm this.
- T-01-12 (DoS via blocking I/O): accept — `async_setup_entry` only awaits `Store.async_load()` (non-blocking) and registry reads (in-memory); no synchronous I/O.

## Self-Check: PASSED

- `custom_components/climate_manager/__init__.py` — FOUND
- `tests/conftest.py` — FOUND
- `tests/test_init.py` — FOUND
- Commit 3e70303 (RED) — FOUND
- Commit 71d2cf5 (GREEN) — FOUND
- 18/18 tests passing — VERIFIED
- Phase 1 primary success criterion (entry.state.value == "loaded") — VERIFIED
