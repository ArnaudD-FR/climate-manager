---
phase: 05-zone-crud-evaluation-engine
reviewed: 2026-05-27T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - custom_components/climate_manager/websocket.py
  - tests/test_websocket.py
  - custom_components/climate_manager/coordinator.py
  - tests/test_coordinator.py
findings:
  critical: 2
  warning: 3
  info: 2
  total: 7
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-27
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Four files were reviewed: the two primary implementation files from phase 05 (`websocket.py`, `coordinator.py`) and their corresponding test files. Cross-referencing was performed against `storage.py`, `const.py`, `schedule.py`, `trv.py`, and `__init__.py`.

Two blockers were found. The first is a logic error in `validate_zone_assignment` that actively prevents the zones feature from being used with more than one room per zone — which is the whole point of zones. The second is a type inconsistency between the two code paths that serve room status to the panel, causing `temperature` and `humidity` to be strings in push events but floats in `get_status` responses. Three warnings and two info items cover missing rollback, confusing variable naming, and test gaps.

---

## Critical Issues

### CR-01: `validate_zone_assignment` prevents multiple rooms per zone — zones are non-functional for their core purpose

**File:** `custom_components/climate_manager/storage.py:43-60`

**Issue:** `validate_zone_assignment` accumulates zone UUIDs in `seen_zone_ids` and raises `ValueError` whenever a second room carries the same `zone_id`. This enforces a "one room per zone" constraint that directly contradicts the zones feature: a zone exists to group multiple rooms under a shared mode and schedule. Any attempt to assign two rooms to the same zone — via `set_room_config` — results in a `ValueError` from `async_save`, which is caught and returned as `ERR_INVALID_FORMAT`. The constraint is documented as "belt-and-suspenders" in RESEARCH.md but was implemented as a hard enforcement. It effectively makes zones useless as a grouping mechanism.

The actual ZONE-04 requirement is "a room can belong to at most one zone", which is already structurally guaranteed by the `rooms` dict being keyed by `area_id` (each room appears exactly once). The `seen_zone_ids` check is an incorrect operationalisation of this requirement.

No existing test seeds two rooms in the same custom zone, so the bug is latent in all EVAL tests.

**Fix:**
```python
def validate_zone_assignment(config: dict) -> None:
    zones = config.get("zones", {})
    for area_id, room_cfg in config.get("rooms", {}).items():
        zone_id = room_cfg.get("zone_id", _SENTINEL)
        if zone_id is _SENTINEL:
            continue  # D-06: absent zone_id = Default Zone member — valid
        if zone_id is None:
            raise ValueError(
                f"Room '{area_id}' has zone_id: null — sparse model prohibits explicit null (D-06)"
            )
        if zone_id not in zones:
            raise ValueError(
                f"Room '{area_id}' references unknown zone_id '{zone_id}'"
            )
    # No seen_zone_ids check — ZONE-04 ("a room belongs to at most one zone") is
    # structurally guaranteed by the rooms dict being keyed by area_id.
```

---

### CR-02: `_build_status_payload` emits `temperature` and `humidity` as strings; `ws_get_status` emits them as floats — panel receives inconsistent types

**File:** `custom_components/climate_manager/coordinator.py:330,341`  
**Cross-reference:** `custom_components/climate_manager/websocket.py:157,171`

**Issue:** There are two code paths that populate `rooms_status` entries for the panel:

1. `coordinator._build_status_payload()` — used by `subscribe_status` push events  
2. `websocket.ws_get_status` — used by the `get_status` request/response command

In `_build_status_payload` (coordinator.py lines 330, 341):
```python
room_entry["temperature"] = sensor_state.state     # str — HA state is always a string
room_entry["humidity"]    = hum_state.state         # str
```

In `ws_get_status` (websocket.py lines 157, 171):
```python
room_entry["temperature"] = float(sensor_state.state)   # float
room_entry["humidity"]    = float(hum_state.state)       # float
```

A panel component that initialises from `get_status` and then receives push events will observe `temperature` switching type from `number` to `string` on the first coordinator tick. Any numeric comparison or display formatting on the frontend will silently break for push-received values.

**Fix:** Apply the same `float()` conversion (with a `try/except`) in `_build_status_payload`:
```python
if temp_sensor:
    sensor_state = self._hass.states.get(temp_sensor)
    if sensor_state is not None and sensor_state.state not in ("unavailable", "unknown"):
        try:
            room_entry["temperature"] = float(sensor_state.state)
        except (ValueError, TypeError):
            pass

if humidity_sensor:
    hum_state = self._hass.states.get(humidity_sensor)
    if hum_state is not None and hum_state.state not in ("unavailable", "unknown"):
        try:
            room_entry["humidity"] = float(hum_state.state)
        except (ValueError, TypeError):
            pass
```

---

## Warnings

### WR-01: Zone write handlers mutate `runtime_config` before `async_save` with no rollback — in-memory state diverges from storage on I/O error

**File:** `custom_components/climate_manager/websocket.py:534-548,586-589,622-628,728-733,777-780`

**Issue:** Five zone write handlers mutate `runtime_config` in place and then call `await entry.runtime_data.store.async_save(...)` without a `try/except`. If `async_save` raises (I/O error, OS-level failure), the mutation has already been applied to the live in-memory config but nothing was written to disk. On the next HA restart, the stored data will be inconsistent with what the integration was operating on during the previous run.

By contrast, `ws_set_room_config` and `ws_delete_zone` both take a snapshot before mutation and restore it on `ValueError`. The zone commands lack this guard.

Affected handlers:
- `ws_create_zone` (line 534)
- `ws_rename_zone` (line 586)
- `ws_set_zone_mode` (line 622)
- `ws_set_zone_time_program` (line 728)
- `ws_reset_zone_time_program` (line 777)

**Fix (pattern — apply to each affected handler):**
```python
# Example for ws_create_zone:
zones_backup = copy.deepcopy(runtime_config.get("zones", {}))
runtime_config.setdefault("zones", {})[zone_id] = new_zone
try:
    await entry.runtime_data.store.async_save(runtime_config)
except Exception as exc:  # noqa: BLE001
    runtime_config["zones"] = zones_backup
    connection.send_error(msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc))
    return
```

---

### WR-02: Variable name `entry` in `ws_get_config` generator shadows the factory's `entry: ClimateManagerConfigEntry` parameter — severe readability hazard

**File:** `custom_components/climate_manager/websocket.py:223-228`

**Issue:** The generator expression on lines 223–227 uses `entry` as its iteration variable, which is the same name as the outer factory function's `entry: ClimateManagerConfigEntry` parameter. In Python 3, generator expressions have their own scope so the outer binding is not mutated, and line 228 (`entry.runtime_data.runtime_config`) does correctly refer to the `ClimateManagerConfigEntry`. However, the code reads as if line 228 accesses the last entity registry entry object, which it does not. This is one of the most confusing naming collisions possible in a closure — a future maintainer refactoring this into a list comprehension would introduce a real runtime bug (list comprehensions do leak their loop variable in Python 3).

```python
# Current (misleading):
climate_entities = sorted(
    entry.entity_id                           # 'entry' = entity registry entry
    for entry in entity_reg.entities.values()
    if entry.entity_id.split(".")[0] == "climate"
)
payload = {**entry.runtime_data.runtime_config, "climate_entities": climate_entities}
#               ^ this 'entry' is the ClimateManagerConfigEntry — not the loop variable above
```

**Fix:**
```python
climate_entities = sorted(
    reg_entry.entity_id
    for reg_entry in entity_reg.entities.values()
    if reg_entry.entity_id.split(".")[0] == "climate"
)
payload = {**entry.runtime_data.runtime_config, "climate_entities": climate_entities}
```

---

### WR-03: `ws_set_zone_time_program` validates program before checking zone existence — clients receive `ERR_INVALID_FORMAT` instead of `ERR_NOT_FOUND` when both conditions are true

**File:** `custom_components/climate_manager/websocket.py:714-727`

**Issue:** The handler calls `validate_daily_program` (lines 714–717) before checking `msg["zone_id"] not in runtime_config.get("zones", {})` (lines 721–727). If a client sends a request with an invalid program **and** a non-existent `zone_id`, the response will be `ERR_INVALID_FORMAT` — which directs the user to fix the program, not the zone ID. The zone existence check should take priority since it is the more specific error condition and is the first thing the handler can know without evaluating the payload.

**Fix:** Swap the order of the two guards:
```python
async def ws_set_zone_time_program(...):
    runtime_config = entry.runtime_data.runtime_config

    if msg["zone_id"] not in runtime_config.get("zones", {}):
        connection.send_error(...)
        return

    ok, err = validate_daily_program(msg["program"])
    if not ok:
        connection.send_error(...)
        return

    runtime_config["zones"][msg["zone_id"]]["time_program"] = msg["program"]
    ...
```

---

## Info

### IN-01: Stray `@pytest.mark.asyncio` on one async test — inconsistent with the rest of the test suite

**File:** `tests/test_coordinator.py:880`

**Issue:** `test_mode_off_to_time_program_pushes_schedule_temp` carries `@pytest.mark.asyncio` but no other async test in either test file uses this decorator. `pytest-homeassistant-custom-component` handles async test dispatch automatically; the extra marker is a no-op but creates a false impression that some tests require explicit asyncio marking.

**Fix:** Remove `@pytest.mark.asyncio` from line 880.

---

### IN-02: Missing test coverage for `set_zone_time_program` "valid program, non-existent zone" path and `rename_zone` not-found path

**File:** `tests/test_websocket.py`

**Issue:** Two error branches in zone write handlers have no test coverage:

1. `ws_set_zone_time_program` lines 721–727: what happens when `zone_id` is not in `zones` dict but the program is valid. The only test for this handler (`test_ws_set_zone_time_program_rejects_partial`) always seeds the zone first, so the zone lookup never fails.

2. `ws_rename_zone` lines 579–585: the `ERR_NOT_FOUND` branch for unknown `zone_id` has no corresponding test. By contrast, `delete_zone` has `test_ws_delete_zone_not_found`.

These are low-risk paths (the branches are simple guard returns), but the gap means a future refactor could silently drop the error response.

**Fix:** Add tests:
```python
async def test_ws_set_zone_time_program_zone_not_found(hass, hass_ws_client):
    await _setup_entry(hass)
    client = await hass_ws_client()
    await client.send_json_auto_id({
        "type": f"{DOMAIN}/set_zone_time_program",
        "zone_id": "nonexistent",
        "program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),  # valid program
    })
    msg = await client.receive_json()
    assert msg["success"] is False

async def test_ws_rename_zone_not_found(hass, hass_ws_client):
    await _setup_entry(hass)
    client = await hass_ws_client()
    await client.send_json_auto_id({
        "type": f"{DOMAIN}/rename_zone",
        "zone_id": "nonexistent",
        "name": "Ghost",
    })
    msg = await client.receive_json()
    assert msg["success"] is False
```

---

_Reviewed: 2026-05-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
