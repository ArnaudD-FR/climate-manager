# Climate Manager

## What This Is

A Home Assistant custom integration that manages home climate controls through
smart radiator thermostats. It provides zone-based heating modes, weekday time
programs, person presence tracking (periodic schedules, even/odd weeks, and HA
`calendar.*` sources), predictive pre-heat with learned thermal inertia, and
automatic TRV temperature offset calibration — including real-time Matter→Tado X
calibration — all configurable through a full Lovelace dashboard panel without
touching YAML.

## Core Value

A household's rooms are always at the right temperature at the right time,
without manual intervention — driven by schedules and who is actually home.

## Current Milestone

**v1.3 Calendar Presence & Pre-heat shipped 2026-06-06.** Planning the next
milestone — no active milestone in flight.

### Candidate goals for the next milestone

- Per-zone boiler declaration / flow-temp normalisation (deferred from v1.3,
  parked in `todos/deferred/`)
- Boiler demand control (v2)
- Multi-language / i18n support (v2)
- Holiday / specific-period manual overrides (v2)
- HACS Default store publishing (currently SSH-deploy only)

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

**Shipped:** v1.3 Calendar Presence & Pre-heat (2026-06-06)

- 8 phases (10-17), 35 plans; 304 files changed, +52,397/-3,873, 393 commits
- Phases 10-11: presence mode UI (HA home tracking label + ⚠ stuck-mode hint)
  and calendar presence backend (`calendar.*` sources, per-cycle `get_events`
  cache, gap-handling modes, CAL-04 wake-up advance)
- Phases 12-13: predictive pre-heat (zone opt-in, learned inertia, status UI)
  and Matter→Tado X real-time calibration (`state_changed` listener, pairing UI)
- Phases 14-15: Default Zone consolidated to a first-class `ZoneConfig`
  (ARCH-01); per-room `room_mode` overrides removed (ARCH-02)
- Phases 16-17: coordinator restructured into a Zone/Person/Room/TRVGroup
  domain graph with structured log traces (OBS-01); seven persona use-case docs
  with coordinator-generated screenshots (DOC-01)

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
- ✓ Calendar presence sources (`calendar.*`, per-cycle cache, gap handling,
  wake-up advance) — v1.3 (CAL-01..04)
- ✓ Predictive pre-heat with learned thermal inertia (zone opt-in, status UI) —
  v1.3 (PREHEAT-01..05)
- ✓ Matter→Tado X real-time calibration on `state_changed` — v1.3
  (MCALIB-01..02)
- ✓ Presence mode UI: "HA home tracking" label + ⚠ stuck-mode hint — v1.3
  (UI-01, UI-02)
- ✓ Default Zone consolidated to first-class `ZoneConfig`; per-room mode
  override removed — v1.3 (ARCH-01, ARCH-02)
- ✓ Structured presence/zone/heating log traces — v1.3 (OBS-01)
- ✓ Seven persona use-case docs with generated screenshots — v1.3 (DOC-01)

### Active

*(none — planning next milestone)*

### Out of Scope

- Specific periods (holidays, holidays at home) — deferred to v2
- GPS / HA zone-based presence detection — out (HA `person.*` home/away covers
  the local-network case)
- Per-zone temperature setpoints — deferred
- Per-zone boiler declaration / flow-temp normalisation — deferred to v1.4+
  (`todos/deferred/`)
- Boiler demand control — deferred to v2 (`todos/deferred/`)
- Multi-language support — deferred to v2 (`todos/deferred/`)
- Custom card UI — using full Lovelace panel instead
- HACS store publishing — development deploy only

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
- Calendar presence delegates to HA's `calendar.get_events` service, cached
  once per evaluation cycle; falls back to absent on entity error (no log spam)
- Pre-heat lead time is learned per room from observed heating cycles
  (convergence after 3-5 cycles); non-converging samples excluded
- Matter→Tado X calibration is event-driven via
  `async_track_state_change_event`; listeners cancel-and-rebuild to avoid ghosts
- As of HA 2026.x: `ha-select`/`ha-tabs`/`ha-textfield` are broken — the panel
  uses native `<select>`/`<input>` and CSS button-tabs instead
- Coordinator is a Zone/Person/Room/TRVGroup domain graph evaluated via a
  per-cycle EvalContext (replaced the monolithic evaluate method in Phase 16)

## Constraints

- **Tech stack**: Python custom integration — HA integration architecture
- **TRV interface**: Standard HA `climate` entity only — no brand-specific APIs
- **HA version**: Latest only — no legacy compatibility required
- **Presence sources**: periodic schedules, even/odd weeks, and HA `calendar.*`
  entities (since v1.3) — no external SDKs or GPS dependencies; calendar
  integration is delegated to HA's own `calendar` domain

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
| Calendar presence via HA `calendar.*` | Reuse HA's calendar domain; no external SDKs   | ✓ Good — Pronote/iCal work through HA without extra deps                                |
| Per-cycle `get_events` cache          | Avoid N fetches when persons share a calendar  | ✓ Good — one fetch per unique entity per evaluate cycle                                 |
| Wake-up advance (CAL-04)              | Pre-empt return so rooms warm before arrival   | ✓ Good — flips absent→present within the lead; wired in v1.3 close                      |
| Pre-heat enable is zone-scoped        | GAP-01: per-room toggle was the wrong altitude | ✓ Good — moved to zone after UAT; room keeps only max-lead                              |
| Learned inertia for pre-heat lead     | Fixed lead over/under-shoots per room          | ✓ Good — converges after 3-5 cycles; bad samples excluded                               |
| Matter calibration via state_changed  | Polling is too slow for free-tier Tado X       | ✓ Good — sub-minute; cancel-and-rebuild avoids ghost listeners                          |
| Default Zone as first-class ZoneConfig| Four flat keys were a special-case sprawl      | ✓ Good — single `default_zone` key, unified code path, migrated on load (ARCH-01)       |
| Remove per-room mode override         | Zones already express the same intent          | ✓ Good — rooms always follow their zone; frost = assign an Off zone (ARCH-02)           |
| "HA home tracking" + ⚠, always shown  | Hiding the option hid the fix-it affordance    | ✓ Good — supersedes the original hide/rename spec (UI-01/02)                            |
| Coordinator domain-object graph       | Monolithic evaluate was hard to trace/extend   | ✓ Good — Zone/Person/Room/TRVGroup + EvalContext; enabled OBS-01 log traces             |

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

*Last updated: 2026-06-06 after v1.3 milestone*
