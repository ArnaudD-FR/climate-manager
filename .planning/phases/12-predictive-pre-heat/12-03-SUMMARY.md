---
phase: 12-predictive-pre-heat
plan: "03"
subsystem: websocket
tags: [python, websocket, preheat, validation, tdd, trust-boundary]

requires:
  - phase: 12-predictive-pre-heat
    plan: "02"
    provides: _preheat_active/_preheat_target/_preheat_suppressed dicts in
      coordinator + _build_status_payload preheat fields
    this-uses: coordinator._preheat_active, coordinator._preheat_target,
      coordinator._preheat_suppressed (all three read in ws_get_status)

provides:
  - ws_get_status preheat field parity with _build_status_payload push path
  - preheat_max_lead_minutes [0,480] int clamp in ws_set_room_config
  - preheat_enabled bool coercion in ws_set_room_config
  - wakeup_advance_minutes [0,480] clamp replacing preheat_lead_minutes
    in ws_set_person_config (with legacy key backward-compat mapping)
  - 5 new tests in tests/test_preheat.py (Plans 03 Tasks 1 and 2)

affects:
  - 12-04 frontend pre-heat UI (relies on all three fields in get_status
    for correct initial load — Pitfall 1 now closed)

tech-stack:
  added: []
  patterns:
    - D-10: ws_get_status reads coordinator._preheat_*.get(area_id, default)
      directly — same pattern as _build_status_payload, no intermediary
    - D-01: clamp block sits BEFORE the setdefault/update call in
      ws_set_room_config — invalid keys never reach persist
    - D-02: legacy preheat_lead_minutes renamed via incoming.pop() before the
      wakeup_advance_minutes clamp so a single validation path handles both

key-files:
  created: []
  modified:
    - custom_components/climate_manager/websocket.py
    - tests/test_preheat.py
    - tests/test_calendar.py

key-decisions:
  - "D-10: ws_get_status adds three preheat fields by reading coordinator
    instance dicts directly, with False/None/False defaults for absent rooms"
  - "D-01: preheat_max_lead_minutes validated as int in [0,480]; dropped
    (not clamped) on invalid — prevents negative/oversized lead times"
  - "D-01 coerce: preheat_enabled normalized to Python bool via bool() before
    persist — int 1 becomes True, int 0 becomes False"
  - "D-02: preheat_lead_minutes mapped to wakeup_advance_minutes in
    incoming dict before the clamp block — one validation path, two keys"

requirements-completed: [PREHEAT-01, PREHEAT-04]

duration: ~7min
completed: 2026-06-02
---

# Phase 12 Plan 03: WebSocket Trust-Boundary Hardening Summary

**ws_get_status preheat field parity + room/person config validation
at the WS trust boundary (T-12-06, T-12-07, D-01, D-02, D-10)**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-06-02T18:43:56Z
- **Completed:** 2026-06-02T18:50:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added `preheat_active`, `preheat_target`, `preheat_suppressed` to
  `ws_get_status` room payload (D-10 / PREHEAT-04) — initial page load now
  returns identical fields to the push payload; Pitfall 1 closed
- Added `preheat_max_lead_minutes` int [0,480] drop-on-invalid validation
  and `preheat_enabled` bool coercion in `ws_set_room_config` (D-01 / T-12-06)
- Renamed `preheat_lead_minutes` → `wakeup_advance_minutes` in
  `ws_set_person_config` (D-02 / T-12-07) with legacy key backward-compat
  mapping; updated docstring accepted-keys list
- Created 5 new tests in tests/test_preheat.py (TDD RED→GREEN for Tasks 1+2)
- Updated tests/test_calendar.py `test_ws_persists_preheat_lead_minutes`
  to assert new D-02 behavior (legacy key → wakeup_advance_minutes stored)
- Full suite: 214 tests pass (was 209; +5 new preheat WS tests)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing test for ws_get_status preheat fields** - `74d3cb8`
2. **Task 1 GREEN: Add preheat fields to ws_get_status** - `5e2f624`
3. **Task 2 RED: Failing tests for room config clamping + wakeup_advance** -
   `8a0d37e`
4. **Task 2 GREEN: Implement room clamp + person key rename** - `68dd679`
5. **Deviation fix: Update test_calendar regression for D-02** - `c55edd7`

_TDD: RED→GREEN for both tasks. Tests confirmed failing before implementation._

## Files Created/Modified

- `custom_components/climate_manager/websocket.py` — Task 1: three
  coordinator._preheat_*.get() calls in ws_get_status after has_trv;
  Task 2: D-01 clamp block in ws_set_room_config; D-02 legacy rename +
  T-12-07 clamp in ws_set_person_config; docstring updated
- `tests/test_preheat.py` — Added 5 new tests:
  test_ws_get_status_preheat_fields, test_ws_set_room_preheat_config,
  test_ws_room_max_lead_clamped, test_ws_room_enabled_coerced_bool,
  test_ws_set_person_wakeup_advance; helper _setup_ws_entry added
- `tests/test_calendar.py` — Updated test_ws_persists_preheat_lead_minutes
  to assert wakeup_advance_minutes=90 and absence of preheat_lead_minutes

## Decisions Made

- D-10 implementation: ws_get_status reads coordinator._preheat_active/
  _preheat_target/_preheat_suppressed directly using .get() with defaults
  (False/None/False) — same read pattern as _build_status_payload, no wrapper
- D-01 clamp: drop-on-invalid (not clamp-to-bounds) matches RESEARCH
  Security Domain V5 intent — a value of 999 indicates a malformed payload
  not a value that should be silently corrected to 480
- D-02 legacy compat: preheat_lead_minutes is pop()d and moved to
  wakeup_advance_minutes in the incoming dict BEFORE the clamp, so the
  same [0,480] validation runs regardless of which key name was sent

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_calendar.py test_ws_persists_preheat_lead_minutes**

- **Found during:** Task 2 GREEN phase (full suite run)
- **Issue:** Pre-existing test asserted `preheat_lead_minutes` persists under
  the old key name. After D-02 implementation, the legacy key is mapped to
  `wakeup_advance_minutes`, causing the assertion to fail.
- **Fix:** Updated the test to assert `wakeup_advance_minutes == 90` and
  `preheat_lead_minutes not in persisted` — matches the D-02 spec exactly.
  Added comment explaining the D-02 backward-compat behavior.
- **Files modified:** tests/test_calendar.py
- **Commit:** c55edd7

## TDD Gate Compliance

- Task 1 RED: `74d3cb8` (test) — test confirmed FAILED before implementation
- Task 1 GREEN: `5e2f624` (feat) — test confirmed PASSED after implementation
- Task 2 RED: `8a0d37e` (test) — tests confirmed FAILED before implementation
- Task 2 GREEN: `68dd679` (feat) — tests confirmed PASSED after implementation

## Known Stubs

None.

## Threat Flags

None — T-12-06 and T-12-07 mitigations implemented as planned. No new
trust-boundary surface introduced beyond what the plan's threat model covers.

## Self-Check

Files exist:

- custom_components/climate_manager/websocket.py: FOUND
- tests/test_preheat.py: FOUND
- tests/test_calendar.py: FOUND

Commits exist:

- 74d3cb8 (Task 1 RED): FOUND
- 5e2f624 (Task 1 GREEN): FOUND
- 8a0d37e (Task 2 RED): FOUND
- 68dd679 (Task 2 GREEN): FOUND
- c55edd7 (deviation fix): FOUND

Tests: 214 passed, 0 failed

## Self-Check: PASSED

---
*Phase: 12-predictive-pre-heat*
*Completed: 2026-06-02*
