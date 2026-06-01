---
phase: 10
slug: presence-mode-ui
created: 2026-06-01
status: complete
tests_total: 9
tests_passed: 9
tests_failed: 0
tests_skipped: 0
---

# Phase 10 — User Acceptance Tests

> Scope note: Original spec (CONTEXT.md) called for rename to "Live tracking"
> + hide when no trackers. After D-04 redesign decisions, actual build keeps
> "HA home tracking" label, always shows option with ⚠ suffix when no trackers,
> and adds HA persistent notification. Tests reflect the delivered behavior.

## Test Results

| ID   | Description                                              | Result  | Notes |
|------|----------------------------------------------------------|---------|-------|
| T-01 | Dropdown: person WITH trackers → "HA home tracking" (no ⚠) | ✅ | |
| T-02 | Dropdown: person WITHOUT trackers → "HA home tracking ⚠" | ✅ | |
| T-03 | Badge: HA mode + trackers → "HA home tracking" (no ⚠) | ✅ | |
| T-04 | Badge: HA mode + no trackers → "HA home tracking ⚠" | ✅ | |
| T-05 | Stuck-mode inline warning visible when mode=ha, no trackers | ✅ | |
| T-06 | No silent mode change on render when mode=ha, no trackers | ✅ | |
| T-07 | HA notification appears when ha-mode person has no trackers | ✅ | |
| T-08 | Notification non-dismissible — reappears after dismiss (≤1 min) | ✅ | |
| T-09 | Notification dismissed immediately when trackers restored | ✅ | |

## Test Details

<!-- Results appended below as tests complete -->
