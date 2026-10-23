# Climate Manager — Architecture Reference

> Keep this document current. Refresh it before completing every milestone.

## Overview

Climate Manager is a Home Assistant custom integration with two layers:

- **Python backend** (`custom_components/climate_manager/`) — all control logic,
  persistence, schedule evaluation, and WebSocket API. Since Phase 16 the
  control logic is organised as a **domain model** (`EvalContext`, `Zone`/
  `ZoneMode`, `Person`/`PersonMode`, `Room`, `TRV`/`TRVGroup`); the coordinator
  builds this object graph and delegates each evaluation cycle to it.
- **Frontend panel** (`frontend/`) — Lit 3 / TypeScript SPA compiled to a single
  `custom_components/climate_manager/www/panel.js` bundle

The two layers communicate exclusively over HA's WebSocket API. No REST
endpoints are used.

---

## Python Backend

### Entry point — `__init__.py`

`async_setup_entry` wires the integration in order:

1. Construct `ClimateManagerStore` and load merged config
2. Run discovery (rooms, persons, room sensors)
3. Assign all to `entry.runtime_data` (typed `ClimateManagerData` dataclass)
4. Wire the pre-heat `PreheatStore` and load samples + running runs
5. Construct `ClimateManagerCoordinator` and run immediate evaluation (restart
   recovery — INFRA-03)
6. Forward the `binary_sensor` + `select` + `sensor` platforms (see
   [HA entities](#ha-entities)) and register the per-cycle `async_sync_devices`
   listener
7. Register minute-polling scheduler via `async_track_time_interval`
8. Register 19 WebSocket commands via `cm_ws.async_register_commands`
9. Serve `www/` directory as static path (`cache_headers=False`)
10. Register sidebar panel via `panel_custom.async_register_panel`
11. Register entity/device registry listeners for live room re-discovery

`async_unload_entry` cancels the scheduler and registry listeners before
unloading the `select` / `sensor` platforms.

`ClimateManagerData` is a typed dataclass stored on `entry.runtime_data`. The
global `hass.data` dict is never used.

---

### Configuration schema — `const.py`

Single source of truth for all constants and `DEFAULT_CONFIG`.

| Concept             | Values                                                         |
| ------------------- | -------------------------------------------------------------- |
| Zone modes          | `off`, `time_program`, `time_program_presences`                |
| Period temperatures | `frost_protection`, `reduced`, `normal`, `comfort`             |
| Presence modes      | `scheduled`, `force_present`, `force_absent`, `ha`, `calendar` |

**Zone model**: Default Zone (room has no `zone_id`) + custom zones (UUID string
keys in `config["zones"]`). Sparse — never store `zone_id: null`. The mode is a
property of the **zone**, not the room — Phase 15 (D-07) removed room-level
modes entirely; every room follows its owning zone's mode and schedule.

Default temperatures: frost=5°C, reduced=18°C, normal=20°C, comfort=22°C.

---

### Storage — `storage.py`

`ClimateManagerStore` wraps `homeassistant.helpers.storage.Store`.

- **Key**: `climate_manager`, schema version 2
- **Load**: sparse-merge stored data over `DEFAULT_CONFIG` deep copy;
  `period_temperatures` merges key-by-key; `rooms`/`persons`/`zones` replace
  wholesale. Post-merge fills any empty day with default schedule periods. Runs
  field migrations (presence mode renames, `preheat_lead_minutes` →
  `wakeup_advance_minutes`).
- **Save**: calls `validate_zone_assignment()` before every write.

Pre-heat inertia persists separately under key `climate_manager_preheat`
(`preheat.PreheatStore`, version 2, not `ClimateManagerStore`):

```text
{"rooms": {area_id: {"samples": [sample, ...], "run": run | null}}}
sample = {timestamp, duration_minutes, start_temp, target_temp, rate, censored}
run    = {start_time, start_temp, target_temp, until, converged, measuring}
```

The v1 layout (`{area_id: [{duration_minutes, timestamp}]}`) has no start
temperature, so the migration drops it and learning starts over.

---

### Control loop — `coordinator.py`

Since Phase 16 the coordinator is a thin orchestrator over the domain model (see
[Domain model](#domain-model) below). It owns two responsibilities: building the
object graph and driving each evaluation cycle.

**`_build_domain_objects(config)`** constructs the `Zone` / `Person` / `Room` /
`TRVGroup` graph from `runtime_config`. It is called on first evaluate and again
whenever a WS handler changes the config — detected by a cheap structural
**fingerprint** (`_config_fingerprint`); an unchanged fingerprint skips the
rebuild. The fingerprint also covers the discovered `runtime_data.rooms`, so a
registry refresh rebuilds too. On rebuild, anti-spam log state is **carried
forward** from the old objects (`Zone._current_period`/`_current_mode_name`,
`Person._last_home`) so a config edit does not replay log lines, and so is each
`TRV`'s push state (`last_pushed`, `last_slot`) so a config edit does not
re-force a push to every valve.

`ClimateManagerCoordinator.async_evaluate()` runs on startup, every minute,
after WS mutations and when a TRV comes back online. Only **one evaluation runs
at a time** (`_eval_lock`): a call arriving during a run returns immediately and
sets `_eval_requested`, which triggers exactly one catch-up run — stalled runs
never pile up and no trigger is lost. Each run is `_async_evaluate_once()`:

```text
1. now = dt_util.now(); rebuild domain objects if fingerprint changed
   (or an entity left out of the graph has appeared)
2. ctx = EvalContext(now, hass, period_temperatures)   # per-cycle cache
3. for person in persons: await person.evaluate(ctx)   # fills presence cache
     → Person emits OBS-01 INFO log on home/away flip
4. gather(zone.evaluate(ctx) for every zone)           # all zones at once
     → ZoneMode.evaluate resolves the period and every room's setpoint,
       then gather(room.apply_setpoint(period, temp, ctx) for its rooms)
         → TRVGroup.push → gather(TRV.push_temperature)  # every valve
     → a running pre-heat overrides a lower scheduled setpoint
     → Zone emits OBS-01 INFO log on (period, mode) change
5. per-room pre-heat pass (Room.compute_preheat)
5b. boiler pass (Boiler.evaluate) — after pre-heat so a pre-heat started this
    tick already counts as demand
6. _check_ha_tracker_warnings (persistent notifications)
7. snapshot status fields: _last_room_periods (per-room), _last_zone_periods,
   _last_present_persons
8. calibration pass (Calibrator.calibrate_all) if calibration_enabled
9. Fire climate_manager_status_update bus event
10. Notify update listeners (HA entities, async_sync_devices)
```

**Concurrent, bounded dispatch**: every valve of every room and zone receives
its command at the same time (`asyncio.gather`, `return_exceptions=True` at the
zone and coordinator levels so one failure never cancels the others). Each
service call is bounded by `TRV_COMMAND_TIMEOUT` (30 s): an unresponsive valve
logs `timeout |`, keeps its `last_pushed`, and is retried on the next cycle.
Calibration calls are bounded the same way.

**Anti-flap push** (`TRV.push_temperature`): skip if the period (`slot`) is
unchanged and `last_pushed == desired`. **Manual-override hold** (D-03): if the
TRV reports a setpoint ≠ last pushed within the same period, it was changed
outside Climate Manager (vendor app or schedule, user) — hold until the next
period transition, where `last_slot` differs and the setpoint is re-applied.
**Forced first push**: when `last_pushed is None` (startup, a TRV new to the
graph, back online) `set_temperature` is sent even if the valve already reports
the setpoint, since its HA state may be stale.

**Boiler** (`boiler.py`, optional `runtime_config["boiler"]`): the boiler heats
while at least one room's effective period (`Room.current_period`: schedule,
presence and pre-heat resolved) is in `BOILER_HEATING_PERIODS` (Normal, Comfort,
Pre-heat) and at least one of its TRVs is available (`Room.has_available_trv`);
Reduced, Frost protection, an Off zone and a room without a working valve ask
for nothing. Room temperatures and valve openings are not used. A `climate`
boiler toggles `hvac_mode` between `on_hvac_mode` / `off_hvac_mode`; a `switch`
/ `input_boolean` uses `turn_on` / `turn_off` (bounded by
`TRV_COMMAND_TIMEOUT`). Like the TRVs it is push-on-change: a command only when
the demand changes, so a manual change stays until the next one. The first
evaluation (startup, new entity) and a return online read the real entity state
and align it. A switch waits for `min_on_minutes` / `min_off_minutes` since the
last switch (the entity's `last_changed` after a restart) — `waiting_until` in
the status. The boiler entity is removed from the rooms' TRV lists. Rebuilds
carry its state (`Boiler.carry_state`); the config is part of the fingerprint.

**Back-online resync**: `_availability_listeners` track every TRV push target
and every room climate entity. A transition from no state / `unavailable` /
`unknown` to a valid state resets the TRV's push state (`online |` log) and
triggers an evaluation, so a valve that was offline at a period change — or
whose integration finished loading after Climate Manager — gets its setpoint
right away. An entity with no TRV object (no state at the last rebuild) requests
a rebuild instead. `is_trv_entity` reads `max_temp` from the entity registry
capabilities when the entity has no state yet, so valves still loading at HA
startup are part of the graph from the first evaluation.

**Pre-heat** (`Room.compute_preheat`, model in `preheat.py`): starts early
heating ahead of the next occupied time. In a presence zone where no assigned
person is home, that is the earliest scheduled arrival
(`schedule.next_occupied_at`). Otherwise (someone home, a plain time program, or
no arrival) it is the next zone setpoint increase: a transition warmer than the
period just before it, so tomorrow's Reduced → Normal counts even while Normal
is the current period. A shared room is not held back by a person away until the
weekend while others are home. The panel's "pre-heat disabled" hint
(`preheat_suppressed`) only means that, in presence mode, no assigned person's
presence can be scheduled (HA tracking or forced). Each room learns a heating
rate in min/°C: the median of its last 7 samples (`learned_rate`). The lead is
recomputed every tick as `rate × (upcoming − room_temp) × 1.1`, bounded to [10
min, `preheat_max_lead_minutes`] (default 240 min, a guard only), so a colder
room starts earlier; while fewer than 3 samples exist, or the room temperature
is unknown, the learning lead is used (`PREHEAT_LEARNING_LEAD_MINUTES`, 120 min,
capped by the max lead). The run lives in `Room._preheat_in_progress`
(`start_time`, `start_temp`, `target_temp`, `until`, `converged`, `measuring`,
`boosted`, `released`, `readings`). Until `until`, `Room.apply_setpoint` keeps
the upcoming setpoint whenever it is warmer than the zone's scheduled one, and
the room period is `preheat` (room period sensor state, panel badge, history
timeline). Reaching the target
(`room_temp ≥ target − PREHEAT_CONVERGENCE_THRESHOLD`) records one sample but
keeps holding until `until`. Not reached by `until`: the run switches to
**measuring** (no hold; the zone setpoint is already the target) and records the
real duration once reached, so a lead that was too short grows. A measuring run
ends **censored** (elapsed time as a lower bound of the rate) when the zone
setpoint drops below the target or after 2 × max lead. A start gap under 0.5 °C
yields no sample. A run whose reason vanished (pre-heat disabled, zone off,
presence suppressed, occupied time no longer within the max lead) is cancelled
without a sample. Skipped when the room is already at/above the upcoming
setpoint, or has no available TRV (none assigned, or all unavailable / unknown:
nothing could heat it); `room_temp` comes from the room temperature sensor, else
the first TRV. The run is saved to the pre-heat store on each state change
(start, convergence, measuring, end): a domain rebuild carries it over
(`carry_preheat_state`) and a restart restores it (`restore_preheat_run`), so
the hold and the measurement keep their original start time. Each run also
records the boiler's conditions (`vendors.boiler_readings`): outdoor
temperature, heating curve and program at the start, the mean flow temperature
over the run; the sample copies them (`outdoor_temp`, `flow_temp`,
`curve_slope`, `curve_shift`, `program`, unknown ones left out) and the
`preheat | … reached/censored` log appends `outdoor=… flow=…`. They are not used
by the lead yet. The status payload exposes `preheat_rate`, `preheat_samples`,
`preheat_lead`, `preheat_boost` and `preheat_anticipation` (shown in the room
card). **Boost — valve wide open, released by anticipation**: the energy to warm
a room is the same at any speed, while the losses favour heating late and fast,
and an overshoot is pure waste; the boiler's flow temperature (its heating
curve) is the only real speed lever. So a run starts as late as the learned rate
allows, heats with the valve wide open, and releases the boost early enough for
the radiator's residual heat to land on the target. A TRV next to a hot radiator
also reads high and would throttle before the room is warm. Until released (hold
and measuring), `apply_setpoint` pushes to the TRVs the setpoint plus the full
boost allowed: `PREHEAT_BOOST_MAX` (3 °C), capped at the TRVs' `max_temp`,
rounded down to 0.5 °C (`Room._preheat_boost`; none without a room temperature).
`_last_setpoint` keeps the unboosted value. Each tick a boosting run records the
room temperature (`readings`, the last 30 min plus the reading at the window's
start); the **heating speed** is the slope over them (`heating_slope`; unknown
under 10 min of readings or when not warming), else 1 / learned rate. The boost
is **released** (`Room._release_due`) once
`(target − room_temp) / speed ≤ anticipation`, or the room reached the target;
without any speed, within `PREHEAT_CONVERGENCE_THRESHOLD` of it. The plain
setpoint is then re-pushed in the same tick (`_drop_boost`), `released` is
persisted and never undone (a dip does not boost again), and the log reads
`preheat | room=… released left=…min slope=…°C/min`. A run already within the
anticipation at its start is released at once and never boosted. Release and
convergence are separate events. The **anticipation is learned** per room, in
minutes, never set (`Room.anticipation`, pre-heat store `anticipation`, default
10): after the release of a boosted run, `observe` follows the room's peak for
`PREHEAT_OVERSHOOT_WINDOW_MINUTES` (60), then `tune_anticipation` moves it by 5
min within [0, 60]: up when the peak exceeds the target by more than 0.2 °C
(released too late), down when it stays more than 0.1 °C below (too early). A
warmer setpoint during the window drops the watch. A change logs
`preheat | room=… anticipation=a→bmin overshoot=…`. Minutes, not °C: after the
release the radiator keeps warming the room for about its time constant τ, so
the overshoot is about τ × the current speed — a hotter flow (cold weather)
overshoots more in °C for the same τ. A legacy `boost_factor` key (the former
factor model) is dropped from the store, and the registry entries of its
`sensor.<area_id>_preheat_boost_factor` at setup
(`sensor._remove_retired_sensors`). **Calibration** (`calibration.py`,
`Calibrator`, owned by the coordinator): incremental offset toward the room
reference sensor, for the calibration targets the vendors resolve (see
[Vendors](#vendors--vendors)). Clamped ±5°C with a threshold guard to avoid
jitter: `calibration_threshold` (0.5 °C), pre-heat or not (the boost compensates
a TRV reading high next to its radiator). Only steady conditions are measured:
the TRV mode and setpoint unchanged for 90 min, and the room sensor and the TRV
reading both within 0.2 °C over the last 60 min. A heating or cooling radiator,
or the sun on a TRV, shows a transient gap that the TRV cancels as soon as its
offset changes: correcting it would wind the offset up to the clamp. A radiator
also keeps warming its TRV for a while after it closed, and the top of that hump
looks flat: the settle time after a setpoint change skips it. No calibration
(nor readings recorded) while the room is boosting (`Room.preheat_boosting`): a
long boost held at one setpoint looks settled too, and the TRV next to the hot
radiator reads well above the room. Dropping the boost changes the setpoint,
which restarts the settle time. After a write the TRV readings start over, so
the next correction waits for the TRV to settle on its new offset. An offset
that does not change (at the clamp) is not written. At most one write attempt
per target every 5 min, failures included (cloud API quotas; with Tado X each
write also triggers a refresh). Each write logs
`calibrate | room=… trv=… sensor=… trv=… delta=… offset=a→b threshold=…`.
Offsets are remembered per target (`last_offset`, keyed by device or entity);
after a restart the first correction starts from the offset the vendor reports.
The periodic pass runs every tick; a state listener on each target's temperature
source (`watched_entities`, refreshed when that set changes) also calibrates the
room as soon as a new reading arrives.

---

### Domain model

The control logic lives in five collaborating object families. Each `*Mode` base
class is a plain class (not an ABC) holding a `weakref` back-link to its owner;
unimplemented overloads raise `assert False`.

| File              | Classes                                                                  | Role                                                                                                                                          |
| ----------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `eval_context.py` | `EvalContext`                                                            | Per-cycle cache passed through the whole call chain: `now`, `period_temperatures`, lazy `_calendar_cache`, `_presence_cache` (D-02)           |
| `zone.py`         | `Zone`, `ZoneModeOff`, `ZoneModeTimeProgram`, `ZoneModeProgramPresences` | Resolves the active period; pushes setpoints to its rooms; emits the `zone` OBS-01 log on `(period, mode)` change                             |
| `person.py`       | `Person`, `PersonModeScheduled/HA/Calendar/ForcePresent/ForceAbsent`     | Evaluates presence (cached in `ctx`); emits the `presence` OBS-01 log on home/away flip and on user mode change                               |
| `room.py`         | `Room`                                                                   | Owns `_trv_groups`, `assigned_persons`, per-room pre-heat state, `_last_period` (status badge); `apply_setpoint`/`apply_off`                  |
| `trv.py`          | `TRV`, `TRVGroup`                                                        | `TRVGroup` is assembled once (resolving `matter_mappings` + boiler filter); `TRV` owns `last_pushed`/`last_slot`, the hold and the `push` log |

`ZoneModeProgramPresences` resolves an effective period **per room** (empty room
→ reduced; occupied → schedule via `compute_occupied_temp`), so each `Room`
tracks its own `_last_period` (`Room.current_period`) for the status badge
rather than a single zone-level value. The zone period (`Zone.current_period`)
is always the zone time program's period (frost protection when Off).
`TRVGroup.from_room_config` applies `is_trv_entity` so boiler/HVAC entities
(`max_temp > 45 °C`) are never push targets. A paired entity (`matter_mappings`
key) is replaced by its Matter entities, and a Matter entity paired with another
one is not pushed on its own (no brand check).

#### OBS-01 structured log traces

Emitted at `INFO` under `custom_components.climate_manager.*`. Each family is
anti-spammed — it logs only on a real state change, never every tick.

| Logger           | Format                                                                                       | Fires on                                          |
| ---------------- | -------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `zone`           | `zone \| zone=<name> state=<old>[<mode>]→<new>[<mode>] reason=<why>`                         | period or mode change (`time_program:` / `user:`) |
| `presence`       | `presence \| person=<name> home=<bool> reason=<mode>` / `mode=<old>→<new> reason=user`       | `_last_home` flip / user mode change              |
| `push`           | `push \| room=<name> trv=<name> temp=<T>°C slot=<period> zone=<name>`                        | setpoint actually sent to a TRV                   |
| `hold`           | `hold \| trv=<name> reported=<T>°C last=<T>°C slot=<period>`                                 | TRV changed outside Climate Manager (once)        |
| `preheat`        | `preheat \| room=<id> target=<T>°C until=<HH:MM> lead=<N>min rate=<R>` / `… reached after …` | pre-heat start / sample (or `censored`)           |
| `online`         | `online \| trv=<name> back online, re-applying setpoint`                                     | TRV available again                               |
| `boiler`         | `boiler \| on rooms=<ids>` / `boiler \| off` / `boiler \| waiting min_on <N>min`             | boiler switch / min on-off wait                   |
| `timeout` (WARN) | `timeout \| trv=<entity_id> temp=<T>°C after <N>s`                                           | TRV did not answer within `TRV_COMMAND_TIMEOUT`   |

To surface these, set `custom_components.climate_manager: info` (or `debug`)
under `logger:` in `configuration.yaml` — custom integrations are filtered at
`WARNING` by default.

---

### Discovery — `discovery.py`

| Function                  | Returns                                            |
| ------------------------- | -------------------------------------------------- |
| `discover_rooms()`        | `{area_id: [climate_entity_ids]}`                  |
| `discover_persons()`      | `[person.* entity_ids]`                            |
| `discover_room_sensors()` | `{area_id: {"temperature": eid, "humidity": eid}}` |

Registry listeners (`entity_registry_updated`, `device_registry_updated`) re-run
discovery live when climate entities are created/removed or a device's area
assignment changes.

---

### Vendors — `vendors/`

The core only drives standard `climate` entities and never names a brand.
Brand-specific behaviour lives in `TRVVendor` subclasses (`vendors/base.py`),
registered in `vendors.VENDORS`; the core calls the aggregate helpers of
`vendors/__init__.py`. Every method has a neutral default, so a brand without a
vendor is pushed setpoints and never calibrated.

| Member                                                | Used by                                                           |
| ----------------------------------------------------- | ----------------------------------------------------------------- |
| `calibration_targets(hass, area, entities, mappings)` | `Calibrator`: which offsets to keep aligned, read on which entity |
| `read_offset` / `write_offset`                        | `Calibrator`: offset reported after a restart / offset write      |
| `suggest_mappings(hass)`                              | Auto-pairing at startup and `suggest_matter_mappings` (WS)        |
| `pairable` + `owns(hass, entity_id)`                  | `get_config.pairable_entities` (room card drag-and-drop pairing)  |
| `accessory_models`                                    | `boiler_candidates` (valve switches are never a boiler)           |
| `poll_interval(hass)`                                 | `get_calibration_status.cloud_polling` (calibration tab banner)   |
| `label`                                               | Calibration tab badge (`vendor` field of each calibration row)    |

A `CalibrationTarget` names one offset: `key` (memory key: device or entity),
`name` (logs, panel), `temp_entity_id` (the climate entity compared with the
room sensor), and optionally `entity_id` / `device_id`.

**Tado X** (`vendors/tado_x.py`, `TadoX`): one cloud climate entity per room and
"Radiator Valve X" devices without a climate entity. One target per valve of the
room: in its area, or, without an area, connected through the zone device
(`via_device_id`). The offset is written with `tado_x.set_temperature_offset`
(`device_id` only, one decimal) and read back from the valve's
`temperature_offset` sensor. A valve is read on the Matter entity with its
serial (`("matter", "serial_<serial>")`), else on the zone's first paired Matter
entity, else on the zone entity. A zone without a known valve is not calibrated.
Suggestions pair a zone entity with the Matter entities of the valves connected
through its device (`via_device_id`).

To support a new brand: subclass `TRVVendor`, override what the brand needs, add
an instance to `VENDORS`, and test it on its own (see
`tests/test_vendor_tado_x.py`; `tests/test_calibration.py` drives the
`Calibrator` with a fake vendor).

**Boiler vendors** (`BoilerVendor`, registered in `vendors.BOILER_VENDORS`)
report the boiler's heating conditions: `readings(hass, entity_id)` returns a
`BoilerReadings` (`outdoor_temp`, `flow_temp`, `curve_slope`, `curve_shift`,
`program`; `None` when unknown). `vendors.boiler_readings(hass, boiler_config)`
takes the owning vendor's readings and lets the optional boiler config sensors
(`outdoor_temperature_entity_id`, `flow_temperature_entity_id`) override them,
so any boiler can record them. They are only recorded with the pre-heat samples
for now (see Pre-heat). The boiler status carries the vendor `label` (panel hint
"Auto (ViCare)"). **ViCare** (`vendors/vicare.py`): the heating circuit's
climate entity carries `heating_curve_slope`, `heating_curve_shift` and
`active_vicare_program`; the flow (`supply_temperature` of the same circuit
suffix, else `boiler_supply_temperature`) and outdoor (`outside_temperature`)
temperatures are sensors of the same device, found by translation key. Both
vendor kinds share `Vendor.owns` (registry platform).

---

### TRV control — `trv.py`

| Function                                            | Purpose                                                                                                                                                                                              |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `set_trv_temperature(hass, entity_id, temp, force)` | Step 1: ensure `hvac_mode=heat`; Step 2: `set_temperature` (skipped if already set, unless `force`). Some TRVs ignore setpoints in auto mode.                                                        |
| `set_trv_off(hass, entity_id)`                      | `set_hvac_mode=off`                                                                                                                                                                                  |
| `supports_hvac_off(hass, entity_id)`                | Inspects `hvac_modes` attribute                                                                                                                                                                      |
| `is_trv_entity(hass, entity_id)`                    | True for room TRVs; False for boiler/HVAC entities (`max_temp > 45 °C`, read from the registry when there is no state yet). Applied in `TRVGroup.from_room_config` and every status/calibration path |

The module also defines the `TRV` and `TRVGroup` domain classes (see
[Domain model](#domain-model)). `TRVGroup` is assembled once per room and holds
the resolved push targets; `TRV.push_temperature` wraps the two-call sequence
with the anti-flap guard, manual-override hold, timeout and the `push` log. The
free functions above remain the low-level service-call layer the classes call
into.

---

### Schedule evaluation — `schedule.py`

Pure Python — no HA imports. All async HA calls stay in `coordinator.py`.

| Function                                               | Purpose                                            |
| ------------------------------------------------------ | -------------------------------------------------- |
| `evaluate_schedule(program, now)`                      | Active period mode at the given time               |
| `resolve_presence(person_config, now, ...)`            | Evaluates person schedule → present/absent         |
| `resolve_calendar_presence(events, ...)`               | Calendar-based presence with gap handling          |
| `compute_occupied_temp(program, now, is_present, ...)` | PERSON-07/08/09 rules (occupied window, sandwich)  |
| `next_occupied_at(person_config, ...)`                 | Next scheduled "present" transition (for pre-heat) |
| `validate_daily_program(program)`                      | Validates a 7-day program before mutation          |

These are pure helpers; the per-mode dispatch lives in `person.py`'s
`PersonMode` subclasses (Phase 16), which call into them:

- `PersonModeHA` — reads HA `person.*` entity state directly (`== "home"`)
- `PersonModeCalendar` — resolves via `ctx.calendar_events()` +
  `resolve_calendar_presence()`
- `PersonModeScheduled` — `resolve_presence()`
- `PersonModeForcePresent` / `PersonModeForceAbsent` — constant `True` / `False`

---

### WebSocket API — `websocket.py`

19 commands registered under `climate_manager/` prefix. All handlers access
state via the config-entry closure (never `hass.data[DOMAIN]`).

**Write pattern**: mutate `runtime_config` → `store.async_save()` →
`send_result` → `coordinator.async_evaluate()` (background task).
`set_zone_mode` / `set_person_config` additionally call `change_mode()` on the
live domain object (captured **before** the `await`) so the OBS-01 user-driven
log fires before the rebuild — for `set_zone_mode` this lives in
`coordinator.async_set_zone_mode`, shared with the zone mode `select` entity.
The Default Zone is addressed by the sentinel `zone_id="default"` (writes
`default_zone.*`); `set_global_mode` / `reset_time_program` / `reset_room_to_*`
were removed in Phases 14–15.

| Category    | Commands                                                                                                                             |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Read        | `get_status`, `get_config`, `get_calibration_status`                                                                                 |
| Global      | `set_period_temperatures`, `set_time_program`, `reset_period_temperatures`                                                           |
| Room        | `set_room_config`                                                                                                                    |
| Person      | `set_person_config`                                                                                                                  |
| Zone        | `create_zone`, `rename_zone`, `set_zone_mode`, `set_zone_preheat`, `delete_zone`, `set_zone_time_program`, `reset_zone_time_program` |
| Calibration | `set_calibration_config`                                                                                                             |
| Boiler      | `set_boiler_config` (`entity_id` null clears; climate hvac modes validated against the entity)                                       |
| Matter      | `set_matter_mapping`, `suggest_matter_mappings`                                                                                      |
| Push        | `subscribe_status`                                                                                                                   |

`subscribe_status` registers a listener for `climate_manager_status_update` bus
events and pushes the status payload to the panel connection on each coordinator
cycle.

---

### HA entities

Native entities exist so the HA recorder historises zone modes and periods
(history graphs, logbook, automations). Platform modules: `binary_sensor.py`,
`select.py`, `sensor.py`; shared base and device helpers in `entity.py`.

| Entity                                                    | Device             | unique_id                                     | State                                          |
| --------------------------------------------------------- | ------------------ | --------------------------------------------- | ---------------------------------------------- |
| `select.<zone>_mode`                                      | zone               | `<entry>_zone_<zone_id>_mode`                 | zone mode, read from `runtime_config`          |
| `sensor.<zone>_period` (enum)                             | zone               | `<entry>_zone_<zone_id>_period`               | `Zone.current_period` (schedule period)        |
| `sensor.<area_id>_period` (enum)                          | room (in its area) | `<entry>_room_<area_id>_period`               | `Room.current_period` (presence-resolved)      |
| `sensor.<area_id>_preheat_rate` (diagnostic, min/°C)      | room (in its area) | `<entry>_room_<area_id>_preheat_rate`         | `Room.learned_rate()` (unknown while learning) |
| `sensor.<area_id>_preheat_anticipation` (diagnostic, min) | room (in its area) | `<entry>_room_<area_id>_preheat_anticipation` | `Room.anticipation()` (learned)                |
| `binary_sensor.climate_manager_boiler_demand` (heat)      | boiler             | `<entry>_boiler_demand`                       | on while a room needs heat; `rooms` attribute  |

- **Devices**: one per zone (`(DOMAIN, "zone_<zone_id>")`, named after the zone,
  Default Zone = `zone_default`) and one per room (`(DOMAIN, "room_<area_id>")`,
  named after and placed in its HA area). Room sensors set their `entity_id`
  explicitly because HA 2026.x prefixes new entity IDs with the area name (would
  yield `sensor.<area>_<area>_period`). A boiler device (`(DOMAIN, "boiler")`)
  exists while a boiler is configured.
- **Updates**: push-only. `ClimateManagerCoordinator.async_add_listener` is a
  DataUpdateCoordinator-style hook fired at the end of every `async_evaluate`;
  each entity writes its state, and HA only records a row when it changes.
  Values are re-read by id from `coordinator.zones` / `coordinator.rooms`
  because the domain graph is rebuilt on config change.
- **Lifecycle**: `async_add_entities_for_ids` adds entities for zones/rooms that
  appear (e.g. `create_zone`). `async_sync_devices` (listener registered in
  `__init__.py`) removes the device of a deleted zone/room — which removes its
  entities — and refreshes device names on zone/area rename.
- **Control**: selecting an option calls `coordinator.async_set_zone_mode`
  (persist with rollback → `Zone.change_mode` OBS-01 log → background
  evaluation), the same path as the `set_zone_mode` WS command. Failures raise
  `HomeAssistantError`.
- Entity names and state labels come from `translations/en.json`
  (`translation_key`: `zone_mode`, `zone_period`, `room_period`).
- **Panel access**: the status payload carries the resolved entity_ids
  (`zones[id].mode_entity_id` / `period_entity_id`,
  `rooms_status[].period_entity_id`), looked up by unique_id in the entity
  registry each cycle — the panel never guesses an entity_id, so user renames
  are followed. Helpers in `frontend/src/ha-nav.ts`: `openMoreInfo` (HA
  more-info dialog), `navigateTo`, `historyPath`. Zone tab: history icons next
  to Mode and Current period, plus a **History** button opening
  `/history?entity_id=…` for the zone and its rooms. Global settings: a
  **History** button in the Boiler card for the boiler entity and the demand
  sensor (`boiler.demand_entity_id` in the status). Room card: the period badge
  opens the room period sensor's more-info.
- **Room card history**: `rooms_status[]` also carries `temperature_entity_id` /
  `humidity_entity_id` (HA area setting → auto-discovered sensor) and
  `preheat_rate_entity_id` / `preheat_anticipation_entity_id`. The expanded card
  embeds HA's native `history-graph` card (`createHistoryCard` →
  `window.loadCardHelpers`) for the room period, temperature, humidity, the
  learned pre-heat parameters and the TRVs that receive setpoints (same rules as
  `TRVGroup`: an entity with paired Matter valves is shown as those valves; a
  paired Matter valve is not shown on its own). It is created lazily on expand
  and dropped on collapse (no history subscriptions for collapsed cards); the
  time range (6 h – 7 days) is kept in `localStorage`; the "open in History"
  link starts at the same range (`start_date`). Without card helpers (docs
  harness) only that link is shown.

---

## Frontend Panel

### Build toolchain — `frontend/`

| File             | Purpose                                                        |
| ---------------- | -------------------------------------------------------------- |
| `vite.config.ts` | Bundles to `../custom_components/climate_manager/www/panel.js` |
| `tsconfig.json`  | TypeScript 5 config                                            |
| `package.json`   | Lit 3 + home-assistant-js-websocket deps                       |

Lit is bundled into `panel.js` — no dependency on HA's own Lit instance.

### Panel registration

- Static URL: `/climate_manager_panel` → `www/` directory
- Component name: `climate-manager-panel` (must match `customElements.define`)
- Registered via `panel_custom.async_register_panel` in `async_setup_entry`
- `manifest.json` declares `["http", "frontend", "panel_custom"]` as
  dependencies

### Source structure — `frontend/src/`

| File/component                                 | Role                                                                                                   |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `panel.ts`                                     | Root `<climate-manager-panel>` element; receives `hass` from HA; owns tab routing                      |
| `ws-client.ts`                                 | Typed WS helpers (thin wrappers over `hass.connection`)                                                |
| `types.ts`                                     | TypeScript interfaces for all WS message shapes (`ClimateConfig`, `StatusPayload`, `RoomStatus`, etc.) |
| `toast.ts`                                     | Global toast notification utility                                                                      |
| `ha-nav.ts`                                    | HA more-info / in-app navigation / History URL / history-graph card helpers                            |
| `shared-styles.ts`                             | Shared CSS design tokens                                                                               |
| `components/rooms-tab.ts` + `room-card.ts`     | Per-room config and schedule editor                                                                    |
| `components/zone-tab.ts`                       | Zone management (create/rename/delete/mode/schedule)                                                   |
| `components/persons-tab.ts` + `person-card.ts` | Person presence config and schedule editor                                                             |
| `components/global-settings-tab.ts`            | Global mode, period temps, calibration                                                                 |
| `components/presence-mode.ts`                  | Presence mode selector widget                                                                          |
| `components/time-bar.ts`                       | Interactive weekly schedule bar (drag to resize periods)                                               |
| `components/week-parity.ts`                    | Even/odd week selector for biweekly schedules                                                          |
| `components/search-picker.ts`                  | Entity/area search dropdown                                                                            |

HA native elements broken in HA 2026.x:

- `ha-select` — use native `<select>` instead
- `ha-tabs` / `paper-tab` — use CSS button tabs + manual panel header
- `ha-textfield` — use native `<input type="number">` with label + suffix span

---

## Data flow

```text
HA event loop (1 min tick)
  → coordinator.async_evaluate()
      → EvalContext(now, …)                    # per-cycle cache
      → zone.evaluate(ctx)                      # resolve period per room
          → room.apply_setpoint(period, temp)  # → TRVGroup.push → TRV
      → person.evaluate(ctx)                    # presence (cached)
      → OBS-01 INFO logs on state change
      → hass.bus.async_fire(status_update)    # notify subscribed panels
      → update listeners                      # entities → recorder history

Panel (initial load)
  → climate_manager/get_config               # full config snapshot
  → climate_manager/subscribe_status         # register live push

Panel (mutation)
  → climate_manager/set_*
      → store.async_save()
      → coordinator.async_evaluate()         # immediate re-evaluation
                                             # → status_update pushed
```

---

## Key design decisions

| Decision                                     | Rationale                                                                                                                            |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `entry.runtime_data` typed dataclass         | No global `hass.data` dict; auto-cleaned on unload                                                                                   |
| Anti-flap push + manual override hold        | Avoids redundant TRV calls; respects manual adjustments                                                                              |
| Sparse storage model                         | Absent keys fall back to `DEFAULT_CONFIG`; forward-compatible                                                                        |
| Zone model (absent `zone_id` = Default Zone) | ZONE-04: room belongs to at most one zone by structure                                                                               |
| Domain model + fingerprint rebuild           | Coordinator delegates to `Zone`/`Person`/`Room`/`TRV` objects; rebuilt only when config changes; anti-spam log state carried forward |
| Native select/sensor entities per zone/room  | Recorder history of zone mode, zone period and room period; mode select reuses the WS `set_zone_mode` path                           |
| `EvalContext` per cycle                      | One object threads `now` + calendar/presence caches through the call chain (D-02)                                                    |
| OBS-01 anti-spammed logs                     | `zone`/`presence`/`heating` lines fire only on real state changes                                                                    |
| Pre-heat learned inertia                     | Median rate (min/°C) of the last 7 samples × gap × 1.1, bounded [10, max lead]; censored samples avoid a short bias; run persisted   |
| Calendar cache per cycle                     | One `get_events` call per unique calendar entity per minute tick                                                                     |
| WebSocket over REST                          | Session already established; no auth token management from JS                                                                        |
| Lit bundled in panel.js                      | Avoids HA Lit version conflicts; larger bundle is acceptable trade-off                                                               |
