# Phase 16: Presence & Heating Log Traces - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Introduce a full domain model refactor (Zone, Person, Room, TRV classes) that
cleanly encapsulates heating state, and emit structured log lines from within
these classes on every presence transition, zone state change, and TRV
temperature write.

**In scope:**

- New `zone.py` — `Zone` class with `ZoneMode` state machine (concrete
  subclasses `ZoneModeOff`, `ZoneModeTimeProgram`, `ZoneModeProgramPresences`);
  `Zone.change_mode(new_mode, reason)` applies mode and logs the transition
- New `person.py` — `Person` class with `PersonMode` state machine (concrete
  subclasses `PersonModeScheduled`, `PersonModeHA`, `PersonModeCalendar`,
  `PersonModeForcePresent`, `PersonModeForceAbsent`); `Person.change_mode(new_mode,
  reason)` applies mode and logs the transition; `Person._last_home` tracks
  last presence result for anti-spam
- New `room.py` — `Room` as a plain class (not a state machine). Owns: TRV
  list, preheat state, calibration state. Delegates temperature resolution to
  its Zone. Pre-heat and calibration are methods on Room (not per-state).
  Pre-heat logic is on the Room base class, shared across all zone modes.
- New `trv.py` — `TRV` class with async methods `push_temperature(temp)`,
  `push_off(frost_temp)`, `calibrate(offset)`. The `_push_if_changed`
  anti-flap guard moves into `TRV.push_temperature`. Owns: `entity_id`,
  `last_pushed`, `platform`, `matter_mapping`.
- `coordinator.py` refactored to instantiate and delegate to domain objects
  rather than holding raw dicts for presence / zone / preheat / calibration
  state
- Three structured log event types (formats from ROADMAP.md success criteria):
  - INFO: `presence | person=<name> home=<bool> reason=<source>`
  - INFO: `zone | zone=<name> state=<old>→<new> reason=<why>`
  - DEBUG: `heating | room=<name> temp=<T>°C zone=<zone> slot=<slot>`

**Out of scope:**

- Frontend changes — no UI impact from this refactor
- WebSocket API contract changes — same commands and payloads
- New heating logic — no behaviour changes, only structural refactor + logging
- Multi-language support — separate feature, deferred
- Boiler demand / per-zone boiler declaration — deferred to v1.4+

</domain>

<decisions>
## Implementation Decisions

### Name Resolution in Log Lines

- **D-01:** All `<name>` fields in log lines use the short suffix — strip
  the domain/prefix. Examples: `person.alice` → `alice`;
  `area_kitchen` → `kitchen` (strip `area_` prefix); `zone_main` → `main`
  (strip `zone_` prefix). Apply this rule consistently across all three log
  event types (presence, zone, heating). No config display-name lookup at
  log time — use the ID suffix.

### Zone State Machine (zone.py)

- **D-02:** Zone state log captures **both period and mode** in the `state`
  field. Format: `state=<old_period>[<old_mode>]→<new_period>[<new_mode>]`.
  Example: `state=frost[time_program]→normal[time_program_presences]`.
  When only the period changes: `state=frost[time_program]→normal[time_program]`.
  When only the mode changes: `state=normal[time_program]→normal[off]`.

- **D-03:** New `zone.py` module with:
  - `ZoneMode` abstract base class with methods `get_room_states(ts: datetime)`
    and `handle_switch(mode: str, reason: str)`.
  - Concrete subclasses: `ZoneModeOff`, `ZoneModeTimeProgram`,
    `ZoneModeProgramPresences`.
  - `Zone` class with `_current_mode: ZoneMode`, `_current_period: str`, and
    `change_mode(new_mode: ZoneMode, reason: str)` which applies the mode and
    logs `zone | zone=<name> state=<old>→<new> reason=<why>` at INFO only when
    state actually changes.
  - Anti-spam: `Zone._current_mode` and `Zone._current_period` store last-logged
    state; log fires only when these change. No separate log guard needed.

### Person State Machine (person.py)

- **D-04:** New `person.py` module with:
  - `PersonMode` abstract base class with method `is_present(ts: datetime, **ctx)`.
  - Concrete subclasses: `PersonModeScheduled`, `PersonModeHA`,
    `PersonModeCalendar`, `PersonModeForcePresent`, `PersonModeForceAbsent`.
  - `Person` class with `_current_mode: PersonMode`, `_last_home: bool | None`,
    and `change_mode(new_mode: PersonMode, reason: str)` for mode transitions.
  - `Person.evaluate(ts, **ctx) -> bool` calls `_current_mode.is_present(ts,
    **ctx)`, compares result to `_last_home`, and logs
    `presence | person=<name> home=<bool> reason=<source>` at INFO only when
    the result flips. Updates `_last_home`.
  - Anti-spam: `Person._last_home` tracks last-logged presence result; log
    fires only when the result changes (present → absent or vice versa).

### Room Class (room.py)

- **D-05:** New `room.py` module with `Room` as a plain class (no state
  machine). `Room` owns:
  - `area_id: str`
  - `trv_list: list[TRV]`
  - Preheat state (migrated from coordinator's `_preheat_in_progress` dict)
  - Calibration state (migrated from coordinator's calibration tracking)
  - Methods: `compute_preheat(zone, ts)`, `record_preheat_sample(...)`,
    `calibrate_trvs(hass, ...)`.
  - Pre-heat logic lives on `Room` (not on a per-state subclass) — it is
    common to all zone modes as specified by the user.
  - Temperature resolution delegates to the assigned Zone:
    `zone.get_room_states(ts)`.

### TRV Class (trv.py)

- **D-06:** New `trv.py` module with `TRV` class:
  - Owns: `entity_id: str`, `last_pushed: float | str | None`, `platform: str`,
    `matter_mapping: list[str] | None`.
  - Async methods: `push_temperature(hass, desired_temp: float)`,
    `push_off(hass, frost_temp: float)`, `calibrate(hass, offset: float)`.
  - The `_push_if_changed` anti-flap guard moves into `TRV.push_temperature`.
    Log line `heating | room=<name> temp=<T>°C zone=<zone> slot=<slot>` at
    DEBUG fires inside `push_temperature` only when `last_pushed != desired_temp`
    (i.e., a real setpoint change). The room name and zone name are passed as
    parameters to `push_temperature` for the log context.

### Module Layout

- **D-07:** Four new modules in `custom_components/climate_manager/`:
  `zone.py`, `person.py`, `room.py`, `trv.py`. Coordinator imports all four
  and delegates. One file per domain object — independently testable.

### Reason Field Content

- **D-08:** Presence log `reason=<source>`: mode name only — `reason=scheduled`,
  `reason=ha`, `reason=calendar`, `reason=force_present`, `reason=force_absent`.
  Simple, greppable.

- **D-09:** Zone state change `reason=<why>`: trigger + detail. Examples:
  `reason=time_program:normal→22:00` (period changed by schedule),
  `reason=user:time_program→off` (WS mode change from panel),
  `reason=presence:override` (presence pushed room to higher setpoint).
  More context than just trigger type to aid diagnosis.

### Anti-spam

- **D-10:** Domain object state is sufficient for anti-spam. No separate
  log-state guard dict needed. Zone logs on `_current_mode` / `_current_period`
  change. Person logs on `_last_home` flip. TRV logs on `last_pushed` change.

- **D-11:** TRV heating log fires only when the setpoint actually changes
  (`last_pushed != desired_temp`). Startup push does fire (intentional —
  useful for diagnosing initial state). Repeated identical setpoints produce
  no log line.

### Reviewed Todos (not folded)

- **Add multi-language support (2026-05-29):** Out of scope for Phase 16.
  Deferred per REQUIREMENTS.md.
- **Boiler demand control (2026-05-27):** Deferred to v1.4+.
- **Per-zone boiler declaration (2026-05-27):** Deferred to v1.4+.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements

- `.planning/REQUIREMENTS.md` §OBS-01 — the single requirement for structured
  log lines; defines the three log formats and anti-spam rule

### Roadmap

- `.planning/ROADMAP.md` §Phase 16 — success criteria and exact log format
  strings that the implementation must match

### Key Source Files — Backend (files to refactor)

- `custom_components/climate_manager/coordinator.py` — the monolithic class
  being decomposed; read the full evaluate cycle, `_compute_desired_temps`,
  `_apply_presence_overrides`, `_async_preheat`, `_async_calibrate`,
  `_push_temperatures`, `_push_if_changed`, `_push_safely`,
  `_compute_present_persons` before splitting into domain objects
- `custom_components/climate_manager/schedule.py` — `resolve_presence()`,
  `resolve_calendar_presence()` — these move into `PersonMode` subclasses
  (or are called from them)
- `custom_components/climate_manager/const.py` — `MODE_OFF`, `MODE_TIME_PROGRAM`,
  `MODE_TIME_PROGRAM_PRESENCES`, `PRESENCE_*` constants, `DEFAULT_CONFIG` —
  read before defining ZoneMode/PersonMode subclass names
- `custom_components/climate_manager/storage.py` — `Store` usage pattern,
  `_save_preheat_store` — preheat store moves to Room responsibility

### Established Patterns (prior phases)

- Phase 15 CONTEXT.md D-01..D-03 — compat shim pattern in storage.py; no
  change needed here (domain objects read same config dict)
- Phase 14 CONTEXT.md — `_resolve_zone_config` and per-zone evaluation logic
  that moves into `Zone.get_room_states(ts)`
- Phase 12 CONTEXT.md D-06..D-09 — preheat sample storage + convergence
  tracking that moves into `Room`
- Phase 9 CONTEXT.md D-01..D-04 — calibration pass structure that moves into
  `Room.calibrate_trvs` and `TRV.calibrate`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `coordinator.py:_push_if_changed` (lines ~1627–1668) — anti-flap guard +
  push logic moves verbatim into `TRV.push_temperature`; the only change is
  the log line added before `set_trv_temperature` call
- `coordinator.py:_compute_present_persons` (lines ~1316–1377) — per-mode
  branches map directly to `PersonMode.is_present()` implementations in each
  subclass
- `coordinator.py:_resolve_zone_config` (lines ~1295–1314) — maps to
  `Zone._current_mode` lookup; after refactor this method is replaced by
  `zone.get_room_states(ts)`
- `coordinator.py:_async_preheat` / `_async_preheat_room` (lines ~572+) —
  moves into `Room.compute_preheat` and `Room.record_preheat_sample`
- `coordinator.py:_async_calibrate` (lines ~880+) — moves into
  `Room.calibrate_trvs` / `TRV.calibrate`

### Established Patterns

- `_LOGGER = logging.getLogger(__name__)` per module — each new module
  (`zone.py`, `person.py`, `room.py`, `trv.py`) has its own `_LOGGER`
- Push-on-change anti-flap: `if last is not None and last == desired_temp:
  return` — preserved in `TRV.push_temperature`
- D-03 manual override hold (coordinator.py ~1657–1665): check
  `float(reported) != last` — preserved in `TRV.push_temperature`

### Integration Points

- Coordinator `__init__` will instantiate `Zone`, `Person`, `Room`, and `TRV`
  objects from stored config on `async_setup_entry`
- `websocket.py` handlers update Zone/Person config via the same
  `set_zone_config` / `set_person_config` pattern — after refactor, WS
  handlers call `zone.change_mode()` or `person.change_mode()` instead of
  mutating the config dict directly
- Tests currently mock coordinator internals (dict access) — will need updating
  to mock domain object methods; prior test structure in `tests/` is the
  reference

</code_context>

<specifics>
## Specific Ideas

- Pre-heat logic must live on the `Room` base class (not per-state), because
  it is common to all zone modes — explicitly confirmed by the user.
- The `Zone.change_mode()` log line fires from within the domain object,
  not from the coordinator. Same for `Person.evaluate()`. This centralizes
  all logging decisions inside the domain model.
- `TRV.push_temperature` receives room name and zone name as string parameters
  for the DEBUG log line — the TRV itself doesn't know which room it belongs
  to, so the caller (Room or coordinator) passes those strings.
- Log format from ROADMAP.md success criteria is the contract — downstream
  must match exactly: `presence | person=<name> home=<bool> reason=<source>`,
  `zone | zone=<name> state=<old>→<new> reason=<why>`,
  `heating | room=<name> temp=<T>°C zone=<zone> slot=<slot>`.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-language support** — separate feature, deferred per REQUIREMENTS.md.
- **Boiler demand control** — deferred to v1.4+.
- **Per-zone boiler declaration** — deferred to v1.4+.
- **Full state machine for WS API handlers** — WS handlers still mutate config
  dicts; the domain objects absorb state, but WS persistence layer is
  unchanged for Phase 16. A future phase could drive all mutations through
  domain objects exclusively.

</deferred>

---

*Phase: 16-presence-heating-log-traces*
*Context gathered: 2026-06-04*
