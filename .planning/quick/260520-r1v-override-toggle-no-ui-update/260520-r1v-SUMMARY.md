---
quick_id: 260520-r1v
slug: override-toggle-no-ui-update
date: 2026-05-20
status: complete
commits:
  - ec38db7
files_modified:
  - frontend/src/components/room-card.ts
---
# Quick Task 260520-r1v: Override Toggle No UI Update — Summary

Added `await this.panel.reloadConfig()` in both `_onOverrideToggle` and
`_onPeriodsChanged` in room-card.ts. Without it, `this.config` stayed stale
after saving — `hasCustomProgram` kept its old value, so the badge, time-bar,
and status line never re-rendered. Build succeeded, deployed.
