# Phase 16: Presence & Heating Log Traces - Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 7 (5 new modules + coordinator refactor + 6 new test files)
**Analogs found:** 7 / 7

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `custom_components/climate_manager/eval_context.py` | utility / dataclass | request-response (per-cycle) | `custom_components/climate_manager/__init__.py` (`ClimateManagerData`) | role-match |
| `custom_components/climate_manager/zone.py` | service / state-machine | event-driven | `custom_components/climate_manager/coordinator.py` (`_resolve_zone_config`, `_compute_desired_temps`) | role-match |
| `custom_components/climate_manager/person.py` | service / state-machine | event-driven | `custom_components/climate_manager/coordinator.py` (`_compute_present_persons`) | role-match |
| `custom_components/climate_manager/room.py` | service / orchestrator | event-driven | `custom_components/climate_manager/coordinator.py` (`_async_preheat_room`, `_async_calibrate_room`) | role-match |
| `custom_components/climate_manager/trv.py` | service / utility (extend) | request-response | `custom_components/climate_manager/trv.py` (existing file) | exact |
| `custom_components/climate_manager/coordinator.py` | service / orchestrator (refactor) | event-driven | `custom_components/climate_manager/coordinator.py` (same file) | exact |
| `tests/test_eval_context.py` | test | — | `tests/test_schedule.py` | exact |
| `tests/test_zone.py` | test | — | `tests/test_schedule.py` | exact |
| `tests/test_person.py` | test | — | `tests/test_schedule.py` | exact |
| `tests/test_room_domain.py` | test | — | `tests/test_trv.py` | role-match |
| `tests/test_trv.py` | test (extend) | — | `tests/test_trv.py` (same file) | exact |
| `tests/test_coordinator.py` | test (update mocks) | — | `tests/test_coordinator.py` (same file) | exact |

---

## Pattern Assignments

### `custom_components/climate_manager/eval_context.py` (utility, per-cycle cache)

**Analog:** `custom_components/climate_manager/__init__.py` (`ClimateManagerData` dataclass)

**File header pattern** (lines 1-2 of every module in this project):
```python
# SPDX-License-Identifier: MIT
"""Climate Manager <module description>."""
```

**Imports pattern** (modelled on `__init__.py` lines 34-36 + `coordinator.py` lines 39-49):
```python
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)
```

**Dataclass pattern** (`__init__.py` lines 71-108):
```python
@dataclass
class ClimateManagerData:
    store: ClimateManagerStore
    runtime_config: dict
    rooms: dict[str, list[str]]
    persons: list[str]
    # Optional fields use field(default=None) / field(default_factory=...)
    coordinator: "ClimateManagerCoordinator | None" = field(default=None)
    preheat_samples: dict = field(default_factory=dict)
```

**EvalContext must follow the same pattern:** dataclass with required positional
fields first, optional cache fields using `field(default_factory=dict)`. The
`calendar_events(entity_id)` async method goes on the class body (not a
standalone function), matching the coordinator's existing
`_prefetch_calendars` async method pattern at `coordinator.py` lines 266-343.

**No-analog section:** `calendar_events()` async lazy-fetch logic is new. Use
the coordinator's `_prefetch_calendars` + `_fetch_one` inner-function pattern
(lines 309-343) as the structural template — but move the fetch into the
dataclass method and cache on first call rather than upfront.

---

### `custom_components/climate_manager/zone.py` (service, state-machine)

**Analog:** `custom_components/climate_manager/coordinator.py`
(methods: `_resolve_zone_config` lines 1292-1314, `_compute_desired_temps`
lines 345-403)

**File header + module-level logger** (`coordinator.py` lines 1-89):
```python
# SPDX-License-Identifier: MIT
"""<docstring>."""

from __future__ import annotations

import logging
import weakref
from datetime import datetime
from typing import TYPE_CHECKING

_LOGGER = logging.getLogger(__name__)
```

**Zone mode resolution pattern** (`coordinator.py` lines 1292-1314):
```python
def _resolve_zone_config(
    self, area_id: str, config: dict
) -> tuple[str, dict]:
    zone_id = config.get("rooms", {}).get(area_id, {}).get("zone_id")
    if zone_id is None:
        dz = config["default_zone"]
        return (dz["mode"], dz["time_program"])
    zone = config.get("zones", {}).get(zone_id)
    if zone is None:
        _LOGGER.warning(
            "Room %s has unknown zone_id %r — using Default Zone",
            area_id,
            zone_id,
        )
        dz = config["default_zone"]
        return (dz["mode"], dz["time_program"])
    return (zone["mode"], zone["time_program"])
```
`Zone.evaluate()` replaces this; the `_LOGGER.warning` fallback pattern is
preserved in `Zone.__init__` or a constructor-time validation.

**MODE_OFF branch pattern** (`coordinator.py` lines 370-379):
```python
if zone_mode == MODE_OFF:
    desired_temps[area_id] = period_temperatures[PERIOD_FROST_PROTECTION]
    room_periods[area_id] = PERIOD_FROST_PROTECTION
    frost_locked_rooms.add(area_id)
    mode_off_rooms.add(area_id)
    continue
```
`ZoneModeOff.evaluate(ctx)` is the direct replacement; iterates
`self.zone.rooms` and calls `room.apply_setpoint(PERIOD_FROST_PROTECTION,
frost_temp, ctx)`.

**WeakRef mode base class pattern** (from RESEARCH.md Pattern 3):
```python
import weakref

class ZoneMode:
    def __init__(self, zone: "Zone") -> None:
        self._zone_ref: weakref.ref["Zone"] = weakref.ref(zone)

    @property
    def zone(self) -> "Zone":
        z = self._zone_ref()
        assert z is not None, "Zone has been garbage-collected"
        return z

    def evaluate(self, ctx: "EvalContext") -> None:
        assert False, f"{type(self).__name__}.evaluate() not implemented"
```

**Zone state INFO log pattern** (new — no existing analog; format locked by
ROADMAP.md via CONTEXT.md D-03/D-09):
```python
# In ZoneMode.evaluate() — fires only when (period, mode_name) changes
if (period, mode_name) != (self._current_period, self._current_mode_name):
    _LOGGER.info(
        "zone | zone=%s state=%s→%s reason=%s",
        zone_name,      # short suffix, e.g. "main" not "zone_main"
        old_state,      # e.g. "frost[time_program]"
        new_state,      # e.g. "normal[time_program]"
        reason,         # e.g. "time_program:normal→22:00"
    )
    self._current_period = period
    self._current_mode_name = mode_name
```

**Const imports pattern** (`coordinator.py` lines 51-66):
```python
from .const import (
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
)
from .schedule import evaluate_schedule
```

---

### `custom_components/climate_manager/person.py` (service, state-machine)

**Analog:** `custom_components/climate_manager/coordinator.py`
(method: `_compute_present_persons` lines 1316-1377)

**Presence mode branch pattern** (`coordinator.py` lines 1333-1377):
```python
for person_id, person_config in persons_config.items():
    if person_config.get("mode") == PRESENCE_HA:
        state_obj = self._hass.states.get(person_id)
        if state_obj is not None and state_obj.state == "home":
            present.append(person_id)
    elif person_config.get("mode") == PRESENCE_CALENDAR:
        cal_cfg = person_config.get("calendar_config") or {}
        eid = cal_cfg.get("entity_id", "")
        events = self._calendar_cache.get(eid, [])
        preheat = person_config.get(
            "wakeup_advance_minutes",
            person_config.get(
                "preheat_lead_minutes",
                DEFAULT_PREHEAT_LEAD_MINUTES,
            ),
        )
        if resolve_calendar_presence(
            events,
            cal_cfg.get("event_means", "absent"),
            now,
            gap_handling=cal_cfg.get("gap_handling", "exact"),
            gap_threshold_minutes=cal_cfg.get("gap_threshold_minutes", 0),
            preheat_lead_minutes=preheat,
            start_of_local_day=dt_util.start_of_local_day,
        ):
            present.append(person_id)
    else:
        if resolve_presence(
            person_config,
            now,
            calendar_cache=self._calendar_cache,
            start_of_local_day=dt_util.start_of_local_day,
        ):
            present.append(person_id)
```
Each `if/elif/else` branch maps directly to a `PersonMode` subclass:
`PersonModeHA`, `PersonModeCalendar`, and the `else` branch covers
`PersonModeScheduled` / `PersonModeForcePresent` / `PersonModeForceAbsent`
(all delegated to `resolve_presence`).

**Anti-spam + INFO log pattern** (new — anti-spam shape from
`coordinator.py` `_push_if_changed` lines 1653-1655, log format from
CONTEXT.md D-08/specifics):
```python
# Person.evaluate(ctx) — fires INFO only on _last_home flip
result = await self._mode.is_present(ctx)
if result != self._last_home:
    _LOGGER.info(
        "presence | person=%s home=%s reason=%s",
        _short_name(self.person_id),   # "alice" not "person.alice"
        result,                        # bool
        self._mode.reason_label,       # "scheduled"|"ha"|"calendar"|etc.
    )
self._last_home = result
ctx._presence_cache[self.person_id] = result
```

**Presence cache dedup** (`coordinator.py` line 192 — `_last_present_persons`
computed once; same single-evaluation pattern):
```python
# Person.evaluate() — check cache first (D-02 in person.py)
if self.person_id in ctx._presence_cache:
    return ctx._presence_cache[self.person_id]
```

**WeakRef base class** — identical shape to `ZoneMode` above. Copy exactly
with `PersonMode` + `person` weakref property.

**PRESENCE_* constant imports** (`coordinator.py` lines 62-66, `schedule.py`
lines 38-40):
```python
from .const import (
    DEFAULT_PREHEAT_LEAD_MINUTES,
    PRESENCE_ABSENT,
    PRESENCE_CALENDAR,
    PRESENCE_HA,
    PRESENCE_PRESENT,
)
from .schedule import (
    resolve_calendar_presence,
    resolve_presence,
)
```

---

### `custom_components/climate_manager/room.py` (service, orchestrator)

**Analog:** `custom_components/climate_manager/coordinator.py`
(methods: `_async_preheat_room` lines 587-860, `_async_calibrate_room`
lines 995-1074)

**Preheat state ownership pattern** (`coordinator.py` `__init__` lines
155-159):
```python
# These dicts move to Room instance variables:
self._preheat_in_progress: dict[str, dict] = {}   # → self._preheat_in_progress
self._preheat_active: dict[str, bool] = {}         # → self._preheat_active
self._preheat_target: dict[str, float | None] = {} # → self._preheat_target
self._preheat_suppressed: dict[str, bool] = {}     # → self._preheat_suppressed
```
After refactor, these become instance variables directly on `Room`
(keyed values collapse into scalars: `self._preheat_active: bool = False`).

**Preheat zone-enabled lookup pattern** (`coordinator.py` lines 615-628):
```python
zone_id = room_config.get("zone_id")
if zone_id is None:
    preheat_enabled = config.get("default_zone", {}).get(
        "preheat_enabled", False
    )
else:
    zone = config.get("zones", {}).get(zone_id)
    if zone is None:
        preheat_enabled = config.get("default_zone", {}).get(
            "preheat_enabled", False
        )
    else:
        preheat_enabled = zone.get("preheat_enabled", False)
```
After refactor, `Room.compute_preheat(ctx)` reads `preheat_enabled` from
`self._zone.preheat_enabled` via the owning `Zone` reference.

**Calibration state tracking pattern** (`coordinator.py` `__init__`
lines 127-132):
```python
# These dicts move to Room instance variables:
self._calibration_last_changed: dict[str, str] = {}
self._calibration_last_delta: dict[str, float] = {}
self._calibration_last_offset: dict[str, float] = {}
```

**Module-level logger** — identical to all other modules:
```python
_LOGGER = logging.getLogger(__name__)
```

**apply_setpoint → TRVGroup delegation** (new; shape from
`coordinator.py` `_push_temperatures` lines 531-570):
```python
async def apply_setpoint(
    self, period: str, temp: float, ctx: "EvalContext"
) -> None:
    """Push temp to all TRV groups in this room."""
    for group in self._trv_groups:
        await group.push(temp, period, ctx)
```

---

### `custom_components/climate_manager/trv.py` (extend existing file)

**Analog:** `custom_components/climate_manager/trv.py` (existing — exact)

**Existing module header** (`trv.py` lines 1-19) — preserve verbatim, extend
docstring to mention new classes:
```python
# SPDX-License-Identifier: MIT
"""Climate Manager TRV control helper.
...
"""
```

**Existing helper functions stay unchanged** (`trv.py` lines 29-251).
`TRV` and `TRVGroup` are added as new classes after the existing functions.

**Anti-flap guard** moving from `coordinator.py` lines 1639-1668 into
`TRV.push_temperature`:
```python
async def _push_if_changed(
    self, entity_id: str, desired_temp: float
) -> None:
    state = self._hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        return
    last = self._last_pushed.get(entity_id)
    if isinstance(last, str):
        last = None
    if last is not None and last == desired_temp:
        return
    if last is not None:
        reported = state.attributes.get("temperature")
        if reported is not None and float(reported) != last:
            return  # manual override hold
    await set_trv_temperature(self._hass, entity_id, desired_temp)
    self._last_pushed[entity_id] = desired_temp
```
After refactor: `entity_id` and `hass` come from `TRV` instance fields;
`self._last_pushed.get(entity_id)` becomes `self.last_pushed`.

**TRVGroup platform-dispatch** moving from `coordinator.py`
`_push_temperatures` lines 519-570 into `TRVGroup` assembly at init:
```python
# Build frozenset of all Matter entity_ids in any mapping value
matter_entity_set: frozenset[str] = frozenset(
    eid for eids in matter_mappings.values() for eid in eids
)
# Per-entity platform check (to_set assembly logic):
if platform == "tado_x":
    mapped = matter_mappings.get(entity_id)
    if mapped:
        to_set.extend(mapped)
    else:
        to_set.append(entity_id)
elif platform == "matter":
    if entity_id not in matter_entity_set:
        to_set.append(entity_id)
else:
    to_set.append(entity_id)
```
This entire block moves into `TRVGroup.__init__` / a factory method called
once at coordinator init — no platform branching at push time.

**DEBUG heating log** (new — fires inside `TRV.push_temperature`, after
anti-flap guard, only when setpoint changes; format from CONTEXT.md specifics):
```python
_LOGGER.debug(
    "heating | room=%s temp=%s°C zone=%s slot=%s",
    room_name,   # short suffix, e.g. "kitchen" not "area_kitchen"
    desired_temp,
    zone_name,   # short suffix
    slot,        # period name, e.g. "normal"
)
await set_trv_temperature(self._hass, entity_id, desired_temp)
self.last_pushed = desired_temp
```

**Push-off pattern** (`coordinator.py` `_push_off_safely` lines 1593-1625)
moves into `TRV.push_off(frost_temp, ctx)`:
```python
async def _push_off_safely(self, entity_id: str, frost_temp: float) -> None:
    state = self._hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        return
    if self._last_pushed.get(entity_id) == "off":
        return  # Anti-flap: already pushed off
    try:
        await set_trv_temperature(self._hass, entity_id, frost_temp)
    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Failed to pre-set frost temp on %s before MODE_OFF", entity_id
        )
    try:
        await set_trv_off(self._hass, entity_id)
        self._last_pushed[entity_id] = "off"
    except Exception:  # noqa: BLE001
        _LOGGER.warning("Failed to push OFF to %s in MODE_OFF", entity_id)
```

---

### `custom_components/climate_manager/coordinator.py` (refactor)

**Analog:** Same file — prior `async_evaluate` at lines 166-264.

**Refactored `async_evaluate` shape** (`coordinator.py` lines 166-264):
```python
async def async_evaluate(self, _utc_now: datetime | None = None) -> None:
    now = dt_util.now()
    config = self._data.runtime_config
    period_temperatures: dict[str, float] = config["period_temperatures"]
    rooms: dict[str, list[str]] = self._data.rooms

    self._calendar_cache = {}
    await self._prefetch_calendars(config, now)
    self._last_present_persons = self._compute_present_persons(config, now)
    self._check_ha_tracker_warnings(config)

    desired_temps, room_periods, frost_locked_rooms, mode_off_rooms = (
        self._compute_desired_temps(config, rooms, period_temperatures, now)
    )
    # ... rest of the method ...
    self._hass.bus.async_fire(
        f"{DOMAIN}_status_update",
        self._build_status_payload(),
    )
```
After refactor this becomes:
```
ctx = EvalContext(now=now, hass=self._hass, period_temperatures=period_temperatures)
for zone in self._zones.values():
    await zone.evaluate(ctx)
for room in self._rooms.values():
    await room.compute_preheat(ctx)
    await room.calibrate_trvs(ctx)
self._hass.bus.async_fire(f"{DOMAIN}_status_update", self._build_status_payload())
```

**`__init__` state dict removals** (`coordinator.py` lines 117-164):
After refactor, remove:
- `self._last_pushed` → owned by `TRV.last_pushed`
- `self._preheat_in_progress/active/target/suppressed` → owned by `Room`
- `self._calendar_cache` → owned by `EvalContext`

Retain:
- `self._last_active_period`, `self._last_present_persons`,
  `self._last_room_periods`, `self._last_zone_periods` — consumed by
  `_build_status_payload`
- `self._calibration_last_changed/delta/offset` — until moved to `Room`
- `self._ha_tracker_listeners`, `self._matter_cal_listeners`
- `self._calendar_warn_issued`, `self._frost_locked_rooms`

**Exception-safe push wrapper pattern** (`_push_safely` lines 1582-1591):
```python
async def _push_safely(
    self, entity_id: str, desired_temp: float, context: str
) -> None:
    try:
        await self._push_if_changed(entity_id, desired_temp)
    except Exception:  # noqa: BLE001
        _LOGGER.warning(
            "Failed to push temperature to %s in %s", entity_id, context
        )
```
This wrapping pattern moves into `TRVGroup.push` or `TRV.push_temperature` —
exceptions are caught and logged, never propagated to the coordinator loop.

---

## Test File Patterns

### `tests/test_eval_context.py`, `tests/test_zone.py`, `tests/test_person.py` (pure-Python unit tests)

**Analog:** `tests/test_schedule.py` (lines 1-34)

**File header + imports pattern**:
```python
"""Tests for <module>.py — <brief description>.

No hass fixture needed. <Functions|Classes> accept <description>.
Tests:
- <test scenario 1>
- <test scenario 2>
"""

import datetime

from custom_components.climate_manager.<module> import (
    <ClassName>,
    <other_names>,
)
from custom_components.climate_manager.const import (
    PERIOD_NORMAL,
    PRESENCE_PRESENT,
    # ...
)
```

For `test_eval_context.py` the `hass` fixture IS needed (calendar fetch calls
`hass.services.async_call`). Use `tests/test_trv.py` pattern (lines 1-18)
for hass-dependent tests.

### `tests/test_room_domain.py`, `tests/test_trv.py` (hass-dependent unit tests)

**Analog:** `tests/test_trv.py` (lines 1-60)

**File header + imports pattern** (`test_trv.py` lines 1-21):
```python
"""Tests for trv.py (<description>).

<What is tested>.
"""

from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.climate_manager.trv import (
    set_trv_temperature,
    # ... other names
)

CLIMATE_ENTITY = "climate.living_room_trv"


async def test_<name>(hass):
    """<Scenario description>."""
    hass.states.async_set(CLIMATE_ENTITY, "auto", {"temperature": 18.0})
    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")
    # ... assertions
```

### `tests/test_coordinator.py` (mock target updates only)

**Analog:** Same file — `test_coordinator.py` lines 112-159

**`_make_runtime_config` helper pattern** (`test_coordinator.py` lines 83-105):
```python
def _make_runtime_config(
    default_zone_mode: str = MODE_TIME_PROGRAM,
    daily_program: dict | None = None,
    rooms_config: dict | None = None,
    persons_config: dict | None = None,
    zones_config: dict | None = None,
) -> dict:
    return {
        "version": 2,
        "default_zone": {
            "name": "Home",
            "mode": default_zone_mode,
            "time_program": daily_program if daily_program is not None
                else ALL_DAYS_NORMAL_PROGRAM,
            "preheat_enabled": False,
        },
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "rooms": rooms_config or {},
        "persons": persons_config or {},
        "zones": zones_config or {},
    }
```
No structural change needed — only mock targets change from:
```python
coordinator._last_pushed[entity_id] = X   # OLD
```
to:
```python
trv_obj.last_pushed = X                   # NEW
```

---

## Shared Patterns

### Per-Module Logger

**Source:** `custom_components/climate_manager/coordinator.py` line 89;
`custom_components/climate_manager/schedule.py` line 28

**Apply to:** All five new modules (`eval_context.py`, `zone.py`, `person.py`,
`room.py`, and the `TRV`/`TRVGroup` classes added to `trv.py`)

```python
_LOGGER = logging.getLogger(__name__)
```

Each module's `__name__` resolves to
`custom_components.climate_manager.<module>`, giving per-module log filtering
in HA's logger config.

### `from __future__ import annotations`

**Source:** `custom_components/climate_manager/coordinator.py` line 39

**Apply to:** All five new modules — required for forward references in
type annotations (e.g., `"Zone"` inside `ZoneMode`, `"EvalContext"` in
method signatures).

### SPDX License Header

**Source:** Every existing source file, line 1

**Apply to:** All new files

```python
# SPDX-License-Identifier: MIT
```

### Name-stripping helper (`_short_name`)

**Source:** `custom_components/climate_manager/coordinator.py` line 1438
(uses `.removeprefix()` for similar purpose); RESEARCH.md Code Examples

**Apply to:** `zone.py`, `person.py`, `trv.py` — wherever log lines
embed `zone=`, `person=`, or `room=` fields.

```python
def _short_name(entity_id: str) -> str:
    """Strip domain/prefix for log display (D-01)."""
    if "." in entity_id:
        return entity_id.split(".", 1)[1]
    for prefix in ("area_", "zone_"):
        if entity_id.startswith(prefix):
            return entity_id[len(prefix):]
    return entity_id
```

### Exception-safe async call pattern

**Source:** `coordinator.py` `_push_safely` lines 1582-1591 and
`_push_off_safely` lines 1593-1625

**Apply to:** `TRV.push_temperature`, `TRV.push_off`, `TRV.calibrate`

```python
try:
    await hass.services.async_call(...)
except Exception:  # noqa: BLE001
    _LOGGER.warning("Failed to <action> on %s", entity_id)
```

### Availability guard pattern

**Source:** `trv.py` lines 70-73, `coordinator.py` line 1641-1643

**Apply to:** Every HA service call in `TRV` methods

```python
state = hass.states.get(entity_id)
if state is None or state.state in ("unavailable", "unknown"):
    return
```

### Assert-False unimplemented overload

**Source:** CONTEXT.md D-04/D-05 (new pattern, no prior codebase analog)

**Apply to:** `ZoneMode.evaluate()` and `PersonMode.is_present()` base methods

```python
def evaluate(self, ctx: "EvalContext") -> None:
    assert False, f"{type(self).__name__}.evaluate() not implemented"
```
Do NOT use `raise NotImplementedError` or `@abstractmethod`.

### `asyncio.gather` concurrent task pattern

**Source:** `coordinator.py` lines 569-570, 927, 584-585

**Apply to:** `Room.apply_setpoint` when pushing to multiple TRV groups;
`coordinator.async_evaluate` zone loop (if concurrent zone evaluation is
desired — keep sequential for now to match existing serial room loop).

```python
tasks = [self._push_safely(eid, target_temp, "ZONE_EVAL") for eid in to_set]
if tasks:
    await asyncio.gather(*tasks)
```

---

## No Analog Found

All files have analogs in the codebase. The following patterns are new
(no prior code to copy from — use RESEARCH.md Pattern 3 and 4 directly):

| Pattern | Applies to | Notes |
|---|---|---|
| WeakRef mode base class | `zone.py` `ZoneMode`, `person.py` `PersonMode` | Use RESEARCH.md Pattern 3 verbatim |
| Structured log lines (3 formats) | `person.py`, `zone.py`, `trv.py` | Use RESEARCH.md Pattern 4 exactly — format strings are contracts |
| `EvalContext.calendar_events()` async lazy fetch | `eval_context.py` | Shape from `coordinator.py:_prefetch_calendars` (lines 266-343); caching logic is new |
| `TRVGroup` class | `trv.py` | Structure is new; assembly logic migrates from `_push_temperatures` (lines 519-570) |

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `tests/`

**Files scanned:** 8 source files + 12 test files

**Pattern extraction date:** 2026-06-04
