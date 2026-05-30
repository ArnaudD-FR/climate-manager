# Climate Manager

## What This Is

A Home Assistant custom integration that manages home climate controls through
smart radiator thermostats. It provides global heating modes, weekday-based time
programs, per-room schedule overrides, and person presence tracking — all
configurable through a full Lovelace dashboard panel without touching YAML.

## Core Value

A household's rooms are always at the right temperature at the right time,
without manual intervention — driven by schedules and who is actually home.

## Current Milestone: v1.2 Presence & Calibration

**Goal:** Support alternate-week presence schedules for shared-custody households
and add automatic TRV calibration from room sensors.

**Target features:**

- Even/odd week presence scheduling — person gains `schedule_type`
  ("single"|"even_odd") + `schedule_even`/`schedule_odd`; backend picks
  schedule by ISO week parity; UI shows a week-switcher toggle in the time-bar
- TRV temperature offset auto-calibration — global option to periodically adjust
  TRV offset using the delta between the room sensor and the TRV's reported
  temperature; Tado X first (`set_temperature_offset`), guarded by
  service/attribute detection

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

**Shipped:** Phase 7 (even/odd week backend — PersonConfig schedule_type, schedule_even/odd, backend
  parity evaluation) and Phase 8 (even/odd week frontend UI — getWeekParity helpers, schedule-type
  select, Even/Odd switcher, per-week save/reset, ISO parity default, live panel verified) — v1.2

**Shipped:** Phase 9 (TRV temperature offset auto-calibration — capability guard, calibration engine, set_calibration_config WS command, Options card toggle in Global Settings) — v1.2

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

### Active

- ✓ Even/odd week presence scheduling (alternate schedules, ISO week parity) —
  v1.2 Phase 8
- ✓ TRV temperature offset auto-calibration from room sensor — v1.2 Phase 9

### Out of Scope

- Specific periods (holidays, holidays at home) — deferred to v2
- Calendar-based presence detection (iCal, Pronote) — deferred to v2
- GPS / HA zone-based presence detection — deferred to v2
- Predictive pre-heat — deferred to v2
- Custom card UI — using full Lovelace panel instead
- HACS store publishing — development deploy only

## Context

- Built as a HACS-compatible HA custom integration in Python + Lit/TypeScript
- Targets latest Home Assistant version — no backwards-compatibility constraints
- TRVs exposed as standard HA `climate` entities via Matter integration (test:
  Tado X)
- Controls TRVs via two sequential calls: `set_hvac_mode(heat)` →
  `set_temperature` — auto mode never used (broken on Tado X via Matter)
- TRV push is concurrent via `asyncio.gather` — mode-change latency ~<1s vs ~10s
  sequential

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

_Last updated: 2026-05-30 — Phase 9 complete, Milestone v1.2 all phases done_
