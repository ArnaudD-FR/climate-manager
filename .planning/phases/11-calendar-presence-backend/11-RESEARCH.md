# Phase 11: Calendar Presence Backend — Research

**Researched:** 2026-06-01
**Domain:** HA calendar entity service API, async coordinator patterns,
  Lit frontend conditional rendering
**Confidence:** HIGH (all key findings verified against installed HA venv
  source code)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Climate Manager does NOT fetch calendar data from external
  sources. Both school timetables (Pronote) and personal calendars (iCal,
  Google Calendar, etc.) are accessed as standard HA `calendar.*` entities
  via `hass.services.async_call("calendar", "get_events", ...)`. HA's
  calendar integrations own fetching, caching, RRULE expansion, and
  credentials.
- **D-02:** No new PyPI dependencies. `pronotepy`, `icalendar`, and
  `recurring-ical-events` are all out of scope. `manifest.json`
  `"requirements"` stays empty.
- **D-03:** New presence mode value: `"calendar"`. Added alongside existing
  modes in `const.py`. `PRESENCE_CALENDAR = "calendar"` constant.
- **D-04:** `resolve_presence()` gains a new dispatch branch for
  `mode == "calendar"`. If calendar entity is unavailable or errors → fall
  back to `False` and log once at WARNING.
- **D-05:** `resolve_presence()` must become `async` (or a new async helper
  is added) since `get_events` is an async service call.
- **D-06:** Period state `"calendar"` added alongside `"present"` /
  `"absent"`.
- **D-07:** Calendar period state only available in Scheduled mode. NOT
  recursive.
- **D-08:** `calendar_config` schema: `{entity_id, event_means}`.
  `event_means`: `"absent"` (default) | `"present"`.
- **D-09:** Additive schema — `calendar_config` absent means person not
  using Calendar mode. No migration needed.
- **D-09b:** One `calendar_config` per person (one calendar entity only).
- **D-10:** `preheat_lead_minutes` per person (int, default 60).
- **D-11:** Lead time per-person, displayed in person card when Calendar
  mode is selected.
- **D-12:** Fixed offset only in Phase 11; Phase 12 adds adaptive learning.
- **D-13:** Per-cycle `_calendar_cache: dict[str, list]` — one get_events
  call per unique entity per `async_evaluate` cycle. Reset at start of
  each cycle.
- **D-14–D-17:** Frontend layout reorder, entity picker, event_means
  toggle, calendar period state in period editor.

### Claude's Discretion

Not specified.

### Deferred Ideas (OUT OF SCOPE)

- Adaptive pre-heat lead time (Phase 12)
- Direct Pronote API via pronotepy
- Per-room or per-zone lead time
- Multiple calendar sources per person
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAL-01 | (SUPERSEDED) Was: Pronote timetable fetch. MUST be rewritten to: Person can configure Calendar mode pointing to a `calendar.*` HA entity; presence determined by active events | HA calendar entity API — verified in venv |
| CAL-02 | (SUPERSEDED) Was: Pronote cache + TTL. MUST be rewritten to: Per-cycle cache (`_calendar_cache`) avoids duplicate `get_events` calls; fallback to absent on error with single WARNING log | Coordinator cache pattern — existing `asyncio.gather()` pattern |
| CAL-03 | (SUPERSEDED) Was: iCal URL + keyword filter. MUST be rewritten to: `event_means` field controls whether active event → present or absent; calendar period state in Scheduled mode | `event_means` semantic — per CONTEXT.md D-08 |
| CAL-04 | (SUPERSEDED) Was: iCal RRULE + timezone handling. MUST be rewritten to: `preheat_lead_minutes` per person — start heating X min before calendar-driven absence ends; default 60 min | Pre-heat detection via event `end` field |
</phase_requirements>

---

## Overview

Phase 11 adds a `"calendar"` presence mode that delegates presence
determination to standard HA `calendar.*` entities. Both school timetables
(Pronote) and personal calendars (iCal, Google, CalDAV) are accessed
uniformly — Climate Manager never fetches external services directly.

Three work streams:

1. **Backend engine** — `const.py` constants, `async_evaluate()` calendar
   prefetch pass, `resolve_presence()` calendar branch, pre-heat detection.
2. **WebSocket** — extend `set_person_config` to accept `calendar_config`
   and `preheat_lead_minutes`; `get_config` already returns person config
   transparently.
3. **Frontend** — person card layout reorder, Calendar mode UI (entity
   picker, event_means, lead time), period editor "Calendar" option with
   inline entity picker.

---

## HA Calendar Service API

### Verified call pattern

[VERIFIED: installed HA venv
`.venv/lib/python3.12/site-packages/homeassistant/components/calendar/`]

```python
from homeassistant.exceptions import HomeAssistantError

response = await self._hass.services.async_call(
    "calendar",
    "get_events",
    service_data={
        "start_date_time": now,           # datetime — defaults to now if absent
        "end_date_time": now + timedelta(hours=24),  # OR use "duration"
    },
    target={"entity_id": "calendar.pronote_jean"},
    blocking=True,
    return_response=True,
)
```

### Key constraints (verified in core.py)

- `return_response=True` **requires** `blocking=True` — raises
  `ServiceValidationError` otherwise.
- `get_events` is registered as `SupportsResponse.ONLY` — calling it
  **without** `return_response=True` raises `ServiceValidationError`
  (`service_lacks_response_request`).
- Service is an **entity service** registered via
  `component.async_register_entity_service`. This means:
  - The entity must exist and be available, OR the call raises
    `HomeAssistantError("Service call requested response data but did not
    match any entities")`.
  - Target uses `target={"entity_id": "..."}` or `service_data` with
    `entity_id` key.

### Response shape

When a single entity is targeted, the return value from `async_call` is:

```python
{
    "calendar.pronote_jean": {
        "events": [
            {
                "start": "2026-06-01T08:00:00+02:00",  # ISO string
                "end": "2026-06-01T17:00:00+02:00",    # ISO string
                "summary": "Cours de maths",
                # description, location — present only when non-None
            },
            # ... more events
        ]
    }
}
```

Fields in each event (from `LIST_EVENT_FIELDS` in `calendar/const.py`):
`"start"`, `"end"`, `"summary"`, `"description"`, `"location"`.
Fields with `None` value are **omitted** from the dict.

### Date/time format of start/end fields

`_event_dict_factory` serializes `datetime.datetime` and `datetime.date`
objects via `.isoformat()`. For all-day events (date-only), the string is
`"2026-06-02"` (no time component). For timed events, it includes the
timezone offset: `"2026-06-02T08:00:00+02:00"`. Parsing must handle both
formats.

### Error conditions to handle

| Condition | What happens | Handling |
|-----------|-------------|---------|
| Calendar entity doesn't exist in HA | `HomeAssistantError` raised | Catch, log WARNING once, return `False` |
| Calendar entity unavailable | `HomeAssistantError` (no matching entities) | Same |
| `calendar` component not loaded | `ServiceNotFound` (subclass of `HomeAssistantError`) | Same |
| Calendar entity exists, no events in window | `response[entity_id]["events"] == []` | Normal — no events = not absent |

All error conditions should be caught as `HomeAssistantError` (the base
class).

### Checking if an event covers `now`

```python
from datetime import datetime
import dateutil.parser  # NOT available — no new deps

# All-day events have date-only ISO strings; timed events include offset.
# Parse without external library:
def _parse_event_dt(s: str) -> datetime:
    """Parse ISO date or datetime string to aware datetime (local TZ)."""
    from homeassistant.util import dt as dt_util
    import datetime as dt
    if "T" in s:
        # datetime with timezone offset
        return dt.datetime.fromisoformat(s)
    else:
        # date-only (all-day event) — treat as start/end of local day
        d = dt.date.fromisoformat(s)
        return dt_util.start_of_local_day(d)
```

Event covers `now` when `event_start <= now < event_end`.

**Important:** `now` from `dt_util.now()` is timezone-aware. Parsed
start/end from ISO strings are also timezone-aware (timed events carry the
offset). All-day events are converted to local midnight, which is
timezone-aware via `dt_util.start_of_local_day()`. No mixing of aware and
naive datetimes.

---

## Existing Code Analysis

### `schedule.py:resolve_presence()` (lines 123–179)

`resolve_presence()` is **synchronous** and **pure Python** (no HA imports
at module level — docstring explicitly states "Pure Python — no Home
Assistant imports"). It dispatches on `mode` then walks the per-day
schedule.

Current mode dispatch:
1. `PRESENCE_PRESENT` (`"force_present"`) → return `True`
2. `PRESENCE_ABSENT` (`"force_absent"`) → return `False`
3. Anything else (including `"scheduled"`) → evaluate schedule periods

The `"ha"` mode is **NOT** handled in `resolve_presence()` — it is handled
separately in `_compute_present_persons()` in coordinator.py (line 614–618)
as a special case before calling `resolve_presence()`.

**Consequence for D-05:** The async calendar lookup cannot happen inside
`resolve_presence()` without breaking the "pure Python" contract and making
the function async. Two viable approaches (see Async Architecture Decision
below).

### Period schedule walk (lines 169–179)

The period walk pattern for schedule mode:

```python
sorted_periods = sorted(periods, key=lambda p: _parse_time(p["start"]))
active_state = "absent"
for period in sorted_periods:
    period_start = _parse_time(period["start"])
    if current_time >= period_start:
        active_state = period["state"]
    else:
        break
return active_state == "present"
```

This returns a bool. To support `"calendar"` as a period state, the return
type needs to change — a period with `state: "calendar"` cannot be
collapsed to a bool without first resolving the calendar. This is the
driver for the async architecture decision.

### `coordinator.py:_compute_present_persons()` (lines 596–623)

```python
def _compute_present_persons(self, config: dict, now: datetime) -> list[str]:
    for person_id, person_config in persons_config.items():
        if person_config.get("mode") == PRESENCE_HA:
            # special async-safe read from hass.states
            state_obj = self._hass.states.get(person_id)
            if state_obj is not None and state_obj.state == "home":
                present.append(person_id)
        else:
            if resolve_presence(person_config, now):
                present.append(person_id)
```

This method is **synchronous** (no `async` keyword). It cannot `await`
anything. It calls `resolve_presence()` synchronously.

### `coordinator.py:async_evaluate()` (lines 124–181)

```python
async def async_evaluate(self, _utc_now=None):
    now = dt_util.now()
    config = self._data.runtime_config
    # ...
    self._last_present_persons = self._compute_present_persons(config, now)
    # ...
    self._apply_presence_overrides(config, rooms, desired_temps, ...)
    # ...
    await self._push_temperatures(rooms, desired_temps, mode_off_rooms)
```

`async_evaluate` IS async. It calls `asyncio.gather()` in `_push_temperatures`
and `_async_calibrate`. The pattern is established for concurrent async
operations within a single evaluate cycle.

### `coordinator.py:_apply_presence_overrides()` (lines 281–344)

Also synchronous. Calls `resolve_presence(person_config, now)` directly.
The calendar branch must produce results before this method runs.

---

## Async Architecture Decision

### Option A: Hoist calendar lookups to coordinator (RECOMMENDED)

Keep `resolve_presence()` synchronous and pure. Add `_calendar_cache:
dict[str, list]` to the coordinator. Add `async def
_prefetch_calendars(config, now)` that runs before the presence pass.
Pass the cached events into the presence evaluation via the person config
or a separate argument.

Implementation sketch:

```python
# In async_evaluate():
self._calendar_cache = {}
await self._prefetch_calendars(config, now)
self._last_present_persons = self._compute_present_persons(config, now)
```

```python
async def _prefetch_calendars(self, config: dict, now: datetime) -> None:
    """Prefetch get_events for all unique calendar entity IDs referenced
    by any person or period. Populates _calendar_cache."""
    entity_ids: set[str] = set()
    for person_config in config.get("persons", {}).values():
        if person_config.get("mode") == "calendar":
            eid = (person_config.get("calendar_config") or {}).get(
                "entity_id"
            )
            if eid:
                entity_ids.add(eid)
        # Also collect calendar entity_ids from period states
        for schedule_key in ("schedule", "schedule_even", "schedule_odd"):
            for day_periods in (
                person_config.get(schedule_key) or {}
            ).values():
                for period in day_periods:
                    if period.get("state") == "calendar":
                        eid = (period.get("calendar_config") or {}).get(
                            "entity_id"
                        )
                        if eid:
                            entity_ids.add(eid)

    async def _fetch_one(eid: str) -> None:
        try:
            result = await self._hass.services.async_call(
                "calendar",
                "get_events",
                service_data={
                    "start_date_time": now,
                    "end_date_time": now + timedelta(hours=24),
                },
                target={"entity_id": eid},
                blocking=True,
                return_response=True,
            )
            events = (result or {}).get(eid, {}).get("events", [])
            self._calendar_cache[eid] = events
        except HomeAssistantError:
            _LOGGER.warning(
                "Calendar entity %s unavailable — falling back to absent",
                eid,
            )
            self._calendar_cache[eid] = []  # sentinel: fallback

    await asyncio.gather(*[_fetch_one(eid) for eid in entity_ids])
```

Then `resolve_presence()` receives the cached events list (not the async
call) via a new optional parameter or via a context dict.

**Rationale for Option A:**
- `schedule.py` keeps its "pure Python, no HA imports" contract.
- `resolve_presence()` stays synchronous → existing unit tests in
  `test_schedule.py` remain valid without `asyncio`.
- `asyncio.gather()` is the established pattern in coordinator.py.
- Cache is reset at the top of each cycle → no stale data.

### Option B: Make `resolve_presence()` async

Add `hass` parameter, make it `async def`, issue `get_events` calls inside.
`_compute_present_persons` also becomes `async` and must be `await`ed.

**Cons:**
- Breaks the "pure Python, no HA imports" module contract in schedule.py.
- All existing unit tests for `resolve_presence()` in `test_schedule.py`
  must be rewritten with `pytest.mark.asyncio`.
- One `get_events` call per person per cycle even with caching — cache must
  be passed in from outside or stored on a module-level dict.
- More invasive change with higher regression surface.

**Verdict: Option A is the correct approach.** `resolve_presence()` stays
sync; the coordinator hoists calendar lookups with `asyncio.gather()`.

---

## Cache Strategy

Per D-13: `_calendar_cache: dict[str, list]` on the coordinator.

```python
# In __init__:
self._calendar_cache: dict[str, list] = {}

# In async_evaluate() — reset at cycle start:
self._calendar_cache = {}
await self._prefetch_calendars(config, now)
```

The cache maps `entity_id → list[event_dict]`. An empty list `[]` means
either no events in the 24h window or a fetch error (fallback). The two
cases are distinguishable only if a separate error flag is stored; for
Phase 11, both cases → `False` (absent) which is correct (D-04 silent
fallback).

**Cache window:** `[now, now + 24h]`. This is wide enough to detect events
ending within `preheat_lead_minutes` (max 480 per UI-SPEC) plus the
current cycle's event coverage, and narrow enough to avoid fetching
irrelevant future events.

**Multiple persons sharing an entity:** `asyncio.gather()` in
`_prefetch_calendars` is keyed by unique `entity_id` set, so a shared
calendar entity is fetched once regardless of how many persons reference it.

---

## Pre-heat Lead Time

### Detection logic

`preheat_lead_minutes` triggers heating before a calendar-driven absence
ends. Concretely: if the person's calendar mode returns "absent" AND an
event ends within `preheat_lead_minutes` minutes, treat the person as
"present" for heating purposes.

Detection algorithm using cached events:

```python
def _resolve_calendar_presence(
    events: list[dict],
    event_means: str,
    now: datetime,
    preheat_lead_minutes: int,
) -> bool:
    """Return True if person should be considered present."""
    lead = timedelta(minutes=preheat_lead_minutes)

    for event in events:
        start_s = event.get("start", "")
        end_s = event.get("end", "")
        if not start_s or not end_s:
            continue
        event_start = _parse_calendar_dt(start_s)
        event_end = _parse_calendar_dt(end_s)

        event_active = event_start <= now < event_end

        if event_means == "absent":
            if event_active:
                # Person is absent. Check if absence ends soon (pre-heat).
                if event_end <= now + lead:
                    return True  # start heating
                return False     # still absent, not pre-heating yet
        else:  # event_means == "present"
            if event_active:
                return True

    # No active event found
    if event_means == "absent":
        return True   # no event = not absent = present
    else:
        return False  # no event = not present
```

**Edge case — overlapping events:** Multiple events may overlap. The
simplest safe rule: if ANY event is active and `event_means == "absent"`,
person is absent (unless pre-heat triggers). If ANY event is active and
`event_means == "present"`, person is present. Walk all events.

**All-day events:** Parsed via `dt.date.fromisoformat()`, then converted to
local midnight start/end via `dt_util.start_of_local_day()`. All-day event
`end` in iCal convention is exclusive (the day after). The `get_events`
service respects this via the HA calendar entity implementation.

---

## Requirements Update

The existing CAL-01..04 in `REQUIREMENTS.md` describe the superseded
Pronote/iCal direct-fetch approach. The planner MUST rewrite them before
writing plans.

### Proposed rewritten requirements

**CAL-01 (HA Calendar mode):**
> A person can be set to "Calendar" presence mode in the panel. A
> `calendar.*` HA entity is configured as the presence source. When an
> event is active on that calendar, the `event_means` field determines
> whether the person is absent (default) or present. When no event is
> active, the inverse applies. On calendar entity error or unavailability,
> the person falls back to absent without log spam.

**CAL-02 (Per-cycle cache):**
> The coordinator fetches `get_events` for each unique `calendar.*` entity
> ID exactly once per `async_evaluate` cycle, caching results in
> `_calendar_cache`. Multiple persons sharing a calendar entity share the
> same fetch result within the cycle.

**CAL-03 (Period state "calendar" in Scheduled mode):**
> In Scheduled mode, individual periods can have state `"calendar"` instead
> of `"present"` / `"absent"`. When active, the period resolves via the
> `calendar_config` attached to that period. Not recursive: a calendar
> period inside a top-level calendar mode is not supported.

**CAL-04 (Pre-heat lead time):**
> A per-person `preheat_lead_minutes` value (default 60, range 0–480) causes
> the coordinator to treat a calendar-absent person as present when the
> active event is scheduled to end within `preheat_lead_minutes` minutes,
> enabling rooms to pre-heat before the person returns.

---

## Frontend Integration Points

### Current `person-card.ts` structure (verified by reading source)

The render() method currently produces this section order:

1. Card header (name, badge, dot)
2. Expanded content:
   a. "Presence mode" label + `<select>` (4 options: scheduled, ha,
      force_present, force_absent)
   b. `schedule-hint` paragraph + optional edit link
   c. "Room associations" label + chips + search-picker
   d. "Presence schedule" section (visible only in scheduled mode):
      - Schedule type select
      - Even/odd week switcher (conditional)
      - Time-bar
      - Reset button

**D-14 requires reordering to:**

1. Card header
2. Expanded content:
   a. "Presence mode" label + `<select>` (add "Calendar" option)
   b. `schedule-hint` paragraph
   c. **Calendar config block** (new, visible only when `mode === "calendar"`)
   d. **Presence schedule section** (visible when `mode === "scheduled"`)
   e. "Room associations" label + chips + search-picker (moved last)

### Calendar entity picker pattern

The `hass` object is available in `persons-tab.ts` via `this.hass`. The
person card receives it through `this.panel.hass`. Filter:

```typescript
const calendarEntityIds = Object.keys(this.panel.hass.states)
  .filter((id) => id.startsWith("calendar."))
  .sort();
```

Friendly name from `hass.states[id].attributes.friendly_name ?? id`.

This is the same pattern used in `persons-tab.ts` line 141:
`this.hass?.states[personId]?.attributes?.device_trackers`.

### Mode select addition

Add `<option value="calendar">Calendar</option>` to the existing
`<select class="mode-select">`. The `_onModeChange` handler already calls
`setPersonConfig({ mode: newMode })` generically — no change needed to the
handler itself. Add a `PRESENCE_MODE_CALENDAR = "calendar"` constant.

### Calendar config block (new, when `mode === "calendar"`)

```html
<!-- Section label: "Calendar source" -->
<!-- Native <select class="mode-select"> populated from hass.states calendar.* -->
<!-- Section label: "Event means" -->
<!-- Native <select> with "Absent during events" / "Present during events" -->
<!-- Section label: "Pre-heat lead time" -->
<!-- <input type="number" min="0" max="480" step="5"> + <span>min</span> -->
```

Auto-save on `change` event for all three controls, as per Phase 9 pattern
(D-09).

Save pattern for calendar config:

```typescript
await this.ws.setPersonConfig(this.personId, {
  calendar_config: { entity_id: newEntityId, event_means: currentMeans },
});
```

Save pattern for lead time:

```typescript
const val = parseInt((e.target as HTMLInputElement).value, 10);
if (!isNaN(val) && val >= 0 && val <= 480) {
  await this.ws.setPersonConfig(this.personId, {
    preheat_lead_minutes: val,
  });
}
```

### Period state "calendar" in time-bar

The time-bar component's `PRESENCE_CYCLE` is currently
`["present", "absent"]`. Adding `"calendar"` to the cycle would make
clicking a period segment cycle through three states. This may surprise
users. The safer approach: the calendar period state is set only through
an explicit `<select>` in the period editor, not by click-cycling.

The planner should note that `time-bar.ts` needs:
- `PRESENCE_COLORS["calendar"] = "#5C6BC0"` (per UI-SPEC)
- `PERIOD_LABELS["calendar"] = "C"` (per UI-SPEC)
- `PERIOD_DISPLAY_NAMES["calendar"] = "Calendar"` (per UI-SPEC)

These go in `types.ts`, which time-bar imports.

Whether to add `"calendar"` to `PRESENCE_CYCLE` (click-cycling) or keep
it as select-only is the planner's call. The UI-SPEC says "period state
`<select>`" implying select-only is the intent.

### Badge for calendar mode

In `_getBadgeInfo()`:
```typescript
case "calendar":
  return { cls: "calendar", text: "Calendar" };
```

CSS class `.mode-badge.calendar` uses same style as `.mode-badge.scheduled`
(secondary/muted colors) per UI-SPEC.

### `types.ts` additions

```typescript
export interface PersonConfig {
  // ... existing fields
  calendar_config?: {
    entity_id: string;
    event_means: "absent" | "present";
  };
  preheat_lead_minutes?: number;
}
```

---

## TDD Opportunities

`tdd_mode: true` is set in `.planning/config.json`. These tasks have
well-defined I/O and are prime TDD candidates:

### HIGH value (write test first)

| Task | Why TDD |
|------|---------|
| `_resolve_calendar_presence()` helper | Pure function: events list × event_means × now × preheat_lead → bool. Exhaustive table of cases. |
| `_prefetch_calendars()` cache deduplication | Test that two persons sharing an entity_id produce one `get_events` call, not two. |
| `_prefetch_calendars()` error fallback | Test that `HomeAssistantError` → `_calendar_cache[eid] = []` and WARNING logged once. |
| Period walk with `state: "calendar"` | Test that `resolve_presence()` returns the cached calendar result for a calendar-state period. |
| `preheat_lead_minutes` pre-heat trigger | Test boundary: event ends in 59 min → absent; event ends in 60 min → present (with default 60). |

### MEDIUM value (test alongside implementation)

| Task | Why |
|------|-----|
| `set_person_config` WS handler: `calendar_config` persistence | Input/output is clear but integration with HA infra makes test setup heavier. |
| Calendar cache reset per cycle | Verifiable via two sequential `async_evaluate` calls. |

### LOW value (verify via UAT instead)

| Task | Why |
|------|-----|
| Frontend calendar entity picker population | Lit rendering is hard to unit-test; UAT is faster. |
| Frontend auto-save on change | Same. |

---

## Test Patterns

### Mocking `calendar.get_events` with `async_mock_service`

[VERIFIED: venv
`pytest_homeassistant_custom_component/common.py` lines 351–388]

`async_mock_service` has a `response` parameter and a `supports_response`
parameter. For `SupportsResponse.ONLY` services, both must be set:

```python
from pytest_homeassistant_custom_component.common import async_mock_service
from homeassistant.core import SupportsResponse

# Prepare the mock response (keyed by entity_id per entity service contract)
mock_events = [
    {
        "start": "2026-06-01T08:00:00+02:00",
        "end": "2026-06-01T17:00:00+02:00",
        "summary": "School",
    }
]
calendar_calls = async_mock_service(
    hass,
    "calendar",
    "get_events",
    response={"calendar.pronote_jean": {"events": mock_events}},
    supports_response=SupportsResponse.ONLY,
)
```

After calling `coordinator.async_evaluate()`:
- `calendar_calls` records all `ServiceCall` objects received.
- The coordinator's `_calendar_cache["calendar.pronote_jean"]` contains
  `mock_events`.

### Simulating entity unavailability

```python
# async_mock_service with raise_exception to simulate entity unavailable
from homeassistant.exceptions import HomeAssistantError
async_mock_service(
    hass,
    "calendar",
    "get_events",
    raise_exception=HomeAssistantError("No entities matched"),
    supports_response=SupportsResponse.ONLY,
)
```

After `async_evaluate()`, verify:
- `coordinator._calendar_cache["calendar.missing"]` is `[]`.
- No test failure — coordinator silently falls back.

### Pattern for pure calendar resolution logic

Tests for `_resolve_calendar_presence()` do NOT need the `hass` fixture —
they are pure Python:

```python
@pytest.mark.freeze_time("2026-06-01 12:00:00")
def test_active_event_absent_by_default():
    events = [
        {
            "start": "2026-06-01T08:00:00+02:00",
            "end": "2026-06-01T17:00:00+02:00",
            "summary": "School",
        }
    ]
    now = dt_util.now()
    assert _resolve_calendar_presence(events, "absent", now, 60) is False
```

### Existing test infrastructure

Tests use:
- `MockConfigEntry` for integration setup
- `async_mock_service` for service mocking
- `hass.states.async_set()` for entity state seeding
- `pytest.mark.freeze_time` (from `freezegun`) for deterministic time
- `asyncio_mode = "auto"` (pyproject.toml) — all async tests run
  automatically without `@pytest.mark.asyncio`

No new test infrastructure needed. New test file: `tests/test_calendar.py`
for unit-level tests of the calendar resolution logic and coordinator
integration.

---

## Validation Architecture

`nyquist_validation: true` — include this section.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-homeassistant-custom-component |
| Config file | `pyproject.toml` — `asyncio_mode = "auto"`, `testpaths = ["tests"]` |
| Quick run command | `.venv/bin/python -m pytest tests/test_calendar.py -v` |
| Full suite command | `.venv/bin/python -m pytest tests/ -v` (or `make test`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| CAL-01 | Calendar mode → absent when event active, `event_means=absent` | unit | `pytest tests/test_calendar.py::test_calendar_mode_absent_during_event` |
| CAL-01 | Calendar mode → present when no event, `event_means=absent` | unit | `pytest tests/test_calendar.py::test_calendar_mode_present_no_event` |
| CAL-01 | Calendar entity error → fallback absent, WARNING logged | unit | `pytest tests/test_calendar.py::test_calendar_fallback_on_error` |
| CAL-02 | Two persons sharing entity → one get_events call | integration | `pytest tests/test_calendar.py::test_calendar_cache_deduplication` |
| CAL-02 | Cache resets per cycle | integration | `pytest tests/test_calendar.py::test_calendar_cache_reset_per_cycle` |
| CAL-03 | Period state "calendar" in schedule resolves via calendar_config | unit | `pytest tests/test_calendar.py::test_calendar_period_state_resolves` |
| CAL-04 | Preheat: event ending in ≤ lead_minutes → present | unit | `pytest tests/test_calendar.py::test_preheat_triggers_at_boundary` |
| CAL-04 | Preheat: event ending in > lead_minutes → absent | unit | `pytest tests/test_calendar.py::test_preheat_no_trigger_before_boundary` |

### Sampling Rate

- **Per task commit:** `pytest tests/test_calendar.py -v -x`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_calendar.py` — new file, covers all CAL-* requirements
  above (no Wave 0 setup task needed if test file is created in Wave 1
  task that implements the tested function)

---

## Implementation Order

### Recommended sequence to avoid blocking

**Wave 1 — Backend core (self-contained, no frontend dependency)**

1. `const.py`: add `PRESENCE_CALENDAR = "calendar"` and
   `DEFAULT_PREHEAT_LEAD_MINUTES = 60`. Update `DEFAULT_CONFIG`
   docstring.
2. `schedule.py`: add `_resolve_calendar_presence()` helper (pure,
   synchronous — takes events list, not hass). Update period walk in
   `resolve_presence()` to handle `state: "calendar"` periods.
3. `coordinator.py`: add `_calendar_cache: dict[str, list]` to
   `__init__`. Add `async def _prefetch_calendars()`. Update
   `async_evaluate()` to reset cache and call prefetch before presence
   pass. Update `_compute_present_persons()` to pass cache to calendar
   resolution. Update `_apply_presence_overrides()` similarly.
4. `websocket.py`: extend `set_person_config` schema comment (schema
   accepts `dict` already — no vol change needed for `calendar_config`
   and `preheat_lead_minutes` since the handler does a sparse-merge);
   document the new fields.
5. Tests: `test_calendar.py` — unit tests for all CAL-* behaviors.

**Wave 2 — Frontend**

6. `types.ts`: add `calendar_config` and `preheat_lead_minutes` to
   `PersonConfig`. Add `"calendar"` to `PRESENCE_COLORS`,
   `PERIOD_LABELS`, `PERIOD_DISPLAY_NAMES`.
7. `person-card.ts`: add calendar mode constant, badge, mode option,
   calendar config block, layout reorder. Period editor calendar state.

**Wave 3 — Integration verification**

8. `REQUIREMENTS.md`: rewrite CAL-01..04.
9. `manifest.json`: bump version to `1.3.0` if not already done.

---

## Risks & Landmines

### Landmine 1: `SupportsResponse.ONLY` requires `return_response=True`

**What goes wrong:** Calling `hass.services.async_call("calendar",
"get_events", ...)` without `return_response=True` raises
`ServiceValidationError: service_lacks_response_request`. This is not
caught by a generic `Exception` handler and will propagate.

**How to avoid:** Always use `return_response=True, blocking=True` when
calling `calendar.get_events`. Catch `HomeAssistantError` as the error
base.

### Landmine 2: Entity service response is keyed by `entity_id`

**What goes wrong:** Code that does `response["events"]` directly will
get `KeyError`. The correct access is `response[entity_id]["events"]`.

**How to avoid:** `events = (result or {}).get(eid, {}).get("events", [])`.

### Landmine 3: All-day event dates are `"YYYY-MM-DD"` strings

**What goes wrong:** `datetime.datetime.fromisoformat("2026-06-02")` does
NOT raise in Python 3.12 — it returns a naive datetime with time 00:00.
Comparing a naive datetime with a timezone-aware `dt_util.now()` raises
`TypeError: can't compare offset-naive and offset-aware datetimes`.

**How to avoid:** Detect all-day events by checking for `"T"` in the
string. Convert date-only strings via `dt_util.start_of_local_day(
datetime.date.fromisoformat(s))` which returns a timezone-aware datetime.

### Landmine 4: `resolve_presence()` "pure Python" contract

**What goes wrong:** Importing `homeassistant` in `schedule.py` breaks
the contract stated in the module docstring and would make all schedule
unit tests require the full HA mock infrastructure.

**How to avoid:** Keep `schedule.py` HA-import-free. The calendar
resolution helper takes `events: list[dict]` (already fetched) not
`hass`.

### Landmine 5: `_apply_presence_overrides()` also calls `resolve_presence()`

`_apply_presence_overrides()` (line 303) calls `resolve_presence()` for
each person in a `for` loop. If the calendar mode is handled in
`resolve_presence()` via a cached events argument, this method also needs
the cache. The planner must ensure the cache is passed consistently to
both `_compute_present_persons()` and `_apply_presence_overrides()`.

### Landmine 6: `time-bar.ts` PRESENCE_CYCLE click-cycling

Adding `"calendar"` to `PRESENCE_CYCLE` would cause click-cycling through
three states, which may confuse users. The UI-SPEC indicates a `<select>`
approach for period state. The time-bar may need a mode where certain states
are only available via select, not click-cycling. Alternatively, keep
`PRESENCE_CYCLE = ["present", "absent"]` unchanged and handle the calendar
period state exclusively via the period editor's `<select>`.

### Landmine 7: `resolve_presence()` return type change for period states

Currently `resolve_presence()` returns `bool`. If a period has
`state: "calendar"`, the function cannot return a bool without resolving
the calendar first. With Option A (hoisted lookup), the cached events are
passed in and the function can remain bool-returning. The period walk
must use the events for `"calendar"` state periods.

### Landmine 8: `get_events` with `target` parameter

The calendar service is an **entity service**. When calling via
`hass.services.async_call`, the entity_id must be passed in `target`
(not in `service_data`). Passing it in `service_data` may or may not
work depending on HA version. The safe pattern verified in the venv source
is `target={"entity_id": eid}`.

Alternatively, put `entity_id` in `service_data` — the entity service
schema (`cv.make_entity_service_schema`) merges `ATTR_ENTITY_ID` into the
data. Either way works. Use `target={"entity_id": eid}` for clarity.

---

## Package Legitimacy Audit

> No new packages are installed in Phase 11 (D-02: no new PyPI
> dependencies). This section is skipped.

**Packages removed due to slopcheck:** none  
**Packages flagged as suspicious:** none

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| HA calendar component | `calendar.get_events` call | ✓ (in venv) | HA 2025.x+ | — |
| pytest-homeassistant-custom-component | Tests | ✓ | installed in venv | — |
| freezegun | `freeze_time` marks | ✓ | installed | — |

**Missing dependencies:** none.

---

## Security Domain

> No new authentication, network calls, or data exposure vectors. Calendar
> data is fetched via HA's internal service bus (already authenticated).
> ASVS V5 input validation is the relevant control.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | HA handles auth |
| V3 Session Management | no | — |
| V4 Access Control | no | WS auth gate (T-03-06) |
| V5 Input Validation | yes | `calendar_config.entity_id` must be validated as a `calendar.*` entity ID |
| V6 Cryptography | no | — |

**Input validation for `calendar_config.entity_id`:** The WS handler
currently accepts any `dict` for `calendar_config`. Before calling
`get_events`, the coordinator should verify the entity ID starts with
`"calendar."` to prevent unexpected service calls. The WS schema can add
a vol validator, or the coordinator can do a prefix check with a silent
skip.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All-day events serialized as `"YYYY-MM-DD"` strings by HA's `_list_events_dict_factory` | HA Calendar Service API | Would need different parsing logic |
| A2 | `target={"entity_id": eid}` is the correct way to pass entity to an entity service via `async_call` | HA Calendar Service API | Service call fails or targets wrong entity |
| A3 | `async_mock_service` with `response=` and `supports_response=SupportsResponse.ONLY` correctly simulates `SupportsResponse.ONLY` behavior in tests | Test Patterns | Tests would not accurately simulate production |

All other claims are VERIFIED against the installed HA venv source code.

---

## Open Questions

1. **Should `"calendar"` be added to `PRESENCE_CYCLE` in time-bar?**
   - What we know: UI-SPEC says period state is set via `<select>`,
     suggesting click-cycling is not the intent.
   - What's unclear: Whether the time-bar drag interactions should
     produce `"calendar"` state or just `"present"`/`"absent"`.
   - Recommendation: Keep `PRESENCE_CYCLE` as-is. The "Calendar" option
     is only available via the period state `<select>` in the period
     editor, not via drag/click on the time-bar segments.

2. **`resolve_presence()` with calendar period states: how is the cache
   passed?**
   - Option A: Add optional `calendar_cache: dict | None = None` param.
   - Option B: Pass the resolved `is_present: bool` for calendar
     periods from the coordinator, not calling `resolve_presence()` for
     the period walk part.
   - Recommendation: Option A — minimal footprint, schedule.py stays
     self-contained.

---

## Sources

### Primary (HIGH confidence — verified in installed HA venv)

- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/homeassistant/core.py` — `ServiceRegistry.async_call()` signature and `return_response` / `blocking` behavior (lines 2697–2815)
- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/homeassistant/components/calendar/__init__.py` — `async_get_events_service` handler, response shape, `SupportsResponse.ONLY` registration (lines 271–314, 864–880)
- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/homeassistant/components/calendar/const.py` — `LIST_EVENT_FIELDS` definition (lines 59–67)
- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/homeassistant/helpers/service.py` — entity service response shape `{entity_id: handler_result}` (lines 925–1052)
- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/pytest_homeassistant_custom_component/common.py` — `async_mock_service` signature with `response` and `supports_response` (lines 351–388)
- Project codebase: `schedule.py`, `coordinator.py`, `const.py`, `websocket.py`, `person-card.ts`, `types.ts`, `persons-tab.ts` — current structure verified by direct read

### Secondary (MEDIUM confidence — official HA docs)

- [Calendar integration | home-assistant.io](https://www.home-assistant.io/integrations/calendar/) — `get_events` parameters and response description
- [Calendar entity | HA Developer Docs](https://developers.home-assistant.io/docs/core/entity/calendar/) — `async_get_events` implementation pattern

### Tertiary (LOW confidence — community / used only for orientation)

- [Service calls with return values · home-assistant/architecture Discussion #777](https://github.com/home-assistant/architecture/discussions/777) — historical context on SupportsResponse pattern

---

## Metadata

**Confidence breakdown:**

- HA Calendar Service API: HIGH — verified directly in venv source
- Async architecture decision: HIGH — based on direct code analysis
- Cache strategy: HIGH — follows established coordinator pattern
- Pre-heat detection algorithm: MEDIUM — logic is sound but edge cases
  (overlapping events, timezone boundary events) may surface in testing
- Frontend patterns: HIGH — direct code read of person-card.ts and
  persons-tab.ts

**Research date:** 2026-06-01  
**Valid until:** 2026-07-01 (stable HA calendar API; frontend patterns
are project-specific and stable)

---

## RESEARCH COMPLETE
