# Phase 7: Even/Odd Week Scheduling — Backend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or
> execution agents. Decisions are captured in CONTEXT.md — this log preserves
> the alternatives considered.

**Date:** 2026-05-29
**Phase:** 7-Even/Odd Week Scheduling — Backend
**Areas discussed:** Seeding responsibility, WS API shape, Storage version bump

---

## Seeding Responsibility

| Option | Description | Selected |
|--------|-------------|----------|
| Backend auto-seeds | Handler detects type switch + missing schedule_even, seeds both from schedule before merge | ✓ |
| Frontend seeds explicitly | Frontend reads current schedule, copies it, sends all three fields together | |

**User's choice:** Backend auto-seeds
**Notes:** Simpler frontend contract; backend guarantees data integrity.

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve schedule_even/odd on revert | Keep in storage silently; user can switch back without losing per-week data | ✓ |
| Clear on revert | Delete schedule_even/odd when switching back to single; lean storage | |

**User's choice:** Preserve silently
**Notes:** Non-destructive; if user reverts accidentaly their per-week edits
survive.

---

## WS API Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Extend set_person_config | No new command; schedule_type/even/odd via standard sparse-merge | ✓ |
| Dedicated convert command | New climate_manager/set_person_schedule_type for atomic type switch | |

**User's choice:** Extend set_person_config
**Notes:** The existing sparse-merge already handles arbitrary fields; no new
plumbing needed.

| Option | Description | Selected |
|--------|-------------|----------|
| Expose all three on get_config | Pass-through from persons dict; no handler changes for reads | ✓ |
| Add explicit fields to get_status | Add schedule_type/even/odd to per-person status response | |

**User's choice:** Expose via get_config pass-through
**Notes:** Zero-effort read path — the coordinator already returns the full
persons dict.

---

## Storage Version Bump

| Option | Description | Selected |
|--------|-------------|----------|
| No bump — zero-migration additive | Absent schedule_type = "single" at read time; no migration code | ✓ |
| Bump to version 3 with migration | Write schedule_type: "single" to all existing persons | |

**User's choice:** No bump
**Notes:** Additive fields; sparse-merge already preserves unknown fields
across versions.

---

## Claude's Discretion

- `resolve_presence()` modification strategy: inline schedule-selection block
  before the existing day-lookup, using `now.date().isocalendar().week % 2`
- Auto-seeding guard: check `"schedule_even" not in current_person_config`
  to avoid overwriting an already-edited even schedule
- TypeScript types: extend `PersonConfig` with `schedule_type?`,
  `schedule_even?`, `schedule_odd?` while touching the schema

## Deferred Ideas

None — discussion stayed within phase scope. Reviewed todos confirmed as
already shipped or belonging to later phases.
