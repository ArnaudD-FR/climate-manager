---
phase: 07-even-odd-week-scheduling-backend
plan: "02"
subsystem: websocket
tags: [tdd, websocket, scheduling, even-odd, seeding]
dependency_graph:
  requires: []
  provides: [ws-set-person-config-even-odd-seeding]
  affects: [custom_components/climate_manager/websocket.py, tests/test_websocket.py]
tech_stack:
  added: []
  patterns: [copy.deepcopy-isolation, key-absence-guard, sparse-merge-write]
key_files:
  modified:
    - custom_components/climate_manager/websocket.py
    - tests/test_websocket.py
decisions:
  - "Use key-absence guard ('schedule_even' not in current_person) rather than
    truthiness check to prevent overwriting empty {} week schedules (Pitfall 1)"
  - "Call copy.deepcopy() twice with separate calls for schedule_even and
    schedule_odd to ensure independent objects (Pitfall 2)"
  - "Insert seeding block BEFORE the existing setdefault chain so incoming
    payload is augmented before the sparse-merge runs"
metrics:
  duration: 3m
  completed: "2026-05-29"
  tasks_completed: 1
  files_modified: 2
---

# Phase 7 Plan 2: WS set_person_config even/odd seeding Summary

**One-liner:** Extended set_person_config to auto-seed schedule_even/schedule_odd
via copy.deepcopy with key-absence guard when switching to even_odd schedule type.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 (RED) | Add failing WS seeding tests | bcbdafc | tests/test_websocket.py |
| 1 (GREEN) | Implement even/odd seeding block in websocket.py | 48ae046 | custom_components/climate_manager/websocket.py |

## What Was Built

Extended `_make_ws_set_person_config` in `websocket.py` with a seeding block
inserted before the existing `setdefault` sparse-merge chain. When the incoming
config has `schedule_type == "even_odd"` and the stored person does not yet have
a `schedule_even` key (key-absence guard, not truthiness), the handler
deep-copies the person's existing `schedule` into both `schedule_even` and
`schedule_odd` as two independent objects.

**Implementation:**

- `incoming = msg["config"]` binds the incoming payload
- Key-absence guard: `if "schedule_even" not in current_person:` (Pitfall 1)
- Two separate `copy.deepcopy()` calls for independence (Pitfall 2)
- `incoming.setdefault(...)` prevents overwrite if the panel already set a value
- The revert path (single switch) runs the existing sparse-merge without any
  seeding — week schedules in storage are preserved silently (SCHED-06, D-02)
- No new `@websocket_command` type registered — D-03 compliant

**Tests added (T-07-W1 through T-07-W4):**

- W1: single→even_odd seeds `schedule_even`/`schedule_odd` from existing
  `schedule` as two independent objects (`is not` assertion)
- W2: second even_odd switch leaves an already-stored `schedule_even` unchanged
- W3: single switch adds no `schedule_even`/`schedule_odd` keys
- W4: even_odd→single revert preserves both week schedule keys in storage

## Test Results

- Baseline: 127 passed, 1 pre-existing failure (test_main_tab_overview_label)
- After implementation: 131 passed, 1 pre-existing failure
- Net new: +4 passing tests, 0 regressions

## Deviations from Plan

None — plan executed exactly as written.

The plan expected W1/W2/W4 to all fail in RED. In practice, W2 and W4 already
passed with the pre-existing sparse-merge (the existing code never touches keys
not in the incoming payload, so already-stored `schedule_even` was naturally
preserved). Only W1 (the seeding test) was truly RED. This is consistent with
correct TDD — W1 was the behavior we needed to add.

## Known Stubs

None. No UI or data-flow stubs introduced by this plan. The seeding block is
fully wired to `runtime_config` via the existing `store.async_save` path.

## Threat Flags

No new threat surface beyond what the threat model documented. The
key-absence guard (T-07-06) and deepcopy isolation (T-07-07) mitigations are
both implemented and covered by automated tests.

## Self-Check

- [x] tests/test_websocket.py modified — confirmed `bcbdafc` in git log
- [x] custom_components/climate_manager/websocket.py modified — confirmed `48ae046` in git log
- [x] 131 passed, 1 pre-existing failure — no regressions
- [x] 4 new test functions present in test_websocket.py
- [x] `schedule_even` appears in set_person_config handler region
- [x] `copy.deepcopy` called at least twice (two separate calls)
- [x] Key-absence guard `"schedule_even" not in current_person` present
- [x] No new `@websocket_command` type registered (D-03)

## Self-Check: PASSED
