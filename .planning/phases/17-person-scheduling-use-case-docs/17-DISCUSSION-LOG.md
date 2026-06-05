# Phase 17: Person Scheduling Use-Case Docs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution
> agents. Decisions are captured in CONTEXT.md — this log preserves the
> alternatives considered.

**Date:** 2026-06-05
**Phase:** 17-person-scheduling-use-case-docs
**Areas discussed:** Screenshot source, Shots per use case, README depth, Scenario definitions

---

## Screenshot source

| Option | Description | Selected |
|--------|-------------|----------|
| Mock harness (extend) | Extend test-harness.html/screenshot.js to loop scenario configs; deterministic, CI/docker | ✓ |
| Live HA capture | Configure each persona on the real HA and screenshot the live panel | |
| You decide | Claude picks | |

**User's choice:** Mock harness (extend)
**Notes:** Later refined (wrap-up turn) — each use case gets its own folder with
a **local Makefile**; the root Makefile delegates to each use-case Makefile.

---

## Shots per use case

| Option | Description | Selected |
|--------|-------------|----------|
| Persons tab only | Single shot: the person card | |
| Persons + Overview | Card + resulting present/absent + zone state | |
| Full annotated set | Persons + Overview + Rooms | |
| You decide | Claude picks | |

**User's choice:** "depends on scenario" (free text)
**Notes:** Captured as per-scenario shot lists — persons card always included,
extra views added where they illustrate that scenario's effect.

---

## README depth

| Option | Description | Selected |
|--------|-------------|----------|
| Reproducible guide | Numbered step-by-step setup on the reader's own HA | |
| Conceptual showcase | Persona intro + config summary table + annotated screenshots | ✓ |
| Guide + why | Reproducible steps plus rationale | |
| You decide | Claude picks | |

**User's choice:** Conceptual showcase

---

## Scenario definitions

| Option | Description | Selected |
|--------|-------------|----------|
| Accept mapping | All five as proposed (rotating-shift & shared-custody both even/odd) | |
| Swap student→calendar | Student uses calendar (school timetable) | |
| Add HA-tracker example | Replace rotating-shift's mode with HA person-entity tracking | ✓ |
| You decide | Claude picks | |

**User's choice:** Add HA-tracker example
**Notes:** Final mapping — simple→single-week, business→calendar,
student→single-week (varied per weekday), rotating-shift→HA tracker,
shared-custody→even/odd. Covers single-week, calendar, ha, and even/odd modes.

---

## Claude's Discretion

- Exact config-summary table layout/wording and per-scenario schedule times.
- Whether root delegation is a new `use-case-docs` target or folded into
  `screenshots`.
- Screenshot file naming within each scenario's `screenshots/` folder.

## Deferred Ideas

- A `force_present`/`force_absent` "guest" 6th scenario (not in the fixed five).
- Step-by-step reproducible setup guides (rejected in favour of showcases).
