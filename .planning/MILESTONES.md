# Milestones

## v1.2 Presence & Calibration (Shipped: 2026-05-31)

**Phases completed:** 3 phases (7-9), 9 plans
**Timeline:** 2026-05-29 → 2026-05-31 (3 days)
**Codebase:** ~3,389 LOC Python + ~6,288 LOC TypeScript, 103 files changed,
93 commits since v1.1
**Quick tasks shipped:** 9 calibration UI improvements post-Phase 9
**Known deferred items at close:** 12 v2 features + 34 quick task tracking
artifacts (work done, status marker absent)

**Key accomplishments:**

1. Even/odd week scheduling backend — `schedule_type`/`schedule_even`/
   `schedule_odd` additive schema; ISO week parity selection in
   `resolve_presence()`; `copy.deepcopy` auto-seeding on single→even_odd
   switch; backward-compat (absent fields default to `single`)

2. Pure `getISOWeekNumber`/`getWeekParity` TypeScript helpers matching Python
   `isocalendar().week % 2` exactly; 8 `node --test` assertions covering W22,
   W23, W01/W53 year-boundary (WR-03) and totality

3. Even/odd week scheduling UI — schedule-type native `<select>`, [Even][Odd]
   CSS button-tab switcher, memoized dual day-array getters, week-scoped
   save/reset handlers, dynamic reset label; all 10 SCHED-04 behaviors
   verified live

4. TRV calibration capability guard — `supports_offset_calibration` attribute-
   first detection + `set_trv_offset` Tado X service helper in `trv.py`;
   7 passing TDD tests

5. TRV auto-calibration engine in coordinator — periodic delta computation,
   configurable 0.5°C threshold guard, offset service call; rooms without
   sensor or incompatible TRV silently skipped

6. `set_calibration_config` WebSocket command + Global Settings Options card
   with ha-switch toggle; calibration state persists across HA restarts

---

## v1.0 MVP (Shipped: 2026-05-26)

**Phases completed:** 3 phases, 14 plans  
**Timeline:** 2026-05-15 → 2026-05-26 (11 days)  
**Codebase:** ~2,000 LOC Python + ~4,100 LOC TypeScript, 168 files changed, 265
commits  
**Quick tasks shipped:** 28 post-phase improvements  
**Known deferred items at close:** 28 quick task directories missing status
marker (work done, tracking artifact only)

**Key accomplishments:**

1. HACS-compatible HA custom integration — manifest, config flow, Store-backed
   persistence, two-call TRV control (heat mode → set_temperature; auto mode
   never used)

2. Full backend scheduling engine — weekday-based time programs, four period
   modes (frost/reduced/normal/comfort), per-room override or global
   inheritance, validated {mon..sun} schema

3. Person presence engine — Automatic/Present/Absent/HA modes, periodic presence
   schedules, room associations, occupied-window heating (presence fills gaps
   between Normal/Comfort periods)

4. ClimateManagerCoordinator — minute-poll control loop, concurrent
   asyncio.gather TRV dispatch (~10s→<1s mode-change), DST-safe wall-clock
   evaluation, startup push on HA restart

5. WebSocket API (8 commands) + Lit/TypeScript Lovelace panel — Global Settings
   (mode, temps, time program), Rooms (per-room schedule, reset-to-global),
   Persons (mode, room associations, presence schedule)

6. Interactive time-bar — drag-resize period boundaries with live preview,
   Android touch support (44px handles, touch-action, overflow:visible,
   e.preventDefault)

---

## v1.1 Heating Zones (Shipped: 2026-05-28)

**Phases completed:** 3 phases (4-6), 9 plans
**Timeline:** 2026-05-26 → 2026-05-28 (2 days)
**Codebase:** 257 files changed, +32,080/-8,183 lines, 162 commits
**Quick tasks shipped:** zone color palette, EditorConfig, screenshots, MIT
license, pre-commit hooks
**Known deferred items at close:** 34 quick task directories missing status
marker (work done, tracking artifact only)

**Key accomplishments:**

1. Zone data model — `zones` dict + `default_zone_name` in DEFAULT_CONFIG;
   `validate_zone_assignment()` helper; TypeScript `ZoneConfig` interface;
   fully additive (STORAGE_VERSION=2 unchanged, v1.0 data loads cleanly)

2. Zone CRUD WebSocket API — 6 new commands (17 total): create, rename, delete
   (snapshot-rollback), set mode, set/reset time program; all guarded with
   ERR_NOT_FOUND and schema validation

3. Coordinator zone-aware per-room dispatch — `_resolve_zone_config()` helper
   replaces global-mode switch; PASS 1 (baseline temp) + PASS 2 (presence
   override); 117 tests passing

4. ZoneTab Lit component (~590 lines) — inline name edit, native mode picker,
   memoized time-bar, chip+search-picker room assignment, inline delete confirm

5. Dynamic zone tabs in panel — Default Zone first (no delete), custom zones
   added/removed dynamically; `+` button to create zones

6. Zone color palette — 8 colors; color dots on tab buttons and room badges;
   HA 2026.x compatibility enforced (native `<input>`/`<select>` only)

---
