# Phase 9: TRV Temperature Offset Auto-Calibration - Pattern Map

**Mapped:** 2026-05-30
**Files analyzed:** 7 (2 modified Python files, 1 const, 1 WS file, 3 frontend
files)
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `trv.py` (add 2 functions) | utility | request-response | `trv.py` existing functions | exact |
| `coordinator.py` (add 2 methods) | service | batch + request-response | `coordinator.py` `_push_safely` + gather pass | exact |
| `const.py` (extend DEFAULT_CONFIG) | config | — | `const.py` existing DEFAULT_CONFIG block | exact |
| `websocket.py` (add 1 command) | middleware | request-response | `websocket.py` `_make_ws_set_room_config` | exact |
| `global-settings-tab.ts` (add card) | component | request-response | `global-settings-tab.ts` `_renderTemperaturesCard` | exact |
| `ws-client.ts` (add 1 method) | utility | request-response | `ws-client.ts` `setGlobalMode` / `setPeriodTemperatures` | exact |
| `types.ts` (extend interface) | config | — | `types.ts` `ClimateConfig` interface | exact |

---

## Pattern Assignments

### `trv.py` — `supports_offset_calibration()`
(utility, capability guard)

**Analog:** `trv.py` `supports_hvac_off` (lines 80–94)

**Capability guard pattern** (lines 80–94):
```python
def supports_hvac_off(hass: HomeAssistant, entity_id: str) -> bool:
    """Return True if the TRV entity advertises HVACMode.OFF in its hvac_modes attribute.

    Returns False when:
    - The entity state is missing (None) — ROOM-03 parity
    - The hvac_modes attribute is absent or None
    - HVACMode.OFF.value ("off") is not in the list
    ...
    """
    state = hass.states.get(entity_id)
    if state is None:
        return False
    return HVACMode.OFF.value in (state.attributes.get("hvac_modes") or [])
```

**New function must follow this exact pattern:**
- Sync function (no `async`)
- Docstring documents every False-return condition
- `state is None` guard as first check (no `state.state == "unavailable"` —
  capability can still be detected when unavailable, matching the existing
  `supports_hvac_off` which only guards on `None`)
- Attribute presence check first (brand-agnostic), service registry check
  second (Tado X-specific): `hass.services.has_service("tado_x",
  "set_temperature_offset")`
- Never raises

---

### `trv.py` — `set_trv_offset()`
(utility, service call helper)

**Analog:** `trv.py` `set_trv_off` (lines 97–116), also modeled on
`set_trv_temperature` (lines 45–77)

**Service call helper pattern** (lines 97–116):
```python
async def set_trv_off(hass: HomeAssistant, entity_id: str) -> None:
    """Issue a single climate.set_hvac_mode=off call ...

    Silently skips the entity if its state is None or "unavailable" (ROOM-03 / T-01-08).
    """
    # Availability guard (ROOM-03, T-01-08): skip missing or unavailable TRVs
    state = hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        return

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": HVACMode.OFF.value},
        blocking=True,
    )
```

**New `set_trv_offset` must follow this exact pattern:**
- `async def` with `hass`, `entity_id`, `offset: float` parameters
- Docstring: "Silently skips the entity if its state is None or 'unavailable'
  (ROOM-03 parity)."
- Availability guard: `if state is None or state.state == "unavailable": return`
- Single `hass.services.async_call("tado_x", "set_temperature_offset",
  {"entity_id": entity_id, "offset": offset}, blocking=True)`
- Caller (coordinator) is responsible for the capability guard before calling
  this function — document this in the docstring

---

### `coordinator.py` — `_async_calibrate()` and `_async_calibrate_room()`
(service, batch + request-response)

**Analog 1:** `coordinator.py` push pass in `async_evaluate` (lines 256–274)

**asyncio.gather concurrency pattern** (lines 256–274):
```python
await asyncio.gather(
    *(
        (
            self._push_off_safely(entity_id, desired_temps[area_id])
            if supports_hvac_off(self._hass, entity_id)
            else self._push_safely(
                entity_id, desired_temps[area_id], "ZONE_EVAL_OFF"
            )
        )
        if area_id in mode_off_rooms
        else self._push_safely(
            entity_id, desired_temps[area_id], "ZONE_EVAL"
        )
        for area_id, entity_ids in rooms.items()
        for entity_id in entity_ids
        if area_id in desired_temps
        and is_trv_entity(self._hass, entity_id)
    )
)
```

**Analog 2:** `coordinator.py` `_push_safely` (lines 418–427)

**Exception-absorbing wrapper pattern** (lines 418–427):
```python
async def _push_safely(
    self, entity_id: str, desired_temp: float, context: str
) -> None:
    """Wrapper around _push_if_changed that logs exceptions instead of propagating them."""
    try:
        await self._push_if_changed(entity_id, desired_temp)
    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Failed to push temperature to %s in %s", entity_id, context
        )
```

**Analog 3:** `coordinator.py` `_build_status_payload` sensor read guard
(lines 375–403) for the sensor state guard pattern:
```python
if sensor_state is None or sensor_state.state not in (
    "unavailable",
    "unknown",
):
    try:
        room_entry["temperature"] = float(sensor_state.state)
    except (ValueError, TypeError):
        pass
```

**`_async_calibrate` must follow these conventions:**
- Called from end of `async_evaluate()`, after the push pass
  `asyncio.gather` (D-01)
- First line: `if not config.get("calibration_enabled", False): return` (D-04)
- Body: `asyncio.gather(*(self._async_calibrate_room(...) for ...))`
- Filter: `is_trv_entity(self._hass, entity_id)` as inline guard (same as
  push pass)
- No context string parameter (unlike `_push_safely`) — calibration failures
  log entity_id directly

**`_async_calibrate_room` must follow these conventions:**
- Private method: `async def _async_calibrate_room(self, area_id, entity_id, config)`
- All early-return guards documented with their decision reference (CALIB-05,
  D-14, CALIB-03, D-08, ROOM-03, Pitfall 2, Pitfall 5)
- Sensor state guard: `if sensor_state.state in ("unavailable", "unknown")`
  — both values, matching `_build_status_payload` guard at lines 375–379
- `float()` cast wrapped in `try/except (ValueError, TypeError)` — same as
  lines 382–384
- `current_temperature is None` guard before `float()` cast (Pitfall 2)
- Exception from `set_trv_offset` caught with `# noqa: BLE001`, logged as
  `_LOGGER.warning(...)` — never propagated (Pitfall 3 / `_push_safely` parity)
- No `async_create_task` or bus events — calibration is fire-and-forget within
  the gather

**Call site in `async_evaluate`** — add after line 278 (after `hass.bus.async_fire`):
```python
await self._async_calibrate(config)
```

---

### `const.py` — extend `DEFAULT_CONFIG`
(config)

**Analog:** `const.py` `DEFAULT_CONFIG` block (lines 180–194)

**Existing DEFAULT_CONFIG tail** (lines 180–194):
```python
DEFAULT_CONFIG: dict = {
    "version": STORAGE_VERSION,
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
    "global_time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    "rooms": {},
    "persons": {},
    "default_zone_name": "Home",
    "zones": {},
}
```

**Two new top-level keys to append (D-09):**
```python
    "calibration_enabled": False,   # CALIB-01: global on/off toggle
    "calibration_threshold": 0.5,   # CALIB-04: jitter guard in °C
```

**Conventions to follow:**
- Inline comment on each new key citing the requirement ID (CALIB-01, CALIB-04)
- `False` not `false` (Python bool) for `calibration_enabled`
- `0.5` as a float literal for `calibration_threshold`
- No import changes needed — no new dependencies

---

### `websocket.py` — `_make_ws_set_calibration_config()`
(middleware, request-response)

**Analog:** `websocket.py` `_make_ws_set_global_mode` (lines 275–301) — the
simplest write command: single key mutation, persist, send result.

**Factory + schema pattern** (lines 275–301):
```python
def _make_ws_set_global_mode(entry: ClimateManagerConfigEntry):
    """Factory: create set_global_mode handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_global_mode",
            vol.Required("mode"): vol.In(VALID_MODES),
        }
    )
    @websocket_api.async_response
    async def ws_set_global_mode(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Set global mode, persist, and re-evaluate."""
        entry.runtime_data.runtime_config["global_mode"] = msg["mode"]
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_global_mode
```

**Key difference for `_make_ws_set_calibration_config`:**
- Schema: `vol.Required("enabled"): bool` (not `vol.In(...)`)
- Mutates `runtime_config["calibration_enabled"] = msg["enabled"]`
- **No `hass.async_create_task(coordinator.async_evaluate())`** — Pitfall 4
  from RESEARCH.md: calibration config does not need immediate re-evaluation
- No rollback needed (no ValueError risk from a single boolean top-level key)

**Registration call in `async_register_commands`** (lines 73–111):
```python
websocket_api.async_register_command(
    hass, _make_ws_set_calibration_config(entry)
)
```
Add this call at the end of the `async_register_commands` function body, after
the last existing registration at line 110.

---

### `global-settings-tab.ts` — `_renderOptionsCard()`
(component, request-response)

**Analog:** `global-settings-tab.ts` `_renderTemperaturesCard` (lines 454–496)
for the ha-card + card-header + card-content structure.

**Card render method pattern** (lines 454–496):
```typescript
private _renderTemperaturesCard() {
  const temps = this.config.period_temperatures;

  const tempField = (id: string, label: string) => html`...`;

  return html`
    <ha-card>
      <div class="card-header">Temperatures</div>
      <div class="card-content">
        ...
        <button class="reset-btn" @click=${this._onResetTemperatures}>
          Reset to default
        </button>
      </div>
    </ha-card>
  `;
}
```

**Auto-save arrow function pattern** (lines 321–344) — for the toggle handler:
```typescript
private _onResetTemperatures = async () => {
  try {
    await this.ws.resetPeriodTemperatures();
    await this.panel.reloadConfig();
    this.panel.showToast("Reset to defaults", false);
  } catch {
    this.panel.showToast("Reset failed — retrying...", true);
  }
};
```

**`_renderOptionsCard` must follow these conventions:**
- Arrow function class field for `_onCalibrationToggle` (not a method) —
  ensures correct `this` binding in Lit event listeners (see comment at
  lines 288–293)
- Read `this.config.calibration_enabled ?? false` for the initial toggle state
- Render `<ha-switch .checked=${enabled} @change=${this._onCalibrationToggle}>`
- Label text: "Auto-calibrate TRV temperature offsets" (from D-12)
- Card header: "Options" (from D-11)
- New CSS class `.option-row` for the toggle label+switch layout — use `display:
  flex; align-items: center; justify-content: space-between` pattern

**`render()` method** (lines 498–502) — add the new card call:
```typescript
render() {
  return html`
    ${this._renderStatusCard()}
    ${this._renderTemperaturesCard()}
    ${this._renderOptionsCard()}
  `;
}
```

**CSS location:** Add `.option-row` and `.option-label` to the existing
`static styles = css\`...\`` block (lines 117–286). Follow the naming pattern
of `.status-row` / `.status-label` already present.

---

### `ws-client.ts` — `setCalibrationConfig()`
(utility, request-response)

**Analog:** `ws-client.ts` `setGlobalMode` (lines 38–42) — simplest
mutating method: one parameter, `sendMessagePromise`, returns
`Promise<{ success: boolean }>`.

**sendMessagePromise pattern** (lines 38–42):
```typescript
/** Set the global heating mode. */
setGlobalMode(mode: string): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/set_global_mode",
    mode,
  });
}
```

**New method:**
```typescript
/** Enable or disable TRV offset auto-calibration globally. */
setCalibrationConfig(enabled: boolean): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/set_calibration_config",
    enabled,
  });
}
```

**Conventions:**
- JSDoc comment above the method (all existing methods have one)
- Return type explicit: `Promise<{ success: boolean }>`
- Property shorthand `enabled,` not `enabled: enabled`
- Append after the last existing method `subscribeStatus` (line 193)

---

### `types.ts` — extend `ClimateConfig`
(config)

**Analog:** `types.ts` `ClimateConfig` interface (lines 63–74)

**Existing ClimateConfig** (lines 63–74):
```typescript
export interface ClimateConfig {
  global_mode: string;
  period_temperatures: Record<string, number>;
  global_time_program: DailyProgram;
  /** D-03: Default Zone display name. Always present in get_config payloads. */
  default_zone_name: string;
  /** ZONE-01: custom zones keyed by UUID. Empty = all rooms in Default Zone. */
  zones: Record<string, ZoneConfig>;
  rooms: Record<string, RoomConfig>;
  persons: Record<string, PersonConfig>;
  climate_entities: string[];
}
```

**Two new optional fields to append (D-09):**
```typescript
  /** CALIB-01: global calibration on/off. Absent = false (sparse config). */
  calibration_enabled?: boolean;
  /** CALIB-04: jitter threshold in °C. Absent = 0.5 (sparse config). */
  calibration_threshold?: number;
```

**Conventions:**
- Optional (`?`) — sparse config model; absent key in payload = backend default
- JSDoc comment citing the requirement ID (CALIB-01, CALIB-04)
- Append before the closing `}` of the `ClimateConfig` interface

---

## Shared Patterns

### Availability Guard
**Source:** `custom_components/climate_manager/trv.py` lines 58–61
**Apply to:** `set_trv_offset` and `_async_calibrate_room`
```python
state = hass.states.get(entity_id)
if state is None or state.state == "unavailable":
    return
```

### Sensor State Guard (3-layer)
**Source:** `custom_components/climate_manager/coordinator.py` lines 375–384
**Apply to:** `_async_calibrate_room` for all sensor reads
```python
sensor_state = self._hass.states.get(sensor_entity_id)
if sensor_state is None or sensor_state.state in ("unavailable", "unknown"):
    return
try:
    sensor_temp = float(sensor_state.state)
except (ValueError, TypeError):
    return
```

### Exception-absorbing wrapper (no-propagate pattern)
**Source:** `custom_components/climate_manager/coordinator.py` lines 418–427
**Apply to:** The `try/except` block wrapping `set_trv_offset` inside
`_async_calibrate_room`
```python
try:
    await set_trv_offset(self._hass, entity_id, new_offset)
except Exception:  # noqa: BLE001
    _LOGGER.warning(
        "Failed to apply offset %.1f to %s", new_offset, entity_id
    )
```

### Write-then-send WebSocket pattern (no re-evaluate variant)
**Source:** `custom_components/climate_manager/websocket.py` lines 293–299
**Apply to:** `ws_set_calibration_config` — same persist + send_result, but
**omit** the `async_create_task(coordinator.async_evaluate())` line (Pitfall 4)
```python
entry.runtime_data.runtime_config["calibration_enabled"] = msg["enabled"]
await entry.runtime_data.store.async_save(
    entry.runtime_data.runtime_config
)
connection.send_result(msg["id"], {"success": True})
# NOTE: no async_evaluate trigger here — see RESEARCH Pitfall 4
```

### Auto-save with toast (frontend)
**Source:** `frontend/src/components/global-settings-tab.ts` lines 336–344
**Apply to:** `_onCalibrationToggle` arrow function
```typescript
private _onResetTemperatures = async () => {
  try {
    await this.ws.resetPeriodTemperatures();
    await this.panel.reloadConfig();
    this.panel.showToast("Reset to defaults", false);
  } catch {
    this.panel.showToast("Reset failed — retrying...", true);
  }
};
```

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Test File Patterns

The phase also extends three test files. Their structure analogs:

### `tests/test_trv.py` — add `supports_offset_calibration` and `set_trv_offset` tests
**Analog:** `tests/test_trv.py` `supports_hvac_off` and `set_trv_off` tests
(file lines 1–16 for import pattern)
```python
from pytest_homeassistant_custom_component.common import async_mock_service
from custom_components.climate_manager.trv import (
    supports_offset_calibration,
    set_trv_offset,
)
```
Service mock pattern: `async_mock_service(hass, "tado_x",
"set_temperature_offset")` — same pattern as existing `async_mock_service(hass,
"climate", "set_hvac_mode")`.

### `tests/test_coordinator.py` — add calibration tests
**Analog:** `tests/test_coordinator.py` lines 1–50 for import and fixture
patterns. New tests use the same `MockConfigEntry + hass` fixture and
`async_mock_service` for `tado_x.set_temperature_offset`.

### `tests/test_websocket.py` — add `set_calibration_config` test
**Analog:** Existing WS tests in `tests/test_websocket.py` follow the pattern
of sending a WS message and asserting `runtime_config` mutation.

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `frontend/src/`
**Files scanned:** 7 source files (full reads), 3 test files (partial reads)
**Pattern extraction date:** 2026-05-30
