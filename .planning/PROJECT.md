# Climate Manager

## What This Is

A Home Assistant custom integration that manages home climate controls through smart radiator thermostats. It provides global heating modes, weekday-based time programs, per-room schedule overrides, and person presence tracking — all configurable through a full Lovelace dashboard panel without touching YAML.

## Core Value

A household's rooms are always at the right temperature at the right time, without manual intervention — driven by schedules and who is actually home.

## Current State

**Shipped:** v1.0 MVP (2026-05-26)

- ~2,000 LOC Python backend + ~4,100 LOC TypeScript frontend
- 3 planned phases + 28 quick-task improvements shipped post-phases
- Deployed to production HA instance via SSH/rsync Makefile target
- Android touch support confirmed working on time-bar drag interface

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

- [ ] Save error handling — error toast persists until dismissed (deferred from v1.0 UAT)
- [ ] Person HA-mode presence (automatic via HA person entities)

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

---
*Last updated: 2026-05-26 after v1.0 milestone*
