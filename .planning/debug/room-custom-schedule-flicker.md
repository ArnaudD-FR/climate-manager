---
status: resolved
slug: room-custom-schedule-flicker
trigger: "there is still flickering for room custom scheduling, ensure that this time scheduling is using the same code as global and person scheduling"
created: 2026-05-26
updated: 2026-05-26
---

# Debug Session: room-custom-schedule-flicker

## Symptoms

- **Expected:** Dragging period boundaries in the room custom schedule time-bar should not flicker after release — same smooth behaviour as global and person scheduling.
- **Actual:** Flickering persists in the room custom scheduling time-bar when dragging period borders.
- **Error messages:** None reported
- **Timeline:** The global/person scheduling flicker was fixed (drag-flicker-after-release session). Room scheduling appears to use different code or did not receive the same fix.
- **Reproduction:** Open a room card, enable custom schedule override, drag a period boundary in the room's time-bar.

## Prior Art

- Session `drag-flicker-after-release` diagnosed root cause: `updated()` in `time-bar.ts` compares prop reference (not content), clearing `_dragPreviewDays` on every re-render. Fix: content-comparison helper `_previewMatchesDays()` + drag-start cleanup.
- Fix was applied to `time-bar.ts` for global settings context.
- User reports room custom scheduling still flickers → either room scheduling uses a different component, or the fix path was not applied to all call sites.

## Current Focus

```
hypothesis: CONFIRMED — room-card.ts was missing the memoized _days getter that global-settings-tab.ts and person-card.ts already had
test: N/A — root cause identified by code inspection
expecting: No more flicker after adding memoized _days getter to RoomCard
next_action: DONE
reasoning_checkpoint:
tdd_checkpoint:
```

## Evidence

- timestamp: 2026-05-26T00:00:00
  finding: global-settings-tab.ts lines 83-95 — memoized _days getter: caches Period[][] by DailyProgram object identity, prevents new array references on re-render
- timestamp: 2026-05-26T00:00:00
  finding: person-card.ts lines 61-72 — same memoized _days getter pattern applied
- timestamp: 2026-05-26T00:00:00
  finding: room-card.ts line 585 (before fix) — .days=${programToDays(this.config.time_program ?? undefined)} called directly in render template, creating a new Period[][] reference on every render cycle
- timestamp: 2026-05-26T00:00:00
  finding: time-bar.ts updated() line 808-812 — clears _dragPreviewDays whenever the days property reference changes; new reference from programToDays() on every parent re-render causes premature clear during WS round-trip

## Eliminated Hypotheses

- Different component file for room scheduling: ELIMINATED — same climate-manager-time-bar is used
- Fix not applied to time-bar.ts: ELIMINATED — time-bar.ts has the correct updated() guard; the bug is in the caller

## Resolution

```
root_cause: room-card.ts passed .days=${programToDays(...)} inline in the render template, creating a new Period[][] reference on every render. time-bar.ts updated() clears _dragPreviewDays when the days prop reference changes, so any status-push re-render during the WS round-trip caused premature flicker. global-settings-tab.ts and person-card.ts had the memoized _days getter to prevent this; room-card.ts was missing it.
fix: Added memoized _days getter to RoomCard (same pattern as GlobalSettingsTab and PersonCard) — caches the programToDays() result by DailyProgram object identity. Changed the time-bar binding from .days=${programToDays(this.config.time_program ?? undefined)} to .days=${this._days}.
verification: vite build passes cleanly (113.23 kB output, 0 errors)
files_changed: frontend/src/components/room-card.ts, custom_components/climate_manager/www/panel.js
```
