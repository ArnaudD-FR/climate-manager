---
phase: 11-calendar-presence-backend
plan: "02"
subsystem: coordinator
tags: [calendar, presence, coordinator, async, cache, tdd]
dependency_graph:
  requires:
    - "11-01: PRESENCE_CALENDAR, resolve_calendar_presence, calendar_cache
      param on resolve_presence"
  provides:
    - "_calendar_cache dict[str, list] on ClimateManagerCoordinator"
    - "_prefetch_calendars() async method — per-cycle get_events fetch"
    - "PRESENCE_CALENDAR branch in _compute_present_persons"
    - "calendar_cache routing in _apply_presence_overrides (Landmine 5)"
  affects:
    - custom_components/climate_manager/coordinator.py
tech_stack:
  added: []
  patterns:
    - "asyncio.gather() for concurrent calendar entity prefetch (one call
      per unique entity_id)"
    - "HomeAssistantError catch → single WARNING + empty-list fallback (D-04)"
    - "entity_id prefix guard 'calendar.' (T-11-03 ASVS V5)"
    - "TDD RED/GREEN: integration tests written before implementation"
key_files:
  created: []
  modified:
    - custom_components/climate_manager/coordinator.py
    - tests/test_calendar.py
decisions:
  - "asyncio.gather() over sequential awaits for concurrent calendar prefetch
    (established coordinator pattern from _push_temperatures)"
  - "Both _compute_present_persons and _apply_presence_overrides share
    identical dispatch (PRESENCE_HA / PRESENCE_CALENDAR / else) to avoid
    Landmine 5 inconsistency"
  - "Test mock swap via hass.services._services.pop instead of re-setup to
    avoid panel re-registration ValueError in same hass fixture"
metrics:
  duration_minutes: 7
  completed_date: "2026-06-02"
  tasks_completed: 2
  files_modified: 2
  tests_added: 5
requirements: [CAL-01, CAL-02]
---

# Phase 11 Plan 02: Calendar Coordinator Integration Summary

**One-liner:** Per-cycle `_calendar_cache` with `asyncio.gather` prefetch,
`PRESENCE_CALENDAR` dispatch in both presence methods, and calendar period
state routing via the cache.

## What Was Built

Extended `coordinator.py` to wire the calendar async infrastructure that
feeds Plan 01's pure helpers:

1. **Imports** — Added `PRESENCE_CALENDAR` to const imports,
   `resolve_calendar_presence` to schedule imports, and
   `HomeAssistantError` from `homeassistant.exceptions`.

2. **`_calendar_cache: dict[str, list]`** — Instance variable initialized
   to `{}` in `__init__`. Comment marks it as D-13: reset each cycle, never
   persisted.

3. **`async def _prefetch_calendars(config, now)`** — Builds a `set[str]`
   of unique calendar entity IDs from two sources:
   - Calendar-mode persons (`mode == PRESENCE_CALENDAR`) read their
     `calendar_config.entity_id`.
   - Scheduled-mode persons scan `schedule`, `schedule_even`, `schedule_odd`
     for periods with `state == "calendar"` and read their
     `calendar_config.entity_id`.
   Each entity_id is validated with `.startswith("calendar.")` (T-11-03
   ASVS V5 — prevents calling unintended services). An inner
   `_fetch_one(eid)` coroutine calls `hass.services.async_call("calendar",
   "get_events", ..., blocking=True, return_response=True)` (Landmine 1),
   reads `(result or {}).get(eid, {}).get("events", [])` (Landmine 2), and
   stores in `_calendar_cache[eid]`. On `HomeAssistantError`, logs one
   WARNING and stores `[]` (D-04 single-WARNING fallback). All fetches run
   concurrently via `asyncio.gather()`.

4. **`async_evaluate` modification** — After `config`/`rooms` bind, adds
   `self._calendar_cache = {}` then `await self._prefetch_calendars(config,
   now)` before `_compute_present_persons` (D-05 — async chain entrypoint
   in coordinator, not schedule.py).

5. **`_compute_present_persons` — `PRESENCE_CALENDAR` branch** — `elif
   person_config.get("mode") == PRESENCE_CALENDAR:` reads `calendar_config`,
   looks up `self._calendar_cache.get(eid, [])`, and calls
   `resolve_calendar_presence(events, event_means, now, preheat,
   start_of_local_day=dt_util.start_of_local_day)`. The existing `else`
   branch now passes `calendar_cache=self._calendar_cache` and
   `start_of_local_day=dt_util.start_of_local_day` to `resolve_presence()`
   so calendar period states in scheduled-mode persons resolve correctly.

6. **`_apply_presence_overrides` — mirrored dispatch (Landmine 5)** —
   Replaced the single `resolve_presence()` call with the same three-branch
   dispatch (`PRESENCE_HA` / `PRESENCE_CALENDAR` / `else`), ensuring room
   temperature overrides see the same calendar-driven presence result as
   the present-persons list.

7. **`tests/test_calendar.py` — 5 new integration tests** —
   - `test_calendar_cache_deduplication`: two persons sharing
     `calendar.shared` → exactly one `get_events` ServiceCall.
   - `test_calendar_cache_reset_per_cycle`: two `async_evaluate` calls
     → 2 total `get_events` calls (cache resets per cycle).
   - `test_calendar_fallback_on_error`: `HomeAssistantError` →
     `_calendar_cache[eid] == []` + exactly one WARNING record.
   - `test_calendar_mode_person_present_in_evaluate`: calendar-mode person
     absent during active event; present when no events.
   - `test_calendar_period_overrides_rooms`: scheduled-mode person with
     calendar period state — `_apply_presence_overrides` uses the cache.

## TDD Gate Compliance

- RED commit (`365ab87`): `test(11-02)` — 5 failing integration tests
- GREEN commit (`7b0aa4f`): `feat(11-02)` — `_prefetch_calendars` + cache
  reset (Task 1 green)
- GREEN commit (`2a9bdb0`): `feat(11-02)` — presence method routing
  (Task 2 green)

Both RED and GREEN gates present in git log.

## Verification Results

```
tests/test_calendar.py     — 16 passed (11 plan-01 + 5 new)
Full suite (tests/)        — 180 passed, 0 failed
grep blocking=True         — 1 (get_events call in _prefetch_calendars)
grep return_response=True  — 1 (same call)
grep calendar_cache=self._calendar_cache — 2 (_compute + _apply)
make lint                  — Passed (ruff, ruff-format, prettier, markdownlint)
```

## Deviations from Plan

**1. [Rule 1 - Bug] test_calendar_mode_person_present_in_evaluate rewrite**

- **Found during:** Task 2 implementation
- **Issue:** Original test design used unload + re-setup within the same
  hass fixture. After unload, re-registering a new config entry raised
  `ValueError: Overwriting panel climate_manager` in
  `async_register_built_in_panel`.
- **Fix:** Rewrote the test to use a single coordinator with a mock service
  swap (`hass.services._services.pop("calendar")` + re-register) between
  the two `async_evaluate` calls. Achieves the same behavioral coverage
  (absent→present) without a second integration setup.
- **Files modified:** `tests/test_calendar.py`
- **Commit:** `2a9bdb0`

## Known Stubs

None — no UI rendering, no hardcoded empty values, no placeholders. The
`_calendar_cache` is populated from live HA service calls and never
carries stale or mocked data beyond test scope.

## Threat Surface Scan

No new network endpoints or auth paths. One new HA service bus call:

| Flag | File | Description |
|------|------|-------------|
| threat_flag: service-call | coordinator.py | `calendar.get_events` service call
  in `_prefetch_calendars` — authenticated via HA internal bus; T-11-03
  mitigation (calendar. prefix guard) and T-11-04 mitigation (single WARNING
  per failing entity) both implemented as planned. |

The T-11-05 mitigation (defensive response access `(result or {}).get(eid,
{}).get("events", [])`) is also implemented (Landmine 2).

## Self-Check

### Files Exist

- [x] `custom_components/climate_manager/coordinator.py` — modified
- [x] `tests/test_calendar.py` — modified

### Commits Exist

- [x] `365ab87` — RED test commit
- [x] `7b0aa4f` — GREEN Task 1 commit
- [x] `2a9bdb0` — GREEN Task 2 commit

## Self-Check: PASSED
