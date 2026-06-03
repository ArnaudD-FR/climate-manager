---
phase: 13-matter-tado-x-real-time-calibration
plan: 01
subsystem: coordinator
tags: [home-assistant, matter, tado-x, calibration, event-driven, state-listener]

# Dependency graph
requires:
  - phase: 09-trv-auto-calibration
    provides: "_async_calibrate_tado_device, _async_calibrate_room, get_tado_valve_devices, supports_offset_calibration — reused for Matter calibration routing"
provides:
  - "matter_mappings default config key in DEFAULT_CONFIG (D-02)"
  - "_matter_cal_listeners dict keyed by entity_id with single Callable per entry (D-08)"
  - "_make_matter_cal_listener @callback factory with current_temperature attribute filter (D-09)"
  - "_async_refresh_matter_listeners cancel-all-then-rebuild lifecycle (D-10)"
  - "_async_calibrate_for_room per-room event-driven calibration (D-04..D-07)"
  - "_push_temperatures D-03 entity-by-entity dispatch with matter_entity_set frozenset"
  - "async_unload_entry cancel loop for _matter_cal_listeners (D-11)"
  - "_resolve_room_sensor shared sensor resolution helper (REFACTOR)"
affects:
  - "13-matter-tado-x-real-time-calibration plan 02 (WS command set_matter_mapping)"
  - "13-matter-tado-x-real-time-calibration plan 03 (frontend pairing UI)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-08: _matter_cal_listeners: dict[str, Callable] — single Callable per entity_id (not list, unlike _ha_tracker_listeners)"
    - "D-09: attribute-scoped state_changed listener — compare new_temp vs old_temp, return early if unchanged"
    - "D-10: cancel-all-then-rebuild in _async_refresh_matter_listeners — safe because WS commands serialised on HA event loop"
    - "D-03: per-area to_set list built from matter_entity_set frozenset — prevents double-add (Pitfall 2+3)"
    - "entity registry BEFORE state machine — test pattern: async_get_or_create before hass.states.async_set avoids _2 suffix from collision guard"

key-files:
  created: []
  modified:
    - custom_components/climate_manager/const.py
    - custom_components/climate_manager/coordinator.py
    - custom_components/climate_manager/__init__.py
    - tests/test_coordinator.py

key-decisions:
  - "Entity registry must be populated before hass.states.async_set in tests — HA's async_generate_entity_id checks state machine for collisions; states set first cause _2 suffix, breaking platform lookups"
  - "Non-registry entities (reg is None) fall to generic else branch in _push_temperatures and _async_refresh_matter_listeners — handles test entities and future entities without platform metadata"
  - "_matter_cal_listeners uses single Callable per key (dict[str, Callable]) NOT list — differs from _ha_tracker_listeners (dict[str, list]) per D-08 spec"

patterns-established:
  - "Register entity in entity registry BEFORE setting HA state — avoids entity_id collision suffix"
  - "_register local helper inside _async_refresh_matter_listeners — idempotent registration guard"
  - "_resolve_room_sensor shared method — area_reg → auto_sensors → rooms_config override chain"

requirements-completed: [MCALIB-01, MCALIB-02]

# Metrics
duration: 95min
completed: 2026-06-03
---

# Phase 13 Plan 01: Matter Listener Lifecycle + D-03 Dispatch Summary

**Event-driven Matter→Tado X calibration: per-entity state_changed listeners
with current_temperature attribute filter, cancel-all-then-rebuild lifecycle,
and D-03 entity-by-entity setpoint dispatch via matter_entity_set frozenset.**

## Performance

- **Duration:** ~95 min
- **Started:** 2026-06-03T14:30Z
- **Completed:** 2026-06-03T16:05Z
- **Tasks:** 2 (both TDD RED→GREEN→REFACTOR)
- **Files modified:** 4

## Accomplishments

- Added `matter_mappings: {}` sparse default to `DEFAULT_CONFIG` (D-02) — no
  migration needed for existing installs
- Implemented `_matter_cal_listeners: dict[str, Callable]` with full lifecycle:
  `_make_matter_cal_listener` (attribute-filter factory), `_async_refresh_matter_listeners`
  (cancel-all-then-rebuild), first-evaluate registration, and unload teardown
- Implemented `_push_temperatures` D-03 dispatch: builds `matter_entity_set`
  frozenset once per call, routes tado_x+mapped → Matter entities only,
  skips Matter entities already covered (Pitfall 3)
- Implemented `_async_calibrate_for_room` per-room event-driven calibration
  with D-04..D-07 routing (Matter entity as temp source, tado valve device
  lookup, entity-based fallback)
- Extracted `_resolve_room_sensor` shared helper (deduplicates sensor
  resolution between `_async_calibrate` and `_async_calibrate_for_room`)
- 233 tests passing, make lint clean

## Task Commits

Each task was committed atomically (TDD: test → feat → refactor):

1. **Task 1: Matter listener lifecycle** (RED→GREEN→REFACTOR)
   - `6adc970` test: add failing tests for Matter listener lifecycle (RED)
   - `cc7ee78` feat: implement Matter listener lifecycle — GREEN
   - `1950742` refactor: extract _register helper in _async_refresh_matter_listeners

2. **Task 2: D-03 dispatch + D-04..D-07 calibration routing** (RED→GREEN→REFACTOR)
   - `8475c59` test: add failing tests for D-03 dispatch and D-04..D-07 routing (RED)
   - `a7c15bb` feat: implement D-03 control-path dispatch — GREEN
   - `1a2f2be` refactor: extract _resolve_room_sensor helper

## Files Created/Modified

- `custom_components/climate_manager/const.py` — Added `matter_mappings: {}`
  to DEFAULT_CONFIG (D-02 sparse default)
- `custom_components/climate_manager/coordinator.py` — Added
  `_matter_cal_listeners`, `_make_matter_cal_listener`,
  `_async_refresh_matter_listeners`, `_async_calibrate_for_room`,
  `_resolve_room_sensor`; rewrote `_push_temperatures` D-03 dispatch
- `custom_components/climate_manager/__init__.py` — Added
  `_matter_cal_listeners` cancel loop in `async_unload_entry` (D-11)
- `tests/test_coordinator.py` — Added 14 new tests (7 Task 1 + 7 Task 2)

## Decisions Made

- **Entity registry before state machine in tests:** HA's entity_id
  generation (`async_generate_entity_id`) checks the HA state machine for
  collisions. Setting `hass.states.async_set("climate.foo")` before
  `async_get_or_create("climate", "platform", "foo")` causes HA to generate
  `climate.foo_2` (collision avoidance). Fix: call `async_get_or_create`
  BEFORE `hass.states.async_set`, capture the returned entity_id, use that
  entity_id everywhere (rooms, matter_mappings, states).
- **Non-registry entities get generic listener/dispatch:** When
  `entity_reg.async_get(entity_id)` returns None (entity not in registry,
  e.g. test entities set via `hass.states.async_set` only), the code falls
  to the generic `else` branch — entity gets a listener (for calibration)
  or setpoint call (for push). This is intentional for robustness.
- **_matter_cal_listeners stores single Callable, not list:** D-08 explicitly
  specifies `dict[str, Callable]` (one cancel per entity). Unlike
  `_ha_tracker_listeners` which uses `dict[str, list]` for extensibility.
  The unload and refresh loops call `cancel()` directly, not
  `for cancel in value: cancel()`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Non-registry entity fallback in
_async_refresh_matter_listeners**
- **Found during:** Task 1 (GREEN phase — test failure debugging)
- **Issue:** Original implementation skipped entities where
  `entity_reg.async_get(entity_id)` returned None, missing listeners for
  test entities and entities not yet registered in HA entity registry
- **Fix:** Changed `if reg is None: continue` to
  `platform = reg.platform if reg is not None else None` — None platform
  falls to `else` branch (generic entity registration)
- **Files modified:** coordinator.py `_async_refresh_matter_listeners`
- **Committed in:** cc7ee78 (Task 1 GREEN commit)

**2. [Rule 2 - Missing Critical] Non-registry entity fallback in
_push_temperatures**
- **Found during:** Task 2 (GREEN phase — test failure, same root cause)
- **Issue:** Same pattern — non-registry entities got no setpoint call
- **Fix:** Same pattern — `platform = reg.platform if reg is not None else None`
  → `else` branch appends to `to_set`
- **Files modified:** coordinator.py `_push_temperatures`
- **Committed in:** a7c15bb (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2 — missing correctness guard)
**Impact on plan:** Both fixes required for tests to work; also correct
production behavior since HA entity registry may not have entries for all
climate entities in some configurations.

## Issues Encountered

**HA entity_id collision in tests:** HA's `async_generate_entity_id` checks
the state machine for conflicts, not just the entity registry. This caused
`_2` suffix on entity_ids when `hass.states.async_set` was called before
`async_get_or_create`. Root cause took ~45 min to diagnose via debug logging.
Resolution: established a consistent test pattern (register → set state) and
created `_register_entity` helper in tests.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundary crossings introduced.
All threat mitigations from the plan's `<threat_model>` are implemented:
- T-13-01 (Tampering via matter_mappings): runtime platform check via
  `entity_reg.async_get().platform` in both `_push_temperatures` and
  `_async_calibrate_for_room`
- T-13-02 (Ghost listener accumulation): cancel-all-then-clear pattern in
  `_async_refresh_matter_listeners`, covered by
  `test_refresh_matter_listeners_cancels_old`
- T-13-03 (Calibration storm): `current_temperature` attribute filter in
  `_make_matter_cal_listener`, `old_state is None` guard, room-scoped
  `_async_calibrate_for_room` (not full multi-room pass)

## Next Phase Readiness

- Backend listener lifecycle + calibration routing complete
- Plan 02 (WS command `set_matter_mapping`) can proceed: needs
  `coordinator._async_refresh_matter_listeners()` method (exists),
  storage mutation pattern (websocket.py has existing analogs), and
  `matter_mappings` config key (in DEFAULT_CONFIG)
- Plan 03 (frontend room card pairing UI) depends on plan 02's WS command

---
*Phase: 13-matter-tado-x-real-time-calibration*
*Completed: 2026-06-03*
