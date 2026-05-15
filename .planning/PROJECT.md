# Climate Manager

## What This Is

A Home Assistant custom integration that manages home climate controls through smart radiator thermostats. It provides global heating modes, weekday-based time programs, per-room schedule overrides, and person presence tracking — all configurable through a full Lovelace dashboard panel. No equivalent integration exists that combines all of these in a single, cohesive system.

## Core Value

A household's rooms are always at the right temperature at the right time, without manual intervention — driven by schedules and who is actually home.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Global mode control (Off / Time program / Time program & presences)
- [ ] Configurable period modes with default temperatures (Frost protection 7°C, Reduced 18°C, Normal 20°C, Comfort 22°C)
- [ ] Global time program (weekday sets + time periods mapped to period modes)
- [ ] Per-room time program override (or inherit global time program)
- [ ] Room configuration with one or more Matter climate entity associations
- [ ] Per-person presence via periodic schedule (weekday sets + time periods with present/absent state)
- [ ] Per-person room associations (presence warms associated rooms)
- [ ] Full Lovelace dashboard panel (global settings, rooms, persons sections)

### Out of Scope

- Specific periods (holidays, holidays at home) — deferred to v2
- Calendar-based presence detection (ical, pronote) — deferred to v2
- GPS-based presence detection — deferred to v2
- Custom card UI approach — using full Lovelace panel instead

## Context

- Built as a HACS-compatible HA custom integration in Python
- Targets latest Home Assistant version — no backwards-compatibility constraints
- Smart radiator thermostats are exposed as standard HA `climate` entities via the Matter integration
- Test device: Tado X TRV paired via Matter
- Integration controls TRVs by setting explicit target temperatures in `heat` mode — never relies on TRV `auto` mode (broken on Tado X via Matter)
- Existing integrations (climate-scheduler variants, Better Thermostat, Versatile Thermostat) each cover one or two dimensions of this spec but none cover the full combination

## Constraints

- **Tech stack**: Python custom integration — HA integration architecture (config entries, entities, services, frontend panel)
- **TRV interface**: Standard HA `climate` entity only — no brand-specific APIs
- **HA version**: Latest only — no legacy compatibility required
- **Presence v1**: Periodic schedule only — no external calendar or GPS dependencies in v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full Lovelace panel (not custom card) | Custom cards limit layout and interaction capabilities for a multi-section config UI | — Pending |
| Target temperatures via `heat` mode | Matter `auto` mode is broken on Tado X; explicit temp control is more reliable and portable | — Pending |
| v1 presence = periodic schedule only | Simplest presence model; calendar/GPS add external dependencies and complexity | — Pending |
| Specific periods deferred to v2 | Adds significant scheduling complexity; core value is achievable without holidays mode | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-15 after initialization*
