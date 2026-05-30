---
phase: 09-trv-temperature-offset-auto-calibration
plan: "01"
subsystem: testing
tags: [python, homeassistant, tdd, trv, calibration, tado-x]

# Dependency graph
requires: []
provides:
  - supports_offset_calibration capability guard in trv.py (D-08/CALIB-03)
  - set_trv_offset service-call helper in trv.py (CALIB-02)
  - 7 unit tests covering both functions in test_trv.py
affects:
  - 09-02 (coordinator plan consumes both function signatures)
  - any plan that calls set_trv_offset or checks supports_offset_calibration

# Tech tracking
tech-stack:
  added: []
  patterns:
    - attribute-first/service-second capability guard (D-08, Pitfall 3)
    - single-call offset service helper mirroring set_trv_off pattern
    - async_mock_service for tado_x domain in unit tests

key-files:
  created: []
  modified:
    - custom_components/climate_manager/trv.py
    - tests/test_trv.py

key-decisions:
  - "Attribute-first (temperature_offset presence) then service-second
    (tado_x.set_temperature_offset) guard order — brand-agnostic before
    Tado X-specific (D-08, Pitfall 3)"
  - "supports_offset_calibration guards only None state (not unavailable) —
    capability can be detected while TRV is temporarily unavailable,
    matching supports_hvac_off pattern exactly"
  - "set_trv_offset service data uses offset parameter name per
    09-RESEARCH.md A1 — if live HA testing in Plan 04 reveals a different
    name, fix it there"

patterns-established:
  - "Capability guard: sync, None-only state guard, attribute check first,
    service registry check second (mirrors supports_hvac_off)"
  - "Offset service helper: async, None/unavailable guard, single
    async_call with blocking=True (mirrors set_trv_off)"

requirements-completed: [CALIB-02, CALIB-03]

# Metrics
duration: 2min
completed: 2026-05-30
---

# Phase 9, Plan 01: TRV Offset Calibration Primitives Summary

**`supports_offset_calibration` attribute-first capability guard and
`set_trv_offset` Tado X service helper added to trv.py with 7 passing tests**

## Performance

- **Duration:** 2 min
- **Started:** 2026-05-30T12:45:34Z
- **Completed:** 2026-05-30T12:47:33Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `supports_offset_calibration(hass, entity_id) -> bool` implemented with
  correct attribute-first/service-second guard order (D-08, Pitfall 3)
- `set_trv_offset(hass, entity_id, offset) -> None` implemented with
  None/unavailable guard and single `tado_x.set_temperature_offset` call
- 7 new unit tests added (Tests 9-15), all passing; full 15-test suite green
- TDD gate compliance: RED commit (test, ImportError) then GREEN commit (feat)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests (RED)** - `0a9081c` (test)
2. **Task 2: Implement both functions (GREEN)** - `dbfee95` (feat)

_Note: TDD plan — test commit precedes feat commit per RED/GREEN protocol_

## Files Created/Modified

- `custom_components/climate_manager/trv.py` - Added
  `supports_offset_calibration` (lines 119-143) and `set_trv_offset`
  (lines 145-168); both follow existing analogs exactly
- `tests/test_trv.py` - Added Tests 9-15: 4 tests for
  `supports_offset_calibration` and 3 tests for `set_trv_offset`

## Decisions Made

- Attribute-first/service-second guard order (D-08, Pitfall 3): checks
  `temperature_offset` attribute before `tado_x.set_temperature_offset`
  service to ensure brand-agnostic detection takes priority
- `supports_offset_calibration` does NOT guard on `state.state ==
  "unavailable"` — mirrors `supports_hvac_off` which only guards on `None`;
  capability detection works even when TRV is temporarily unavailable
- Service data parameter name `offset` used as specified in
  09-RESEARCH.md A1; deferred empirical verification to Plan 04 live testing

## Deviations from Plan

None - plan executed exactly as written.

The pre-commit ruff-format hook reformatted `test_trv.py` after Task 1
(tightened whitespace in `async_set` call); re-staged and re-committed
within the same task. Not a deviation — standard hook behavior.

## TDD Gate Compliance

- RED gate: `test(09-01)` commit `0a9081c` — ImportError confirmed
- GREEN gate: `feat(09-01)` commit `dbfee95` — all 15 tests passing

Both gates present in git log in correct order.

## Issues Encountered

- `.venv/bin/python` not present in worktree; used main repo
  `/home/arnaud/dev/climate_manager/.venv/bin/python` directly. Tests ran
  correctly because `pyproject.toml` configures pytest with correct paths.

## Known Stubs

None - both functions are fully implemented with real logic. No hardcoded
empty values or placeholder returns.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes
introduced. Both functions are internal helpers operating within the existing
HA service bus security model.

## Next Phase Readiness

- `supports_offset_calibration` and `set_trv_offset` are ready for
  consumption by Plan 02 (coordinator calibration engine)
- Signatures are stable: Plan 02 can import both directly
- No blockers

---
*Phase: 09-trv-temperature-offset-auto-calibration*
*Completed: 2026-05-30*
