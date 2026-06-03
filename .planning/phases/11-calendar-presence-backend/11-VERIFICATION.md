---
phase: 11-calendar-presence-backend
verified: 2026-06-03T19:41:40Z
status: complete
score: 17/17 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Deploy and open a person card. Select 'Calendar' presence mode."
    expected: >
      A 'Calendar source' entity picker listing calendar.* entities by
      friendly name, an 'Event means' select (Absent/Present during events),
      and a 'Pre-heat lead time' number input (default 60, suffix 'min')
      appear. Changing any control shows a 'Saved' toast with no Save button.
      Reloading the panel persists all three values.
    why_human: >
      Lit rendering and auto-save behavior cannot be verified by grep;
      requires visual confirmation in a live HA instance. Plan 04 Task 3
      (checkpoint:human-verify, blocking gate) was not yet approved.
  - test: >
      With a person in Calendar mode, verify that selecting a calendar entity
      and triggering an event (or waiting for the coordinator cycle) makes
      the person appear absent in the panel status bar.
    expected: >
      The person disappears from the present-persons list during an active
      event with event_means='absent'. With no active event, the person is
      present.
    why_human: >
      End-to-end coordinator cycle with a real HA calendar entity cannot be
      exercised by grep or unit tests.
  - test: >
      Switch the person to Scheduled mode. In the period editor, change a
      period's state to 'Calendar' via the period-state select.
    expected: >
      An inline entity picker and event_means select appear below that period
      row. The period block shows indigo color (#5C6BC0) and 'C' label.
      Clicking or dragging on the time-bar still only toggles present/absent
      (never lands on calendar).
    why_human: >
      Period editor rendering (D-17) and time-bar click-cycling exclusion
      (Landmine 6) require visual verification in a live panel.
  - test: >
      Verify the D-14 layout reorder: expand a person card and confirm the
      scheduling/calendar section renders ABOVE the room associations list.
    expected: >
      Presence mode selector and (when applicable) calendar config block or
      schedule editor appear before the room association chips.
    why_human: Rendered DOM order is not verifiable by static analysis.
---

# Phase 11: Calendar Presence Backend — Verification Report

**Phase Goal:** Integrate HA calendar entities as a presence source — persons
can set Calendar mode, the coordinator fetches calendar events each cycle,
and the frontend exposes the full calendar config UI.
**Verified:** 2026-06-02
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | PRESENCE_CALENDAR = "calendar" constant exists in const.py | VERIFIED | `const.py:44 PRESENCE_CALENDAR = "calendar"` |
| 2  | DEFAULT_PREHEAT_LEAD_MINUTES = 60 in const.py | VERIFIED | `const.py:59 DEFAULT_PREHEAT_LEAD_MINUTES: int = 60` |
| 3  | calendar_config sparse key not added to DEFAULT_CONFIG | VERIFIED | grep confirms it is comment-only in const.py |
| 4  | resolve_calendar_presence() implements full event_means × active × preheat table | VERIFIED | `schedule.py:122-201` — full algorithm; 19 tests pass |
| 5  | _parse_calendar_dt handles all-day DATE strings without TypeError | VERIFIED | `schedule.py:92-119`; `test_allday_event_handling` passes |
| 6  | Period state "calendar" in resolve_presence dispatches via per-period calendar_config | VERIFIED | `schedule.py:319-331`; `test_calendar_period_state_resolves` passes |
| 7  | schedule.py has zero HA imports | VERIFIED | grep `from homeassistant` returns no output |
| 8  | _calendar_cache reset at start of every async_evaluate cycle | VERIFIED | `coordinator.py:161 self._calendar_cache = {}` before `_prefetch_calendars` |
| 9  | _prefetch_calendars fetches once per unique entity_id (dedup) | VERIFIED | `coordinator.py:219` uses `set[str]`; `test_calendar_cache_deduplication` passes |
| 10 | HomeAssistantError → single WARNING + empty fallback per entity | VERIFIED | `coordinator.py:267-279`; `_calendar_warn_issued` set prevents spam; `test_calendar_fallback_on_error` passes |
| 11 | get_events called with blocking=True and return_response=True | VERIFIED | `coordinator.py:258-259` |
| 12 | PRESENCE_CALENDAR branch in _compute_present_persons reads _calendar_cache | VERIFIED | `coordinator.py:744-757` |
| 13 | PRESENCE_CALENDAR branch in _apply_presence_overrides reads _calendar_cache | VERIFIED | `coordinator.py:410-421` |
| 14 | resolve_presence called with calendar_cache=self._calendar_cache in both methods | VERIFIED | `coordinator.py:426` and `coordinator.py:765` |
| 15 | set_person_config persists calendar_config with entity_id prefix guard (calendar.) | VERIFIED | `websocket.py:504-521`; `test_ws_persists_calendar_config`, `test_ws_rejects_non_calendar_entity_id` pass |
| 16 | PersonConfig.calendar_config + preheat_lead_minutes in types.ts; calendar tokens in PRESENCE_COLORS/PERIOD_LABELS/PERIOD_DISPLAY_NAMES | VERIFIED | `types.ts:64-69`, `:193`, `:204`, `:215` |
| 17 | PRESENCE_MODE_CALENDAR in person-card.ts with Calendar option, badge, config block, and auto-save handlers | VERIFIED | `person-card.ts:45,664,675,766`; handlers at lines 471/488/514 |

**Score:** 17/17 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/climate_manager/const.py` | PRESENCE_CALENDAR + DEFAULT_PREHEAT_LEAD_MINUTES | VERIFIED | Both present at lines 44, 59 |
| `custom_components/climate_manager/schedule.py` | resolve_calendar_presence() + _parse_calendar_dt() + calendar period dispatch | VERIFIED | Lines 92-201, 319-331; zero HA imports |
| `custom_components/climate_manager/coordinator.py` | _calendar_cache + _prefetch_calendars() + calendar dispatch in both presence methods | VERIFIED | Lines 133, 204-281, 410-421, 744-757 |
| `custom_components/climate_manager/websocket.py` | set_person_config validates calendar_config + preheat_lead_minutes | VERIFIED | Lines 504-528 |
| `frontend/src/types.ts` | PersonConfig calendar fields + calendar period tokens | VERIFIED | Lines 64-69, 193, 204, 215 |
| `frontend/src/components/person-card.ts` | Calendar mode UI + badge + config block + handlers | VERIFIED | Lines 45, 471-518, 655-667, 766-892 |
| `tests/test_calendar.py` | 19 tests covering all plan acceptance criteria | VERIFIED | 19/19 pass (confirmed by test run) |
| `custom_components/climate_manager/www/panel.js` | Built frontend artifact | VERIFIED | File exists |
| `.planning/REQUIREMENTS.md` | CAL-01..04 rewritten to HA-native wording | VERIFIED | No Pronote/iCal/RRULE language; event_means + preheat_lead_minutes present |
| `.planning/ROADMAP.md` | Phase 11 success criteria updated; 5 plans listed | VERIFIED | pronote/ical/RRULE grep returns no matches in Phase 11 block |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `schedule.py:resolve_presence` | `schedule.py:resolve_calendar_presence` | `active_state == "calendar"` dispatch | VERIFIED | `schedule.py:319` |
| `coordinator.async_evaluate` | `coordinator._prefetch_calendars` | await before _compute_present_persons | VERIFIED | `coordinator.py:161-162` |
| `coordinator._compute_present_persons` | `schedule.resolve_calendar_presence` | PRESENCE_CALENDAR branch + _calendar_cache | VERIFIED | `coordinator.py:744-757` |
| `coordinator._apply_presence_overrides` | `schedule.resolve_presence` | `calendar_cache=self._calendar_cache` | VERIFIED | `coordinator.py:423-427` |
| `person-card.ts calendar controls` | `ws.setPersonConfig` | @change handlers | VERIFIED | `person-card.ts:475, 501, 518` |
| `person-card.ts entity picker` | `hass.states` | `filter id.startsWith('calendar.')` | VERIFIED | `person-card.ts:692` |
| `websocket.set_person_config` | `store.async_save + coordinator.async_evaluate` | sparse-merge then write-then-evaluate | VERIFIED | `websocket.py:500-528` pattern confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `coordinator._compute_present_persons` | `self._calendar_cache` | `_prefetch_calendars` via `calendar.get_events` | Yes — live HA service call with blocking=True | FLOWING |
| `person-card.ts` calendar entity picker | `calendarEntityIds` | `this.panel.hass?.states` filtered to `calendar.*` | Yes — live hass.states | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All test_calendar.py tests pass | `.venv/bin/python -m pytest tests/test_calendar.py -x --tb=no -q` | 19 passed | PASS |
| schedule.py has zero HA imports | `grep -c "from homeassistant" schedule.py` | 0 | PASS |
| PRESENCE_CALENDAR constant importable | grep const.py | line 44 confirmed | PASS |
| get_events uses blocking=True + return_response=True | grep coordinator.py | lines 258-259 confirmed | PASS |

### Probe Execution

Step 7c: SKIPPED — no `scripts/*/tests/probe-*.sh` files declared or found for
this phase. Plans 01-03 used inline pytest commands (all passing). Plan 04 uses
a blocking human checkpoint.

### Requirements Coverage

| REQ-ID | Source Plans | Description | Status | Evidence |
|--------|-------------|-------------|--------|----------|
| CAL-01 | 11-01, 11-02, 11-03, 11-04 | Calendar mode presence via calendar.* entity + event_means | SATISFIED | resolve_calendar_presence(), _prefetch_calendars(), set_person_config guard, person-card UI |
| CAL-02 | 11-02 | One get_events call per unique entity per cycle, cached | SATISFIED | _prefetch_calendars dedup set + test_calendar_cache_deduplication |
| CAL-03 | 11-01, 11-04 | Scheduled period state "calendar" resolves via per-period calendar_config | SATISFIED | schedule.py:319-331; person-card period editor calendar state |
| CAL-04 | 11-01, 11-03, 11-04 | preheat_lead_minutes (default 60, range 0-480) pre-heats before return | SATISFIED | resolve_calendar_presence preheat logic; websocket clamp; person-card input |

All four CAL requirements fully traced to implemented code. No orphaned
requirements found.

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `frontend/src/types.ts:99-103` | `TODO(phase-10):` comment referencing calibration_threshold | INFO | Pre-existing TODO from Phase 10; references future work scoped to a known follow-on phase. Not introduced by Phase 11. No BLOCKER. |

No TBD, FIXME, or XXX markers found in any file modified by Phase 11.
No stub implementations detected. No empty return patterns in relevant paths.

### Human Verification Required

Plan 04 (Task 3) includes a **blocking `checkpoint:human-verify` gate** for
the Calendar mode UI. This gate must be cleared before the phase can be marked
fully complete. The following checks require a live HA instance with the panel
deployed.

#### 1. Calendar Mode Config Block

**Test:** Run `make build && make deploy`. Open a person card, expand it,
select "Calendar" in the presence mode picker.
**Expected:** A "Calendar source" entity picker lists your HA calendar.*
entities by friendly name. An "Event means" select offers "Absent during
events" (default) and "Present during events". A "Pre-heat lead time" number
input shows 60 with a "min" suffix. Changing any control shows a "Saved"
toast. Reload and confirm persistence.
**Why human:** Lit rendering and auto-save UX are not unit-testable.

#### 2. End-to-End Presence Resolution

**Test:** Configure a person to Calendar mode pointing at a calendar entity
with an active event. Wait for or force a coordinator cycle (1 min).
**Expected:** The person is absent in the panel status when an event is
active (event_means=absent). The person is present when no event is active.
**Why human:** Live HA calendar service call required; not mockable in static
analysis.

#### 3. Period Calendar State in Schedule Editor

**Test:** Switch a person to Scheduled mode. In the period editor, select
"Calendar" from the period-state dropdown for a period.
**Expected:** An inline entity picker and event_means select appear below
the period row. The period block renders in indigo (#5C6BC0) with "C" label.
Click/drag on the time-bar still only cycles present/absent.
**Why human:** Period editor rendering (D-17) and time-bar cycling exclusion
(Landmine 6) need visual verification.

#### 4. D-14 Layout Reorder

**Test:** Expand any person card.
**Expected:** The scheduling/calendar section (mode picker + calendar config
or schedule editor) appears ABOVE the room associations list.
**Why human:** DOM render order is not verifiable by static analysis.

### Gaps Summary

No automated gaps found. All 17 must-haves are VERIFIED by code inspection and
test execution. Four human verification items remain from Plan 04's blocking
checkpoint:human-verify gate (Task 3). The phase goal is code-complete; the
blocking gate requires a human approval signal before the phase is fully closed.

---

_Verified: 2026-06-02_
_Verifier: Claude (gsd-verifier)_
