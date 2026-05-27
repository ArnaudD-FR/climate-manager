---
created: 2026-05-27T00:00:00.000Z
title: Multi-week presence scheduling with even/odd week support
area: general
files: []
---

## Problem

Person presence schedules currently support a single weekly pattern repeated every week.
This doesn't cover split-custody households where a child alternates between homes on
even and odd weeks, with potentially different per-day configurations each week.

Two sub-features requested:

1. **Even/odd week scheduling**: each person can have two independent 7-day schedules —
   one for even ISO weeks, one for odd weeks. Each day in each week is configured
   independently (present / absent).

2. **Pronote integration**: a new scheduling source that reads the child's school
   timetable from the Pronote API (French school management platform) to automatically
   derive presence — e.g. the child is "absent" on school days and "present" during
   holidays or free periods.

## Solution

TBD — likely involves:
- Data model: person config gains `schedule_type` ("single" | "even_odd") and a second
  `schedule_odd` / `schedule_even` field alongside the existing `schedule`
- Schedule evaluator: compute current ISO week parity at evaluation time and select the
  correct week's schedule
- UI: presence time-bar gains a week-switcher toggle (Even / Odd) to edit each week
- Pronote: new optional scheduling source type; reads Pronote API credentials from
  person config and fetches timetable; caches result; maps school/holiday blocks to
  present/absent states
- Pronote support is additive — existing manual scheduling remains the default
