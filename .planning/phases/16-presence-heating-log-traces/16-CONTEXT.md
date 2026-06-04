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

### EvalContext — per-cycle shared cache (eval_context.py)

- **D-02:** New `EvalContext` dataclass (in its own `eval_context.py` or at
  the top of `coordinator.py`) created once at the start of every
  `async_evaluate` call. Replaces the upfront `_prefetch_calendars` pass.
  ```python
  class EvalContext:
      now: datetime
      hass: HomeAssistant
      period_temperatures: dict[str, float]
      _calendar_cache: dict[str, list]   # entity_id → events, filled on demand
      _presence_cache: dict[str, bool]   # person_id → is_home, filled on demand

      async def calendar_events(self, entity_id: str) -> list: ...
      # fetches once per entity per cycle; subsequent calls return cached result
  ```
  Calendar events are fetched inside `PersonModeCalendar.is_present(ctx)` on
  first access; all other modes never touch the calendar. A person assigned to
  rooms in two different zones evaluates once — the second zone reads
  `ctx._presence_cache[person_id]`.

### Zone State Machine (zone.py)

- **D-03:** Zone state log captures **both period and mode** in the `state`
  field. Format: `state=<old_period>[<old_mode>]→<new_period>[<new_mode>]`.
  Example: `state=frost[time_program]→normal[time_program_presences]`.
  When only the period changes: `state=frost[time_program]→normal[time_program]`.
  When only the mode changes: `state=normal[time_program]→normal[off]`.

- **D-04:** New `zone.py` module. Key design rules:
  - `ZoneMode` is a **plain base class** (not ABC). Unimplemented overloads
    use `assert False, f"{type(self).__name__}.evaluate() not implemented"` —
    no ABC machinery.
  - `ZoneMode.__init__(self, zone: Zone)` receives a `weakref.ref[Zone]`
    (stores as `self._zone_ref`). The `zone` property dereferences it with an
    assert. ZoneMode holds **no config** — it reads `zone.time_program`,
    `zone.rooms`, etc. through the weakref at call time.
  - `time_program` lives on `Zone`, not `ZoneMode`. `ZoneMode.evaluate(ctx)`
    reads `self.zone.time_program` when needed; no config parameters on the
    method signature.
  - Concrete subclasses: `ZoneModeOff`, `ZoneModeTimeProgram`,
    `ZoneModeProgramPresences`. Each overrides `evaluate(ctx: EvalContext)`.
  - `Zone` class owns: `zone_id`, `_mode: ZoneMode`, `_time_program: dict`,
    `_rooms: list[Room]`, `_current_period: str | None`.
  - `Zone.evaluate(ctx)` delegates entirely to `self._mode.evaluate(ctx)`.
  - `Zone.change_mode(new_mode: ZoneMode, reason: str)` replaces `_mode`
    and is called by WS handlers on user config change.
  - `Zone.update_config(time_program: dict)` updates `_time_program` (plain
    setter, no logging — config change, not state transition).
  - Anti-spam: `Zone._current_period` (updated by ZoneMode.evaluate) stores
    last-logged period; log fires only when it changes.

### Person State Machine (person.py)

- **D-05:** New `person.py` module. Key design rules:
  - `PersonMode` is a **plain base class**. Unimplemented overloads use
    `assert False` — no ABC.
  - `PersonMode.__init__(self, person: Person)` receives a `weakref.ref[Person]`.
    PersonMode reads its own config through `self.person.<field>` at call time.
    No config parameters on method signatures.
  - `PersonMode.is_present(ctx: EvalContext) -> bool` — assert-guarded base.
  - `PersonMode.next_occupied_at(ctx: EvalContext) -> datetime | None` —
    base returns `None` (not overridden for HA/Force* modes). Only
    `PersonModeScheduled` and `PersonModeCalendar` override this with a real
    implementation (schedule forward-walk / calendar cache lookup).
  - Concrete subclasses: `PersonModeScheduled`, `PersonModeHA`,
    `PersonModeCalendar`, `PersonModeForcePresent`, `PersonModeForceAbsent`.
  - `Person` class owns: `person_id`, `_mode: PersonMode`, `_last_home:
    bool | None`, `room_ids: list[str]`, schedule/calendar config fields.
  - `Person.evaluate(ctx) -> bool`: checks `ctx._presence_cache` first
    (returns cached result if already evaluated this cycle); calls
    `_mode.is_present(ctx)`; logs INFO on flip; stores in `_last_home` and
    `ctx._presence_cache[person_id]`.
  - `Person.change_mode(new_mode: PersonMode, reason: str)` called by WS
    handlers.
  - `Person.next_occupied_at(ctx)` delegates to `self._mode.next_occupied_at(ctx)`.

### Room Class (room.py)

- **D-06:** New `room.py` module with `Room` as a plain class (no state
  machine). `Room` owns:
  - `area_id: str`
  - `assigned_persons: list[Person]` — Room knows its persons directly
    (populated at coordinator init from person `room_ids` config).
  - `_trv_groups: list[TRVGroup]` — logical push units (see D-07).
  - Preheat state (migrated from coordinator's `_preheat_in_progress` dict).
  - Calibration state (migrated from coordinator's calibration tracking).
  - `Room.apply_setpoint(period: str, temp: float, ctx: EvalContext)` — pushes
    temp to all TRV groups; called by ZoneMode subclasses.
  - `Room.compute_preheat(ctx)`, `Room.record_preheat_sample(...)`,
    `Room.calibrate_trvs(ctx)` — separate passes called by coordinator after
    zone evaluation.
  - Pre-heat logic lives on `Room` (not per-state) — common to all zone modes.

### TRVGroup and TRV (trv.py)

- **D-07:** New `trv.py` module with two classes:
  - **`TRVGroup`** — one logical push unit, contains one or more `TRV`
    instances. Encapsulates the tado_x/Matter dispatch that currently lives in
    `_push_temperatures` if/elif chain. `TRVGroup` is assembled at coordinator
    init from `matter_mappings` config — by construction time, each group
    contains the correct entity/entities to push to. At push time, no platform
    branching: `TRVGroup.push(temp, slot, ctx)` iterates its TRVs.
  - **`TRV`** — owns `entity_id`, `last_pushed`, `platform`. Async methods:
    `push_temperature(temp, *, room_name, zone_name, slot, ctx)`,
    `push_off(frost_temp, ctx)`, `calibrate(offset, ctx)`. The `_push_if_changed`
    anti-flap guard and D-03 manual-override hold move verbatim into
    `push_temperature`. DEBUG log fires only when `last_pushed != temp`.

### Module Layout

- **D-08:** Five new/refactored modules in `custom_components/climate_manager/`:
  `eval_context.py` (or inline in coordinator), `zone.py`, `person.py`,
  `room.py`, `trv.py`. One concept per file — independently testable.

### Evaluate Call Flow

- **D-09:** `coordinator.async_evaluate()` becomes:
  ```
  ctx = EvalContext(now, hass, period_temperatures)
  for zone in self._zones.values():
      await zone.evaluate(ctx)          # zone delegates to ZoneMode
  # after zone passes:
  for room in self._rooms.values():
      await room.compute_preheat(ctx)   # pre-heat pass
      await room.calibrate_trvs(ctx)    # calibration pass
  ```
  ZoneMode subclasses own all per-room dispatch:
  - `ZoneModeOff.evaluate(ctx)`: iterates `self.zone.rooms`, calls
    `room.apply_setpoint("frost_protection", frost_temp, ctx)` for each.
  - `ZoneModeTimeProgram.evaluate(ctx)`: calls `evaluate_schedule(
    zone.time_program, ctx.now)`, logs period change, iterates `zone.rooms`,
    calls `room.apply_setpoint(period, temp, ctx)`.
  - `ZoneModeProgramPresences.evaluate(ctx)`: same baseline as above; then
    for each room, iterates `room.assigned_persons`, calls
    `await person.evaluate(ctx)` (cached in ctx), passes `any_present` to
    `compute_occupied_temp`, calls `room.apply_setpoint(period, temp, ctx)`.
  `room.apply_setpoint` iterates `room._trv_groups`; each group iterates its
  TRVs; each `TRV.push_temperature` does the anti-flap check and emits the
  DEBUG heating log.

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

- Pre-heat logic must live on `Room` (not per-state subclass) — common to
  all zone modes; confirmed explicitly.
- `ZoneMode` and `PersonMode` use `assert False` for unimplemented overloads,
  not Python ABC. This gives a clear runtime crash rather than silent
  `NotImplementedError`.
- `ZoneMode` and `PersonMode` constructors each take a weakref to their owner
  (`Zone` / `Person`). They read config through the weakref at call time —
  no config parameters on method signatures, no config stored on the mode.
- `Zone.update_config(time_program)` is a plain config setter (no logging).
  Mode transitions go through `Zone.change_mode(new_mode, reason)`.
- `Person.evaluate(ctx)` checks `ctx._presence_cache` first — a person
  assigned to rooms in two zones evaluates exactly once per tick.
- `TRVGroup` is assembled at init from `matter_mappings` config. At push time
  there is no platform branching — the correct TRVs are already in the group.
  `TRV.push_temperature` receives `room_name` and `zone_name` as keyword args
  for the DEBUG log.
- Log format from ROADMAP.md is the contract — match exactly:
  `presence | person=<name> home=<bool> reason=<source>`,
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
