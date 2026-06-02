---
status: partial
phase: 12-predictive-pre-heat
source: [12-VERIFICATION.md]
started: 2026-06-02T18:55:00Z
updated: 2026-06-02T18:55:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Pre-heating status line renders during active pre-heat
expected: When a room is pre-heating, the room card shows
  "Pre-heating (→ XX.X°C)" with the actual target temperature
result: [pending]

### 2. Suppression warning conditional rendering
expected: "Pre-heat disabled — presence cannot be scheduled" appears
  only when preheat_enabled=true AND preheat_suppressed=true (ha-mode
  only room); not shown when pre-heat is simply disabled
result: [pending]

### 3. Max lead time input visibility toggle
expected: The max lead time number input appears only when the Pre-heat
  checkbox is checked; hidden when unchecked
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
