# Roadmap: Climate Manager

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-05-26)
- ✅ **v1.1 Heating Zones** — Phases 4-6 (shipped 2026-05-28)
- 🚧 **v1.2 Presence & Calibration** — Phases 7-9 (in progress)

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
- [x] Phase 5: Zone CRUD & Evaluation Engine (3/3 plans) — completed
      2026-05-27
- [x] Phase 6: Zone & Room Assignment UI (4/4 plans) — completed 2026-05-28

</details>

### 🚧 v1.2 Presence & Calibration (In Progress)

**Milestone Goal:** Households with alternate-week custody can give each person
two independent weekly presence schedules, automatically selected by ISO week
parity, and the integration can keep TRV readings honest by auto-calibrating
their temperature offset against the room's reference sensor.

- [x] **Phase 7: Even/Odd Week Scheduling — Backend** — Person schema gains (completed 2026-05-29)
      `schedule_type`/`schedule_even`/`schedule_odd`; evaluator selects by week
      parity
- [ ] **Phase 8: Even/Odd Week Scheduling — Frontend** — Week-switcher toggle
      in the persons time-bar, visible only for even/odd persons
- [ ] **Phase 9: TRV Temperature Offset Auto-Calibration** — Periodic offset
      calibration from room sensor, guarded by TRV capability, configurable in
      Global Settings

## Phase Details

### Phase 7: Even/Odd Week Scheduling — Backend

**Goal**: A person can have two independent weekly presence schedules, and the
backend automatically applies the correct one based on the current ISO week
parity — without breaking any existing single-schedule person.
**Depends on**: Phase 6
**Requirements**: SCHED-01, SCHED-02, SCHED-03, SCHED-05, SCHED-06
**Success Criteria** (what must be TRUE):

1. A person's `schedule_type` can be set to `single` (default) or `even_odd`
   via the backend, and existing persons loaded from v1.1 storage with no
   `schedule_type` field behave exactly as before (treated as `single`, no
   migration, no data loss)
2. When a person is `even_odd`, the coordinator evaluates presence using
   `schedule_even` during even ISO weeks and `schedule_odd` during odd ISO
   weeks (parity from `date.isocalendar().week % 2`)
3. Switching a person from `single` to `even_odd` seeds both `schedule_even`
   and `schedule_odd` from the existing `schedule`, so the person's current
   presence pattern is preserved on both weeks
4. Switching a person from `even_odd` back to `single` leaves `schedule`
   unchanged and presence reverts to the single-schedule behaviour

**Plans**: 2 plans (Wave 1, parallel)

- [x] 07-01-PLAN.md — Evaluator week-parity selection + schema/types stub
      (SCHED-01, SCHED-02, SCHED-03)
- [x] 07-02-PLAN.md — set_person_config auto-seeding + revert preservation
      (SCHED-01, SCHED-05, SCHED-06)

### Phase 8: Even/Odd Week Scheduling — Frontend

**Goal**: A user can configure both week schedules for an even/odd person
directly in the panel, with a clear Even/Odd toggle that scopes time-bar edits
to one week at a time, and the toggle never appears for single-schedule
persons.
**Depends on**: Phase 7
**Requirements**: SCHED-04
**Success Criteria** (what must be TRUE):

1. A person card shows a schedule-type control letting the user pick between a
   single schedule and even/odd schedules
2. When a person is set to even/odd, an Even / Odd week-switcher toggle appears
   above the presence time-bar; for single-schedule persons the toggle is
   absent
3. With the toggle on Even, time-bar edits change only `schedule_even`; with it
   on Odd, edits change only `schedule_odd` — switching the toggle redraws the
   bar to the selected week without losing the other week's edits
4. Changes made for each week persist after reload and match what the backend
   applies during the corresponding ISO week

**Plans**: TBD
**UI hint**: yes

### Phase 9: TRV Temperature Offset Auto-Calibration

**Goal**: When enabled, the integration periodically corrects each compatible
TRV's temperature offset so its readings track the room's reference sensor,
while silently leaving incompatible or sensor-less rooms untouched and avoiding
jittery over-correction.
**Depends on**: Phase 6 (independent of Phases 7-8)
**Requirements**: CALIB-01, CALIB-02, CALIB-03, CALIB-04, CALIB-05
**Success Criteria** (what must be TRUE):

1. A user can enable or disable TRV offset auto-calibration globally from the
   Global Settings tab, and the setting persists across restarts
2. When calibration is enabled and a room has both a reference temperature
   sensor and a compatible TRV, the coordinator periodically applies an offset
   so the TRV's reported temperature converges toward the reference sensor
   reading
3. Rooms whose TRV does not support offset adjustment (no `temperature_offset`
   attribute / no `tado_x.set_temperature_offset` service) are skipped with no
   error or log spam
4. Rooms without a reference temperature sensor configured are skipped — no
   offset is ever applied to them
5. An offset is applied only when the measured delta exceeds the configurable
   threshold (default 0.5°C), so small fluctuations do not cause repeated
   offset changes

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 7 → 8 → 9 (Phase 9 may run in parallel with
7-8 — it shares no requirements or files with the scheduling feature).

| Phase                                | Milestone | Plans Complete | Status      | Completed  |
| ------------------------------------ | --------- | -------------- | ----------- | ---------- |
| 1. Foundation                        | v1.0      | 3/3            | Complete    | 2026-05-16 |
| 2. Backend Engines & Coordinator     | v1.0      | 2/2            | Complete    | 2026-05-17 |
| 3. WebSocket API & Frontend Panel    | v1.0      | 9/9            | Complete    | 2026-05-21 |
| 4. Zone Data Model & Storage         | v1.1      | 2/2            | Complete    | 2026-05-27 |
| 5. Zone CRUD & Evaluation Engine     | v1.1      | 3/3            | Complete    | 2026-05-27 |
| 6. Zone & Room Assignment UI         | v1.1      | 4/4            | Complete    | 2026-05-28 |
| 7. Even/Odd Week Scheduling — Backend | v1.2     | 2/2 | Complete   | 2026-05-29 |
| 8. Even/Odd Week Scheduling — Frontend | v1.2    | 0/TBD          | Not started | -          |
| 9. TRV Temperature Offset Auto-Calibration | v1.2 | 0/TBD         | Not started | -          |
