---
phase: 09-trv-temperature-offset-auto-calibration
reviewed: 2026-05-30T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - custom_components/climate_manager/trv.py
  - custom_components/climate_manager/websocket.py
  - frontend/src/components/global-settings-tab.ts
  - frontend/src/types.ts
  - frontend/src/ws-client.ts
  - tests/test_trv.py
  - tests/test_websocket.py
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-05-30
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 09 adds TRV temperature offset auto-calibration: two new guard/setter
functions in `trv.py`, a calibration engine in the coordinator, a new WebSocket
command, and a frontend Options card with an `ha-switch` toggle.

The overall structure is sound and consistent with existing patterns. Two
correctness blockers stand out: (1) `set_trv_offset` unconditionally calls the
`tado_x` brand-specific service even when capability was detected via the
brand-agnostic attribute path, silently failing on every calibration tick for
non-Tado TRVs; (2) the `set_calibration_config` WebSocket handler mutates
in-memory state before `async_save` without a rollback, leaving the process
inconsistent if the save fails — the one write handler in the file that lacks
the CR-01 snapshot pattern present in every other write handler.

Four warnings cover: missing `"unknown"` state guard in the new TRV functions
(inconsistent with the coordinator's own sensor guard pattern), unbounded offset
accumulation in the calibration engine, the `ha-switch` component whose event
API has not been confirmed safe in HA 2026.x, and a dead type field
(`calibration_threshold` in `ClimateConfig`) with no WS command to mutate it.
Three info items address code style overruns, a masking test, and a missing
rejection test.

---

## Critical Issues

### CR-01: `set_trv_offset` always calls `tado_x` service even for non-Tado TRVs

**File:** `custom_components/climate_manager/trv.py:119-167`

**Issue:** `supports_offset_calibration` uses an **attribute-first** check: it
returns `True` whenever a TRV exposes a `temperature_offset` attribute in its
state — regardless of brand. This path is explicitly documented as
"brand-agnostic". However, `set_trv_offset` **always** calls the
`tado_x.set_temperature_offset` service. For a Zigbee2MQTT, Z-Wave, or any
other brand TRV that happens to expose `temperature_offset`, the coordinator
will call a service that does not exist, receive a `ServiceNotFound` error,
catch it via `BLE001`, log a warning, and silently fail. This happens **every
minute** while calibration is enabled, flooding logs and never applying any
correction.

The test suite masks this: `test_set_trv_offset_issues_single_service_call`
(test 13) sets up both the `temperature_offset` attribute AND registers the
`tado_x` mock service, so the attribute path is never exercised without the
service present.

**Fix:** Introduce a routing branch in `set_trv_offset` (or a separate
`set_trv_offset_generic`) that chooses the correct service based on which
detection path fired. The simplest safe approach: check whether the
`temperature_offset` attribute is present (generic path — write it back via
`climate.set_temperature` does not apply offsets, so this may need a
brand-specific `climate_manager` service or defer to a future phase), and
only call `tado_x.set_temperature_offset` when the service exists. At minimum,
add a guard before the service call:

```python
async def set_trv_offset(
    hass: HomeAssistant, entity_id: str, offset: float
) -> None:
    state = hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        return

    # Route: Tado X service takes priority; attribute-only TRVs have no
    # write path yet — skip silently rather than raising ServiceNotFound.
    if not hass.services.has_service("tado_x", "set_temperature_offset"):
        return  # No write path available for this brand

    await hass.services.async_call(
        "tado_x",
        "set_temperature_offset",
        {"entity_id": entity_id, "offset": offset},
        blocking=True,
    )
```

This is still incomplete for non-Tado brands, but stops the silent log flood.
`supports_offset_calibration` should align: if there is no write path
(attribute present, tado_x service absent), return `False`.

---

### CR-02: `set_calibration_config` mutates in-memory state before `async_save` with no rollback

**File:** `custom_components/climate_manager/websocket.py:1011-1017`

**Issue:** Every other write handler in `websocket.py` (including
`set_global_mode`, `set_room_config`, `set_zone_mode`, `delete_zone`, etc.)
follows the CR-01 snapshot pattern: take a backup of the affected key, mutate,
try `async_save`, and restore the backup on failure. `set_calibration_config`
is the only write handler that mutates `runtime_config["calibration_enabled"]`
**before** `async_save` without wrapping the save in `try/except` and without
a backup. If `async_save` raises (e.g., I/O error, JSON serialization failure),
the in-memory state reads `True`/`False` while the stored file still holds the
old value. The next restart will reload the stale stored value, creating a
silent inconsistency.

**Fix:** Apply the same pattern as all other write handlers:

```python
old_value = entry.runtime_data.runtime_config.get("calibration_enabled")
entry.runtime_data.runtime_config["calibration_enabled"] = msg["enabled"]
try:
    await entry.runtime_data.store.async_save(
        entry.runtime_data.runtime_config
    )
except Exception as exc:  # noqa: BLE001
    entry.runtime_data.runtime_config["calibration_enabled"] = old_value
    connection.send_error(
        msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
    )
    return
connection.send_result(msg["id"], {"success": True})
```

---

## Warnings

### WR-01: New TRV functions miss the `"unknown"` state guard

**File:** `custom_components/climate_manager/trv.py:58-61, 106-109, 157-160`

**Issue:** `set_trv_temperature`, `set_trv_off`, and `set_trv_offset` all guard
against `state.state == "unavailable"` but not against `"unknown"`. A HA
climate entity enters state `"unknown"` during startup, reconnect, or when
the device has not yet reported a reading. Issuing service calls to an entity
in state `"unknown"` is not a no-op — the call is dispatched and may silently
fail or produce incorrect device behavior.

The coordinator's own sensor guards (lines 328-332 and 471, 490) already
include `"unknown"` alongside `"unavailable"`. The TRV functions are
inconsistent with this established pattern.

**Fix:** Extend all three guards:

```python
if state is None or state.state in ("unavailable", "unknown"):
    return
```

---

### WR-02: Calibration offset accumulates without an upper/lower clamp

**File:** `custom_components/climate_manager/coordinator.py:349-364`

**Issue:** The calibration formula:

```python
delta = sensor_temp - current_temp
new_offset = existing_offset + delta
```

applies `delta` to the running `existing_offset` every minute the condition
`abs(delta) > threshold` holds. If the sensor reading is noisy or the TRV
takes several minutes to reflect the applied offset (common over Zigbee), the
offset can grow to extreme values (e.g., ±10°C or beyond) before the loop
stabilizes. Most TRV devices have a hardware-enforced maximum offset range
(e.g., ±5°C for Tado X); a value outside that range will cause the service
call to fail with a validation error. Successive failed calls are silently
swallowed by the `BLE001` handler, so the operator gets no feedback that the
offset has blown past the device limit.

**Fix:** Clamp `new_offset` to a reasonable hardware-safe range. A constant
like `OFFSET_MAX = 5.0` (degrees C) is appropriate for common TRVs:

```python
_OFFSET_CLAMP = 5.0  # degrees C — typical TRV hardware limit

new_offset = max(-_OFFSET_CLAMP, min(_OFFSET_CLAMP, existing_offset + delta))
```

This prevents runaway accumulation and keeps calls within the device's accepted
range.

---

### WR-03: `ha-switch` component API not verified for HA 2026.x

**File:** `frontend/src/components/global-settings-tab.ts:535-538`

**Issue:** The project memory records that `ha-textfield`, `ha-select`, and
`ha-tabs` are broken or removed in HA 2026.x. The Options card uses
`ha-switch` with a `@change` event handler that reads `event.target.checked`.
`ha-switch` is not recorded in the memory as broken, but it has not been
affirmatively verified either. If `ha-switch` has been changed in HA 2026.x
to not expose a `checked` property on its `change` event target (e.g., if it
fires a synthetic event), `_onCalibrationToggle` will receive `undefined` for
`enabled`, which will be passed as-is to `setCalibrationConfig(undefined)`.
The voluptuous `bool` schema on the backend will then reject the message, and
the UI will show "Save failed" with no useful explanation.

**Fix:** Before shipping, verify `ha-switch` behavior in HA 2026.x. If broken,
replace with a native `<input type="checkbox">` styled with HA CSS variables,
consistent with the `<input type="number">` workaround already applied to
temperature fields. A safe defensive pattern that works regardless:

```typescript
private _onCalibrationToggle = async (e: Event) => {
  const target = e.target as HTMLInputElement | null;
  if (!target) return;
  // ha-switch may expose 'checked' as a property; fall back to attribute
  const enabled = "checked" in target ? target.checked : false;
  // ...
};
```

---

### WR-04: `calibration_threshold` typed in `ClimateConfig` but no mutation path exists

**File:** `frontend/src/types.ts:77`, `frontend/src/ws-client.ts` (absent)

**Issue:** `ClimateConfig` declares `calibration_threshold?: number` (line 77
of `types.ts`), correctly reflecting that `const.py` seeds `DEFAULT_CONFIG`
with `"calibration_threshold": 0.5`. However, there is no WebSocket command
to change this value — `ws-client.ts` provides `setCalibrationConfig(enabled)`
only. The UI also exposes no control for the threshold. The field is present in
`get_config` responses (because `DEFAULT_CONFIG` keys appear there) but is
permanently stuck at `0.5` with no way for the operator to tune it.

This is either an incomplete feature (the threshold control was planned but not
implemented in phase 09) or a dead type declaration. Either way it creates a
misleading contract: the type says the value is configurable, but it is not.

**Fix:** If the threshold is intentionally not user-configurable in this phase,
remove `calibration_threshold` from `ClimateConfig` to avoid the misleading
declaration, and add a comment in `const.py` that it is a compile-time constant.
If it is planned for a future phase, add a `TODO(phase-10)` comment in both
files so the gap is tracked.

---

## Info

### IN-01: Line-length violations in `trv.py` and `websocket.py` docstrings

**File:** `custom_components/climate_manager/trv.py:9, 34-35, 81, 88` and
`custom_components/climate_manager/websocket.py:13-21, 140, 149, 173`

**Issue:** CLAUDE.md specifies a maximum of 80 characters per line for Python
files. Multiple docstring lines in both files exceed this limit (up to 100
characters in `websocket.py` comments). `make lint` will report editorconfig
violations on these lines.

**Fix:** Wrap the offending docstring lines to 80 characters. These are comment
lines only — no logic change required.

---

### IN-02: Test 13 masks the attribute-path / service routing inconsistency (CR-01)

**File:** `tests/test_trv.py:192-204`

**Issue:** `test_set_trv_offset_issues_single_service_call` sets up the entity
with `{"temperature_offset": 0.0}` (attribute path triggers in
`supports_offset_calibration`) **and** registers `async_mock_service(hass,
"tado_x", "set_temperature_offset")`. The test therefore only exercises the
path where both the attribute and the service are present simultaneously. There
is no test for the scenario where the attribute is present but the `tado_x`
service is absent — the case that exercises the bug identified in CR-01.

**Fix:** Add a test:

```python
async def test_set_trv_offset_fails_gracefully_without_tado_service(hass):
    """set_trv_offset with temperature_offset attr but no tado_x service
    should not call any service (no write path available).
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature_offset": 0.0})
    # tado_x service NOT registered — simulates non-Tado brand TRV
    # set_trv_offset should return without raising
    await set_trv_offset(hass, CLIMATE_ENTITY, 1.5)
    # No assertion on calls — the point is no ServiceNotFound exception raised
```

This test will fail until CR-01 is fixed, which is the desired RED→GREEN cycle.

---

### IN-03: No test for `set_calibration_config` rejection of non-bool payload

**File:** `tests/test_websocket.py:1122-1168`

**Issue:** The docstring for `ws_set_calibration_config` references T-09-01:
`vol.Required("enabled"): bool rejects non-bool payloads before the handler
runs`. But `tests/test_websocket.py` only tests `enabled: True` and
`enabled: False` — there is no test asserting that `enabled: 1`, `enabled: "true"`,
or a missing `enabled` key causes the WS handler to return an error response
without mutating `runtime_config`. The coverage for the schema guard is absent.

**Fix:** Add a test:

```python
async def test_ws_set_calibration_config_rejects_non_bool(hass, hass_ws_client):
    """set_calibration_config rejects non-bool enabled values (T-09-01)."""
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/set_calibration_config", "enabled": 1}
    )
    msg = await client.receive_json()

    assert msg["success"] is False
    # runtime_config must not have been mutated
    assert "calibration_enabled" not in entry.runtime_data.runtime_config \
        or entry.runtime_data.runtime_config["calibration_enabled"] is False
```

---

_Reviewed: 2026-05-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
