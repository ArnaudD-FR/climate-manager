# Phase 5: Zone CRUD & Evaluation Engine - Pattern Map

**Mapped:** 2026-05-27 **Files analyzed:** 4 (websocket.py, coordinator.py,
tests/test_websocket.py, tests/test_coordinator.py) **Analogs found:** 4 / 4

---

## File Classification

| New/Modified File                                  | Role                       | Data Flow        | Closest Analog                                      | Match Quality             |
| -------------------------------------------------- | -------------------------- | ---------------- | --------------------------------------------------- | ------------------------- |
| `custom_components/climate_manager/websocket.py`   | service (WS handler layer) | request-response | `websocket.py` itself (existing handlers)           | exact — extend in place   |
| `custom_components/climate_manager/coordinator.py` | service (control loop)     | event-driven     | `coordinator.py` itself (existing `async_evaluate`) | exact — refactor in place |
| `tests/test_websocket.py`                          | test                       | request-response | `tests/test_websocket.py` itself (existing tests)   | exact — extend in place   |
| `tests/test_coordinator.py`                        | test                       | event-driven     | `tests/test_coordinator.py` itself (existing tests) | exact — extend in place   |

All four files are existing files being extended. No new files are created in
this phase.

---

## Pattern Assignments

### `websocket.py` — 6 new zone command factories

**Analog:** All 11 existing handlers in `websocket.py`. The zone handlers are
mechanical copies of the same factory closure structure.

---

#### Pattern 1: Base factory closure (copy verbatim for every zone command)

**Source:** `websocket.py` lines 221–245 (`_make_ws_set_global_mode`)

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
        entry.runtime_data.runtime_config["global_mode"] = msg["mode"]
        await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())

    return ws_set_global_mode
```

**Rules derived from this pattern:**

- Factory function is named
  `_make_ws_<command_name>(entry: ClimateManagerConfigEntry)`
- Inner async function is named `ws_<command_name>`
- Schema dict is passed to `@websocket_api.websocket_command({...})`
- `@websocket_api.async_response` decorator always follows the command decorator
- Handler signature:
  `(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None`
- Write-then-evaluate order: mutate → save → send_result →
  async_create_task(evaluate)
- State accessed via entry closure (`entry.runtime_data.*`), never via
  `hass.data`
- Factory returns the inner function by name

---

#### Pattern 2: CR-01 snapshot-rollback (copy for delete_zone and any mutation touching both zones + rooms)

**Source:** `websocket.py` lines 342–358 (`_make_ws_set_room_config`)

```python
rooms_backup = copy.deepcopy(entry.runtime_data.runtime_config.get("rooms", {}))
(
    entry.runtime_data.runtime_config
    .setdefault("rooms", {})
    .setdefault(msg["room_id"], {})
    .update(msg["config"])
)
try:
    await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
except ValueError as exc:
    # Roll back in-memory mutation so runtime_config stays consistent
    entry.runtime_data.runtime_config["rooms"] = rooms_backup
    connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc))
    return
connection.send_result(msg["id"], {"success": True})
hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
```

**For `delete_zone`:** snapshot BOTH `zones` AND `rooms` before any mutation
(the handler mutates both in one operation):

```python
zones_backup = copy.deepcopy(runtime_config.get("zones", {}))
rooms_backup = copy.deepcopy(runtime_config.get("rooms", {}))
# ... mutations ...
try:
    await entry.runtime_data.store.async_save(runtime_config)
except ValueError as exc:
    runtime_config["zones"] = zones_backup
    runtime_config["rooms"] = rooms_backup
    connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc))
    return
```

---

#### Pattern 3: validate_daily_program pre-save gate (copy for set_zone_time_program)

**Source:** `websocket.py` lines 305–313 (`_make_ws_set_time_program`)

```python
ok, err = validate_daily_program(msg["program"])
if not ok:
    connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, err)
    return  # T-03-05: return BEFORE save/evaluate
```

**Critical:** validation fires BEFORE any mutation of `runtime_config`. Never
mutate first.

---

#### Pattern 4: deepcopy for time_program reset (copy for reset_zone_time_program)

**Source:** `websocket.py` lines 442–443 (`_make_ws_reset_time_program`)

```python
entry.runtime_data.runtime_config["global_time_program"] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM)
```

For `reset_zone_time_program(target='global')`, mirror
`reset_room_to_global_program`:

**Source:** `websocket.py` lines 472–477
(`_make_ws_reset_room_to_global_program`)

```python
runtime_config = entry.runtime_data.runtime_config
room_id = msg["room_id"]
global_time_program = runtime_config.get("global_time_program", {})
room = runtime_config.setdefault("rooms", {}).setdefault(room_id, {})
room["room_mode"] = "custom"
room["time_program"] = copy.deepcopy(global_time_program)
```

---

#### Pattern 5: async_register_commands block (where to add 6 new calls)

**Source:** `websocket.py` lines 60–78

```python
def async_register_commands(
    hass: HomeAssistant, entry: ClimateManagerConfigEntry
) -> None:
    websocket_api.async_register_command(hass, _make_ws_get_status(entry))
    websocket_api.async_register_command(hass, _make_ws_get_config(entry))
    websocket_api.async_register_command(hass, _make_ws_set_global_mode(entry))
    websocket_api.async_register_command(hass, _make_ws_set_period_temperatures(entry))
    websocket_api.async_register_command(hass, _make_ws_set_time_program(entry))
    websocket_api.async_register_command(hass, _make_ws_set_room_config(entry))
    websocket_api.async_register_command(hass, _make_ws_set_person_config(entry))
    websocket_api.async_register_command(hass, _make_ws_subscribe_status(entry))
    websocket_api.async_register_command(hass, _make_ws_reset_period_temperatures(entry))
    websocket_api.async_register_command(hass, _make_ws_reset_time_program(entry))
    websocket_api.async_register_command(hass, _make_ws_reset_room_to_global_program(entry))
```

Add 6 lines after line 78, one per zone command factory.

---

#### Pattern 6: imports block (what to add for zone handlers)

**Source:** `websocket.py` lines 29–57

```python
import copy
from typing import TYPE_CHECKING

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
import voluptuous as vol

if TYPE_CHECKING:
    from . import ClimateManagerConfigEntry

from .const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
    _DEFAULT_DAILY_PROGRAM,
)
from .schedule import validate_daily_program
from .trv import is_trv_entity

VALID_MODES = [MODE_OFF, MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES]
```

**Add to imports:** `import uuid` (stdlib, for `create_zone` UUID generation).
Add `VALID_MODES` is already defined at line 57 — no new const import needed for
modes. `_DEFAULT_DAILY_PROGRAM` is already imported.

---

### `coordinator.py` — evaluation engine refactor

**Analog:** `coordinator.py` itself. The refactor restructures `async_evaluate`
and its two private helpers.

---

#### Pattern 7: Current async_evaluate top-level branch (what gets replaced)

**Source:** `coordinator.py` lines 104–145

```python
async def async_evaluate(self, _utc_now: datetime | None = None) -> None:
    now = dt_util.now()
    config = self._data.runtime_config  # shared reference — never copy
    global_mode = config["global_mode"]
    period_temperatures: dict[str, float] = config["period_temperatures"]
    rooms: dict[str, list[str]] = self._data.rooms

    if global_mode == MODE_OFF:
        desired_temp = period_temperatures[PERIOD_FROST_PROTECTION]
        await asyncio.gather(*(
            self._push_off_safely(entity_id, desired_temp)
            if supports_hvac_off(self._hass, entity_id)
            else self._push_safely(entity_id, desired_temp, "MODE_OFF")
            for entity_ids in rooms.values()
            for entity_id in entity_ids
        ))
        self._last_active_period = None
        self._last_present_persons = self._compute_present_persons(config, now)

    elif global_mode == MODE_TIME_PROGRAM:
        await self._evaluate_time_program(now, config, period_temperatures, rooms)

    elif global_mode == MODE_TIME_PROGRAM_PRESENCES:
        await self._evaluate_time_program_presences(
            now, config, period_temperatures, rooms
        )
    else:
        _LOGGER.warning("Unknown global_mode %r — no TRV commands issued", global_mode)

    self._hass.bus.async_fire(
        f"{DOMAIN}_status_update",
        self._build_status_payload(),
    )
```

**What changes:** The `if global_mode == MODE_OFF / elif / elif` block is
replaced by a per-room zone-dispatch loop. The `_evaluate_time_program` and
`_evaluate_time_program_presences` methods are removed or become dead code.

---

#### Pattern 8: Per-room room_mode branching (preserve as outer check in new loop)

**Source:** `coordinator.py` lines 198–223 (`_evaluate_time_program`) — the
room_mode branch that must remain as the outermost check before zone resolution:

```python
for area_id, entity_ids in rooms.items():
    room_config = room_configs.get(area_id, {})
    room_mode = room_config.get("room_mode", "global")

    # D-20: branch on room_mode before schedule evaluation
    if room_mode == ROOM_MODE_FROST:
        desired_temp = period_temperatures[PERIOD_FROST_PROTECTION]
        room_periods[area_id] = PERIOD_FROST_PROTECTION
    else:
        if room_mode == ROOM_MODE_CUSTOM:
            room_daily_program = room_config.get("time_program")
            daily_program = room_daily_program if room_daily_program else global_daily_program
        else:
            daily_program = global_daily_program

        period_mode = evaluate_schedule(daily_program, now)
        desired_temp = period_temperatures.get(period_mode)
        if desired_temp is None:
            _LOGGER.warning(
                "Unknown period mode %r for area %s — skipping", period_mode, area_id
            )
            continue
        room_periods[area_id] = period_mode

    pushes.extend((entity_id, desired_temp) for entity_id in entity_ids if is_trv_entity(self._hass, entity_id))
```

**In the refactored loop:** `ROOM_MODE_FROST` and `ROOM_MODE_CUSTOM` continue to
`continue` before zone resolution is attempted. Zone resolution only runs when
`room_mode` is neither frost nor custom (i.e., the room follows its zone).

---

#### Pattern 9: Two-pass presence algorithm (preserve for presence-eligible rooms)

**Source:** `coordinator.py` lines 259–365 (`_evaluate_time_program_presences`)

Step 1 — baseline dict (lines 262–290):

```python
desired_temps: dict[str, float] = {}
room_periods: dict[str, str] = {}
frost_locked_rooms: set[str] = set()
for area_id in rooms:
    room_config = room_configs.get(area_id, {})
    room_mode = room_config.get("room_mode", "global")
    if room_mode == ROOM_MODE_FROST:
        desired_temps[area_id] = period_temperatures[PERIOD_FROST_PROTECTION]
        room_periods[area_id] = PERIOD_FROST_PROTECTION
        frost_locked_rooms.add(area_id)
    else:
        if room_mode == ROOM_MODE_CUSTOM:
            room_daily_program = room_config.get("time_program")
            daily_program = room_daily_program if room_daily_program else global_daily_program
        else:
            daily_program = global_daily_program
        period_mode = evaluate_schedule(daily_program, now)
        desired_temp_baseline = period_temperatures.get(period_mode)
        if desired_temp_baseline is None:
            _LOGGER.warning(...)
            continue
        desired_temps[area_id] = desired_temp_baseline
        room_periods[area_id] = period_mode
```

Step 2 — present-person-wins rule (lines 298–353):

```python
present_locked_rooms: set[str] = set()
for _person_id, person_config in persons_config.items():
    room_ids: list[str] = person_config.get("room_ids", [])
    if not room_ids:
        continue
    is_present = resolve_presence(person_config, now)
    if is_present:
        present_persons_this_tick.append(_person_id)
    for area_id in room_ids:
        if area_id not in rooms:
            continue
        if area_id in frost_locked_rooms:
            continue
        room_config = room_configs.get(area_id, {})
        room_mode = room_config.get("room_mode", "global")
        if room_mode == ROOM_MODE_CUSTOM:
            room_daily_program = room_config.get("time_program")
            daily_program = room_daily_program if room_daily_program else global_daily_program
        else:
            daily_program = global_daily_program
        occupied_temp, occupied_period = compute_occupied_temp(
            daily_program, now, is_present, period_temperatures
        )
        if is_present:
            if area_id in present_locked_rooms:
                if occupied_temp > desired_temps[area_id]:
                    desired_temps[area_id] = occupied_temp
                    room_periods[area_id] = occupied_period
            else:
                desired_temps[area_id] = occupied_temp
                room_periods[area_id] = occupied_period
                present_locked_rooms.add(area_id)
        else:
            if area_id not in present_locked_rooms:
                desired_temps[area_id] = occupied_temp
                room_periods[area_id] = occupied_period
```

**In the refactor:** Step 2 must use `zone_time_program` (resolved per room) as
the `daily_program` for the presence pass when the room belongs to a custom
zone. For Default Zone rooms the existing `global_daily_program` /
`ROOM_MODE_CUSTOM` branch is unchanged.

---

#### Pattern 10: Push gather pattern (preserve as-is)

**Source:** `coordinator.py` lines 359–365

```python
await asyncio.gather(*(
    self._push_safely(entity_id, desired_temps[area_id], "MODE_TIME_PROGRAM_PRESENCES")
    for area_id, entity_ids in rooms.items()
    for entity_id in entity_ids
    if area_id in desired_temps and is_trv_entity(self._hass, entity_id)
))
```

Replace the context string `"MODE_TIME_PROGRAM_PRESENCES"` with `"ZONE_EVAL"` in
the refactored loop.

---

#### Pattern 11: \_last_active_period backward-compatibility (preserve for Default Zone)

**Source:** `coordinator.py` lines 192–193 and 293–294

```python
# _evaluate_time_program (line 192-193):
global_period_mode = evaluate_schedule(global_daily_program, now)
self._last_active_period = global_period_mode

# _evaluate_time_program_presences (line 293-294):
global_period_mode = evaluate_schedule(global_daily_program, now)
self._last_active_period = global_period_mode
```

After the refactor: set `_last_active_period` to the Default Zone's evaluated
period (or `None` when `global_mode == MODE_OFF`). This preserves the existing
`get_status` and `_build_status_payload` contract which reads
`self._last_active_period` as the global indicator.

---

#### Pattern 12: \_compute_present_persons (reuse as-is for zone presence evaluation)

**Source:** `coordinator.py` lines 147–172

```python
def _compute_present_persons(self, config: dict, now: datetime) -> list[str]:
    persons_config: dict = config.get("persons", {})
    present: list[str] = []
    for person_id, person_config in persons_config.items():
        if person_config.get("mode") == PRESENCE_HA:
            state_obj = self._hass.states.get(person_id)
            if state_obj is not None and state_obj.state == "home":
                present.append(person_id)
        else:
            if resolve_presence(person_config, now):
                present.append(person_id)
    return present
```

This method is used unchanged for zone presence evaluation (D-11: all configured
persons, not scoped to zone rooms).

---

### `tests/test_websocket.py` — 10 new zone CRUD tests

**Analog:** All 9 existing tests in `tests/test_websocket.py`. New tests are
structural copies.

---

#### Pattern 13: WS test scaffold (copy for every zone command test)

**Source:** `tests/test_websocket.py` lines 26–35 and 65–81

```python
async def _setup_entry(hass) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_ws_set_global_mode_persists_and_evaluates(hass, hass_ws_client):
    entry = await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/set_global_mode", "mode": MODE_OFF}
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    assert msg["result"]["success"] is True
    assert entry.runtime_data.runtime_config["global_mode"] == MODE_OFF
```

**Rules:**

- Test function signature: `async def test_*(hass, hass_ws_client)`
- Always call `await _setup_entry(hass)` first to get `entry`
- Always `await hass_ws_client()` then `send_json_auto_id({...})` then
  `receive_json()`
- Assert `msg["success"] is True` before asserting result fields
- Assert in-memory runtime_config after success to verify persistence
- No `@pytest.mark.asyncio` needed — `asyncio_mode = "auto"` in pyproject.toml

---

#### Pattern 14: Validation rejection test (copy for set_zone_time_program partial program test)

**Source:** `tests/test_websocket.py` lines 89–114

```python
async def test_ws_set_time_program_rejects_partial(hass, hass_ws_client):
    entry = await _setup_entry(hass)

    original_program = dict(entry.runtime_data.runtime_config["global_time_program"])

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_time_program",
            "program": {"mon": []},  # missing tue, wed, thu, fri, sat, sun
        }
    )
    msg = await client.receive_json()

    assert msg.get("success") is False or msg.get("type") == "result" and msg.get("success") is False
    # global_time_program must be unchanged — T-03-05 validation gate
    assert entry.runtime_data.runtime_config["global_time_program"] == original_program
```

**For zone tests:** same pattern — capture original value before sending, assert
unchanged after rejection.

---

#### Pattern 15: Seeding runtime_config before WS call (copy for zone tests that need existing zones)

**Source:** `tests/test_websocket.py` lines 131–135

```python
entry.runtime_data.rooms = {"living_room": ["climate.x"], "kitchen": ["climate.y"]}
entry.runtime_data.runtime_config["persons"] = {
    "person.alice": {"room_ids": ["living_room"]},
}
entry.runtime_data.coordinator._last_present_persons = ["person.alice"]
```

For zone tests that need an existing zone to operate on (delete, rename,
set_mode, etc.):

```python
# Seed a custom zone so the handler has something to act on
zone_id = "test-zone-uuid-1234"
entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
    "name": "Test Zone",
    "mode": MODE_TIME_PROGRAM,
    "time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
}
```

---

### `tests/test_coordinator.py` — 5 new zone evaluation tests

**Analog:** All existing tests in `tests/test_coordinator.py`. New tests are
structural copies.

---

#### Pattern 16: Coordinator test scaffold with \_make_runtime_config (copy for all zone eval tests)

**Source:** `tests/test_coordinator.py` lines 79–93

```python
def _make_runtime_config(
    global_mode: str = MODE_TIME_PROGRAM,
    daily_program: dict | None = None,
    rooms_config: dict | None = None,
    persons_config: dict | None = None,
) -> dict:
    return {
        "version": 2,
        "global_mode": global_mode,
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "global_time_program": daily_program if daily_program is not None else ALL_DAYS_NORMAL_PROGRAM,
        "rooms": rooms_config or {},
        "persons": persons_config or {},
    }
```

**For zone eval tests:** add a `zones_config` parameter to this helper:

```python
def _make_runtime_config(
    global_mode: str = MODE_TIME_PROGRAM,
    daily_program: dict | None = None,
    rooms_config: dict | None = None,
    persons_config: dict | None = None,
    zones_config: dict | None = None,   # NEW — for Phase 5 zone evaluation tests
) -> dict:
    return {
        "version": 2,
        "global_mode": global_mode,
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "global_time_program": daily_program if daily_program is not None else ALL_DAYS_NORMAL_PROGRAM,
        "rooms": rooms_config or {},
        "persons": persons_config or {},
        "zones": zones_config or {},    # NEW
        "default_zone_name": "Home",   # NEW (matches DEFAULT_CONFIG)
    }
```

---

#### Pattern 17: Full integration coordinator test (copy for EVAL-01..05 tests)

**Source:** `tests/test_coordinator.py` lines 379–409
(`test_room_mode_frost_protection_pushes_frost_temp`)

```python
@pytest.mark.freeze_time("2026-01-05 12:00:00")
async def test_room_mode_frost_protection_pushes_frost_temp(hass):
    hass.states.async_set("climate.frost_trv", "heat", {"temperature": 20.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = _make_runtime_config(
        global_mode=MODE_TIME_PROGRAM,
        daily_program=ALL_DAYS_NORMAL_PROGRAM,
        rooms_config={"area_x": {"room_mode": ROOM_MODE_FROST}},
    )
    entry.runtime_data.rooms = {"area_x": ["climate.frost_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    calls = [c for c in temp_calls if c.data.get("entity_id") == "climate.frost_trv"]
    assert len(calls) >= 1
    assert calls[-1].data["temperature"] == DEFAULT_PERIOD_TEMPERATURES[PERIOD_FROST_PROTECTION]
```

**Template for zone eval tests:**

1. `@pytest.mark.freeze_time(...)` — pick a time that places the test in a known
   schedule period
2. Seed TRV state with `hass.states.async_set(...)`
3. `async_mock_service` for both `set_hvac_mode` and `set_temperature`
4. `MockConfigEntry` + setup + `await hass.async_block_till_done()`
5. Patch `runtime_config` via
   `_make_runtime_config(zones_config={...}, rooms_config={...})`
6. Patch `entry.runtime_data.rooms`
7. `await coordinator.async_evaluate()` + `await hass.async_block_till_done()`
8. Filter `temp_calls` by entity_id, assert `calls[-1].data["temperature"]`

---

#### Pattern 18: \_make_simple_coordinator for unit tests (copy for \_resolve_zone_config unit tests if written)

**Source:** `tests/test_coordinator.py` lines 595–605

```python
def _make_simple_coordinator(hass) -> ClimateManagerCoordinator:
    from custom_components.climate_manager.storage import ClimateManagerStore
    data = ClimateManagerData(
        store=ClimateManagerStore(hass),
        runtime_config=_make_runtime_config(),
        rooms={},
        persons=[],
        room_auto_sensors={},
    )
    return ClimateManagerCoordinator(hass, data)
```

Use this pattern for any unit test that calls a coordinator method directly
(e.g., `_resolve_zone_config`) without needing TRV push behavior.

---

## Shared Patterns

### Write-then-evaluate (all 6 zone write handlers)

**Source:** `websocket.py` lines 240–243

```python
await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
connection.send_result(msg["id"], {"success": True})
hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
```

Applied to: `create_zone`, `rename_zone`, `set_zone_mode`,
`set_zone_time_program`, `reset_zone_time_program`, `delete_zone` (same final
three lines; `delete_zone` has the try/except wrapping the save).

### ERR_NOT_FOUND for missing zone_id

**Source:** `websocket_api.ERR_NOT_FOUND` (HA constant, same module as
`ERR_INVALID_FORMAT`)

Pattern (not yet in codebase — first use in Phase 5):

```python
if zone_id not in runtime_config.get("zones", {}):
    connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, f"Zone {zone_id!r} not found")
    return
```

Applied to: `delete_zone`, `rename_zone` (custom zone path), `set_zone_mode`,
`set_zone_time_program`, `reset_zone_time_program`.

### Sparse key removal (delete_zone room migration)

**Source:** `const.py` lines 121–123 (comment block):

```
"zone_id": "<uuid>"   # optional — absent = belongs to Default Zone
                      # Writing zone_id: null is prohibited (D-06 sparse model).
```

Enforced by `storage.py:validate_zone_assignment`. The delete handler must use
`room_cfg.pop("zone_id", None)` — never `room_cfg["zone_id"] = None`.

### status_update event fire (after every async_evaluate)

**Source:** `coordinator.py` lines 142–145

```python
self._hass.bus.async_fire(
    f"{DOMAIN}_status_update",
    self._build_status_payload(),
)
```

This line must remain at the end of the refactored `async_evaluate`, unchanged.

---

## No Analog Found

None. All files being modified have existing patterns that cover Phase 5
additions exactly. No genuinely novel patterns are needed — the zone handlers
are mechanical copies of the existing 11 WS handlers, and the coordinator
evaluation loop refactor reuses existing per-room algorithms.

---

## Key Anti-Patterns to Avoid (derived from source code analysis)

These are wrong patterns that would compile but break behavior — extracted from
source code structure:

| Anti-pattern                                                                                             | Where it would break                                                      | Correct approach                                                                                |
| -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Reading `global_mode` as system-wide switch in new eval loop                                             | `coordinator.py` — custom zone rooms would be governed by `global_mode`   | Zone resolution via `_resolve_zone_config`; `global_mode` only consulted for Default Zone rooms |
| Setting `room["zone_id"] = None` in delete_zone                                                          | `storage.py:validate_zone_assignment` raises ValueError for explicit null | `room_cfg.pop("zone_id", None)` — removes the key entirely                                      |
| Deleting `zones[zone_id]` before popping zone_id from rooms                                              | `validate_zone_assignment` sees dangling references and raises            | Correct order: pop from rooms → del from zones → then save once                                 |
| `runtime_config["zones"][zone_id]["time_program"] = runtime_config["global_time_program"]` (no deepcopy) | zone and global programs share list references; mutations bleed across    | Always `copy.deepcopy(runtime_config["global_time_program"])`                                   |
| `runtime_config["zones"]["default"]` in rename_zone                                                      | Default Zone has no entry in `zones{}`                                    | Check `zone_id == "default"` sentinel → update `runtime_config["default_zone_name"]`            |
| Mutating runtime_config before `validate_daily_program` in set_zone_time_program                         | Invalid program written to runtime_config even when error is sent         | Validate first, return on error, mutate only if valid                                           |

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `tests/` **Files
read:** `websocket.py` (526 lines), `coordinator.py` (508 lines),
`tests/test_websocket.py` (354 lines), `tests/test_coordinator.py` (979 lines),
`const.py` (188 lines) **Pattern extraction date:** 2026-05-27
