# Requirements

**Project:** Climate Manager
**Version:** v1
**Source:** specs.md + questioning session (2026-05-15)

---

## v1 Requirements

### Global Mode & Temperature (GLOBAL)

- [ ] **GLOBAL-01**: User can set the global mode to one of: Off, Time program, Time program & presences
- [ ] **GLOBAL-02**: In Off mode, all rooms are set to frost protection temperature unless overridden by a specific period
- [ ] **GLOBAL-03**: User can configure default temperatures for each period mode: Frost protection (default 7°C), Reduced (default 18°C), Normal (default 20°C), Comfort (default 22°C)

### Time Programs (SCHED)

- [ ] **SCHED-01**: User can define a global time program made of weekday groups, each with a set of week days and a sequence of time periods
- [ ] **SCHED-02**: Each time period in a program is defined by a start time and a period mode (Frost protection / Reduced / Normal / Comfort)
- [ ] **SCHED-03**: The last time period of the day ends at midnight; the first period of the next weekday group takes over
- [ ] **SCHED-04**: Each calendar day must appear in at most one weekday group within a time program (validated at save time)
- [ ] **SCHED-05**: User can define a per-room time program that overrides the global time program for that room; if not defined, the room inherits the global time program

### Rooms (ROOM)

- [ ] **ROOM-01**: User can configure rooms; each room has a name and one or more associated HA climate entity IDs
- [ ] **ROOM-02**: Rooms without a climate entity association are ignored by the system
- [ ] **ROOM-03**: When a room has multiple TRVs and one becomes unavailable, the system continues sending commands to the remaining available TRVs

### Person Presence (PERSON)

- [ ] **PERSON-01**: User can configure persons; each person has a presence mode: Automatic, Present, or Absent
- [ ] **PERSON-02**: In Present mode, the person is always considered present regardless of time or schedule
- [ ] **PERSON-03**: In Absent mode, the person is always considered absent regardless of time or schedule
- [ ] **PERSON-04**: In Automatic mode, presence is determined by a periodic schedule (weekday groups with time periods marked present/absent)
- [ ] **PERSON-05**: In Automatic mode with no schedule periods configured, the person defaults to absent
- [ ] **PERSON-06**: Each person has a set of associated rooms; when the person is present, those rooms are warmed up
- [ ] **PERSON-07**: In "Time program & presences" mode, when a person is present, the room heats from the start of the first Normal or Comfort period of the day to the end of the last Normal or Comfort period of the day
- [ ] **PERSON-08**: In "Time program & presences" mode, when a person is present and a Reduced or Frost protection period falls between two Normal/Comfort periods, the room maintains the temperature of the preceding Normal/Comfort period (no cool-down during the gap)
- [ ] **PERSON-09**: In "Time program & presences" mode, when a person is absent, the room is set to Reduced temperature

### UI Panel (UI)

- [ ] **UI-01**: The integration provides a full Lovelace dashboard panel (not a custom card) accessible from the HA sidebar
- [ ] **UI-02**: The panel has a Global Settings section: set global mode, configure default temperatures for each period mode, define the global time program
- [ ] **UI-03**: The panel has a Rooms section: for each room, set the per-room time program (or inherit global), manage associated climate entities
- [ ] **UI-04**: The panel has a Persons section: for each person, set presence mode (Automatic/Present/Absent), manage room associations, configure the periodic presence schedule

### Technical Foundation (INFRA)

- [ ] **INFRA-01**: The integration has a correct HA custom integration structure (manifest.json with required fields, config flow, no external PyPI dependencies); deploys via SSH/rsync to `/config/custom_components/`; HACS publishing is out of scope for v1
- [ ] **INFRA-02**: All configuration persists across HA restarts (stored via homeassistant.helpers.storage.Store)
- [ ] **INFRA-03**: On HA startup, the integration recomputes the active period from the current time and immediately applies the correct temperature to all managed TRVs (no reliance on state restore)
- [ ] **INFRA-04**: TRVs are controlled via two sequential service calls: climate.set_hvac_mode (heat) then climate.set_temperature — auto mode is never used
- [ ] **INFRA-05**: The integration handles DST transitions correctly by always deriving the active period from the current wall-clock time (dt_util.now())

---

## v2 Requirements (deferred)

- Specific periods: Holidays at home (normal mode from first period), Holidays (frost protection + warm-up to reduced before end)
- Calendar-based presence detection (iCal, Pronote)
- GPS / HA zone-based presence detection

---

## Out of Scope

- TRV brand-specific APIs — standard HA climate entity interface only
- YAML-only configuration — all config through the Lovelace panel
- Energy reporting / consumption tracking — use HA's built-in energy dashboard
- Window/door open detection — use dedicated integrations (e.g., Better Thermostat)
- Predictive pre-heat — requires per-room thermal model
- Multiple simultaneous time programs per room — one active program per room

---

## Key Clarifications (from specs use cases)

**Use case 1 — Time program & presences mode (PERSON-07, PERSON-08, PERSON-09):**
When a person is present, the room is heated continuously from the first Normal/Comfort period of the day to the last Normal/Comfort period. Any Reduced or Frost protection period sandwiched between two Normal/Comfort periods is overridden: the room holds the temperature of the preceding Normal/Comfort period. This means presence "fills in the gaps" — the room stays warm throughout the occupied window without cooling down during intermediate reduced periods.

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-04 | Phase 1 | Pending |
| ROOM-01 | Phase 1 | Pending |
| ROOM-02 | Phase 1 | Pending |
| ROOM-03 | Phase 1 | Pending |
| GLOBAL-01 | Phase 2 | Pending |
| GLOBAL-02 | Phase 2 | Pending |
| GLOBAL-03 | Phase 2 | Pending |
| SCHED-01 | Phase 2 | Pending |
| SCHED-02 | Phase 2 | Pending |
| SCHED-03 | Phase 2 | Pending |
| SCHED-04 | Phase 2 | Pending |
| SCHED-05 | Phase 2 | Pending |
| PERSON-01 | Phase 2 | Pending |
| PERSON-02 | Phase 2 | Pending |
| PERSON-03 | Phase 2 | Pending |
| PERSON-04 | Phase 2 | Pending |
| PERSON-05 | Phase 2 | Pending |
| PERSON-06 | Phase 2 | Pending |
| PERSON-07 | Phase 2 | Pending |
| PERSON-08 | Phase 2 | Pending |
| PERSON-09 | Phase 2 | Pending |
| INFRA-03 | Phase 2 | Pending |
| INFRA-05 | Phase 2 | Pending |
| UI-01 | Phase 3 | Pending |
| UI-02 | Phase 3 | Pending |
| UI-03 | Phase 3 | Pending |
| UI-04 | Phase 3 | Pending |
