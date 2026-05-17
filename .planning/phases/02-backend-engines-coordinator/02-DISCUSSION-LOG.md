# Phase 2: Backend Engines & Coordinator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-16
**Phase:** 2-Backend Engines & Coordinator
**Areas discussed:** Scheduler trigger, Presence edge cases, Phase 2 entities

---

## Scheduler trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Poll every minute | async_track_time_interval fires every 60s; derive active period from dt_util.now() each tick; DST-safe by construction | ✓ |
| Event-driven transitions | async_track_point_in_time schedules exact callbacks at period boundaries; fewer evaluations but complex DST handling | |
| HA time-change events | async_track_time_change fires on HA minute ticks; equivalent to polling, slightly less direct | |

**User's choice:** Poll every minute

**Notes:**
- User flagged concern about TRV battery drain from frequent polling. Resolved: coordinator tracks `_last_pushed` per entity and only sends service calls when target temp changes — same call frequency as event-driven in practice.
- User added a new behavior: when a user manually adjusts a TRV, the coordinator should hold off overriding until the next period transition. Hold lifts automatically when desired_temp changes. On HA restart, hold state is lost and coordinator resumes immediately (INFRA-03).
- User asked whether DST can be detected from within the integration (yes, via `dt_util.now().dst()` / UTC offset comparison), but this doesn't simplify scheduling — polling sidesteps the problem entirely.

---

## Manual override hold (emerged from Scheduler discussion)

| Option | Description | Selected |
|--------|-------------|----------|
| Until next period transition | Hold lifts automatically when the period changes (desired_temp ≠ last_pushed) | ✓ |
| Until user explicitly releases | Persistent hold requiring a release action via the panel | |
| No hold — coordinator always wins | Override within one minute; ignores user intent | |

**User's choice:** Until next period transition

**Notes:** This emerged as a new requirement not in the original REQUIREMENTS.md. Added as D-03 in CONTEXT.md.

---

## Presence edge cases

### No Normal/Comfort periods for a present person's room

| Option | Description | Selected |
|--------|-------------|----------|
| Reduced temperature | Apply Reduced as the occupied-but-not-comfort baseline | ✓ |
| Normal temperature | Always apply Normal when someone is present | |
| Follow schedule as-is | Presence only overrides the sandwiched-gap, not the whole schedule | |

**User's choice:** Reduced temperature

### Uncovered days in time program

| Option | Description | Selected |
|--------|-------------|----------|
| Apply frost protection | Safest fallback for uncovered time | |
| Apply reduced temperature | Fallback for edge case gap | (fallback if gap somehow exists) |
| Enforce all-7-days coverage | Validate at save time; reject incomplete programs | ✓ |

**User's choice:** Enforce all 7 days at save time. User clarified: "the user can only overload existing periods" — weekday group coverage is mandatory. Added as new requirement D-06. If a gap somehow exists at runtime (e.g., data corruption), fallback to Reduced.

### Person with no room associations

| Option | Description | Selected |
|--------|-------------|----------|
| Skip silently | No heating effect; coordinator ignores the person | ✓ |
| Warn in HA logs | Skip but emit a log warning | |
| Block startup | Refuse to load | |

**User's choice:** Skip silently in backend.

**Notes:** User added: if a person has schedule/mode configured but no rooms, a warning badge should appear next to their name in the UI. Deferred to Phase 3 (panel doesn't exist yet). D-07 and D-08 were originally separate decisions but merged — both express the same backend behavior (skip silently regardless of whether the person has settings).

---

## Phase 2 entities

| Option | Description | Selected |
|--------|-------------|----------|
| Pure backend — no entities | Phase 2 is control loop only; hardware testing via Developer Tools and logs | ✓ |
| Global mode selector entity | Select entity for toggling global mode before panel exists | |
| Mode selector + status sensors | Maximum observability but significantly wider scope | |

**User's choice:** Pure backend — no HA entities in Phase 2.

---

## Claude's Discretion

- Coordinator class structure (standalone class vs. method on ClimateManagerData)
- `_last_pushed` storage mechanism
- Scheduler listener registration / cancellation pattern
- Evaluation order within a tick (sequential vs. concurrent per room)
- `dt_util.now()` usage for weekday/time resolution

## Deferred Ideas

- Phase 3 UI warning badge: person with schedule/mode but no room associations → warning indicator in Persons panel
- Configurable polling interval (v2 — 60s is appropriate for Phase 1 hardware)
- Presence override entities (global mode select, per-person override) — decided against in Phase 2, could be v2 convenience
