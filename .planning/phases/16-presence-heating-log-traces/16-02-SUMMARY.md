---
phase: 16-presence-heating-log-traces
plan: "02"
subsystem: eval-context
tags: [tdd, green-phase, domain-model, obs-01, d-02]
dependency_graph:
  requires:
    - tests/test_eval_context.py (Plan 16-01 RED scaffold)
  provides:
    - custom_components/climate_manager/eval_context.py
  affects:
    - custom_components/climate_manager/coordinator.py (will adopt EvalContext
      in place of _prefetch_calendars upfront pass)
    - custom_components/climate_manager/person.py (not yet created — will read
      _presence_cache from EvalContext)
    - custom_components/climate_manager/zone.py (not yet created — will pass
      EvalContext to ZoneMode.evaluate)
tech_stack:
  added: []
  patterns:
    - EvalContext dataclass with lazy calendar fetch (D-02)
    - _warn_issued set for per-entity WARNING-once semantics (T-16-04)
    - async_mock_service for HA service call capture in tests
key_files:
  created:
    - custom_components/climate_manager/eval_context.py
  modified:
    - tests/test_eval_context.py
decisions:
  - "EvalContext is a standalone file (not inlined in coordinator.py) to prevent
    zone.py/person.py import cycles — RESEARCH Open Question 2 recommendation"
  - "calendar_events() uses lazy fetch: cache hit returns immediately; miss calls
    hass.services.async_call once and stores result in _calendar_cache"
  - "T-16-03 entity_id prefix guard placed BEFORE service call — empty list +
    WARNING returned if entity_id does not start with 'calendar.'"
  - "T-16-04 per-entity warning-once via _warn_issued set on the dataclass;
    cleared on recovery (discards from set after successful fetch)"
  - "test_eval_context.py fixed: patch.object(hass.services, 'async_call') fails
    on HA's read-only ServiceRegistry slot; replaced with async_mock_service"
metrics:
  duration: "3m5s"
  completed: "2026-06-04T20:39:58Z"
  tasks_completed: 1
  tasks_total: 1
  files_created: 1
  files_modified: 1
---

# Phase 16 Plan 02: EvalContext Dataclass Summary

**One-liner:** EvalContext dataclass with lazy, deduplicated calendar fetch via
`calendar_events(entity_id)` — one `hass.services.async_call` per entity per
cycle, with prefix validation and warning-once error handling.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement EvalContext dataclass with lazy calendar cache | a2ea120 | custom_components/climate_manager/eval_context.py, tests/test_eval_context.py |

## What Was Built

**`custom_components/climate_manager/eval_context.py`** — a standalone
dataclass module (127 lines) providing the per-evaluation-cycle shared cache:

- `@dataclass class EvalContext` with three required positional fields: `now`,
  `hass`, `period_temperatures`; plus `_calendar_cache` and `_presence_cache`
  (both `field(default_factory=dict)`) and `_warn_issued` (
  `field(default_factory=set)`)
- `async def calendar_events(self, entity_id: str) -> list` — lazy fetch
  returning cached result on hit; on miss: validates `calendar.` prefix
  (T-16-03), calls `hass.services.async_call("calendar", "get_events", ...)`
  with a start-of-local-day 24-hour window, caches response or `[]` on
  `HomeAssistantError` (T-16-04)
- No import of `coordinator.py` — import cycle risk eliminated

## Verification

All 4 `tests/test_eval_context.py` tests pass GREEN:

```
tests/test_eval_context.py::test_calendar_events_fetches_once_per_entity PASSED
tests/test_eval_context.py::test_calendar_events_calls_service_on_cache_miss PASSED
tests/test_eval_context.py::test_two_callers_same_entity_deduplication PASSED
tests/test_eval_context.py::test_presence_cache_starts_empty PASSED
```

Full suite: 253 passed (249 baseline + 4 new). The other 3 RED scaffold files
(test_zone.py, test_person.py, test_room_domain.py) still fail at collection
as expected — their implementation modules do not exist yet.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_eval_context.py mock strategy**

- **Found during:** Task 1 (GREEN phase execution)
- **Issue:** The RED scaffold used `patch.object(hass.services, "async_call",
  new_callable=AsyncMock)`, which raises `AttributeError: 'ServiceRegistry'
  object attribute 'async_call' is read-only` — HA's ServiceRegistry exposes
  `async_call` as a slot-based read-only attribute that `unittest.mock.patch`
  cannot replace.
- **Fix:** Replaced `patch.object` with `async_mock_service(hass, "calendar",
  "get_events")` from `pytest_homeassistant_custom_component.common` — the
  canonical HA test pattern used throughout the codebase (test_trv.py,
  test_coordinator.py). Updated import accordingly.
- **Files modified:** `tests/test_eval_context.py`
- **Commit:** a2ea120 (included in task commit)

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.
The `eval_context.py` module's only external interaction is `hass.services.async_call`,
already present in the threat register as T-16-03/T-16-04 and fully mitigated.

## Known Stubs

None — `_presence_cache` is an empty dict field provided as a write target for
`Person.evaluate()` (plan 16-03). It is not wired yet, but this is intentional
per the dependency graph (plan 16-03 owns `_presence_cache` population). The
field itself is complete and correct.

## Self-Check: PASSED

- custom_components/climate_manager/eval_context.py — FOUND (127 lines)
- tests/test_eval_context.py — FOUND (modified)
- Task commit a2ea120 — FOUND
