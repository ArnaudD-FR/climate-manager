# Requirements — v1.3 Calendar Presence & Pre-heat

## Active Requirements

### Calendar Presence Sources

- [ ] **CAL-01**: A person can be set to "Calendar" presence mode in the
  panel. A `calendar.*` HA entity is configured as the presence source.
  When an event is active on that calendar, the `event_means` field
  determines whether the person is absent (default) or present. When no
  event is active, the inverse applies. On `calendar.*` entity error or
  unavailability, the person falls back to absent without log spam.
- [ ] **CAL-02**: The coordinator fetches `get_events` for each unique
  `calendar.*` entity ID exactly once per `async_evaluate` cycle, caching
  results in `_calendar_cache`. Multiple persons sharing a calendar entity
  share the same fetch result within the cycle. On fetch failure, the entity
  falls back to an empty event list with a single WARNING log.
- [ ] **CAL-03**: In Scheduled mode, individual periods can have state
  `"calendar"` instead of `"present"` / `"absent"`. When active, the period
  resolves via the `calendar_config` attached to that period (entity_id +
  event_means). Not recursive: a calendar period inside a top-level calendar
  mode is not supported.
- [ ] **CAL-04**: A per-person `wakeup_advance_minutes` value (default 60,
  range 0–480) causes the coordinator to treat a calendar-absent person as
  present when the active event is scheduled to end within
  `wakeup_advance_minutes` minutes, enabling rooms to pre-heat before the
  person returns.

### Predictive Pre-heat

- [ ] **PREHEAT-01**: User can enable or disable predictive pre-heat per room
  from the Rooms tab, with a configurable maximum lead time (default 120 min)
- [ ] **PREHEAT-02**: When enabled, the coordinator starts heating the room
  before the next normal or comfort period using a learned inertia factor;
  the initial lead time defaults to 60 min until inertia is learned
- [ ] **PREHEAT-03**: The integration learns each room's thermal inertia from
  observed heating cycles (convergence after 3-5 complete cycles); heating
  samples where the target was not reached within the cap are excluded from
  learning to avoid model corruption
- [ ] **PREHEAT-04**: When a room is actively pre-heating, its status in the
  panel shows "Pre-heating (→ XX.X°C)"; rooms where pre-heat is suppressed
  because the presence source is live/reactive (no scheduled transitions)
  show a warning: "Pre-heat disabled — presence cannot be scheduled"
- [ ] **PREHEAT-05**: Pre-heat is compatible with even/odd week scheduling and
  calendar presence sources (schedule_even, schedule_odd, and `calendar.*`
  HA entity-backed calendar periods are all valid sources for
  next-transition computation)

### Matter→Tado X Real-Time Calibration

- [ ] **MCALIB-01**: User can configure a room-level mapping from a Matter TRV
  entity to its Tado X device; when mapped, the calibration pass fires
  immediately on Matter entity `state_changed` rather than waiting for the
  polling interval, enabling sub-minute calibration responsiveness
- [ ] **MCALIB-02**: Matter state_changed listeners are registered and
  cancelled via the existing `cancel_registry_listeners` lifecycle pattern;
  mapping removal or integration reload does not accumulate ghost listeners

### Presence Mode UI

- [ ] **UI-01**: The "HA" presence mode option is hidden in the mode picker
  for persons whose HA person entity has no linked device trackers
  (`attributes.device_trackers` is empty or absent)
- [ ] **UI-02**: The "HA" presence mode is renamed to "Live tracking" (or
  equivalent clear label) everywhere it appears in the panel

### Architecture Cleanup

- [ ] **ARCH-01**: Default Zone is stored as a first-class `ZoneConfig` under
  a single `default_zone` key; `global_mode`, `global_time_program`,
  `default_zone_name`, and `default_zone_preheat_enabled` flat keys are
  removed and migrated on load
- [ ] **ARCH-02**: `room_mode: custom` is removed from coordinator, storage,
  and frontend; rooms that previously used custom scheduling are migrated to
  a dedicated single-room zone with the same schedule

### Observability

- [ ] **OBS-01**: Structured log lines are emitted at INFO level on presence
  transitions and zone state changes, and at DEBUG level on each TRV
  set_temperature call; repeated identical states do not produce duplicate lines

### Documentation

- [ ] **DOC-01**: Five person-scheduling use-case documents with screenshots
  exist under `docs/use-cases/`; `make screenshots` captures all scenario
  screenshots cleanly

## Future Requirements

- Per-zone boiler declaration for accurate pre-heat flow temp normalisation —
  deferred to v1.4 or later
- Multiple `calendar.*` sources per person — deferred (v1.3 ships one entity
  per person only)
- Adaptive pre-heat lead time via inertia learning — Phase 12
  (`preheat_lead_minutes` is a fixed value in Phase 11)
- Predictive pre-heat post-convergence threshold tuning — monitor post-v1.3
- Holiday/specific-period overrides (manual) — deferred to v2

## Out of Scope

- GPS-based presence detection — overkill, removed from consideration
- HA zone-based presence — already implemented via "HA" mode (`person.*`
  home/away state)
- Per-zone temperature setpoints — deferred
- Boiler demand control — deferred to v2
- Multi-language support — deferred

## Traceability

| REQ-ID     | Phase    | Plan                          |
| ---------- | -------- | ----------------------------- |
| CAL-01     | Phase 11 | 11-01, 11-02, 11-03, 11-04   |
| CAL-02     | Phase 11 | 11-02                         |
| CAL-03     | Phase 11 | 11-01, 11-04                  |
| CAL-04     | Phase 11 | 11-01, 11-03, 11-04           |
| PREHEAT-01 | Phase 12 | 12-03, 12-04                  |
| PREHEAT-02 | Phase 12 | 12-01, 12-02                  |
| PREHEAT-03 | Phase 12 | 12-02                         |
| PREHEAT-04 | Phase 12 | 12-02, 12-03, 12-04          |
| PREHEAT-05 | Phase 12 | 12-01                         |
| MCALIB-01  | Phase 13 | TBD                           |
| MCALIB-02  | Phase 13 | TBD                           |
| UI-01      | Phase 10 | 10-01, 10-02                  |
| UI-02      | Phase 10 | 10-01, 10-02                  |
