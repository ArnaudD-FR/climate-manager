---
phase: 11-calendar-presence-backend
plan: "04"
subsystem: frontend-calendar-ui
tags: [calendar, presence, lit, typescript, ui]
dependency_graph:
  requires:
    - "11-01: PRESENCE_CALENDAR constant, resolve_calendar_presence"
    - "11-03: PersonConfig.calendar_config, preheat_lead_minutes in types.ts,
      PRESENCE_COLORS/PERIOD_LABELS/PERIOD_DISPLAY_NAMES.calendar in types.ts"
  provides:
    - "Calendar mode option in person card mode select"
    - "Calendar badge (.mode-badge.calendar) in person card"
    - "Calendar config block: entity picker, event_means select, preheat input"
    - "D-14 layout reorder: mode -> hint -> calendar config -> schedule -> rooms"
    - "D-17 calendar period state in time-bar popup _modeOptions (select-only)"
    - "Per-period inline calendar config rendered below time-bar"
    - "Period.calendar_config optional field in types.ts (D-06)"
  affects:
    - frontend/src/components/person-card.ts
    - frontend/src/components/time-bar.ts
    - frontend/src/types.ts
tech_stack:
  added: []
  patterns:
    - "Auto-save on change (D-09) — _onCalendarEntityChange, _onEventMeansChange,
      _onPreheatChange, _onPeriodCalendarConfigChange all call setPersonConfig"
    - "hass.states filter for calendar.* entity list (D-15)"
    - "PRESENCE_COLORS.calendar from types.ts — no hardcoded hex"
key_files:
  created: []
  modified:
    - frontend/src/components/person-card.ts
    - frontend/src/components/time-bar.ts
    - frontend/src/types.ts
decisions:
  - "Calendar option placed after HA option in mode select (before Force Present
    / Force Absent) — natural grouping of external-source modes"
  - "PRESENCE_CYCLE in time-bar stays [present, absent] — calendar added to
    _modeOptions() only (Landmine 6: select-only, not click/drag cycling)"
  - "Inline per-period calendar config rendered below time-bar in person-card.ts
    (not inside time-bar popup) — separates data concerns from rendering"
  - "Period.calendar_config added as optional field on presence Period union arm
    — additive sparse schema consistent with person-level calendar_config"
metrics:
  duration_minutes: 18
  completed_date: "2026-06-02"
  tasks_completed: 2
  files_modified: 3
  tests_added: 0
requirements: [CAL-01, CAL-03, CAL-04]
---

# Phase 11 Plan 04: Calendar Mode UI Summary

**One-liner:** Calendar presence mode UI with entity picker, event_means
toggle, preheat lead input, and per-period calendar state in the schedule
editor — all auto-saving via setPersonConfig.

## What Was Built

Extended `person-card.ts`, `time-bar.ts`, and `types.ts` to surface the
calendar presence configuration that Plans 01-03 wired in the backend:

### Task 1: Calendar mode option, badge, config block, and layout reorder

1. **Mode constant** — `PRESENCE_MODE_CALENDAR = "calendar"` added to the
   existing mode constant block.

2. **Mode select** — Calendar option added after HA option in the presence
   mode `<select>` (before Force Present / Force Absent).

3. **Badge** — `case PRESENCE_MODE_CALENDAR: return { cls: "calendar", text:
   "Calendar" }` in `_getBadgeInfo()`; `.mode-badge.calendar` CSS rule uses
   same muted secondary background/text as `.mode-badge.scheduled` (UI-SPEC).

4. **Auto-save handlers** — Three new handlers following the `_onModeChange`
   pattern (setPersonConfig → reloadConfig → showToast, no Save button):
   - `_onCalendarEntityChange` — saves `calendar_config.entity_id +
     event_means`
   - `_onEventMeansChange` — saves `calendar_config.event_means + entity_id`
   - `_onPreheatChange` — parses int, guards 0<=val<=480, saves
     `preheat_lead_minutes` (T-11-09 defense-in-depth)

5. **Calendar config block** — Rendered only when `currentMode ===
   PRESENCE_MODE_CALENDAR`:
   - "Calendar source" section label + native `<select class="mode-select">`
     populated from `Object.keys(panel.hass.states).filter(id =>
     id.startsWith("calendar.")).sort()` with friendly_name as text
   - Empty state: single disabled option "No calendar entities found in Home
     Assistant."
   - "Event means" section label + native `<select>` with "Absent during
     events" (default) / "Present during events"
   - "Pre-heat lead time" section label + native `<input type="number"
     min="0" max="480" step="5">` with `<span>min</span>` suffix
   - `.preheat-row` CSS for inline row layout

6. **D-14 layout reorder** — Expanded card now renders in order:
   (1) Presence mode label + select, (2) hint/schedule-hint paragraph,
   (3) Calendar config block (calendar mode only), (4) Presence schedule
   section (scheduled mode only), (5) Room associations (moved last).

7. **Calendar mode hint** — Static text "Presence determined by calendar
   events on the selected entity." shown in place of `presenceModeHint()`
   when mode is calendar.

### Task 2: Calendar period state in the schedule period editor

1. **Period type extension** — `types.ts` `Period` union's presence arm
   gains optional `calendar_config?: { entity_id: string; event_means:
   "absent" | "present" }` (D-06 per-period calendar config).

2. **Time-bar _modeOptions()** — For presence mode, "Calendar" button added
   to the popup's "Change mode" section (key: "calendar", color:
   PRESENCE_COLORS["calendar"] from types.ts). `PRESENCE_CYCLE` unchanged at
   `["present", "absent"]` — calendar reachable only via popup, not
   click/drag cycling (Landmine 6).

3. **Per-period calendar config handler** — `_onPeriodCalendarConfigChange(
   dayIndex, periodStart, newCalendarConfig)` saves updated period data to
   the active week's schedule field.

4. **Inline calendar config rendering** — After the time-bar in the schedule
   section, an IIFE scans the active days array for periods with `state ===
   "calendar"` and renders inline config for each: period label "Calendar:
   `<friendly_name>` (Day HH:MM)", entity picker, event_means select. Both
   selects auto-save via `_onPeriodCalendarConfigChange`.

5. **Color/label tokens** — Time-bar `_modeOptions()` uses
   `PRESENCE_COLORS["calendar"]` (no hardcoded hex in person-card.ts).

## Verification Results

```
cd frontend && npm run build    — ✓ built in ~250ms, 168 kB panel.js
make lint                       — ✓ prettier + ruff + markdownlint passed
tsc --noEmit (person-card.ts)   — 0 errors
PRESENCE_CYCLE grep             — ["present", "absent"] only (calendar absent)
startsWith("calendar.") grep    — 1 occurrence in person-card.ts
```

## Deviations from Plan

None — plan executed exactly as written.

One minor clarification in implementation: the "period-state `<select>`"
referred to in Task 2 was interpreted as the time-bar popup's "Change mode"
button list (which is the existing period editor UX). Rather than converting
the buttons to a `<select>` element (a larger change to time-bar), "Calendar"
was added as a new button in `_modeOptions()` for presence mode. This is
equivalent semantically and matches the existing UX pattern in time-bar.
The inline calendar config per-period is rendered in person-card.ts below
the time-bar, not inside the popup.

## Known Stubs

None. All UI controls are wired to `setPersonConfig` auto-save handlers.
The calendar entity picker is populated from `hass.states` at render time —
no static placeholders.

## Threat Surface Scan

No new network endpoints. Trust boundary mitigations:

- **T-11-09** (lead time number input): `_onPreheatChange` guards
  `0 <= val <= 480` in the handler — defense-in-depth above server-side
  clamp in Plan 03 WS handler.
- **T-11-10** (calendar entity list from hass.states): entity IDs already
  visible to the authenticated panel session, no new exposure.

## Self-Check

### Files Exist

- [x] `frontend/src/components/person-card.ts` — modified (Task 1+2)
- [x] `frontend/src/components/time-bar.ts` — modified (Task 2)
- [x] `frontend/src/types.ts` — modified (Task 2)

### Commits Exist

- [x] `7e32cc8` — Task 1: Calendar mode option, badge, config block, layout
- [x] `69973e0` — Task 2: Calendar period state in schedule period editor

## Self-Check: PASSED

## Pending

Task 3 is a `checkpoint:human-verify` (blocking). Human verification of the
Calendar mode UI required before this plan can be marked complete.
