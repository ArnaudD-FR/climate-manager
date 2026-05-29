# Phase 4: Zone Data Model & Storage - Pattern Map

**Mapped:** 2026-05-27 **Files analyzed:** 4 (2 Python modified, 1 TypeScript
modified, 1 Python test new) **Analogs found:** 4 / 4

---

## File Classification

| New/Modified File                              | Role    | Data Flow        | Closest Analog                                                        | Match Quality |
| ---------------------------------------------- | ------- | ---------------- | --------------------------------------------------------------------- | ------------- |
| `custom_components/climate_manager/const.py`   | config  | transform        | `custom_components/climate_manager/const.py` (self — additive edit)   | exact         |
| `custom_components/climate_manager/storage.py` | service | CRUD             | `custom_components/climate_manager/storage.py` (self — additive edit) | exact         |
| `frontend/src/types.ts`                        | config  | transform        | `frontend/src/types.ts` (self — additive edit)                        | exact         |
| `tests/test_storage.py`                        | test    | request-response | `tests/test_storage.py` (self — additive edit)                        | exact         |

---

## Pattern Assignments

### `custom_components/climate_manager/const.py` (config, additive extension)

**Analog:** `custom_components/climate_manager/const.py` (existing file — extend
in place)

**Existing DEFAULT_CONFIG pattern** (lines 150–157 — the block being extended):

```python
DEFAULT_CONFIG: dict = {
    "version": STORAGE_VERSION,
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
    "global_time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    "rooms": {},    # sparse: only rooms with non-default config (SCHED-05, D-11)
    "persons": {},  # sparse: only persons with non-default settings (D-11)
}
```

**What to add — two new top-level keys** (insert after `"persons": {}`):

```python
    "default_zone_name": "Home",  # D-03: Default Zone display name (user-editable in Phase 5/6)
    "zones": {},                  # ZONE-01: custom zones, keyed by UUID string (D-07)
                                  # Empty dict = no custom zones; all rooms belong to Default Zone.
                                  # DEFAULT_CONFIG["zones"] MUST stay {} — pitfall 2: dict.update()
                                  # would resurrect deleted zones if DEFAULT_CONFIG["zones"] were
                                  # non-empty.
```

**Existing comment-block pattern to follow for documentation** (lines 103–148):
The rooms sub-schema is documented as a comment block immediately above
DEFAULT_CONFIG. Follow the same pattern for the zones sub-schema. Insert a new
comment block after the persons sub-schema comment (after line 143) and before
the DEFAULT_CONFIG declaration:

```python
# Zones sub-schema (keyed by UUID string — D-07):
#   {
#     "<uuid>": {
#       "name": "<string>",          # display name (user-editable)
#       "mode": "<global_mode>",     # same enum as global_mode:
#                                    #   off | time_program | time_program_presences
#       "time_program": {            # same structure as global_time_program
#         "mon": [{"start": "HH:MM", "mode": "<period_mode>"}, ...],
#         "tue": [...],
#         ...
#         "sun": [...]
#       }
#     }
#   }
#   Empty dict = no custom zones exist (all rooms belong to Default Zone).
#   Default Zone is NOT stored here — it is a virtual zone backed by
#   global_mode + global_time_program + default_zone_name (D-01, D-02, D-03).
#
# Room entry extension for Phase 4 (add to room sub-schema comment above):
#   "zone_id": "<uuid>",   # optional string — absent = belongs to Default Zone (D-05, D-06)
#                          # Only present if room is assigned to a custom zone.
#                          # Writing zone_id: null is prohibited (D-06 sparse model).
```

**Imports pattern** (line 8 — already present, no change needed):

```python
import copy
```

**Key constraint:** STORAGE_VERSION (line 16) stays at `2` — D-04 prohibits
bumping.

---

### `custom_components/climate_manager/storage.py` (service, CRUD — additive extension)

**Analog:** `custom_components/climate_manager/storage.py` (existing file —
extend in place)

**Existing imports pattern** (lines 12–18 — add `uuid` import alongside `copy`):

```python
import copy

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DEFAULT_CONFIG, STORAGE_KEY, STORAGE_VERSION, _DEFAULT_DAILY_PROGRAM
```

**What to add to imports:**

```python
import copy
import uuid  # D-07: UUID generation for zone IDs (used by Phase 5 CRUD; documented here)
```

**Existing sparse-merge core pattern** (lines 59–64 — NO changes needed):

```python
result = copy.deepcopy(DEFAULT_CONFIG)
for key, value in stored.items():
    if isinstance(value, dict) and isinstance(result.get(key), dict):
        result[key].update(value)  # merge nested dicts key-by-key
    else:
        result[key] = value
```

This loop already handles `"zones"` and `"default_zone_name"` correctly once
they are in DEFAULT_CONFIG. No modification to `async_load` required.

**New helper to add — module-level function before the class** (ZONE-04 guard):

```python
def validate_zone_assignment(config: dict) -> None:
    """Raise ValueError if zone assignment invariants are violated (ZONE-04).

    Checks:
    1. Every zone_id on a room entry references an existing zone in config["zones"].
    2. No zone_id value appears on more than one room entry (belt-and-suspenders;
       structural dict keying already prevents a single room from appearing twice).

    Called by async_save() before persisting. Phase 5 WebSocket handlers may also
    import and call this directly before triggering save.
    """
    zones = config.get("zones", {})
    seen_zone_ids: set[str] = set()
    for area_id, room_cfg in config.get("rooms", {}).items():
        zone_id = room_cfg.get("zone_id")
        if zone_id is None:
            continue  # D-06: absent zone_id = Default Zone member — valid
        if zone_id not in zones:
            raise ValueError(
                f"Room '{area_id}' references unknown zone_id '{zone_id}'"
            )
        if zone_id in seen_zone_ids:
            raise ValueError(
                f"zone_id '{zone_id}' assigned to multiple rooms — ZONE-04 violated"
            )
        seen_zone_ids.add(zone_id)
```

**Existing async_save pattern** (lines 87–92 — extend to call validation):

```python
async def async_save(self, config: dict) -> None:
    """Persist the configuration via the Store helper.

    Never uses open(), json.load, or json.dump (Pitfall 2).
    """
    await self._store.async_save(config)
```

**What to change in async_save** — add validation call before save:

```python
async def async_save(self, config: dict) -> None:
    """Persist the configuration via the Store helper.

    Validates zone assignment invariants (ZONE-04) before writing.
    Never uses open(), json.load, or json.dump (Pitfall 2).
    """
    validate_zone_assignment(config)
    await self._store.async_save(config)
```

**Existing migration pattern** (lines 74–84) — model for any future zone
migration:

```python
# Migration: rename person presence modes to current wire values.
for person_cfg in result.get("persons", {}).values():
    if person_cfg.get("mode") == "automatic":
        person_cfg["mode"] = "scheduled"
    elif person_cfg.get("mode") == "present":
        person_cfg["mode"] = "force_present"
    elif person_cfg.get("mode") == "absent":
        person_cfg["mode"] = "force_absent"
```

Phase 4 adds NO migration code (D-04). This block is shown so the planner knows
where future zone migrations would be inserted if ever needed.

---

### `frontend/src/types.ts` (config, transform — additive extension)

**Analog:** `frontend/src/types.ts` (existing file — extend in place)

**Existing interface pattern to follow** (lines 24–32 — RoomConfig as the
model):

```typescript
/** Per-room configuration stored in ClimateConfig.rooms. */
export interface RoomConfig {
  /**
   * Room heating mode (D-20). Absent key implies "global".
   * Legal values: "global" | "frost_protection" | "custom"
   */
  room_mode?: "global" | "frost_protection" | "custom";
  time_program?: DailyProgram | null;
}
```

**What to add — new ZoneConfig interface** (insert before RoomConfig, after
PersonConfig or at logical grouping point):

```typescript
/** Custom zone configuration stored in ClimateConfig.zones. */
export interface ZoneConfig {
  name: string;
  /** Same enum as global_mode: "off" | "time_program" | "time_program_presences" */
  mode: string;
  time_program: DailyProgram;
}
```

**What to extend — RoomConfig** (add `zone_id` as optional field — pitfall 4:
MUST be optional):

```typescript
export interface RoomConfig {
  room_mode?: "global" | "frost_protection" | "custom";
  time_program?: DailyProgram | null;
  /** Absent = Default Zone member (D-06); UUID string when room is in a custom zone (D-07). */
  zone_id?: string;
}
```

**What to extend — ClimateConfig** (lines 42–49 — add two new fields):

```typescript
export interface ClimateConfig {
  global_mode: string;
  period_temperatures: Record<string, number>;
  global_time_program: DailyProgram;
  /** D-03: Default Zone display name. Absent in v1.0 data → falls back to "Home". */
  default_zone_name: string;
  /** ZONE-01: custom zones keyed by UUID string. Empty = all rooms in Default Zone. */
  zones: Record<string, ZoneConfig>;
  rooms: Record<string, RoomConfig>;
  persons: Record<string, PersonConfig>;
  climate_entities: string[];
}
```

**JSDoc comment style** (existing pattern from lines 8–16):

```typescript
/** A single period entry in a daily program. */
export interface Period {
  /** "HH:MM" start time */
  start: string;
```

All new interfaces and fields follow the same `/** ... */` JSDoc pattern.

---

### `tests/test_storage.py` (test, request-response — additive extension)

**Analog:** `tests/test_storage.py` (existing file — add new test functions)

**Existing test structure pattern** (lines 13–18 — every test follows this
shape):

```python
async def test_<behavior_description>(hass):
    """Docstring: what the test verifies."""
    store = ClimateManagerStore(hass)
    # arrange: set up state
    # act: call the function under test
    # assert: check result
```

**Existing fixture usage** — `hass` fixture only, injected by
pytest-homeassistant-custom-component. No additional fixtures needed for Phase 4
tests.

**Existing import block** (lines 1–10 — copy for new tests):

```python
import copy
import pytest

from custom_components.climate_manager.const import DEFAULT_CONFIG
from custom_components.climate_manager.storage import ClimateManagerStore
```

For ZONE-04 tests, also import the helper:

```python
from custom_components.climate_manager.storage import validate_zone_assignment
```

**Pattern for DEFAULT_CONFIG extension tests** (modeled on lines 37–51):

```python
async def test_load_fresh_install_includes_zones_and_default_zone_name(hass):
    """Fresh install returns DEFAULT_CONFIG with zones:{} and default_zone_name present."""
    store = ClimateManagerStore(hass)
    result = await store.async_load()
    assert "zones" in result
    assert result["zones"] == {}
    assert "default_zone_name" in result
    assert result["default_zone_name"] == "Home"
```

**Pattern for sparse-merge backward-compat tests** (modeled on lines 37–51):

```python
async def test_load_v10_data_without_zones_gets_defaults(hass):
    """v1.0 stored data without zones/default_zone_name loads cleanly (D-04, ZONE-03)."""
    store = ClimateManagerStore(hass)
    # Simulate v1.0 stored data — no zones, no default_zone_name
    await store._store.async_save({"global_mode": "off"})
    result = await store.async_load()
    assert result["zones"] == {}
    assert result["default_zone_name"] == "Home"
    assert result["global_mode"] == "off"  # stored value survives
```

**Pattern for validate_zone_assignment unit tests** (pure function — no hass
needed):

```python
def test_validate_zone_assignment_valid_config_passes():
    """validate_zone_assignment raises nothing for a valid config."""
    config = {
        "zones": {"uuid-1": {"name": "Zone A", "mode": "time_program", "time_program": {}}},
        "rooms": {"living_room": {"zone_id": "uuid-1", "room_mode": "global"}},
    }
    validate_zone_assignment(config)  # must not raise


def test_validate_zone_assignment_unknown_zone_id_raises():
    """validate_zone_assignment raises ValueError for unknown zone_id (referential integrity)."""
    config = {
        "zones": {},
        "rooms": {"living_room": {"zone_id": "nonexistent-uuid"}},
    }
    with pytest.raises(ValueError, match="unknown zone_id"):
        validate_zone_assignment(config)


def test_validate_zone_assignment_default_zone_rooms_pass():
    """Rooms without zone_id (Default Zone members) pass validation (D-06)."""
    config = {
        "zones": {},
        "rooms": {"bedroom": {"room_mode": "custom"}},  # no zone_id
    }
    validate_zone_assignment(config)  # must not raise
```

**Pattern for zone round-trip test** (modeled on lines 55–88):

```python
async def test_save_then_load_round_trips_zone(hass):
    """A saved zone survives load and appears under zones[uuid] (ZONE-01)."""
    store = ClimateManagerStore(hass)
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["zones"]["test-uuid"] = {
        "name": "Test Zone",
        "mode": "time_program",
        "time_program": {d: [] for d in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]},
    }
    await store.async_save(config)
    loaded = await store.async_load()
    assert "test-uuid" in loaded["zones"]
    assert loaded["zones"]["test-uuid"]["name"] == "Test Zone"
```

---

## Shared Patterns

### Sparse Storage Convention

**Source:** `custom_components/climate_manager/const.py` lines 150–157,
`storage.py` lines 59–64 **Apply to:** All new fields in DEFAULT_CONFIG and all
room entry extensions

```python
# Keys with empty-dict default (zones, rooms, persons): absence in stored data = fall back to {}
# Keys with scalar default (default_zone_name, global_mode): absence = fall back to DEFAULT_CONFIG value
# NEVER store null explicitly for optional fields — omit the key entirely (sparse model, D-11)
result = copy.deepcopy(DEFAULT_CONFIG)
for key, value in stored.items():
    if isinstance(value, dict) and isinstance(result.get(key), dict):
        result[key].update(value)
    else:
        result[key] = value
```

### Deep-Copy Isolation

**Source:** `custom_components/climate_manager/storage.py` lines 51–53 and 59
**Apply to:** Every caller that builds a config dict from DEFAULT_CONFIG

```python
# Always work on a deep copy — never mutate DEFAULT_CONFIG directly (Pitfall 1)
return copy.deepcopy(DEFAULT_CONFIG)
# or
result = copy.deepcopy(DEFAULT_CONFIG)
```

### Comment-Block Sub-Schema Documentation

**Source:** `custom_components/climate_manager/const.py` lines 103–148 **Apply
to:** All new sub-schemas added to DEFAULT_CONFIG (zones) Pattern: multi-line
comment block showing the full dict shape with inline comments, placed
immediately before DEFAULT_CONFIG, after existing sub-schema blocks.

### Test Fixture Pattern

**Source:** `tests/conftest.py` lines 14–16, `tests/test_storage.py` lines 13–18
**Apply to:** All new test functions in test_storage.py

```python
# Fixture auto-enabled by conftest.py — just declare `hass` as parameter
async def test_<name>(hass):
    store = ClimateManagerStore(hass)
    ...
# Pure-function helpers (validate_zone_assignment) need no hass fixture
def test_<name>():
    validate_zone_assignment(...)
```

---

## No Analog Found

All four files already exist in the codebase. Every Phase 4 change is additive
to an existing file. No new files are introduced with no analog.

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `frontend/src/`,
`tests/` **Files read:** `const.py`, `storage.py`, `frontend/src/types.ts`,
`tests/test_storage.py`, `tests/conftest.py` **Pattern extraction date:**
2026-05-27
