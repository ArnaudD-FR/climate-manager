# Phase 2: Backend Engines & Coordinator - Pattern Map

**Mapped:** 2026-05-16 **Files analyzed:** 6 (4 new, 2 modified) **Analogs
found:** 6 / 6

---

## File Classification

| New/Modified File                                  | Role    | Data Flow                          | Closest Analog                               | Match Quality                                               |
| -------------------------------------------------- | ------- | ---------------------------------- | -------------------------------------------- | ----------------------------------------------------------- |
| `custom_components/climate_manager/coordinator.py` | service | event-driven (minute-poll)         | `custom_components/climate_manager/trv.py`   | role-partial (same HA async pattern, different data flow)   |
| `custom_components/climate_manager/schedule.py`    | utility | transform (datetime → period mode) | `custom_components/climate_manager/const.py` | role-partial (pure Python, no HA imports)                   |
| `tests/test_coordinator.py`                        | test    | request-response                   | `tests/test_init.py`                         | exact (MockConfigEntry + hass fixture + async_mock_service) |
| `tests/test_schedule.py`                           | test    | transform                          | `tests/test_trv.py`                          | role-match (unit test structure, pure function calls)       |
| `custom_components/climate_manager/__init__.py`    | config  | CRUD                               | self (existing file)                         | exact (extend in-place)                                     |
| `custom_components/climate_manager/const.py`       | config  | —                                  | self (existing file)                         | exact (extend in-place)                                     |

---

## Pattern Assignments

### `custom_components/climate_manager/coordinator.py` (service, event-driven)

**Analog:** `custom_components/climate_manager/trv.py` (same HA async pattern) +
`custom_components/climate_manager/__init__.py` (runtime_data access pattern)

**No direct analog exists** — this is the first event-driven service class in
the project. Use patterns extracted from the two closest files below, plus the
RESEARCH.md code examples.

**Imports pattern** — copy from `trv.py` lines 14, 31–49 style:

```python
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
    PERIOD_REDUCED,
)
from .schedule import compute_occupied_temp, evaluate_schedule, resolve_presence
from .trv import set_trv_temperature

if TYPE_CHECKING:
    from . import ClimateManagerData

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(minutes=1)
```

**HA state read pattern** — copy from `trv.py` lines 31–33:

```python
# trv.py lines 31-33 — availability guard pattern
state = hass.states.get(entity_id)
if state is None or state.state == "unavailable":
    return
```

Apply same pattern in `_push_if_changed` for manual override detection:

```python
state = self._hass.states.get(entity_id)
if state is not None and last is not None:
    reported = state.attributes.get("temperature")  # ATTR_TEMPERATURE, not current_temperature
    if reported is not None and float(reported) != last:
        return  # Manual override hold (D-03)
```

**HA service call pattern** — copy from `trv.py` lines 35–49:

```python
# trv.py lines 35-49 — blocking=True, domain/service/data pattern
await hass.services.async_call(
    "climate",
    "set_hvac_mode",
    {"entity_id": entity_id, "hvac_mode": "heat"},
    blocking=True,
)
```

The coordinator calls `set_trv_temperature(self._hass, entity_id, desired_temp)`
— do not inline the two-call sequence. Import and call `set_trv_temperature`
directly.

**Docstring style** — copy from `trv.py` lines 1–13 and lines 17–29:

```python
"""Climate Manager coordinator.

One-line summary.

Design decisions from CONTEXT.md / RESEARCH.md:
- D-01: Poll every minute via async_track_time_interval
- D-02: Push-on-change only (_last_pushed dict)
- D-03: Manual override hold
"""
```

**Logging pattern** — copy from any module that defines `_LOGGER`:

```python
_LOGGER = logging.getLogger(__name__)
```

Use `_LOGGER.debug(...)` for per-tick evaluation traces, `_LOGGER.warning(...)`
for unexpected states (e.g., TRV state parse failure).

---

### `custom_components/climate_manager/schedule.py` (utility, transform)

**Analog:** `custom_components/climate_manager/const.py` (pure Python, no HA
imports)

**Module header pattern** — copy from `const.py` lines 1–6:

```python
"""Climate Manager schedule evaluation functions.

Pure Python — no Home Assistant imports.
All functions accept datetime objects directly; callers supply dt_util.now().
"""
```

**No HA imports** — `const.py` establishes this convention (line 6: "No Home
Assistant imports — pure constants only"). `schedule.py` must follow the same
rule. Only stdlib imports (`datetime`) and imports from `.const`.

**Constant block pattern** — copy from `const.py` lines 9–12 section style:

```python
# ---------------------------------------------------------------------------
# Day name → Python weekday() mapping (0=Mon ... 6=Sun)
# ---------------------------------------------------------------------------

DAY_TO_WEEKDAY: dict[str, int] = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
}

ALL_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
```

**Function docstring pattern** — copy from `trv.py` lines 17–29 style (decision
refs in docstring):

```python
def evaluate_schedule(weekday_groups: list[dict], now: datetime.datetime) -> str:
    """Return the active period_mode for the current time.

    Algorithm: find today's group, sort periods, walk in order, return last
    period whose start <= now.time(). Falls back to PERIOD_FROST_PROTECTION.

    SCHED-02: each period active from start until next period's start.
    SCHED-03: last period of day ends at midnight.
    """
```

---

### `tests/test_coordinator.py` (test, integration)

**Analog:** `tests/test_init.py` — exact match (MockConfigEntry + hass fixture +
runtime_data assertions)

**File header and imports pattern** — copy from `test_init.py` lines 1–13:

```python
"""Tests for ClimateManagerCoordinator integration behavior.

Tests:
- Coordinator pushes to TRVs immediately on startup (INFRA-03)
- Scheduler is registered and cancellable on unload (Pitfall 1)
- Push-on-change: no second call if temperature unchanged (D-02)
- Manual override hold: skip entity when TRV reports different temp (D-03)
"""
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.climate_manager.const import DOMAIN
from custom_components.climate_manager import ClimateManagerData
```

**MockConfigEntry setup pattern** — copy from `test_init.py` lines 15–24:

```python
# test_init.py lines 15-24 — the canonical setup sequence for all coordinator tests
entry = MockConfigEntry(domain=DOMAIN, data={})
entry.add_to_hass(hass)
await hass.config_entries.async_setup(entry.entry_id)
await hass.async_block_till_done()
```

**State seeding pattern** — copy from `test_trv.py` lines 20–21:

```python
# test_trv.py line 20 — seed HA state before calling the function under test
hass.states.async_set("climate.bedroom_trv", "heat", {"temperature": 20.0})
```

For coordinator tests: seed TRV states before `async_setup` so the startup push
has real entities to push to.

**Service call capture pattern** — copy from `test_trv.py` lines 23–24:

```python
# test_trv.py lines 23-24 — register mock services BEFORE the action under test
hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
temp_calls = async_mock_service(hass, "climate", "set_temperature")
```

**Assertion style** — copy from `test_trv.py` lines 28–38:

```python
assert len(temp_calls) >= 1
assert temp_calls[0].data["entity_id"] == "climate.bedroom_trv"
assert temp_calls[0].data["temperature"] == 20.0
```

**Unload assertion pattern** — copy from `test_init.py` lines 57–65:

```python
# test_init.py lines 57-65 — verify unload returns True
result = await hass.config_entries.async_unload(entry.entry_id)
assert result is True
```

Extend for Phase 2: assert `entry.runtime_data.cancel_scheduler is not None`
before unload.

**`freezegun` time-freeze pattern** — no existing test uses it yet; use
RESEARCH.md Pattern:

```python
import pytest

@pytest.mark.freeze_time("2026-01-05 08:30:00")  # Monday 08:30 UTC (= local in test harness)
async def test_coordinator_applies_monday_morning_period(hass):
    ...
```

The `conftest.py` `auto_enable_custom_integrations` fixture applies
automatically — no additional fixture needed for `freeze_time`.

---

### `tests/test_schedule.py` (test, pure unit)

**Analog:** `tests/test_trv.py` — role-match (direct function import, no
MockConfigEntry needed)

**File header pattern** — copy from `test_trv.py` lines 1–10:

```python
"""Tests for schedule.py — pure Python schedule evaluation functions.

No hass fixture needed. Functions accept datetime objects directly.
Tests:
- evaluate_schedule: finds active period for current time
- validate_7day_coverage: rejects missing/duplicate days (D-06)
- resolve_presence: PERSON-01 through PERSON-05 modes
- compute_occupied_temp: PERSON-07/08/09 occupied window and gap-fill
"""
import datetime

import pytest

from custom_components.climate_manager.schedule import (
    compute_occupied_temp,
    evaluate_schedule,
    resolve_presence,
    validate_7day_coverage,
)
```

**Direct function call pattern** — copy from `test_trv.py` lines 26:

```python
# test_trv.py line 26 — call function under test directly, no service layer
await set_trv_temperature(hass, CLIMATE_ENTITY, 21.0)
```

For schedule tests (synchronous functions):

```python
# No await — schedule functions are pure Python, not async
result = evaluate_schedule(weekday_groups, now)
assert result == "normal"
```

**Named constant for test fixtures** — copy from `test_trv.py` line 12:

```python
# test_trv.py line 12 — module-level constant for entity under test
CLIMATE_ENTITY = "climate.living_room_trv"
```

For schedule tests, define reusable weekday_groups fixtures at module level or
as `@pytest.fixture` — no hass dependency needed.

**`pytest.mark` usage** — copy from `test_trv.py` line 58 (no marks needed for
pure tests); `freeze_time` is not required in `test_schedule.py` — pass
`datetime` objects directly to functions, which is cleaner and faster than
freezegun.

---

### `custom_components/climate_manager/__init__.py` (modified — extend in-place)

**Analog:** self (existing file, extend in-place)

**Dataclass extension pattern** — copy from `__init__.py` lines 28–45, add two
fields:

```python
# __init__.py lines 28-45 — existing dataclass; Phase 2 appends two fields
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class ClimateManagerData:
    store: ClimateManagerStore
    runtime_config: dict
    rooms: dict[str, list[str]]
    persons: list[str]
    # Phase 2 additions — use field(default=None) to avoid mutable default error (Pitfall 5)
    coordinator: "ClimateManagerCoordinator | None" = field(default=None)
    cancel_scheduler: "Callable[[], None] | None" = field(default=None)
```

**Import extension pattern** — copy from `__init__.py` lines 15–21, add new
imports:

```python
# Existing imports (lines 15-21) — add after these:
from datetime import timedelta

from homeassistant.helpers.event import async_track_time_interval

from .coordinator import ClimateManagerCoordinator
```

**async_setup_entry extension pattern** — copy from `__init__.py` lines 52–80,
extend the body after `entry.runtime_data = ClimateManagerData(...)` (line 73):

```python
# After existing runtime_data assignment (line 73) — wire coordinator
coordinator = ClimateManagerCoordinator(hass, entry.runtime_data)
entry.runtime_data.coordinator = coordinator

# INFRA-03: immediate push on startup before first scheduler tick
await coordinator.async_evaluate()

# Register minute-polling scheduler; store cancel callback for clean unload (Pitfall 1)
entry.runtime_data.cancel_scheduler = async_track_time_interval(
    hass,
    coordinator.async_evaluate,
    timedelta(minutes=1),
    name="climate_manager_scheduler",
)
```

**async_unload_entry extension pattern** — copy from `__init__.py` lines 83–92,
prepend scheduler cancellation before the existing `async_unload_platforms`
call:

```python
async def async_unload_entry(hass, entry):
    # Cancel scheduler FIRST — no ghost listeners (Pitfall 1, T-01-10)
    if entry.runtime_data.cancel_scheduler is not None:
        entry.runtime_data.cancel_scheduler()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

---

### `custom_components/climate_manager/const.py` (modified — add 3 constants)

**Analog:** self (existing file, extend in-place)

**Constant block pattern** — copy from `const.py` lines 19–21 section style:

```python
# ---------------------------------------------------------------------------
# Presence mode constants (PERSON-01; Pitfall 7 — define before use in schedule.py)
# ---------------------------------------------------------------------------

PRESENCE_AUTOMATIC = "automatic"
PRESENCE_PRESENT = "present"
PRESENCE_ABSENT = "absent"
```

Insert after the `# Period mode name constants` block (after line 30) and before
the `# Default values` block (line 33). This matches the file's existing pattern
of grouping related constants under a comment header.

---

## Shared Patterns

### HA Async Service Call (blocking=True)

**Source:** `custom_components/climate_manager/trv.py` lines 35–49 **Apply to:**
`coordinator.py` (indirectly, via `set_trv_temperature` import)

```python
await hass.services.async_call(
    "climate",
    "set_hvac_mode",
    {"entity_id": entity_id, "hvac_mode": "heat"},
    blocking=True,
)
```

### HA State Read with None Guard

**Source:** `custom_components/climate_manager/trv.py` lines 31–33 **Apply to:**
`coordinator.py` `_push_if_changed` method

```python
state = hass.states.get(entity_id)
if state is None or state.state == "unavailable":
    return
```

### MockConfigEntry Test Setup Sequence

**Source:** `tests/test_init.py` lines 15–24 **Apply to:**
`tests/test_coordinator.py` — every integration test function

```python
entry = MockConfigEntry(domain=DOMAIN, data={})
entry.add_to_hass(hass)
await hass.config_entries.async_setup(entry.entry_id)
await hass.async_block_till_done()
```

### async_mock_service Capture Pattern

**Source:** `tests/test_trv.py` lines 23–24 **Apply to:**
`tests/test_coordinator.py` — all tests verifying TRV pushes

```python
hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
temp_calls = async_mock_service(hass, "climate", "set_temperature")
# Register BEFORE the action under test
```

### conftest.py autouse Fixture

**Source:** `tests/conftest.py` lines 8–14 **Apply to:** Both new test files
inherit automatically (autouse=True covers the whole package). No additional
fixture needed in test_coordinator.py or test_schedule.py.

### Module Docstring + Decision Refs

**Source:** `custom_components/climate_manager/trv.py` lines 1–13 **Apply to:**
`coordinator.py` and `schedule.py` — list REQ-IDs and D-xx decisions addressed
by the module.

---

## No Analog Found

No files are without an analog — all new files have at least a partial match via
existing project files. The closest gap is `coordinator.py` which has no
event-driven service class precedent in the project; the RESEARCH.md Pattern 1
code example (lines 241–297) is the authoritative reference for that file.

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `tests/` **Files
scanned:** 9 (6 integration source + 3 key test files) **Pattern extraction
date:** 2026-05-16
