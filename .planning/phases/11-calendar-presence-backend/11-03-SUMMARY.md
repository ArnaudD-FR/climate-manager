---
phase: 11-calendar-presence-backend
plan: "03"
subsystem: websocket + frontend-types
tags: [calendar, presence, websocket, tdd, typescript]
dependency_graph:
  requires:
    - "11-01: PRESENCE_CALENDAR, resolve_calendar_presence, calendar_cache
      param on resolve_presence"
    - "11-02: _prefetch_calendars, _calendar_cache, PRESENCE_CALENDAR dispatch
      in coordinator presence methods"
  provides:
    - "set_person_config entity-id prefix guard (T-11-06 ASVS V5)"
    - "preheat_lead_minutes clamp 0-480 (T-11-07)"
    - "set_person_config docstring: full accepted-key contract"
    - "PersonConfig.calendar_config? and preheat_lead_minutes? in types.ts"
    - "PRESENCE_COLORS.calendar, PERIOD_LABELS.calendar,
      PERIOD_DISPLAY_NAMES.calendar in types.ts"
  affects:
    - custom_components/climate_manager/websocket.py
    - frontend/src/types.ts
    - tests/test_calendar.py
tech_stack:
  added: []
  patterns:
    - "TDD RED/GREEN: test first, then implementation"
    - "WS handler trust-boundary validation (drop invalid keys, not error)"
    - "Additive sparse-merge preserved unchanged (D-09)"
    - "write-then-evaluate tail unchanged (store.async_save → send_result →
      async_create_task coordinator.async_evaluate)"
key_files:
  created: []
  modified:
    - custom_components/climate_manager/websocket.py
    - frontend/src/types.ts
    - tests/test_calendar.py
decisions:
  - "Drop invalid calendar_config silently (not error) — preserves partial
    update semantics; UI guard prevents accidental send anyway"
  - "Clamp/drop preheat_lead_minutes outside 0-480 — matches UI input bounds;
    T-11-07 mitigation"
  - "Inline dict(msg['config']) copy before mutation — preserves original msg
    for future logging without mutating the received message"
metrics:
  duration_minutes: 8
  completed_date: "2026-06-02"
  tasks_completed: 2
  files_modified: 3
  tests_added: 3
requirements: [CAL-01, CAL-04]
---

# Phase 11 Plan 03: set_person_config Calendar Fields Summary

**One-liner:** Entity-id prefix guard and preheat clamp in set_person_config
WS handler; PersonConfig calendar fields + period tokens in types.ts.

## What Was Built

Extended the existing `set_person_config` WebSocket handler and
`types.ts` to wire the persistence layer for calendar presence fields:

1. **`websocket.py` — entity-id prefix guard (T-11-06)** — Before the
   sparse-merge `update(incoming)`, a new validation block:
   - If `incoming` contains `calendar_config`, checks that it is a dict
     with a string `entity_id` starting with `"calendar."`. If not,
     drops the `calendar_config` key silently (never persisted, never
     passed to `_prefetch_calendars`).
   - If `incoming` contains `preheat_lead_minutes`, checks it is an int
     in range 0–480. Out-of-range or non-int values are dropped (T-11-07).
   - Working copy is `dict(msg["config"])` to avoid mutating the received
     message dict.

2. **`websocket.py` — docstring update** — The handler docstring now
   enumerates all accepted sparse keys: `mode`, `room_ids`,
   `schedule`/`schedule_even`/`schedule_odd`, `schedule_type`,
   `calendar_config: {"entity_id": str, "event_means": "absent"|"present"}`,
   and `preheat_lead_minutes: int (0-480)`.

3. **`types.ts` — PersonConfig extensions** — Two optional fields added:
   - `calendar_config?: { entity_id: string; event_means: "absent"|"present" }`
     (D-08, D-09b — exactly one calendar per person)
   - `preheat_lead_minutes?: number` (D-10; absent = 60)

4. **`types.ts` — calendar period tokens** — Three constant additions for
   the calendar period mode in schedule bars and badges:
   - `PRESENCE_COLORS.calendar = "#5C6BC0"` (UI-SPEC indigo-400)
   - `PERIOD_LABELS.calendar = "C"` (short accessibility label)
   - `PERIOD_DISPLAY_NAMES.calendar = "Calendar"` (full display name)

5. **`tests/test_calendar.py` — 3 new WS tests** —
   - `test_ws_persists_calendar_config`: round-trips `calendar_config`
     through `set_person_config` and asserts `runtime_config["persons"]`
     contains `entity_id` + `event_means`.
   - `test_ws_persists_preheat_lead_minutes`: sends `preheat_lead_minutes=90`
     and asserts persisted value equals 90.
   - `test_ws_rejects_non_calendar_entity_id`: sends
     `calendar_config.entity_id = "light.kitchen"` and asserts the
     entity_id is NOT present in `runtime_config`.

## TDD Gate Compliance

- RED commit (`a931372`): `test(11-03)` — 3 WS tests added; 1 failing
  (`test_ws_rejects_non_calendar_entity_id` — no validation yet)
- GREEN commit (`f0579cc`): `feat(11-03)` — entity-id guard + preheat
  clamp; all 3 tests pass

Both RED and GREEN gates present in git log.

## Verification Results

```
tests/test_calendar.py -k ws_   — 3 passed
tests/test_calendar.py          — 19 passed (16 prior + 3 new)
Full suite (tests/)             — 183 passed, 0 failed
grep -c calendar_config types.ts — 1 (>= 1)
grep -c preheat_lead_minutes types.ts — 1 (>= 1)
PRESENCE_COLORS.calendar        — "#5C6BC0" present
PERIOD_LABELS.calendar          — "C" present
PERIOD_DISPLAY_NAMES.calendar   — "Calendar" present
types.ts errors (tsc)           — 0 errors in types.ts specifically
make lint                       — Passed (ruff, ruff-format, prettier,
                                   markdownlint)
```

## Deviations from Plan

None — plan executed exactly as written.

The ruff pre-commit hook caught one style issue during the RED commit
(F841 unused variable `msg` in `test_ws_rejects_non_calendar_entity_id`).
Fixed before commit: changed `msg = await client.receive_json()` to a
bare `await client.receive_json()` with an explanatory comment.

## Known Stubs

None — no UI rendering stubs, no hardcoded empty values that would block
the plan goal. The `calendar_config` and `preheat_lead_minutes` fields
are optional (sparse schema) and their absence is a well-defined default
(no calendar, 60 min lead time).

## Threat Surface Scan

No new network endpoints or auth paths. Validation added at existing
trust boundary:

| Flag | File | Description |
|------|------|-------------|
| threat_flag: tamper-mitigation | websocket.py | T-11-06 calendar_config
  entity_id prefix check; T-11-07 preheat_lead_minutes clamp — both
  implement drop-invalid semantics at the WS handler trust boundary. |

## Self-Check

### Files Exist

- [x] `custom_components/climate_manager/websocket.py` — modified
- [x] `frontend/src/types.ts` — modified
- [x] `tests/test_calendar.py` — modified

### Commits Exist

- [x] `a931372` — RED test commit
- [x] `f0579cc` — GREEN implementation commit
- [x] `1c29d5f` — Task 2 types.ts commit

## Self-Check: PASSED
