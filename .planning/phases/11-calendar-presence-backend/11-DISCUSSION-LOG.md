# Phase 11: Calendar Presence Backend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-01
**Phase:** 11-calendar-presence-backend
**Areas discussed:** Phase scope, Config schema, Cache persistence, pronotepy dependency

---

## Phase scope

| Option | Description | Selected |
|--------|-------------|----------|
| Backend + UI (Recommended) | Python engine + Persons tab config UI in one phase | ✓ |
| Backend only | Python engine only; UI in a follow-up phase | |

**User's choice:** Backend + UI

**Follow-up — Where does calendar config UI appear?**

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in person card | Fields appear below mode picker when Calendar is selected | |
| Separate section/modal | Dedicated modal or card per person | |
| You decide | Leave to planner | |

**User's choice (freeform):** Calendar and presence mode should be part of the
presence mode picker. Also available as a period state within Scheduled mode
for complex planning (e.g., school days in even weeks only, manual schedule on
weekends). When calendar mode/state is set, config fields appear inline below.
Scheduling section should be above the rooms list.

**Follow-up — Two levels of calendar?**

| Option | Description | Selected |
|--------|-------------|----------|
| Both mode AND period state | Top-level mode + period state within Scheduled | ✓ (Pronote only) |
| Period state only | Only within Scheduled mode | |
| Top-level mode only | No per-period calendar | |

**User's clarification:** Only Pronote at two levels; iCal top-level mode only.
*(Later superseded: Pronote references dropped — all sources are HA calendar
entities; both levels apply to the generic "Calendar" concept.)*

**Follow-up — Calendar period state semantics:**

**User's choice:** During a calendar-marked period, the person is absent during
school slot hours as returned by the calendar; present outside those hours
within the period.

**Notes:** Late addition from user — drop all Pronote references (HA-native
approach renders them irrelevant); scheduling section moves above rooms list
in person card.

---

## Config schema

| Option | Description | Selected |
|--------|-------------|----------|
| New `mode` values `pronote`/`ical` (Recommended) | Extend mode field | ✓ |
| New `schedule_source` field | Parallel field alongside mode | |
| Extend `schedule_type` | Add to existing single/even_odd values | |

**Follow-up — Credential storage:**

**User's choice (freeform):** User should be able to pick up existing HA
calendars and Pronote integration — no credential entry in Climate Manager.
HA already owns the integrations.

**Follow-up — Confirming HA-native approach:**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — both read from HA calendar entities (Recommended) | `calendar.*` entities via `get_events` | ✓ |
| Mixed: Pronote from HA, iCal fetched directly | | |
| Self-hosted fetching as originally planned | pronotepy + ical | |

**Follow-up — Mode label in UI:**

| Option | Description | Selected |
|--------|-------------|----------|
| 'Calendar' only — entity picker (Recommended) | Single generic mode | ✓ |
| Separate Pronote / iCal labels | Two modes, same implementation | |

**Follow-up — Event semantics:**

| Option | Description | Selected |
|--------|-------------|----------|
| Absent DURING events (Recommended) | Active event = away | |
| Absent when NO events | Inverse | |
| Propose as user choice | Configurable toggle | ✓ |

**Notes:** Late addition — default `event_means = "absent"`; still configurable
per-person/per-period. All Pronote branding dropped.

---

## Cache persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Cache per evaluate cycle (Recommended) | One `get_events` call per entity per cycle, in-memory | ✓ |
| Short-lived in-memory cache with TTL | N-minute cache | |
| No caching — call per person per evaluate | Simplest code | |

**User's choice:** Cache per evaluate cycle.

**Notes:** HA owns the calendar data and its own caching; Climate Manager only
needs to avoid duplicate calls within a single evaluate pass.

---

## pronotepy dependency

| Option | Description | Selected |
|--------|-------------|----------|
| Correct — no PyPI deps needed (Recommended) | HA calendar entities handle everything | ✓ |
| Keep pronotepy as fallback | Direct fetch if no HA integration | |

**User's choice:** No PyPI deps needed.

---

## Claude's Discretion

- `resolve_presence()` async refactor approach (async wrapper vs. making the
  function itself async) — left to planner
- Whether the calendar pre-fetch (`_prefetch_calendars`) is a new private
  method or inline in `async_evaluate` — left to planner

## Deferred Ideas

- Adaptive pre-heat (inertia learning) → Phase 12
- Multiple calendar sources per person (logical OR/AND) → future phase
- Per-room or per-zone lead time → Phase 12
- Direct Pronote API via pronotepy → superseded by HA-native approach
