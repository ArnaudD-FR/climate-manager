# Climate Manager

## What This Is

A Home Assistant custom integration that manages home climate controls through smart radiator thermostats. It provides global heating modes, weekday-based time programs, per-room schedule overrides, and person presence tracking — all configurable through a full Lovelace dashboard panel without touching YAML.

## Core Value

A household's rooms are always at the right temperature at the right time, without manual intervention — driven by schedules and who is actually home.

## Current Milestone: v1.1 Heating Zones

**Goal:** Add named heating zones — groups of rooms that run their own mode and weekly schedule independently from the global configuration.

**Target features:**
- Zone CRUD (create, rename, delete named zones)
- Room assignment to zones (rooms not in any zone fall back to global)
- Zone mode override (Off / Time program / Time program & presences — overrides global)
- Zone time program (own weekly schedule, same weekday-group + period structure as global)
- Backend evaluation: zone config evaluated before global
- UI: Zones section in the Lovelace panel

## Current State

**Shipped:** v1.0 MVP (2026-05-26)

- ~2,000 LOC Python backend + ~4,100 LOC TypeScript frontend
- 3 planned phases + 28 quick-task improvements shipped post-phases
- Deployed to production HA instance via SSH/rsync Makefile target
- Android touch support confirmed working on time-bar drag interface

**In Progress:** v1.1 Heating Zones (milestone active)

- Phase 4 complete (2026-05-27): zone storage data model — `zones`/`default_zone_name` in DEFAULT_CONFIG, `validate_zone_assignment` helper, TypeScript ZoneConfig type stubs; STORAGE_VERSION unchanged at 2
- Phase 5 complete (2026-05-27): zone CRUD WebSocket API (6 commands, 17 total) + coordinator refactored to per-room zone-aware dispatch; 117 tests passing

## Requirements

### Validated

- ✓ Global mode control (Off / Time program / Time program & presences) — v1.0
- ✓ Configurable period temperatures (Frost 7°C, Reduced 18°C, Normal 20°C, Comfort 22°C) — v1.0
- ✓ Global time program (weekday groups + time periods mapped to period modes) — v1.0
- ✓ Per-room time program override (or inherit global) — v1.0
- ✓ Room configuration with climate entity associations — v1.0
- ✓ Per-person presence via periodic schedule — v1.0
- ✓ Per-person room associations (presence warms associated rooms) — v1.0
- ✓ Full Lovelace dashboard panel (global settings, rooms, persons) — v1.0
- ✓ HACS-compatible integration structure, persistent storage, two-call TRV control — v1.0
- ✓ Startup push + DST-safe scheduling — v1.0

### Active

- [ ] Multi-zone heating (named zones with independent mode + schedule) — v1.1
- [ ] Zone CRUD and room assignment UI — v1.1
- [ ] Backend zone evaluation (zone overrides global for assigned rooms) — v1.1

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
- TRVs exposed as standard HA `climate` entities via Matter integration (test: Tado X)
- Controls TRVs via two sequential calls: `set_hvac_mode(heat)` → `set_temperature` — auto mode never used (broken on Tado X via Matter)
- TRV push is concurrent via `asyncio.gather` — mode-change latency ~<1s vs ~10s sequential

## Constraints

- **Tech stack**: Python custom integration — HA integration architecture
- **TRV interface**: Standard HA `climate` entity only — no brand-specific APIs
- **HA version**: Latest only — no legacy compatibility required
- **Presence v1**: Periodic schedule only — no external calendar or GPS dependencies

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full Lovelace panel (not custom card) | More control over multi-section config UI | ✓ Good — complex state (schedules, person associations) needed Lit reactive properties |
| Target temperatures via `heat` mode | Matter `auto` mode is broken on Tado X | ✓ Good — explicit temp control is reliable and portable |
| v1 presence = periodic schedule only | Simplest model; calendar/GPS add external deps | ✓ Good — core value achieved without complexity |
| Specific periods deferred to v2 | Adds significant scheduling complexity | ✓ Good — not needed for core household use |
| SSH deploy; no HACS publishing | Dev tool, not distribution mechanism | ✓ Good — fast iteration with `make deploy` |
| Concurrent TRV push (asyncio.gather) | Sequential push ~10s for multi-TRV homes | ✓ Good — latency dropped to <1s |
| {mon..sun} schema for time programs | Per-day granularity needed for user config | ✓ Good — maps cleanly to UI and weekly patterns |

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
*Last updated: 2026-05-27 — Phase 5 complete*
