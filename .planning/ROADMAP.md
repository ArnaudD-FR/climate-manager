# Roadmap: Climate Manager

## Overview

Climate Manager ships in three phases that follow the natural build-order constraint of the architecture: first, an installable HACS integration with persistent storage and verified TRV control; second, the complete backend — scheduling engines, presence logic, and the coordinator control loop, hardware-validated against real TRVs; third, the WebSocket API and Lovelace frontend panel that make all of it user-configurable without touching YAML.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - HACS-compatible integration scaffold with persistent storage and verified TRV control
- [x] **Phase 2: Backend Engines & Coordinator** - Complete scheduling/presence logic and coordinator control loop, hardware-validated with real TRVs (completed 2026-05-17)
- [ ] **Phase 3: WebSocket API & Frontend Panel** - Full Lovelace dashboard panel for configuring global settings, rooms, and persons

## Phase Details

### Phase 1: Foundation

**Goal**: An installable, HACS-compatible integration that persists its configuration across HA restarts and can send correct two-call commands to TRVs
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-04, ROOM-01, ROOM-02, ROOM-03
**Success Criteria** (what must be TRUE):

  1. The integration installs via HACS and appears in HA without errors, config flow completes successfully
  2. Room configuration (name + climate entity IDs) survives an HA restart without data loss
  3. A TRV is set to heat mode with an explicit target temperature via the two-call sequence (set_hvac_mode → set_temperature) — auto mode is never used
  4. Rooms with no associated climate entity are silently ignored; rooms with multiple TRVs continue operating when one TRV becomes unavailable

**Plans**: 3 plans

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Integration scaffold: manifest, const.py full schema, Makefile deploy loop, dev venv

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Backend modules: sparse Store, registry discovery, two-call TRV control, config flow

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Wire setup/unload via runtime_data; pytest smoke test (integration loads clean)

### Phase 2: Backend Engines & Coordinator

**Goal**: All heating logic runs correctly — the right temperature is applied to every managed TRV at every moment, driven by schedules, global mode, and person presence, including correct behavior on HA restart and across DST transitions
**Depends on**: Phase 1
**Requirements**: GLOBAL-01, GLOBAL-02, GLOBAL-03, SCHED-01, SCHED-02, SCHED-03, SCHED-04, SCHED-05, PERSON-01, PERSON-02, PERSON-03, PERSON-04, PERSON-05, PERSON-06, PERSON-07, PERSON-08, PERSON-09, INFRA-03, INFRA-05
**Success Criteria** (what must be TRUE):

  1. In Off mode, all managed TRVs are set to the frost protection temperature (default 7°C)
  2. In Time program mode, TRVs follow the active period's temperature according to the room's time program (or the global program if no room override is defined); transitions fire at the correct clock time
  3. In Time program & presences mode, a present person keeps their associated rooms heated continuously across the occupied window (no cool-down during sandwiched Reduced/Frost periods); an absent person's rooms revert to Reduced temperature
  4. On HA restart, the integration recomputes the active period from the current wall-clock time (dt_util.now()) and immediately pushes the correct setpoint to all TRVs — no stale state restored
  5. DST transitions do not cause missed or duplicate period firings; the scheduler always derives from current wall-clock time

**Plans**: 2 plans

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Pure-Python schedule + presence engine (evaluate_schedule, resolve_presence, compute_occupied_temp, 7-day validator) + unit tests

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — ClimateManagerCoordinator control loop + setup/unload wiring (minute poll, push-on-change, override hold, INFRA-03 startup push) + integration tests

**Plans created:** 2026-05-17

### Phase 3: WebSocket API & Frontend Panel

**Goal**: Users can configure every aspect of the integration — global mode, temperature defaults, global and per-room time programs, persons, presence schedules, and room associations — through a full Lovelace dashboard panel, without touching YAML or HA config files
**Depends on**: Phase 2
**Requirements**: UI-01, UI-02, UI-03, UI-04
**Success Criteria** (what must be TRUE):

  1. The Climate Manager panel appears in the HA sidebar and loads without a 404 or JS error
  2. The Global Settings section lets the user switch global mode, adjust default temperatures for all four period modes, and define the global time program — changes persist and take effect immediately
  3. The Rooms section lets the user assign a per-room time program or reset it to inherit the global program, and manage the climate entity associations for each room
  4. The Persons section lets the user set presence mode (Automatic/Present/Absent), manage room associations, and configure the periodic presence schedule for each person

**Plans**: 4 plans

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Per-day schema refactor (gap closure): const.py/schedule.py/coordinator.py + tests to {mon..sun} schema, STORAGE_VERSION=2

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — Python WebSocket API (8 commands) + coordinator status push + panel_custom registration + manifest deps + test_websocket.py

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 03-03-PLAN.md — Vite/Lit frontend scaffold: single-file build, root panel shell, shared time-bar component, Makefile build/deploy wiring

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 03-04-PLAN.md — Global Settings / Rooms / Persons tabs wired to auto-save + end-to-end human-verify checkpoint

**UI hint**: yes
**Plans created:** 2026-05-17

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/3 | Not started | - |
| 2. Backend Engines & Coordinator | 2/2 | Complete    | 2026-05-17 |
| 3. WebSocket API & Frontend Panel | 2/4 | In Progress|  |
