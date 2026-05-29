# Requirements — v1.2 Presence & Calibration

## Active Requirements

### Even/Odd Week Presence Scheduling

- [ ] **SCHED-01**: User can set a person's schedule type to "single" (default,
  current behaviour) or "even/odd" (two independent weekly schedules)
- [ ] **SCHED-02**: When schedule type is "even/odd", the backend evaluator selects
  the correct schedule based on ISO week parity at evaluation time
- [ ] **SCHED-03**: The storage schema for persons gains `schedule_type`,
  `schedule_even`, and `schedule_odd` fields; existing persons without these
  fields default to `schedule_type: "single"` (no migration needed — additive)
- [ ] **SCHED-04**: The persons UI shows a week-switcher toggle (Even / Odd) in the
  presence time-bar only when `schedule_type == "even_odd"`; editing affects
  only the selected week's schedule
- [ ] **SCHED-05**: Switching a person from "single" to "even/odd" seeds both
  `schedule_even` and `schedule_odd` from the existing `schedule` so no data is
  lost
- [ ] **SCHED-06**: Switching back from "even/odd" to "single" preserves `schedule`
  unchanged (even week used as canonical)

### TRV Temperature Offset Auto-Calibration

- [ ] **CALIB-01**: User can enable/disable TRV offset auto-calibration globally
  from the Global Settings tab
- [ ] **CALIB-02**: When enabled, the coordinator periodically computes the delta
  between the room's reference temperature sensor and the TRV's reported
  `current_temperature`, then calls the offset service if the TRV supports it
- [ ] **CALIB-03**: The calibration guard detects whether a TRV supports offset
  adjustment (by checking for a `temperature_offset` attribute or the
  `tado_x.set_temperature_offset` service); rooms without a compatible TRV are
  silently skipped
- [ ] **CALIB-04**: A configurable minimum delta threshold (default 0.5°C) prevents
  jitter — offsets are only applied when the measured delta exceeds the
  threshold
- [ ] **CALIB-05**: Calibration only runs when the room has a reference temperature
  sensor configured; rooms without a sensor are silently skipped

## Future Requirements

- Per-zone temperature setpoints (currently global only) — deferred to v2
- Calendar-based presence (iCal, Pronote) — deferred to v2
- GPS / HA zone-based presence — deferred to v2
- Adaptive pre-heat — deferred to v2
- Multi-language support — deferred

## Out of Scope

- Tado X proprietary API — all TRV control via standard HA `climate` entity and
  named services only (no brand-specific HTTP calls)
- Boiler demand control — deferred to separate milestone
- Pronote / external presence sources — deferred to v2
- Holiday / specific-period overrides — deferred to v2

## Traceability

| REQ-ID   | Phase    | Plan         |
| -------- | -------- | ------------ |
| SCHED-01 | Phase 7  | 07-01, 07-02 |
| SCHED-02 | Phase 7  | 07-01        |
| SCHED-03 | Phase 7  | 07-01        |
| SCHED-04 | Phase 8  | TBD          |
| SCHED-05 | Phase 7  | 07-02        |
| SCHED-06 | Phase 7  | 07-02        |
| CALIB-01 | Phase 9  | TBD          |
| CALIB-02 | Phase 9  | TBD          |
| CALIB-03 | Phase 9  | TBD          |
| CALIB-04 | Phase 9  | TBD          |
| CALIB-05 | Phase 9  | TBD          |
