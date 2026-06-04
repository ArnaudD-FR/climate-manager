---
phase: 16-presence-heating-log-traces
plan: "04"
subsystem: person-domain-model
tags: [tdd, green-phase, domain-model, obs-01, d-05, d-08, d-10]
dependency_graph:
  requires:
    - tests/test_person.py (Plan 16-01 RED scaffold)
    - custom_components/climate_manager/eval_context.py (Plan 16-02)
  provides:
    - custom_components/climate_manager/person.py
  affects:
    - custom_components/climate_manager/zone.py (ZoneModeProgramPresences
      will call Person.evaluate next)
    - custom_components/climate_manager/coordinator.py (will delegate
      _compute_present_persons to Person.evaluate)
tech_stack:
  added: []
  patterns:
    - PersonMode plain base class with weakref back-link (D-05)
    - assert False for unimplemented overloads (not ABC, not NotImplementedError)
    - reason_label class attribute per subclass (D-08)
    - _last_home anti-spam flip detection (D-10)
    - ctx._presence_cache dedup keyed by full person_id (Pitfall 6)
    - evaluate_sync() wrapper for sync test contexts
key_files:
  created:
    - custom_components/climate_manager/person.py
  modified:
    - tests/test_person.py
decisions:
  - "PersonMode + Person both in one file (person.py) — co-located because
    PersonMode is entirely owned by and exists to serve Person"
  - "evaluate_sync() uses asyncio.new_event_loop() + run_until_complete() to
    avoid event-loop conflicts with pytest-asyncio's per-test loop"
  - "All five mode subclasses delegate config reads through weakref self.person
    at call time — no config parameters on is_present() signature (D-05)"
  - "PersonModeScheduled.is_present passes ctx._calendar_cache through
    resolve_presence() for calendar-period fall-through (Landmine 5)"
metrics:
  duration: "7m"
  completed: "2026-06-04T20:49:59Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 16 Plan 04: Person Domain Model Summary

**One-liner:** PersonMode state machine (five weakref-backed subclasses,
assert-False base) + Person.evaluate with INFO presence log on _last_home
flip and ctx._presence_cache deduplication.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1+2 (GREEN) | PersonMode subclasses + Person.evaluate | dc128a7 | custom_components/climate_manager/person.py, tests/test_person.py |

Note: Task 1 (PersonMode base + subclasses) and Task 2 (Person class)
share a single GREEN commit because Person depends on PersonMode and both
were fully specified before coding began. The RED gate was confirmed at plan
start (ImportError on test_person.py). This follows the same bundling
approach used in 16-03 for TRV + TRVGroup.

## What Was Built

### `_short_name(entity_id: str) -> str` (module-level helper, D-01)

Local copy consistent with trv.py — strips domain/prefix from entity IDs
for log display. `person.alice` → `alice`; `area_kitchen` → `kitchen`;
`zone_main` → `main`.

### `class PersonMode` (plain base class, D-05)

- `__init__(self, person)` — stores `weakref.ref(person)` as `_person_ref`
- `person` property — dereferences weakref with assert-not-None guard
- `async def is_present(self, ctx)` — base raises `assert False` (not
  `NotImplementedError`, no `@abstractmethod`)
- `def next_occupied_at(self, ctx)` — base returns `None`
- `reason_label: str = ""` — class-level attribute overridden per subclass

### Five concrete subclasses

| Subclass | reason_label | is_present behaviour |
|---|---|---|
| `PersonModeScheduled` | `"scheduled"` | `resolve_presence(person_config, ctx.now, calendar_cache=ctx._calendar_cache, ...)` |
| `PersonModeHA` | `"ha"` | `hass.states.get(person_id).state == "home"` |
| `PersonModeCalendar` | `"calendar"` | `await ctx.calendar_events(eid)` → `resolve_calendar_presence(...)` |
| `PersonModeForcePresent` | `"force_present"` | returns `True` |
| `PersonModeForceAbsent` | `"force_absent"` | returns `False` |

`PersonModeScheduled` and `PersonModeCalendar` override `next_occupied_at`
(stub returning `None` for now — forward-walk is a future enhancement).
HA and Force* modes use the base `None`.

### `class Person`

- `__init__` — stores `person_id`, `hass`, `person_config`, `calendar_config`,
  `room_ids`; builds initial mode via `_make_mode()` factory; `_last_home = None`
- `async def evaluate(ctx)`:
  1. Cache check: `if person_id in ctx._presence_cache: return cached` (Pitfall 6)
  2. Mode call: `result = await self._mode.is_present(ctx)`
  3. Flip check: if `result != self._last_home`: emit INFO log + update `_last_home`
  4. Store: `ctx._presence_cache[person_id] = result`; return result
- `def evaluate_sync(ctx)` — sync wrapper using `asyncio.new_event_loop()`
- `def change_mode(new_mode, reason)` — swaps `_mode` (WS handler API)
- `def next_occupied_at(ctx)` — delegates to `_mode.next_occupied_at(ctx)`

## Verification

```
tests/test_person.py::test_person_evaluate_emits_info_on_home_flip PASSED
tests/test_person.py::test_person_no_log_on_same_home_value PASSED
tests/test_person.py::test_person_name_strip_d01 PASSED
tests/test_person.py::test_person_reason_is_mode_name_only PASSED
tests/test_person.py::test_person_presence_cache_dedup PASSED
270 passed (261 baseline + 9 new: 5 person + 4 eval_context)
```

test_zone.py and test_room_domain.py remain in RED (correct — zone.py and
room.py not yet implemented; those are other plans in Wave 3).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed caplog API in test_person.py**

- **Found during:** Task 1 GREEN execution
- **Issue:** The RED scaffold (Plan 16-01) used `caplog.at_context(
  caplog.set_level(...))` which does not exist in pytest 8.x.
  `LogCaptureFixture` has no `at_context` method; `set_level` also returns
  `None`, so even if the method existed the context manager argument would
  be `None`. The correct API is `caplog.at_level(level, logger=...)`.
- **Fix:** Replaced all four occurrences of
  `with caplog.at_context(caplog.set_level(...)):` with
  `with caplog.at_level(logging.INFO, logger=PERSON_LOGGER):`
- **Files modified:** `tests/test_person.py`
- **Commit:** dc128a7 (included in task commit)

## TDD Gate Compliance

- RED gate: ImportError on test_person.py at plan start — confirmed.
  The test file was committed as 6ecd414 in Plan 16-01 and fails at
  collection with `ModuleNotFoundError: No module named
  'custom_components.climate_manager.person'` before this plan runs.
- GREEN gate: commit dc128a7 — all 5 person tests pass, 270 total.
- REFACTOR gate: not required — code is clean; ruff-format ran cleanly.

## Known Stubs

`PersonModeScheduled.next_occupied_at` and
`PersonModeCalendar.next_occupied_at` return `None` for now. The plan
specifies these as stubs with the note "full forward-walk is a future
enhancement." The calling contract (zone.py plan 16-05) only requires the
method exists; it will not be called until zone.py's preheat logic is wired.
Not a correctness regression.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema
changes. T-16-07 (calendar entity_id prefix validation) is fully mitigated
by EvalContext.calendar_events (plan 16-02); PersonModeCalendar only passes
entity_id through. T-16-08 (presence cache key collision) mitigated by
keying ctx._presence_cache on full person_id (Pitfall 6).

## Self-Check: PASSED

Files exist:
- custom_components/climate_manager/person.py — FOUND (322 lines, above 100 min)
- tests/test_person.py — FOUND (modified)

Commit exists:
- dc128a7 (GREEN: PersonMode + Person implementation) — FOUND

Key acceptance criteria verified:
- person.py contains `class PersonMode` — FOUND (line 71)
- person.py contains all five subclass names — FOUND (lines 118, 144, 160, 199, 208)
- person.py contains `assert False` — FOUND (line 102)
- person.py contains `weakref.ref(` — FOUND (line 86)
- person.py contains `resolve_calendar_presence(` — FOUND (line 184)
- person.py contains `resolve_presence(` — FOUND (line 127)
- person.py contains `class Person` — FOUND (line 239)
- person.py contains literal `presence | person=%s home=%s reason=%s` — FOUND
- person.py reads ctx._presence_cache before mode call — FOUND (line 287)
- person.py writes ctx._presence_cache after mode call — FOUND (line 302)
- person.py keys cache by self.person_id — FOUND (lines 287, 302)
- 270 tests pass at/above baseline — CONFIRMED
