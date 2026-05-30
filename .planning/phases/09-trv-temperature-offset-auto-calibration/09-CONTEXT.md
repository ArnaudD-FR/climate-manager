# Phase 9: TRV Temperature Offset Auto-Calibration - Context

**Gathered:** 2026-05-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a periodic TRV temperature offset calibration engine to the coordinator.
When enabled globally, the integration reads each room's configured reference
temperature sensor, computes the delta vs the TRV's reported
`current_temperature`, and calls `tado_x.set_temperature_offset` (or equivalent)
to converge the TRV reading toward the sensor truth — avoiding jitter via a
configurable threshold. The Global Settings tab gains an "Options" card with a
toggle to enable/disable the feature. Incompatible TRVs and sensor-less rooms
are silently skipped.

**In scope:**

- `coordinator.py`: new `_async_calibrate()` private method called from
  `async_evaluate()` at the end (after the temperature push pass); per-room
  calibration logic delegated to further private helpers as needed
- `trv.py`: new `set_trv_offset()` service call helper (mirrors
  `set_trv_temperature` pattern); capability guard `supports_offset_calibration()`
- `const.py`: new `calibration_enabled` key in `DEFAULT_CONFIG` (default
  `False`); `calibration_threshold` key (default `0.5`)
- `websocket.py`: extend `ws_set_global_mode`/settings pattern — new WS command
  `climate_manager/set_calibration_config` (or extend existing
  `set_period_temperatures` pattern) to persist the toggle
- `frontend/src/components/global-settings-tab.ts`: new "Options" ha-card
  section with `ha-switch` for the calibration toggle; auto-saves on change
- `frontend/src/ws-client.ts`: new `setCalibrationConfig(enabled: boolean)`
  method
- `frontend/src/types.ts`: extend `ClimateConfig` with `calibration_enabled`
  and `calibration_threshold`

**Out of scope:**

- Configurable calibration interval (fixed: every `async_evaluate` cycle)
- Threshold UI input (threshold stays at default 0.5°C; not surfaced in panel)
- Auto-discovered sensor fallback (manual `temperature_sensor` config only)
- Any brand-specific Tado X API — service call via standard HA service bus only
- TRV calibration for rooms without `temperature_sensor` in room config

</domain>

<decisions>
## Implementation Decisions

### Calibration Architecture

- **D-01:** Calibration runs as a private method `_async_calibrate()` called
  from the end of `async_evaluate()` — after the temperature push pass
  completes. `async_evaluate` owns only orchestration; all logic lives in
  private methods.
- **D-02:** Calibration fires every `async_evaluate` cycle (every minute). No
  separate `async_track_time_interval` — the delta threshold (D-07) prevents
  unnecessary service calls when the offset is already correct.
- **D-03:** The calibration pass is a `asyncio.gather()` over all rooms, same
  concurrency pattern as the temperature push. Per-room logic delegated to a
  private helper (e.g., `_async_calibrate_room(area_id, entity_id, ...)`).
- **D-04:** Calibration is skipped entirely when `calibration_enabled` is
  `False` in config. No service calls, no attribute reads.

### Offset Math

- **D-05:** Delta formula:
  `delta = room_sensor_temp − TRV.current_temperature`
  (positive delta = room reads higher than TRV → offset needs to increase)
- **D-06:** New offset formula:
  `new_offset = TRV.temperature_offset_attribute + delta`
  (incremental — reads current offset from state attribute, adds delta)
  Current offset source: `hass.states.get(entity_id).attributes.get("temperature_offset", 0.0)`
- **D-07:** Offset service call only when `abs(delta) > calibration_threshold`
  (default 0.5°C). Prevents jitter from small sensor fluctuations.
- **D-08:** The capability guard checks for `temperature_offset` attribute
  presence OR `tado_x.set_temperature_offset` service registration. Rooms where
  no TRV passes the guard are silently skipped (no log, no error).

### Configuration Storage

- **D-09:** Two new keys added to `DEFAULT_CONFIG` in `const.py`:
  - `calibration_enabled: False` — global on/off
  - `calibration_threshold: 0.5` — jitter guard in °C
  Threshold is not surfaced in the UI (toggle only). Both keys are top-level,
  alongside `global_mode`.
- **D-10:** A new WebSocket command exposes the toggle —
  `climate_manager/set_calibration_config`. Accepts `{"enabled": bool}`.
  Follows the sparse-merge pattern of `set_room_config`.

### UI — Global Settings "Options" Card

- **D-11:** A new ha-card titled "Options" is added to `global-settings-tab.ts`
  as the third card (after Current Status and Temperatures).
- **D-12:** The calibration toggle is rendered as `<ha-switch>` with label
  "Auto-calibrate TRV temperature offsets". Auto-saves on `change` event —
  calls `setCalibrationConfig(enabled)`. No Save button (consistent with D-08
  from Phase 3 convention).
- **D-13:** The Options card is only rendered when at least one configuration
  option is present; for now that's just the calibration toggle. It is NOT
  rendered as a disabled state when there are no compatible TRVs — the user
  configures globally, the backend skips incompatible rooms silently.

### Sensor Resolution

- **D-14:** Calibration uses only the manually configured `temperature_sensor`
  key from `rooms[area_id]` config. No fallback to auto-discovered sensors.
  A room without an explicit `temperature_sensor` entry is silently skipped
  (CALIB-05). This matches the word "configured" in CALIB-05.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §TRV Temperature Offset Auto-Calibration —
  CALIB-01..05 requirements (full acceptance criteria)
- `.planning/ROADMAP.md` §Phase 9 — success criteria and phase boundaries

### Existing Architecture Patterns
- `custom_components/climate_manager/trv.py` — service call pattern for TRV
  control; `set_trv_temperature`, `supports_hvac_off`, `is_trv_entity` all
  model the guard + call structure to follow
- `custom_components/climate_manager/coordinator.py` — `async_evaluate` flow,
  `asyncio.gather` push pattern, private method conventions
- `custom_components/climate_manager/const.py` §DEFAULT_CONFIG — where new
  config keys are added; existing sparse-config pattern
- `custom_components/climate_manager/websocket.py` §`_make_ws_set_room_config`
  — sparse-merge + rollback pattern to follow for new calibration WS command

### Frontend Patterns
- `frontend/src/components/global-settings-tab.ts` — existing two-card
  structure; D-11 adds "Options" as third card
- `frontend/src/ws-client.ts` — existing WS call pattern to follow for new
  `setCalibrationConfig` method
- `frontend/src/types.ts` §ClimateConfig — where new `calibration_enabled` /
  `calibration_threshold` fields are added

### Tado X Research
- `.planning/quick/260528-417-check-ha-tado-x-compatibility/417-SUMMARY.md` —
  compatibility analysis; confirms service names and attribute patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `trv.py:set_trv_temperature()` — models the service call pattern: guard
  (state None/unavailable check), then `hass.services.async_call(blocking=True)`.
  New `set_trv_offset()` follows the exact same structure.
- `trv.py:supports_hvac_off()` — models the capability guard pattern: read
  state attribute, return bool. `supports_offset_calibration()` follows this.
- `coordinator.py:_push_safely()` / `asyncio.gather()` — models the concurrent
  room-loop pattern for `_async_calibrate()`.
- `websocket.py:_make_ws_set_room_config()` — sparse-merge + in-memory rollback
  on `ValueError`; follow this for `_make_ws_set_calibration_config()`.

### Established Patterns
- **Private method decomposition:** `async_evaluate` calls private helpers;
  business logic never lives directly in the orchestrating method.
- **Two-tier guard:** `is_trv_entity()` filters non-TRV climate entities;
  capability guard (`supports_offset_calibration`) filters TRVs that don't
  support offset. Stack them both.
- **Silent skip:** ROOM-03 / availability guard — unavailable entity → return
  immediately, no exception, no log. Same applies here.
- **Sparse config keys:** absent config key = default value (no migration
  needed for existing installations).
- **Auto-save on change:** `ha-switch` fires `change` event → WS call → no
  Save button. Matches Global Settings temperature fields (blur-save).

### Integration Points
- `coordinator.py:async_evaluate()` — new `await self._async_calibrate(config)`
  call added at the end (after the temperature push `asyncio.gather`).
- `const.py:DEFAULT_CONFIG` — two new keys: `calibration_enabled`, `calibration_threshold`.
- `websocket.py:async_register_commands()` — register new
  `climate_manager/set_calibration_config` command.
- `global-settings-tab.ts:render()` — add `${this._renderOptionsCard()}` call.

</code_context>

<specifics>
## Specific Ideas

- The "Options" card name was specified by the user — not "Configuration" or
  "Calibration". It's meant to be a general-purpose home for future toggles,
  not a single-feature card.
- `ha-switch` was specifically chosen for the toggle despite HA 2026.x component
  reliability concerns with other `ha-*` elements. If it renders nothing in
  production, fall back to a styled native `<input type="checkbox">` with the
  same auto-save behavior.

</specifics>

<deferred>
## Deferred Ideas

- **Configurable threshold in UI** — user chose toggle-only. Threshold remains
  0.5°C default, adjustable only via storage (not surfaced). Could be added to
  the Options card in a future phase if users request it.
- **Configurable calibration interval** — decided to use the same minute cadence
  as `async_evaluate`. A dedicated slower interval could be added later.
- **Auto-discovery sensor fallback** — manual config only for now. Auto-fallback
  could be added in a future quality-of-life improvement.
- **Multi-language support** — noted as a matching todo (score 0.9) but already
  deferred to v2 in REQUIREMENTS.md.

None from this discussion required scope creep redirection.

</deferred>

---

*Phase: 9-TRV Temperature Offset Auto-Calibration*
*Context gathered: 2026-05-30*
