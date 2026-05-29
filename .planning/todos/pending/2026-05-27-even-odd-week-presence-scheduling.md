---
created: 2026-05-27T00:00:00.000Z
title: Even/odd week presence scheduling for shared custody
area: general
files: []
---

## Problem

Person presence schedules support a single weekly pattern repeated every week.
This doesn't cover shared-custody households where a child alternates homes on
even and odd ISO weeks, with potentially different per-day configurations each
week.

## Solution

- Data model: person config gains `schedule_type` ("single" | "even_odd") and
  two schedule arrays `schedule_even` / `schedule_odd`
- Backend evaluator: compute ISO week parity at evaluation time, select the
  matching schedule; falls back to `schedule` when `schedule_type == "single"`
- UI: presence time-bar gains a week-switcher toggle (Even / Odd) shown only
  when `schedule_type == "even_odd"`; editing affects only the selected week's
  schedule
- Minor version bump (additive, no breaking changes)
