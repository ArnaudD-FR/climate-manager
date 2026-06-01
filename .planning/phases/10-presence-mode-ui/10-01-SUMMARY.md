---
plan: 10-01
phase: 10-presence-mode-ui
status: complete
completed: 2026-06-01
commits:
  - f709e11
  - 72b3e18
key-files:
  created:
    - frontend/src/components/presence-mode.ts
    - frontend/src/components/presence-mode.test.ts
  modified: []
---

## Summary

Created `presence-mode.ts` — a pure, Lit-free helper module that encodes all
Phase 10 UI decisions as exported constants and functions — and
`presence-mode.test.ts` with 8 unit tests covering all UI-01/UI-02 behaviors.

## What Was Built

**`presence-mode.ts`** exports:

- `MODE_LABEL_HA = "HA home tracking"` — the display string for the ha mode
  (D-01/UI-02). Kept the existing label; no rename introduced.
- `computeHasDeviceTrackers(trackers: unknown): boolean` — returns true only
  for a non-empty array; handles undefined, null, and empty array as false
  (D-02).
- `shouldShowHaOption(hasDeviceTrackers: boolean): boolean` — gates the ha
  option on tracker presence (D-04).
- `presenceModeHint(mode, hasDeviceTrackers): string` — returns the
  schedule-hint text including the stuck-mode warning for ha + no trackers
  (D-05).

No Lit imports — the module is fully testable with
`node --experimental-strip-types` (same pattern as `week-parity.ts`).

**`presence-mode.test.ts`** — 8 tests, all green:

- MODE_LABEL_HA equals "HA home tracking"
- computeHasDeviceTrackers: false for undefined, false for [], true for
  non-empty
- shouldShowHaOption: false when no trackers, true when trackers exist
- presenceModeHint: stuck-mode warning for ha+no trackers, correct hint for
  ha+trackers

## TDD Gate

- RED commit: `f709e11` — test(10-01): add failing presence-mode helper tests
- GREEN commit: `72b3e18` — feat(10-01): implement presence-mode pure helpers

## Deviations

**D-01 label kept as "HA home tracking"** — the original plan proposed
renaming to "Live tracking" but this was rejected mid-execution: "Live
tracking" implies GPS, which this mode does not use. The label stays as
"HA home tracking". Plan 02 must not rename it either.

## Self-Check: PASSED

- 8/8 tests green
- `make lint` green
- No Lit import in presence-mode.ts
- All four exports present
