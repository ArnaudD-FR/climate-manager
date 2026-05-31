# Requirements — v1.3 Calendar Presence & Pre-heat

## Active Requirements

### Calendar Presence Sources

- [ ] **CAL-01**: User can configure a person's presence source as "Pronote"
  with a school URL, username, and password; the integration fetches the
  school timetable and marks the person absent during school slots and present
  during free/holiday periods
- [ ] **CAL-02**: The Pronote timetable is cached with a configurable TTL
  (default 6h) to avoid IP bans; on fetch failure the person falls back to
  their manual schedule without error or log spam
- [ ] **CAL-03**: User can configure a person's presence source as "iCal" with
  an ICS URL and optional keyword filter; events matching the keyword mark the
  person absent, all other times are present
- [ ] **CAL-04**: The iCal calendar is fetched and cached with a configurable
  TTL (default 1h); RRULE recurring events are expanded correctly using
  `recurring-ical-events`; DATE vs DATETIME types and timezone-naive events
  are handled safely; on fetch failure the person falls back to manual schedule

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
  calendar presence sources (schedule_even, schedule_odd, Pronote, iCal
  timetables are all valid sources for next-transition computation)

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

## Future Requirements

- Per-zone boiler declaration for accurate pre-heat flow temp normalisation —
  deferred to v1.4 or later
- Pronote session renewal and multi-account support — deferred
- iCal event classification beyond keyword matching (richer rules) — deferred
  to v1.4
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

| REQ-ID     | Phase   | Plan |
| ---------- | ------- | ---- |
| CAL-01     | Phase 11 | TBD  |
| CAL-02     | Phase 11 | TBD  |
| CAL-03     | Phase 11 | TBD  |
| CAL-04     | Phase 11 | TBD  |
| PREHEAT-01 | Phase 12 | TBD  |
| PREHEAT-02 | Phase 12 | TBD  |
| PREHEAT-03 | Phase 12 | TBD  |
| PREHEAT-04 | Phase 12 | TBD  |
| PREHEAT-05 | Phase 12 | TBD  |
| MCALIB-01  | Phase 13 | TBD  |
| MCALIB-02  | Phase 13 | TBD  |
| UI-01      | Phase 10 | TBD  |
| UI-02      | Phase 10 | TBD  |
