---
slug: time-period-label-display
status: resolved
trigger: ui-improvement
created: 2026-05-18
---

# Debug Session: time-period-label-display

## Symptom

Period blocks in the time-bar component show only single-character labels ("F",
"R", "N", "C") when they should display full names ("Frost protection",
"Normal", "Reduced", "Comfort", "Present", "Absent") when wide enough, and
ellipsize or hide when too narrow.

## Investigation

### Root Cause

`PERIOD_LABELS` in `types.ts` only stores single-character labels. The
`_renderSegment` method in `time-bar.ts` already has the scaffolding for
conditional label rendering (hides label when `widthPct <= 2.7`) but:

1. Labels are single chars ("F"/"N"/"R"/"C") — no full names available
2. `.segment-label` CSS lacks `text-overflow: ellipsis` — text just clips hard
3. `.segment-label` has no `max-width` constraint — can't shrink to trigger
   ellipsis

## Resolution

### root_cause

`PERIOD_LABELS` contained only single-character labels, and `segment-label` CSS
lacked `text-overflow: ellipsis` plus `max-width` to enable graceful truncation.

### fix

Added `PERIOD_DISPLAY_NAMES` constant to `types.ts` with full names. Updated
`_labelForPeriod` in `time-bar.ts` to use them. Fixed `.segment-label` CSS to
apply
`text-overflow: ellipsis; max-width: 100%; padding: 0 4px; box-sizing: border-box;`.
Kept the `widthPct > 2.7` hide threshold (hides label on segments narrower than
~16px).
