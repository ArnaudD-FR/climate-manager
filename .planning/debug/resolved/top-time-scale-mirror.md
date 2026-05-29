---
slug: top-time-scale-mirror
status: resolved
trigger: manual
goal: find_and_fix
created: 2026-05-18
---

# Debug Session: top-time-scale-mirror

## Symptoms

The top time ruler (`_renderTimeScale()`) does not match the bottom time axis (`.time-axis`).

- **Top:** 9 absolutely-positioned ticks at hours 0, 3, 6, 9, 12, 15, 18, 21, 24 with bare numbers and tick lines
- **Bottom:** 5 flex-spaced labels (00:00, 06:00, 12:00, 18:00, 24:00) with no tick lines

Goal: replace the top ruler with an exact copy of the bottom one — same HTML structure, same CSS classes, same labels.

## Current Focus

**hypothesis:** `_renderTimeScale()` uses different markup (absolute positioning, tick lines, bare hour numbers) vs the bottom `.time-axis` (flex space-between, HH:MM labels, no tick lines).

**next_action:** Extract a shared `_renderTimeAxis(marginTop?)` helper and call it for both top and bottom positions.

## Evidence

- timestamp: 2026-05-18T00:00:00Z
  file: frontend/src/components/time-bar.ts
  finding: |
    Bottom axis (lines 824-831): `.time-axis` > `.time-axis-inner` with flex+space-between,
    labels: 00:00 06:00 12:00 18:00 24:00, padding-left:48px padding-right:80px.
    Top ruler (lines 868-895): `.time-scale` > `.time-scale-inner` with 9 absolute ticks,
    tick lines + bare numbers, different number of ticks, different label format.

## Resolution

root_cause: The top ruler was implemented with a different approach (absolute ticks, bare numbers) instead of reusing the bottom axis structure (flex space-between, HH:MM labels).

fix: Extract shared `_renderTimeAxis()` helper returning the `.time-axis` markup. Call it for both top (margin-top:0, margin-bottom:2px) and bottom (existing margin-top:2px). Remove `_renderTimeScale()` and its CSS. Remove `.time-scale` / `.time-scale-inner` / `.time-scale-tick*` CSS rules.
