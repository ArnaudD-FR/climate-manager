---
status: resolved
slug: rooms-card-status-off-not-reduced
trigger: "in rooms tab, when global mode is off, the room card header the room status should not be 'reduced'. It should be off"
created: 2026-05-26
updated: 2026-05-26
---

# Debug Session: rooms-card-status-off-not-reduced

## Symptoms

- **Expected:** When global mode is "off", the room card header status should display "off"
- **Actual:** Room card header status shows "reduced" instead of "off"
- **Error messages:** None reported
- **Timeline:** Unknown — likely related to recent MODE_OFF backend work (260526-ffr)
- **Reproduction:** Set global mode to "off", navigate to Rooms tab, observe room card header status text

## Current Focus

```
hypothesis: CONFIRMED — periodDisplay computed before globalMode guard; no branch for off mode
test: Inspected _renderHeaderStatus in room-card.ts
expecting: periodDisplay set to "Off" when globalMode === "off"
next_action: FIXED
reasoning_checkpoint: globalMode was read after periodDisplay was already computed; no guard existed
tdd_checkpoint:
```

## Evidence

- timestamp: 2026-05-26T00:00:00
  file: frontend/src/components/room-card.ts
  lines: 396-408
  note: periodDisplay computed at lines 403-405 from active_period without checking globalMode; globalMode read later at line 408 with no branch for "off"

## Eliminated Hypotheses

- Frontend mode label map missing "off" key — ELIMINATED: map had `off: "Off"` at line 417; that was for modeLabel, not periodDisplay

## Resolution

```
root_cause: In _renderHeaderStatus(), periodDisplay was computed from roomStatus.active_period (e.g. "reduced") before globalMode was read, with no guard for the "off" case. When global mode is "off" the backend still reports an active_period from the schedule, so the clock status item displayed the period name instead of "Off".
fix: Moved globalMode computation before periodDisplay. Added an explicit branch: when globalMode === "off", periodDisplay is set to "Off"; otherwise computed from active_period as before.
verification: Built panel.js confirmed — line 2289-2290 shows `if (s === "off") c = "Off"` in compiled output.
files_changed:
  - frontend/src/components/room-card.ts
  - custom_components/climate_manager/www/panel.js (built artifact)
```
