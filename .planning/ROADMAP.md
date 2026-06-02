# Roadmap: Climate Manager

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-05-26)
- ✅ **v1.1 Heating Zones** — Phases 4-6 (shipped 2026-05-28)
- ✅ **v1.2 Presence & Calibration** — Phases 7-9 (shipped 2026-05-31)
- 🚧 **v1.3 Calendar Presence & Pre-heat** — Phases 10-13 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) — SHIPPED 2026-05-26</summary>

- [x] Phase 1: Foundation (3/3 plans) — completed 2026-05-16
- [x] Phase 2: Backend Engines & Coordinator (2/2 plans) — completed 2026-05-17
- [x] Phase 3: WebSocket API & Frontend Panel (9/9 plans) — completed 2026-05-21

See: `.planning/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.1 Heating Zones (Phases 4-6) — SHIPPED 2026-05-28</summary>

- [x] Phase 4: Zone Data Model & Storage (2/2 plans) — completed 2026-05-27
- [x] Phase 5: Zone CRUD & Evaluation Engine (3/3 plans) — completed 2026-05-27
- [x] Phase 6: Zone & Room Assignment UI (4/4 plans) — completed 2026-05-28

See: `.planning/milestones/v1.1-ROADMAP.md` for full phase details.

</details>

<details>
<summary>✅ v1.2 Presence & Calibration (Phases 7-9) — SHIPPED 2026-05-31</summary>

- [x] Phase 7: Even/Odd Week Scheduling — Backend (2/2 plans) — completed
      2026-05-29
- [x] Phase 8: Even/Odd Week Scheduling — Frontend (3/3 plans) — completed
      2026-05-30
- [x] Phase 9: TRV Temperature Offset Auto-Calibration (4/4 plans) —
      completed 2026-05-30

See: `.planning/milestones/v1.2-ROADMAP.md` for full phase details.

</details>

### 🚧 v1.3 Calendar Presence & Pre-heat (In Progress)

**Milestone Goal:** Persons can use standard HA `calendar.*` entities as
their presence source; the coordinator caches `get_events` per cycle and
falls back gracefully on entity errors. A fixed pre-heat lead time starts
heating before the person returns. Rooms can opt in to predictive pre-heat
using a learned inertia model. Matter TRV state-change events trigger
immediate calibration. The "HA" presence mode is renamed and conditionally
hidden.

- [ ] **Phase 10: Presence Mode UI** — Rename "HA" mode to "Live tracking"
      and hide it when no device trackers are linked to the person entity
- [x] **Phase 11: Calendar Presence Backend** — Calendar mode backed by (completed 2026-06-02)
      `calendar.*` HA entities; per-cycle cache, pre-heat lead time
- [ ] **Phase 12: Predictive Pre-heat** — Inertia-learning pre-heat engine,
      per-room toggle, panel status display
- [ ] **Phase 13: Matter→Tado X Real-Time Calibration** — Event-driven
      calibration on Matter state_changed; listener lifecycle management

## Phase Details

### Phase 10: Presence Mode UI

**Goal**: The panel's person presence mode picker no longer shows the "HA"
option when the person entity has no device trackers, and the option is
renamed to "Live tracking" everywhere it appears.
**Depends on**: Phase 9
**Requirements**: UI-01, UI-02
**Success Criteria** (what must be TRUE):

1. The mode picker for a person whose `person.*` HA entity has an empty or
   absent `device_trackers` attribute never renders the "HA" / "Live
   tracking" option
2. Every instance of the "HA" label in the panel is replaced with "Live
   tracking" (WebSocket payloads may keep `"ha"` as the internal key)
3. The mode picker still shows "Live tracking" and lets it be selected when
   the person entity has at least one device tracker

**Plans**: 2 plans
- [x] 10-01-PLAN.md — Lit-free presence-mode helpers + unit tests (UI-01,
      UI-02)
- [x] 10-02-PLAN.md — wire helpers into person-card/persons-tab: label
      rename, conditional option, stuck-mode warning

### Phase 11: Calendar Presence Backend

**Goal**: A person's presence can be driven by a `calendar.*` HA entity;
the coordinator caches `get_events` per cycle and falls back to absent on
error. A per-person `preheat_lead_minutes` offset starts heating before the
person returns.
**Depends on**: Phase 10
**Requirements**: CAL-01, CAL-02, CAL-03, CAL-04
**Success Criteria** (what must be TRUE):

1. Setting a person to "Calendar" mode with a `calendar.*` entity makes
   them absent during active events when `event_means` is `"absent"`, or
   present when `event_means` is `"present"`; no event → inverse applies
2. The coordinator fetches `get_events` once per unique `calendar.*` entity
   per `async_evaluate` cycle and falls back to absent with a single WARNING
   on entity error
3. A Scheduled-mode period with state `"calendar"` resolves via its attached
   `calendar_config`; top-level Calendar mode periods are not recursive
4. A per-person `preheat_lead_minutes` (default 60) treats a calendar-absent
   person as present when the active event ends within the lead window,
   enabling pre-heat before the person returns

**Plans**: 5 plans
- [x] 11-01-PLAN.md — backend calendar presence logic + pure unit tests
      (const.py, schedule.py, tests/test_calendar.py)
- [x] 11-02-PLAN.md — coordinator per-cycle calendar cache + prefetch +
      presence routing (CAL-01, CAL-02)
- [x] 11-03-PLAN.md — WebSocket persistence for calendar_config +
      preheat_lead_minutes; types.ts (CAL-01, CAL-04)
- [x] 11-04-PLAN.md — frontend person-card Calendar mode UI + layout reorder
      + period calendar state (CAL-01, CAL-03, CAL-04)
- [x] 11-05-PLAN.md — rewrite CAL-01..04 + ROADMAP success criteria to the
      HA-native design

### Phase 12: Predictive Pre-heat

**Goal**: Rooms can opt in to pre-heat; the coordinator starts heating before
the next scheduled normal/comfort period using a learned inertia factor; the
panel shows pre-heating status and a suppression warning when applicable.
**Depends on**: Phase 11
**Requirements**: PREHEAT-01, PREHEAT-02, PREHEAT-03, PREHEAT-04, PREHEAT-05
**Success Criteria** (what must be TRUE):

1. A room with pre-heat enabled and a next transition ≥ lead-time minutes
   away receives a set_temperature call at the normal setpoint before the
   transition time
2. After 3–5 complete heating cycles the integration adjusts the lead time
   based on observed convergence; samples that never reached the target are
   excluded
3. The panel room card shows "Pre-heating (→ XX.X°C)" when pre-heat is
   active and "Pre-heat disabled — presence cannot be scheduled" when the
   presence source has no deterministic next transition

**Plans**: TBD

### Phase 13: Matter→Tado X Real-Time Calibration

**Goal**: When a Matter TRV entity is mapped to its Tado X device, a
state_changed listener fires the calibration pass immediately, enabling
sub-minute responsiveness without waiting for the polling interval.
**Depends on**: Phase 9
**Requirements**: MCALIB-01, MCALIB-02
**Success Criteria** (what must be TRUE):

1. Configuring a Matter→Tado X mapping in a room causes the integration to
   register an async_track_state_change_event listener on the Matter entity
2. A state_changed event on the Matter entity triggers `_async_calibrate`
   for that room within the same HA event loop turn
3. Removing the mapping or reloading the integration cancels the listener
   without accumulating ghost listeners

**Plans**: TBD

## Progress

| Phase                                      | Milestone | Plans Complete | Status   | Completed  |
| ------------------------------------------ | --------- | -------------- | -------- | ---------- |
| 1. Foundation                              | v1.0      | 3/3            | Complete | 2026-05-16 |
| 2. Backend Engines & Coordinator           | v1.0      | 2/2            | Complete | 2026-05-17 |
| 3. WebSocket API & Frontend Panel          | v1.0      | 9/9            | Complete | 2026-05-21 |
| 4. Zone Data Model & Storage               | v1.1      | 2/2            | Complete | 2026-05-27 |
| 5. Zone CRUD & Evaluation Engine           | v1.1      | 3/3            | Complete | 2026-05-27 |
| 6. Zone & Room Assignment UI               | v1.1      | 4/4            | Complete | 2026-05-28 |
| 7. Even/Odd Week Scheduling — Backend      | v1.2      | 2/2            | Complete | 2026-05-29 |
| 8. Even/Odd Week Scheduling — Frontend     | v1.2      | 3/3            | Complete | 2026-05-30 |
| 9. TRV Temperature Offset Auto-Calibration | v1.2      | 4/4            | Complete | 2026-05-30 |
| 10. Presence Mode UI                        | v1.3      | 2/2            | Complete | 2026-06-01 |
| 11. Calendar Presence Backend               | v1.3      | 5/5 | Complete   | 2026-06-02 |
| 12. Predictive Pre-heat                     | v1.3      | 0/?            | Pending  | —          |
| 13. Matter→Tado X Real-Time Calibration     | v1.3      | 0/?            | Pending  | —          |
