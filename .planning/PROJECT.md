# Climate Manager

## What This Is

A Home Assistant custom integration that manages home climate controls through
smart radiator thermostats. It provides global heating modes, weekday-based time
programs, per-room schedule overrides, person presence tracking with even/odd
week scheduling, and automatic TRV temperature offset calibration — all
configurable through a full Lovelace dashboard panel without touching YAML.

## Core Value

A household's rooms are always at the right temperature at the right time,
without manual intervention — driven by schedules and who is actually home.

## Current Milestone: v1.3 Calendar Presence & Pre-heat

**Goal:** Presence can be driven from external calendars (Pronote school
timetable, iCal work/holidays), rooms pre-heat automatically before occupied
periods using adaptive inertia learning, and calibration becomes sub-minute
via Matter→Tado X sensor mapping.

**Target features:**

- Pronote presence source — child's school timetable maps to absent/present
- iCal presence source — work/holiday calendar maps to absent/present
- Predictive pre-heat — adaptive lead time with learned inertia factor; fixed
  flow temp fallback (no boiler entity required)
- Matter→Tado X sensor mapping — sub-minute calibration on Tado X free tier
- Hide HA presence mode when person has no tracked device in HA
- Rename HA presence mode label for clarity

## Current State

**Shipped:** v1.0 MVP (2026-05-26)

- ~2,000 LOC Python backend + ~4,100 LOC TypeScript frontend
- 3 planned phases + 28 quick-task improvements shipped post-phases
- Deployed to production HA instance via SSH/rsync Makefile target
- Android touch support confirmed working on time-bar drag interface

**Shipped:** v1.1 Heating Zones (2026-05-28)

- Phase 4: zone storage data model — `zones`/`default_zone_name` in
  DEFAULT_CONFIG, `validate_zone_assignment`, TypeScript type stubs
- Phase 5: zone CRUD WebSocket API (6 commands, 23 total) + coordinator
  refactored to per-room zone-aware dispatch; 117 tests passing
- Phase 6: zone/room assignment UI — dynamic zone tabs, zone-tab component,
  room badge + picker, colored zone dots, 121 tests passing

**Shipped:** v1.2 Presence & Calibration (2026-05-31)

- ~3,389 LOC Python + ~6,288 LOC TypeScript; 103 files changed, 93 commits
- Phase 7: even/odd week scheduling backend — additive person schema
  (`schedule_type`/`schedule_even`/`schedule_odd`), ISO week parity selection
  in `resolve_presence()`, `copy.deepcopy` auto-seeding on switch
- Phase 8: even/odd week scheduling UI — schedule-type select, Even/Odd
  button-tab switcher, memoized dual day-array getters, week-scoped save/reset;
  pure `getISOWeekNumber`/`getWeekParity` helpers unit-tested with `node --test`
- Phase 9: TRV auto-calibration — capability guard, delta threshold (0.5°C),
  periodic coordinator pass, `set_calibration_config` WS command, Global
  Settings toggle; 9 quick-task calibration UI improvements post-phase

## Requirements

### Validated

- ✓ Global mode control (Off / Time program / Time program & presences) — v1.0
- ✓ Configurable period temperatures (Frost 7°C, Reduced 18°C, Normal 20°C,
  Comfort 22°C) — v1.0
- ✓ Global time program (weekday groups + time periods mapped to period modes) —
  v1.0
- ✓ Per-room time program override (or inherit global) — v1.0
- ✓ Room configuration with climate entity associations — v1.0
- ✓ Per-person presence via periodic schedule — v1.0
- ✓ Per-person room associations (presence warms associated rooms) — v1.0
- ✓ Full Lovelace dashboard panel (global settings, rooms, persons) — v1.0
- ✓ HACS-compatible integration structure, persistent storage, two-call TRV
  control — v1.0
- ✓ Startup push + DST-safe scheduling — v1.0
- ✓ Heating zones with per-zone mode and time programs — v1.1
- ✓ Zone/room assignment UI with color palette — v1.1
- ✓ Even/odd week presence scheduling (alternate schedules, ISO week parity) —
  v1.2 (SCHED-01..06)
- ✓ TRV temperature offset auto-calibration from room sensor — v1.2
  (CALIB-01..05)

### Active

*(none — planning next milestone)*

### Out of Scope

- Specific periods (holidays, holidays at home) — deferred to v2
- Calendar-based presence detection (iCal, Pronote) — deferred to v2
- GPS / HA zone-based presence detection — deferred to v2
- Predictive pre-heat — deferred to v2
- Per-zone temperature setpoints — deferred to v2
- Boiler demand control — deferred to v2
- Custom card UI — using full Lovelace panel instead
- HACS store publishing — development deploy only
- Multi-language support — deferred
- Matter/Tado X sensor mapping for real-time calibration — deferred to v2

## Context

- Built as a HACS-compatible HA custom integration in Python + Lit/TypeScript
- Targets latest Home Assistant version — no backwards-compatibility constraints
- TRVs exposed as standard HA `climate` entities via Matter integration (test:
  Tado X)
- Controls TRVs via two sequential calls: `set_hvac_mode(heat)` →
  `set_temperature` — auto mode never used (broken on Tado X via Matter)
- TRV push is concurrent via `asyncio.gather` — mode-change latency ~<1s vs
  ~10s sequential
- ha-switch confirmed working in HA 2026.x (used for calibration toggle)

## Constraints

- **Tech stack**: Python custom integration — HA integration architecture
- **TRV interface**: Standard HA `climate` entity only — no brand-specific APIs
- **HA version**: Latest only — no legacy compatibility required
- **Presence v1**: Periodic schedule only — no external calendar or GPS
  dependencies

## Key Decisions

| Decision                              | Rationale                                      | Outcome                                                                                |
| ------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------- |
| Full Lovelace panel (not custom card) | More control over multi-section config UI      | ✓ Good — complex state (schedules, person associations) needed Lit reactive properties |
| Target temperatures via `heat` mode   | Matter `auto` mode is broken on Tado X         | ✓ Good — explicit temp control is reliable and portable                                |
| v1 presence = periodic schedule only  | Simplest model; calendar/GPS add external deps | ✓ Good — core value achieved without complexity                                        |
| Specific periods deferred to v2       | Adds significant scheduling complexity         | ✓ Good — not needed for core household use                                             |
| SSH deploy; no HACS publishing        | Dev tool, not distribution mechanism           | ✓ Good — fast iteration with `make deploy`                                             |
| Concurrent TRV push (asyncio.gather)  | Sequential push ~10s for multi-TRV homes       | ✓ Good — latency dropped to <1s                                                        |
| {mon..sun} schema for time programs   | Per-day granularity needed for user config     | ✓ Good — maps cleanly to UI and weekly patterns                                        |
| Even/odd schema as additive fields    | No storage migration; absent = single          | ✓ Good — zero-downgrade path for existing persons                                      |
| copy.deepcopy for week-schedule seed  | Prevents shared-reference mutation bugs        | ✓ Good — W2/W4 tests confirmed isolation                                               |
| ISO week parity (week % 2)            | Matches Python isocalendar().week exactly      | ✓ Good — frontend/backend parity verified by 8 unit tests                              |
| TRV calibration via attribute guard   | Avoids service-call errors on non-Tado TRVs    | ✓ Good — incompatible rooms silently skipped, no log spam                              |
| 0.5°C delta threshold for calibration | Prevents jitter from minor sensor fluctuation  | ✓ Good — smooths out calibration cycles in production                                  |
| ha-switch for calibration toggle      | Standard HA component; simpler than native     | ✓ Good — confirmed visible and functional in HA 2026.x                                 |

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

*Last updated: 2026-05-31 after v1.2 milestone*
