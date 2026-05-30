# Phase 9: TRV Temperature Offset Auto-Calibration - Research

**Researched:** 2026-05-30
**Domain:** Home Assistant integration — TRV offset calibration engine + Global
Settings UI toggle
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Calibration runs as `_async_calibrate()` called from the end of
  `async_evaluate()` — after the temperature push pass.
- **D-02:** Calibration fires every `async_evaluate` cycle (every minute). No
  separate timer. The delta threshold prevents unnecessary service calls.
- **D-03:** Calibration pass uses `asyncio.gather()` over all rooms, same
  concurrency pattern as the temperature push. Per-room logic delegated to
  `_async_calibrate_room(area_id, entity_id, ...)`.
- **D-04:** Calibration is skipped entirely when `calibration_enabled` is
  `False`. No service calls, no attribute reads.
- **D-05:** Delta formula: `delta = room_sensor_temp − TRV.current_temperature`
- **D-06:** New offset formula:
  `new_offset = TRV.temperature_offset_attribute + delta`
  (incremental; reads current offset from
  `hass.states.get(entity_id).attributes.get("temperature_offset", 0.0)`)
- **D-07:** Offset service call only when `abs(delta) > calibration_threshold`
  (default 0.5°C).
- **D-08:** Capability guard: checks for `temperature_offset` attribute OR
  `tado_x.set_temperature_offset` service registration. Silent skip when neither
  is present.
- **D-09:** Two new keys in `DEFAULT_CONFIG`: `calibration_enabled: False`,
  `calibration_threshold: 0.5`.
- **D-10:** New WebSocket command `climate_manager/set_calibration_config`.
  Accepts `{"enabled": bool}`. Follows sparse-merge pattern of `set_room_config`.
- **D-11:** New "Options" ha-card added to `global-settings-tab.ts` as the
  third card (after Current Status and Temperatures).
- **D-12:** Toggle rendered as `<ha-switch>` with label "Auto-calibrate TRV
  temperature offsets". Auto-saves on `change` event. No Save button.
- **D-13:** Options card always rendered when at least one option is present —
  not conditioned on TRV compatibility.
- **D-14:** Calibration uses only the manually configured `temperature_sensor`
  key from `rooms[area_id]` config. No fallback to auto-discovered sensors.

### Claude's Discretion

None specified — all major decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- Configurable calibration interval
- Threshold UI input (threshold stays at 0.5°C default; not surfaced in panel)
- Auto-discovered sensor fallback
- Any brand-specific Tado X API calls (service call via HA service bus only)
- Calibration for rooms without `temperature_sensor` in room config
- Multi-language support
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CALIB-01 | User can enable/disable TRV offset auto-calibration globally from the Global Settings tab | `ha-switch` toggle in "Options" card; `calibration_enabled` key in config; WS command `set_calibration_config` |
| CALIB-02 | When enabled, coordinator periodically computes delta between room sensor and TRV current_temperature, calls offset service if TRV supports it | `_async_calibrate()` in `async_evaluate()` after push pass; `asyncio.gather()` per-room concurrency; `set_trv_offset()` helper |
| CALIB-03 | Calibration guard detects whether TRV supports offset adjustment; rooms without compatible TRV are silently skipped | `supports_offset_calibration()` checks `temperature_offset` attribute or `tado_x.set_temperature_offset` service; silent return |
| CALIB-04 | Configurable minimum delta threshold (default 0.5°C) prevents jitter | `calibration_threshold` in `DEFAULT_CONFIG`; `abs(delta) > threshold` guard in `_async_calibrate_room()` |
| CALIB-05 | Calibration only runs when room has a reference temperature sensor configured; rooms without sensor are silently skipped | Read `rooms[area_id].get("temperature_sensor")` from `runtime_config`; absent → return immediately |
</phase_requirements>

---

## Summary

Phase 9 adds a TRV temperature offset auto-calibration engine to the existing
coordinator. The implementation is additive: two new private methods in
`coordinator.py`, one new helper function and one new capability guard in
`trv.py`, two new constants in `const.py`, one new WebSocket command in
`websocket.py`, and a new "Options" card section in the Global Settings tab
frontend component.

All locked decisions are high-confidence because they were derived directly from
the existing codebase patterns during the Phase 9 CONTEXT discussion. No
external dependencies are introduced. The Tado X compatibility analysis
(260528-417) confirmed that `tado_x.set_temperature_offset` is the correct
service name to detect for the capability guard, and that the `temperature_offset`
attribute is the standard attribute to read for the current offset value.

The implementation follows four established patterns without deviation:
`supports_hvac_off` → `supports_offset_calibration`; `set_trv_temperature` →
`set_trv_offset`; `_push_safely` + `asyncio.gather` → `_async_calibrate` +
`asyncio.gather`; `_make_ws_set_room_config` sparse-merge → new calibration WS
command.

**Primary recommendation:** Implement strictly to the locked decisions. No new
patterns are required — every required piece has a direct precedent in the
existing codebase.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Calibration enabled/disabled toggle | Backend (HA integration) | Frontend panel | Config persisted by backend; toggle is UI surface only |
| Offset delta computation | Backend (coordinator.py) | — | Reads live HA state; must run server-side |
| TRV capability detection | Backend (trv.py) | — | Must query HA service registry and entity state |
| Offset service call | Backend (trv.py) | — | `hass.services.async_call` — backend only |
| Config persistence | Backend (storage) | — | Store.async_save — same as all other config writes |
| Toggle UI | Frontend panel | — | `ha-switch` in `global-settings-tab.ts` |
| WS protocol bridge | Backend (websocket.py) | Frontend (ws-client.ts) | Command registered backend, called from frontend |

---

## Standard Stack

No new packages are required. This phase uses only the existing integration
stack.

### Core (already installed)

| Component | Version | Purpose |
|-----------|---------|---------|
| `homeassistant.core.HomeAssistant` | HA 2025.x/2026.x | `hass.states.get`, `hass.services` |
| `homeassistant.components.websocket_api` | HA 2025.x/2026.x | New WS command registration |
| `voluptuous` | bundled with HA | Schema validation for WS command payload |
| `asyncio` | stdlib | `asyncio.gather()` for concurrent room calibration |
| Lit 3.x / TypeScript 5.x | frontend stack | `ha-switch` toggle in `global-settings-tab.ts` |

### Package Legitimacy Audit

> Not applicable — no new packages are installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
async_evaluate() [coordinator.py]
    │
    ├── PASS 1: baseline temperatures per room
    ├── PASS 2: presence override
    ├── Push pass: asyncio.gather(_push_safely / _push_off_safely)
    │
    └── PASS 3 (NEW): await self._async_calibrate(config)  [D-01, D-02, D-04]
            │
            ├── calibration_enabled == False → return immediately [D-04]
            │
            └── asyncio.gather(
                    _async_calibrate_room(area_id, entity_id, config)
                    for area_id, entity_ids in rooms.items()
                    for entity_id in entity_ids
                    if is_trv_entity(hass, entity_id)
                )  [D-03]
                    │
                    ├── room has temperature_sensor? → No → return [CALIB-05, D-14]
                    ├── TRV supports offset? → No → return [CALIB-03, D-08]
                    ├── TRV unavailable? → return [ROOM-03 parity]
                    ├── sensor state valid? → No → return
                    ├── TRV current_temperature valid? → No → return
                    ├── delta = sensor_temp − current_temperature [D-05]
                    ├── abs(delta) <= threshold? → return (no jitter) [D-07]
                    └── new_offset = existing_offset + delta [D-06]
                        → set_trv_offset(hass, entity_id, new_offset)
```

### Recommended Project Structure

No structural changes — all new code goes into existing files:

```
custom_components/climate_manager/
├── trv.py            # + supports_offset_calibration(), set_trv_offset()
├── coordinator.py    # + _async_calibrate(), _async_calibrate_room()
├── const.py          # + calibration_enabled, calibration_threshold in DEFAULT_CONFIG
└── websocket.py      # + _make_ws_set_calibration_config(), registration call

frontend/src/
├── types.ts          # + calibration_enabled, calibration_threshold in ClimateConfig
├── ws-client.ts      # + setCalibrationConfig(enabled: boolean) method
└── components/
    └── global-settings-tab.ts  # + _renderOptionsCard(), CSS for toggle row
```

### Pattern 1: Capability Guard (mirrors `supports_hvac_off`)

**What:** Read entity state attributes or check service registry to determine
if a TRV supports a feature. Return `bool`.

**When to use:** Before any service call that not all TRVs support.

**Example (existing — `supports_hvac_off`):**

```python
# Source: custom_components/climate_manager/trv.py [VERIFIED: codebase]
def supports_hvac_off(hass: HomeAssistant, entity_id: str) -> bool:
    state = hass.states.get(entity_id)
    if state is None:
        return False
    return HVACMode.OFF.value in (state.attributes.get("hvac_modes") or [])
```

**New pattern for `supports_offset_calibration` (D-08):**

```python
# [ASSUMED] — exact implementation to be written; pattern derived from
# supports_hvac_off + D-08 decision
def supports_offset_calibration(hass: HomeAssistant, entity_id: str) -> bool:
    """Return True if TRV supports offset adjustment.

    Guard 1: temperature_offset attribute present in state.
    Guard 2: tado_x.set_temperature_offset service is registered.
    Either condition is sufficient (D-08).
    Returns False when entity state is None (ROOM-03 parity).
    """
    state = hass.states.get(entity_id)
    if state is None:
        return False
    if "temperature_offset" in state.attributes:
        return True
    return hass.services.has_service("tado_x", "set_temperature_offset")
```

### Pattern 2: Service Call Helper (mirrors `set_trv_temperature`)

**What:** Guard for availability, then `hass.services.async_call(blocking=True)`.

**Example (existing — `set_trv_temperature`):**

```python
# Source: custom_components/climate_manager/trv.py [VERIFIED: codebase]
async def set_trv_temperature(hass, entity_id, temperature):
    state = hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        return
    await hass.services.async_call(
        "climate", "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": "heat"}, blocking=True
    )
    await hass.services.async_call(
        "climate", "set_temperature",
        {"entity_id": entity_id, "temperature": temperature}, blocking=True
    )
```

**New pattern for `set_trv_offset` (D-08):**

```python
# [ASSUMED] — structure derived from set_trv_temperature + D-08
async def set_trv_offset(hass: HomeAssistant, entity_id: str, offset: float) -> None:
    """Call tado_x.set_temperature_offset to apply a new offset.

    Silently skips unavailable entities (ROOM-03 parity).
    The caller (coordinator) is responsible for the capability guard.
    """
    state = hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        return
    await hass.services.async_call(
        "tado_x",
        "set_temperature_offset",
        {"entity_id": entity_id, "offset": offset},
        blocking=True,
    )
```

**Important:** The Tado X service name and parameter name `offset` are confirmed
from the 260528-417 Tado X compatibility research. [CITED:
.planning/quick/260528-417-check-ha-tado-x-compatibility/417-SUMMARY.md]

### Pattern 3: Concurrent Room Loop (mirrors push pass in `async_evaluate`)

**What:** `asyncio.gather()` over all rooms with guard conditions inline.

**Example (existing — push pass):**

```python
# Source: custom_components/climate_manager/coordinator.py [VERIFIED: codebase]
await asyncio.gather(
    *(
        self._push_safely(entity_id, desired_temps[area_id], "ZONE_EVAL")
        for area_id, entity_ids in rooms.items()
        for entity_id in entity_ids
        if area_id in desired_temps
        and is_trv_entity(self._hass, entity_id)
    )
)
```

**New pattern for `_async_calibrate` (D-03):**

```python
# [ASSUMED] — structure derived from push pass + D-03
async def _async_calibrate(self, config: dict) -> None:
    if not config.get("calibration_enabled", False):
        return  # D-04: skip entirely when disabled
    rooms = self._data.rooms
    await asyncio.gather(
        *(
            self._async_calibrate_room(area_id, entity_id, config)
            for area_id, entity_ids in rooms.items()
            for entity_id in entity_ids
            if is_trv_entity(self._hass, entity_id)
        )
    )
```

### Pattern 4: WebSocket Command Factory (mirrors `_make_ws_set_room_config`)

**What:** Factory function returning a decorated `async` handler. Sparse-merge
into `runtime_config`, persist, send result.

**Key structure (existing):**

```python
# Source: custom_components/climate_manager/websocket.py [VERIFIED: codebase]
def _make_ws_set_room_config(entry):
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/set_room_config",
        vol.Required("room_id"): str,
        vol.Required("config"): dict,
    })
    @websocket_api.async_response
    async def ws_set_room_config(hass, connection, msg):
        # sparse-merge + rollback pattern
        ...
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
    return ws_set_room_config
```

**New pattern for `_make_ws_set_calibration_config` (D-10):**

The schema must accept `{"type": "climate_manager/set_calibration_config",
"enabled": bool}`. No rollback is needed (single top-level key mutation, no
ValueError risk from store.async_save). No `async_evaluate()` trigger needed —
calibration only runs during the next scheduled evaluation cycle.

### Pattern 5: Frontend Toggle (auto-save on `change`)

**What:** `<ha-switch>` fires a `change` event. Handler reads
`event.target.checked`, calls WS method, shows toast on success/error.

**Important note from CONTEXT.md (specifics section):** If `ha-switch` renders
nothing in HA 2026.x production, fall back to a styled native
`<input type="checkbox">` with identical auto-save behavior.

```typescript
// [ASSUMED] — pattern derived from existing temperature blur-save pattern
private _onCalibrationToggle = async (e: Event) => {
  const enabled = (e.target as HTMLInputElement).checked;
  try {
    await this.ws.setCalibrationConfig(enabled);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed", true);
  }
};
```

### Anti-Patterns to Avoid

- **Calling `_async_calibrate` BEFORE the push pass completes:** Calibration
  must run after the push pass so any offset applied this tick does not
  interfere with TRV setpoint state reads used in the push pass. (D-01: "at the
  end of `async_evaluate()`")
- **Raising exceptions inside `_async_calibrate_room`:** Silent returns only.
  Any exception from `set_trv_offset` must be caught and logged as a warning —
  never propagated to `asyncio.gather`. Model on `_push_safely`.
- **Reading `temperature_sensor` from `room_auto_sensors` instead of
  `runtime_config`:** D-14 is explicit: only the manually configured
  `rooms[area_id]["temperature_sensor"]` key is used. The `room_auto_sensors`
  dict (populated by `discover_room_sensors`) and the HA area registry
  `temperature_entity_id` attribute are NOT used for calibration.
- **Writing `calibration_threshold` in the UI:** The threshold stays at 0.5°C
  default. The Options card only surfaces the boolean toggle.
- **Using `async_create_task` to trigger `async_evaluate` after
  `set_calibration_config`:** The calibration setting affects future
  evaluation cycles, not the current state. Unlike `set_global_mode` or
  `set_period_temperatures`, no immediate re-evaluation is needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrent per-room processing | Custom async loop | `asyncio.gather()` | Already used in push pass; gathers exceptions via error handling wrapper |
| WS command schema validation | Manual payload checks | `voluptuous` schemas | Already used for all 17 existing commands; `vol.Required("enabled"): bool` |
| Sensor state validation | Custom try/except | Guard for `None`, `"unavailable"`, `"unknown"` + `float()` cast | Same guard used throughout coordinator.py for all sensor reads |
| HA service availability check | Introspection via states | `hass.services.has_service(domain, service)` | Standard HA API; used correctly for the `tado_x` service guard |

**Key insight:** Every mechanism needed in Phase 9 already exists in the
codebase. The implementation is strictly about composition of established
patterns, not new invention.

---

## Common Pitfalls

### Pitfall 1: `temperature_offset` Attribute vs. Current Temperature

**What goes wrong:** Developer confuses the `temperature_offset` attribute
(the TRV's calibration offset — what we read to compute new_offset) with
`current_temperature` (the TRV's measured temperature — what we use for the
delta).

**Why it happens:** Both are attributes on the TRV climate entity.
`current_temperature` is the raw sensor reading FROM the TRV; `temperature_offset`
is the correction value APPLIED to it (on some hardware, the reported
`current_temperature` may already incorporate the offset).

**How to avoid:** D-05 and D-06 are explicit:
- Delta = `rooms[area_id]["temperature_sensor"]` state → `current_temperature`
  attribute on the TRV
- New offset = `temperature_offset` attribute on the TRV + delta

**Warning signs:** If calibration seems to double-apply corrections each
minute, the implementation is likely adding delta to `current_temperature`
instead of `temperature_offset`.

### Pitfall 2: Missing Guard for `current_temperature` Being None

**What goes wrong:** A TRV that hasn't yet reported sensor data returns `None`
for `current_temperature`. Computing `delta = sensor_temp - None` raises
`TypeError` and crashes `_async_calibrate_room`, causing all subsequent rooms
in the `gather` to be affected.

**Why it happens:** `current_temperature` is legitimately absent on startup or
after connectivity loss. This is documented in `is_trv_entity` (which explicitly
notes "Missing current_temperature is not treated as a disqualifier").

**How to avoid:** In `_async_calibrate_room`, guard:
```python
current_temp = state.attributes.get("current_temperature")
if current_temp is None:
    return  # TRV hasn't reported yet — skip silently
```

**Warning signs:** `TypeError` in calibration logs on first startup.

### Pitfall 3: `hass.services.has_service` vs. Attribute Presence

**What goes wrong:** The capability guard checks ONLY the `tado_x` service
(assuming all supporting TRVs use Tado X), missing TRVs from other brands
that expose `temperature_offset` via standard climate attributes.

**Why it happens:** The D-08 decision states "either condition is sufficient."
The attribute check is the primary, brand-agnostic guard. The service check is
the Tado X-specific fallback for TRVs that expose an offset service but not the
attribute.

**How to avoid:** Check attribute FIRST (brand-agnostic), then service
(Tado X-specific). Do not reverse the order.

### Pitfall 4: Triggering `async_evaluate` After `set_calibration_config`

**What goes wrong:** Following the pattern of `set_global_mode` exactly —
calling `hass.async_create_task(coordinator.async_evaluate())` after saving
calibration config — triggers an unnecessary full evaluation cycle including
all TRV pushes.

**Why it happens:** All other write WS commands call `async_evaluate` because
they change temperatures or mode. Calibration config only changes whether offset
service calls run in the NEXT evaluation cycle.

**How to avoid:** `_make_ws_set_calibration_config` must NOT call
`async_evaluate` after saving. Just `connection.send_result(msg["id"],
{"success": True})`.

### Pitfall 5: Sensor State "unknown" Included in Delta

**What goes wrong:** A sensor that just became available may report `"unknown"`
as its state (a string, not a number). `float("unknown")` raises `ValueError`.
If the guard only checks for `"unavailable"` and `None`, "unknown" slips through.

**Why it happens:** HA sensors transition through `"unknown"` on startup.
The coordinator already guards against this for display-purpose sensor reads
(in `_build_status_payload`) but the calibration path may miss it if copied
carelessly.

**How to avoid:** In `_async_calibrate_room`, guard sensor state:
```python
sensor_state = self._hass.states.get(sensor_entity_id)
if sensor_state is None or sensor_state.state in ("unavailable", "unknown"):
    return
try:
    sensor_temp = float(sensor_state.state)
except (ValueError, TypeError):
    return
```

### Pitfall 6: `ha-switch` Rendering Failure in HA 2026.x

**What goes wrong:** `ha-switch` renders nothing visible in HA 2026.x (same
class of breakage as `ha-textfield`, `ha-tabs`, `ha-select` previously).

**How to avoid:** CONTEXT.md specifics section explicitly documents this risk
and mandates a fallback: if `ha-switch` doesn't render, replace with a styled
native `<input type="checkbox">` with identical auto-save behavior. Plan for
the fallback in implementation: test in a live HA 2026.x instance during
manual acceptance testing.

---

## Code Examples

### Reading temperature_offset from TRV state

```python
# Source: CONTEXT.md D-06 [CITED: 09-CONTEXT.md]
existing_offset = hass.states.get(entity_id).attributes.get(
    "temperature_offset", 0.0
)
```

### Full `_async_calibrate_room` skeleton

```python
# [ASSUMED] — derived from all locked decisions
async def _async_calibrate_room(
    self,
    area_id: str,
    entity_id: str,
    config: dict,
) -> None:
    """Calibrate one TRV toward the room's reference sensor.

    Silently returns when:
    - No temperature_sensor configured for this room (CALIB-05, D-14)
    - TRV doesn't support offset (CALIB-03, D-08)
    - TRV is unavailable (ROOM-03 parity)
    - Sensor state is unavailable/unknown/invalid
    - TRV current_temperature is None (not yet reported)
    - abs(delta) <= calibration_threshold (CALIB-04, D-07)
    """
    # CALIB-05, D-14: only manual temperature_sensor config
    room_config = config.get("rooms", {}).get(area_id, {})
    sensor_entity_id = room_config.get("temperature_sensor")
    if not sensor_entity_id:
        return

    # CALIB-03, D-08: capability guard
    if not supports_offset_calibration(self._hass, entity_id):
        return

    # ROOM-03 parity: unavailable TRV
    state = self._hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        return

    # Sensor state guard (Pitfall 5)
    sensor_state = self._hass.states.get(sensor_entity_id)
    if sensor_state is None or sensor_state.state in ("unavailable", "unknown"):
        return
    try:
        sensor_temp = float(sensor_state.state)
    except (ValueError, TypeError):
        return

    # current_temperature guard (Pitfall 2)
    current_temp = state.attributes.get("current_temperature")
    if current_temp is None:
        return
    try:
        current_temp = float(current_temp)
    except (ValueError, TypeError):
        return

    # D-05: delta formula
    delta = sensor_temp - current_temp

    # D-07: jitter guard
    threshold = config.get("calibration_threshold", 0.5)
    if abs(delta) <= threshold:
        return

    # D-06: incremental offset
    existing_offset = state.attributes.get("temperature_offset", 0.0)
    try:
        existing_offset = float(existing_offset)
    except (ValueError, TypeError):
        existing_offset = 0.0
    new_offset = existing_offset + delta

    try:
        await set_trv_offset(self._hass, entity_id, new_offset)
    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Failed to apply offset %.1f to %s", new_offset, entity_id
        )
```

### WebSocket command schema for `set_calibration_config`

```python
# [ASSUMED] — derived from D-10 and existing WS command patterns
@websocket_api.websocket_command({
    vol.Required("type"): f"{DOMAIN}/set_calibration_config",
    vol.Required("enabled"): bool,
})
@websocket_api.async_response
async def ws_set_calibration_config(hass, connection, msg):
    entry.runtime_data.runtime_config["calibration_enabled"] = msg["enabled"]
    await entry.runtime_data.store.async_save(
        entry.runtime_data.runtime_config
    )
    connection.send_result(msg["id"], {"success": True})
    # NOTE: no async_evaluate trigger — calibration runs on next scheduled cycle
```

### Frontend: Options card render method

```typescript
// [ASSUMED] — derived from D-11, D-12, D-13 and existing card render pattern
private _renderOptionsCard() {
  const enabled = this.config.calibration_enabled ?? false;
  return html`
    <ha-card>
      <div class="card-header">Options</div>
      <div class="card-content">
        <div class="option-row">
          <span class="option-label">
            Auto-calibrate TRV temperature offsets
          </span>
          <ha-switch
            .checked=${enabled}
            @change=${this._onCalibrationToggle}
          ></ha-switch>
        </div>
      </div>
    </ha-card>
  `;
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Manual TRV offset via Tado app | `tado_x.set_temperature_offset` via HA service | Integration can automate what was a manual UI action |
| No integration-level offset tracking | Read `temperature_offset` attribute from TRV state | Enables incremental correction without resetting to a fixed value |

**Relevant from memory:** `ha-switch` is a `ha-*` element. Per project memory,
`ha-select`, `ha-tabs`, and `ha-textfield` are broken in HA 2026.x. `ha-switch`
has not been confirmed broken — CONTEXT.md specifically chose it and documents
a checkbox fallback if it fails. [CITED: ~/.claude/projects/.../MEMORY.md]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `set_trv_offset` calls `tado_x.set_temperature_offset` with `{"entity_id": ..., "offset": ...}` as service data | Code Examples | If the parameter name differs (e.g., `temperature_offset` instead of `offset`), service call will be rejected by HA schema validation. Verify against ha-tado-x source before merging. |
| A2 | `hass.services.has_service(domain, service)` is the correct HA API to detect service registration at runtime | Standard Stack / Pitfall 3 | If HA renamed or deprecated this method in 2026.x, the guard will fail. Fallback: always rely on attribute check as primary guard. |
| A3 | `ha-switch` renders correctly in HA 2026.x | Common Pitfalls / Pitfall 6 | If broken, fallback is `<input type="checkbox">` per CONTEXT.md specifics. Low risk — plan explicitly covers fallback. |
| A4 | The `temperature_offset` attribute on a Tado X entity reflects the CURRENTLY APPLIED offset (not a user preference or a stale value) | Architecture Patterns | If the attribute is stale or represents something other than the applied offset, the incremental formula (D-06) will accumulate error. Verify empirically on live hardware. |

---

## Open Questions

1. **Tado X service data parameter name**
   - What we know: Service is `tado_x.set_temperature_offset`. The entity_id
     parameter is standard. The offset parameter name is `offset` per quick task
     417-SUMMARY.md analysis but this was inferred, not from reading ha-tado-x
     source.
   - What's unclear: Exact parameter name in the service schema
     (`offset` vs. `temperature_offset` vs. something else).
   - Recommendation: During implementation, inspect the ha-tado-x service schema
     via HA Developer Tools > Services before writing `set_trv_offset`. If it
     differs from `offset`, update the implementation — do not guess.

2. **`temperature_offset` attribute: reported before or after offset applied**
   - What we know: D-06 reads the current offset for the incremental formula.
   - What's unclear: Whether `current_temperature` on Tado X includes or
     excludes the offset. If `current_temperature` already incorporates the
     offset, the delta is accurate. If not, the calibration may converge to a
     wrong value.
   - Recommendation: Test empirically. Set a known offset in Tado app, read
     `current_temperature` and `temperature_offset` from HA, compare to the
     room sensor. Document the finding as a comment in `_async_calibrate_room`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest / pytest-homeassistant-custom-component | Tests | ✓ | pytest 9.0.2 | — |
| make test | Test runner | ✓ | GNU Make | `.venv/bin/python -m pytest tests/ -v` |
| ha-tado-x integration (live HA) | Manual acceptance testing | ✓ (user hardware) | v1.8.11 confirmed | n/a — simulation tests cover backend logic |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-homeassistant-custom-component |
| Config file | `setup.cfg` (standard pytest discovery) |
| Quick run command | `.venv/bin/python -m pytest tests/test_trv.py tests/test_coordinator.py -v` |
| Full suite command | `make test` (`.venv/bin/python -m pytest tests/ -v`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File |
|--------|----------|-----------|-------------------|------|
| CALIB-01 | `calibration_enabled` persists via WS command | unit | `make test` | ❌ Wave 0: `tests/test_websocket.py` (extend) |
| CALIB-02 | `_async_calibrate_room` calls `set_trv_offset` when enabled and conditions met | unit | `make test` | ❌ Wave 0: `tests/test_coordinator.py` (extend) |
| CALIB-03 | `supports_offset_calibration` returns False when attribute absent and service absent | unit | `make test` | ❌ Wave 0: `tests/test_trv.py` (extend) |
| CALIB-03 | `_async_calibrate_room` silently skips incompatible TRV | unit | `make test` | ❌ Wave 0: `tests/test_coordinator.py` (extend) |
| CALIB-04 | Delta ≤ 0.5°C → no service call | unit | `make test` | ❌ Wave 0: `tests/test_coordinator.py` (extend) |
| CALIB-04 | Delta > 0.5°C → service call with correct offset | unit | `make test` | ❌ Wave 0: `tests/test_coordinator.py` (extend) |
| CALIB-05 | Room without `temperature_sensor` → no service call | unit | `make test` | ❌ Wave 0: `tests/test_coordinator.py` (extend) |
| All | `calibration_enabled: False` → zero service calls | unit | `make test` | ❌ Wave 0: `tests/test_coordinator.py` (extend) |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/test_trv.py tests/test_coordinator.py -v`
- **Per wave merge:** `make test`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

All new tests extend existing files (no new test files needed for backend):

- [ ] `tests/test_trv.py` — add `supports_offset_calibration` tests:
  - returns `True` when `temperature_offset` attribute present
  - returns `True` when attribute absent but `tado_x.set_temperature_offset`
    service is registered
  - returns `False` when neither condition holds
  - returns `False` when entity state is `None`
- [ ] `tests/test_trv.py` — add `set_trv_offset` tests (mirrors `set_trv_off`
  pattern):
  - issues one `tado_x.set_temperature_offset` call with correct entity_id and
    offset value
  - silently skips unavailable entity
  - silently skips missing entity
- [ ] `tests/test_coordinator.py` — add calibration tests:
  - `calibration_enabled=False` → zero offset service calls
  - room without `temperature_sensor` → zero offset calls
  - incompatible TRV (no attribute, no service) → zero offset calls
  - delta ≤ 0.5°C → zero offset calls
  - delta > 0.5°C → one offset call with `new_offset = existing + delta`
  - sensor state "unavailable" → zero offset calls
  - sensor state "unknown" → zero offset calls
  - `current_temperature` is `None` → zero offset calls
- [ ] `tests/test_websocket.py` — add calibration WS command test:
  - `set_calibration_config {"enabled": true}` → persists `calibration_enabled:
    True` in runtime_config
  - `set_calibration_config {"enabled": false}` → persists `calibration_enabled:
    False`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | HA WebSocket auth gate (T-03-06, already in place) |
| V5 Input Validation | yes | `vol.Required("enabled"): bool` in WS schema rejects invalid payloads |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Invalid payload to `set_calibration_config` | Tampering | `voluptuous` schema rejects non-bool `enabled` before handler runs (T-03-04 parity) |
| Offset injection via spoofed sensor | Tampering | Sensor entity_id is read from `runtime_config["rooms"]` (server-side) — never from WS payload |

---

## Project Constraints (from CLAUDE.md)

- **TRV interface**: Standard HA `climate` entity + named services only. Tado X
  support is via `tado_x.set_temperature_offset` service — not a direct API call.
- **Code style**: 4-space indent Python, 2-space indent TypeScript/JS, max 80
  chars per line, LF line endings, final newline, no trailing whitespace.
- **Run `make lint` before committing** (editorconfig enforcement via pre-commit).
- **Build frontend with `make build`** before deploy; test with `make test`.
- **No external PyPI dependencies** in v1 — this phase introduces none.
- **GSD workflow**: All file changes through GSD execute phase; no direct edits
  outside workflow.

---

## Sources

### Primary (HIGH confidence)

- `custom_components/climate_manager/trv.py` — `supports_hvac_off`,
  `set_trv_temperature`, `set_trv_off` patterns [VERIFIED: codebase]
- `custom_components/climate_manager/coordinator.py` — `async_evaluate`,
  `_push_safely`, `asyncio.gather` concurrency pattern [VERIFIED: codebase]
- `custom_components/climate_manager/const.py` — `DEFAULT_CONFIG` schema,
  sparse config pattern [VERIFIED: codebase]
- `custom_components/climate_manager/websocket.py` — factory function pattern,
  sparse-merge, voluptuous schema, 17 existing commands [VERIFIED: codebase]
- `frontend/src/components/global-settings-tab.ts` — existing card render
  structure, auto-save pattern [VERIFIED: codebase]
- `frontend/src/ws-client.ts` — `sendMessagePromise` method pattern [VERIFIED:
  codebase]
- `frontend/src/types.ts` — `ClimateConfig` interface [VERIFIED: codebase]
- `.planning/phases/09-trv-temperature-offset-auto-calibration/09-CONTEXT.md`
  — all locked decisions D-01 through D-14 [VERIFIED: codebase]

### Secondary (MEDIUM confidence)

- `.planning/quick/260528-417-check-ha-tado-x-compatibility/417-SUMMARY.md`
  — confirms `tado_x.set_temperature_offset` service name and `temperature_offset`
  attribute pattern [CITED: project research artifact]

### Tertiary (LOW confidence)

- `set_trv_offset` service data parameter name (`offset`) — inferred from 417
  analysis, not verified against ha-tado-x source code. Flagged as A1 in
  Assumptions Log.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new dependencies; all existing
- Architecture: HIGH — all patterns have direct precedents in the codebase;
  decisions are locked from CONTEXT discussion
- Pitfalls: HIGH — derived from existing guard patterns in the codebase;
  verified against coordinator.py sensor read guards
- Tado X service parameter name: LOW — inferred from compatibility analysis,
  not verified against ha-tado-x source

**Research date:** 2026-05-30
**Valid until:** 2026-06-30 (stable HA integration patterns; Tado X service
schema could change with ha-tado-x updates)
