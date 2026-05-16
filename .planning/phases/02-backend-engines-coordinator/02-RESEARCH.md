# Phase 2: Backend Engines & Coordinator - Research

**Researched:** 2026-05-16
**Domain:** Home Assistant async scheduling, time-based control loops, schedule evaluation algorithms
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Scheduler Trigger**
- D-01: Poll every minute via `async_track_time_interval(hass, coordinator.async_evaluate, timedelta(minutes=1))`. DST-safe by construction.
- D-02: Push-on-change only — `_last_pushed: dict[str, float]` tracks last pushed temperature per entity_id. Service call only when desired_temp differs.
- D-03: Manual override hold — if TRV reports a temperature different from `_last_pushed[entity_id]`, skip this entity for this tick. Hold lifts automatically at next period transition.
- D-04: On HA restart, `_last_pushed` is empty. Coordinator evaluates immediately on startup and pushes correct temperature to all TRVs (INFRA-03).
- D-05: Present person + room has no Normal or Comfort periods for the day → apply Reduced temperature.
- D-06: New requirement — time programs must cover all 7 days (Mon–Sun). Exactly one weekday group per day. Validated at save time.
- D-07: Person with no room associations → skip silently.
- D-08: Person with schedule/mode but no room associations → skip silently.
- D-09: Pure backend — no HA entities in Phase 2.

### Claude's Discretion
- Coordinator class structure: how `_last_pushed` is stored, whether coordinator is a standalone class or a method on ClimateManagerData, how the scheduler listener is registered/cleaned up on unload.
- Evaluation order within a tick: sequential or parallel.
- How `dt_util.now()` is used for weekday/time resolution.

### Deferred Ideas (OUT OF SCOPE)
- Phase 3 UI warning badge for persons with no room associations.
- Configurable polling interval (v2).
- Presence override HA entities (v2).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GLOBAL-01 | User can set global mode: Off, Time program, Time program & presences | Mode constants already in const.py; coordinator reads `runtime_config["global_mode"]` |
| GLOBAL-02 | Off mode → all rooms set to frost protection temperature | Coordinator evaluates `MODE_OFF` branch; all rooms get PERIOD_FROST_PROTECTION temp |
| GLOBAL-03 | User can configure default temperatures for each period mode | `runtime_config["period_temperatures"]` provides the lookup; already in schema |
| SCHED-01 | Global time program: weekday groups with time periods | `runtime_config["global_time_program"]["weekday_groups"]` schema already defined |
| SCHED-02 | Each time period: start time + period mode | Schedule evaluation algorithm resolves HH:MM against dt_util.now() |
| SCHED-03 | Last period of day ends at midnight; first period of next weekday group takes over | Period evaluation handles `time >= last_start` with midnight sentinel |
| SCHED-04 | Each calendar day in at most one weekday group (extended to exactly one by D-06) | 7-day coverage validator needed — pure Python set comparison |
| SCHED-05 | Per-room time program overrides global; if not defined, room inherits global | Coordinator selects `rooms[area_id]["time_program"]` if present, else `global_time_program` |
| PERSON-01 | Person presence mode: Automatic, Present, Absent | `persons[person_id]["mode"]` lookup; default "automatic" |
| PERSON-02 | Present mode → always present | Short-circuit in presence resolver |
| PERSON-03 | Absent mode → always absent | Short-circuit in presence resolver |
| PERSON-04 | Automatic mode → periodic schedule determines presence | Schedule evaluation on person's `schedule.weekday_groups` |
| PERSON-05 | Automatic + no schedule configured → person defaults to absent | Empty weekday_groups → return absent |
| PERSON-06 | Person has associated rooms; when present, those rooms are warmed | `persons[person_id]["room_ids"]` list of area_ids |
| PERSON-07 | Time program & presences: present person → heat from first Normal/Comfort period to last | Occupied window algorithm: find min start of Normal/Comfort, max end of Normal/Comfort |
| PERSON-08 | Present person: sandwiched Reduced/Frost period → hold temp from preceding Normal/Comfort | "Fill gaps" logic: within the occupied window, use the previous N/C period's temperature |
| PERSON-09 | Absent person → Reduced temperature | Fallback to PERIOD_REDUCED temperature |
| INFRA-03 | On HA startup → immediately compute active period and push to all TRVs | `coordinator.async_evaluate()` called immediately in `async_setup_entry` before first tick |
| INFRA-05 | DST safety — always derive active period from dt_util.now() | `async_track_time_interval` polls every minute; each tick calls `dt_util.now()` fresh |
</phase_requirements>

---

## Summary

Phase 2 implements the complete heating control loop: a custom coordinator class that polls every minute, evaluates the active heating period from the current wall-clock time, and pushes temperatures to TRVs only when the target changes. All logic is pure backend Python — no HA entities, no WebSocket API.

The central technical challenge is the schedule evaluation algorithm, particularly the PERSON-07/08/09 "occupied window with gap-fill" logic. The algorithm is pure Python datetime arithmetic and does not depend on any HA-specific API — it is independently testable. The HA integration points are well-defined: `async_track_time_interval` for polling, `dt_util.now()` for DST-safe wall-clock time, and the established `entry.runtime_data` pattern for coordinator storage and clean unload.

The existing Phase 1 codebase provides all building blocks: `set_trv_temperature()`, `ClimateManagerStore`, `ClimateManagerData`, and `discover_rooms()/discover_persons()`. Phase 2 adds a `coordinator.py` module and extends `__init__.py` to wire it in. The test infrastructure (pytest + pytest-homeassistant-custom-component + freezegun 1.5.1) is already installed and working.

**Primary recommendation:** Implement the coordinator as a standalone `ClimateManagerCoordinator` class in `coordinator.py`. Store the `async_track_time_interval` cancel callback as a field on `ClimateManagerData`. This keeps `__init__.py` clean and makes the coordinator directly accessible from Phase 3 via `entry.runtime_data.coordinator`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schedule evaluation (which period is active now) | Pure Python (coordinator.py) | — | No HA API needed; just datetime arithmetic. Independently testable. |
| Person presence resolution | Pure Python (coordinator.py) | — | Mode lookup + schedule eval; no HA state reading needed |
| TRV temperature dispatch | HA async service layer | trv.py (existing) | Calls `hass.services.async_call`; already wrapped in `set_trv_temperature()` |
| Polling trigger | HA event layer | homeassistant.helpers.event | `async_track_time_interval` fires the evaluation callback |
| Wall-clock time source | homeassistant.util.dt | — | `dt_util.now()` is the single source of truth for local time |
| Configuration reading | entry.runtime_data | ClimateManagerStore | Config is loaded at startup; coordinator reads from `runtime_data.runtime_config` |
| Manual override detection | HA state machine | hass.states | `hass.states.get(entity_id).attributes.get("temperature")` reads TRV's current target |
| 7-day coverage validation | Pure Python (validator function) | — | Set comparison; called at config save time (Phase 3), but algorithm tested in Phase 2 |

---

## Standard Stack

### Core APIs (all from Phase 1 CLAUDE.md — verified in installed venv HA 2024.12.5)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.helpers.event.async_track_time_interval` | HA 2024.12.5 | Minute-polling trigger | Returns `CALLBACK_TYPE` (cancel callable); DST-safe; no re-scheduling needed |
| `homeassistant.util.dt` (as `dt_util`) | HA 2024.12.5 | DST-safe wall-clock time | `dt_util.now()` uses `DEFAULT_TIME_ZONE` set by HA at startup from `configuration.yaml` |
| `homeassistant.core.HomeAssistant` | HA 2024.12.5 | hass reference for state reads | `hass.states.get()` for manual override detection |
| `datetime.timedelta` | stdlib | 60-second poll interval | Standard Python; `timedelta(minutes=1)` |
| `freezegun` | 1.5.1 | Time freezing in tests | Already installed; patching integrated with pytest-homeassistant-custom-component |

### Verified Signatures [VERIFIED: installed venv source]

**`async_track_time_interval`:**
```python
# homeassistant/helpers/event.py line 1672
@callback
@bind_hass
def async_track_time_interval(
    hass: HomeAssistant,
    action: Callable[[datetime], Coroutine[Any, Any, None] | None],
    interval: timedelta,
    *,
    name: str | None = None,
    cancel_on_shutdown: bool | None = None,
) -> CALLBACK_TYPE:
    """Add a listener that fires repetitively at every timedelta interval.

    The listener is passed the time it fires in UTC time.
    """
```

Key facts:
- Returns `CALLBACK_TYPE = Callable[[], None]` — calling it cancels the listener.
- `action` receives a UTC datetime (from `dt_util.utcnow()`). **Do not use this datetime argument for local time.** Call `dt_util.now()` inside the action instead.
- `action` can be an async coroutine function — HA detects `HassJobType.Coroutinefunction` and schedules it via `async_run_hass_job`.
- `cancel_on_shutdown: None` (default) means HA does NOT auto-cancel on shutdown — the integration MUST cancel it in `async_unload_entry`.

**`dt_util.now()`:**
```python
# homeassistant/util/dt.py line 127
def now(time_zone: dt.tzinfo | None = None) -> dt.datetime:
    """Get now in specified time zone."""
    return dt.datetime.now(time_zone or DEFAULT_TIME_ZONE)
```

- `DEFAULT_TIME_ZONE` is set by HA at startup from `configuration.yaml` time_zone. Test harness sets it to "US/Pacific" in `async_test_home_assistant`.
- Returns a timezone-aware `datetime`. `.weekday()` gives 0=Monday ... 6=Sunday. `.time()` gives a `datetime.time` for HH:MM comparison.
- DST transitions are handled transparently — Python's `datetime.now(tz)` returns the correct local time regardless of DST offset.

**TRV manual override detection attribute:**
```python
# The target temperature on a TRV climate entity is in state.attributes["temperature"]
# (ATTR_TEMPERATURE = "temperature" from homeassistant/const.py line 701)
state = hass.states.get(entity_id)
reported_target = state.attributes.get("temperature")  # float or None
```
- Compare `reported_target` with `_last_pushed.get(entity_id)` to detect manual user override.
- `ATTR_CURRENT_TEMPERATURE = "current_temperature"` (from climate/const.py) — this is the measured room temperature, NOT the target. Do not confuse the two.

---

## Architecture Patterns

### System Architecture Diagram

```
HA startup
    │
    ▼
async_setup_entry()
    │── ClimateManagerStore.async_load() ──► runtime_config
    │── discover_rooms() ──────────────────► rooms dict
    │── discover_persons() ─────────────────► persons list
    │── ClimateManagerCoordinator(hass, runtime_data)
    │── coordinator.async_evaluate()   ◄── immediate push (INFRA-03)
    │── async_track_time_interval()    ──► cancel_callback stored on runtime_data
    │
    ▼
Every 60 seconds
    │
    ▼
coordinator.async_evaluate(utc_now)
    │
    │── now = dt_util.now()           ◄── local wall-clock time
    │── global_mode = runtime_config["global_mode"]
    │
    ├── MODE_OFF ──────────────────────────────────────────────┐
    │                                                           │
    ├── MODE_TIME_PROGRAM ──────────────────────────────────────┤
    │   │                                                       │
    │   └── for each room:                                      │
    │       │── resolve_time_program(room) ──► weekday_groups   │
    │       │── evaluate_schedule(weekday_groups, now) ──► period_mode
    │       │── desired_temp = period_temperatures[period_mode] │
    │       └── for each TRV in room: push_if_changed()         │
    │                                                           │
    ├── MODE_TIME_PROGRAM_PRESENCES ───────────────────────────┤
    │   │                                                       │
    │   └── for each person:                                    │
    │       │── resolve_presence(person, now) ──► present/absent
    │       └── for each room in person.room_ids:              │
    │           │── resolve_time_program(room) ──► weekday_groups
    │           │── compute_occupied_temp(weekday_groups, now, present) ──► desired_temp
    │           └── for each TRV: push_if_changed()            │
    │                                                           │
    │   (rooms not associated with any person also evaluated    │
    │    using MODE_TIME_PROGRAM logic — no presence override)  │
    │                                                           ▼
    │                                                    desired_temp = frost_protection
    │                                                    for all rooms/TRVs
    ▼
push_if_changed(entity_id, desired_temp):
    │── desired_temp == _last_pushed.get(entity_id) → skip
    │── reported_target = hass.states.get().attributes["temperature"]
    │── reported_target != _last_pushed.get(entity_id) → manual override → skip
    └── else: set_trv_temperature(hass, entity_id, desired_temp)
              _last_pushed[entity_id] = desired_temp
```

### Recommended Project Structure

```
custom_components/climate_manager/
├── __init__.py          # async_setup_entry wires coordinator + scheduler
├── const.py             # constants (Phase 1, unchanged)
├── storage.py           # ClimateManagerStore (Phase 1, unchanged)
├── trv.py               # set_trv_temperature (Phase 1, unchanged)
├── discovery.py         # discover_rooms/persons (Phase 1, unchanged)
├── coordinator.py       # NEW: ClimateManagerCoordinator class
└── schedule.py          # NEW: pure-Python schedule evaluation functions

tests/
├── conftest.py          # unchanged
├── test_init.py         # Phase 1 tests (unchanged) + Phase 2 wiring tests
├── test_trv.py          # unchanged
├── test_storage.py      # unchanged
├── test_discovery.py    # unchanged
├── test_schedule.py     # NEW: schedule evaluator unit tests (no hass needed)
├── test_presence.py     # NEW: presence algorithm unit tests (no hass needed)
└── test_coordinator.py  # NEW: coordinator integration tests (uses hass fixture)
```

**Rationale for `schedule.py` split:** The schedule evaluation functions are pure Python (no HA imports). Isolating them in `schedule.py` makes unit tests trivial — no hass fixture needed, no freezegun needed in most cases (just pass a datetime directly). The coordinator calls into `schedule.py`; `coordinator.py` handles HA integration.

### Pattern 1: Coordinator Class Structure

```python
# coordinator.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import MODE_OFF, MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES
from .schedule import evaluate_schedule, compute_occupied_temp, resolve_presence
from .trv import set_trv_temperature

if TYPE_CHECKING:
    from . import ClimateManagerData

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(minutes=1)


class ClimateManagerCoordinator:
    """Control loop: evaluates schedules every minute and pushes to TRVs."""

    def __init__(self, hass: HomeAssistant, data: ClimateManagerData) -> None:
        self._hass = hass
        self._data = data
        self._last_pushed: dict[str, float] = {}

    async def async_evaluate(self, _utc_now: datetime | None = None) -> None:
        """Evaluate all rooms and push temperatures. Called every minute and on startup."""
        now = dt_util.now()  # local wall-clock time — ignore _utc_now arg (it's UTC)
        config = self._data.runtime_config
        # ... evaluation logic ...

    async def _push_if_changed(self, entity_id: str, desired_temp: float) -> None:
        """Push temperature to TRV only if it differs from last pushed value."""
        last = self._last_pushed.get(entity_id)

        # Push-on-change: skip if already at desired temp
        if last is not None and last == desired_temp:
            return

        # Manual override detection: if TRV reports different temp than we last pushed,
        # the user adjusted it manually — hold until next period transition
        state = self._hass.states.get(entity_id)
        if state is not None and last is not None:
            reported = state.attributes.get("temperature")
            if reported is not None and float(reported) != last:
                return  # Manual override hold

        await set_trv_temperature(self._hass, entity_id, desired_temp)
        self._last_pushed[entity_id] = desired_temp
```

### Pattern 2: ClimateManagerData Extension

```python
# __init__.py — extend the dataclass with coordinator and cancel_scheduler fields
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class ClimateManagerData:
    store: ClimateManagerStore
    runtime_config: dict
    rooms: dict[str, list[str]]
    persons: list[str]
    # Phase 2 additions:
    coordinator: ClimateManagerCoordinator | None = field(default=None)
    cancel_scheduler: Callable[[], None] | None = field(default=None)
```

### Pattern 3: async_setup_entry / async_unload_entry

```python
# __init__.py

async def async_setup_entry(hass, entry):
    store = ClimateManagerStore(hass)
    runtime_config = await store.async_load()
    rooms = await discover_rooms(hass)
    persons = await discover_persons(hass)

    data = ClimateManagerData(
        store=store, runtime_config=runtime_config,
        rooms=rooms, persons=persons,
    )
    entry.runtime_data = data

    # Phase 2: wire coordinator and scheduler
    coordinator = ClimateManagerCoordinator(hass, data)
    data.coordinator = coordinator

    # INFRA-03: immediate push on startup before first tick
    await coordinator.async_evaluate()

    # Register minute-polling scheduler; store cancel callback for clean unload
    data.cancel_scheduler = async_track_time_interval(
        hass, coordinator.async_evaluate, timedelta(minutes=1),
        name="climate_manager_scheduler",
    )
    return True


async def async_unload_entry(hass, entry):
    # Cancel scheduler first — no ghost listeners (Pitfall from Phase 1 research)
    if entry.runtime_data.cancel_scheduler is not None:
        entry.runtime_data.cancel_scheduler()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

### Pattern 4: Schedule Evaluation Algorithm

**Weekday mapping** — const.py day strings to Python `datetime.weekday()`:

```python
# datetime.weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
DAY_TO_WEEKDAY = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
}
```

**Schedule evaluation** (pure Python, no HA imports):

```python
# schedule.py
import datetime
from .const import PERIOD_FROST_PROTECTION

def evaluate_schedule(weekday_groups: list[dict], now: datetime.datetime) -> str:
    """Return the active period_mode for the current time.

    Algorithm:
    1. Find the weekday_group whose 'days' list contains today's weekday.
    2. Sort periods by start time ascending.
    3. Walk periods in reverse; return the first period whose start <= now.time().
    4. If no period starts at or before now → fallback to PERIOD_FROST_PROTECTION.

    Midnight crossover is handled naturally: the last period of the day
    ends at midnight by convention (SCHED-03). There is no explicit end time
    — each period is active from its start until the next period's start.
    The first period of the next weekday group takes over after midnight, which
    means the evaluator correctly picks up the new day's first period on the
    next minute-tick after midnight.
    """
    today = now.weekday()  # 0=Mon ... 6=Sun
    current_time = now.time()

    for group in weekday_groups:
        days = [DAY_TO_WEEKDAY[d] for d in group["days"]]
        if today not in days:
            continue
        # Found today's group — find active period
        periods = sorted(group["periods"], key=lambda p: p["start"])
        active_mode = None
        for period in periods:
            h, m = map(int, period["start"].split(":"))
            period_start = datetime.time(h, m)
            if current_time >= period_start:
                active_mode = period["mode"]
            else:
                break
        return active_mode or PERIOD_FROST_PROTECTION

    return PERIOD_FROST_PROTECTION  # No group covers today (should not happen after D-06)
```

### Pattern 5: PERSON-07/08/09 Occupied Window Algorithm

This is the most complex algorithm in Phase 2. The spec says:

- Present person → heat continuously from the **first** Normal/Comfort period of the day to the **end of the last** Normal/Comfort period of the day.
- A sandwiched Reduced/Frost period between two Normal/Comfort periods → hold the temperature of the **preceding** Normal/Comfort period (no cool-down).
- Absent person → Reduced temperature always.

**Algorithm:**

```python
def compute_occupied_temp(
    weekday_groups: list[dict],
    now: datetime.datetime,
    is_present: bool,
    period_temperatures: dict[str, float],
) -> float:
    """Return the desired temperature for a person-associated room.

    PERSON-07: present → heat from first N/C period to end of last N/C period.
    PERSON-08: sandwiched Reduced/Frost between two N/C periods → hold preceding N/C temp.
    PERSON-09: absent → PERIOD_REDUCED temperature.
    D-05: present but no N/C periods in today's schedule → PERIOD_REDUCED temperature.
    """
    from .const import PERIOD_REDUCED, PERIOD_NORMAL, PERIOD_COMFORT

    if not is_present:
        return period_temperatures[PERIOD_REDUCED]

    today = now.weekday()
    current_time = now.time()

    # Find today's weekday group
    today_periods: list[dict] = []
    for group in weekday_groups:
        days = [DAY_TO_WEEKDAY[d] for d in group["days"]]
        if today in days:
            today_periods = sorted(group["periods"], key=lambda p: p["start"])
            break

    # Find all Normal/Comfort periods in today's schedule
    nc_modes = {PERIOD_NORMAL, PERIOD_COMFORT}
    nc_periods = [p for p in today_periods if p["mode"] in nc_modes]

    if not nc_periods:
        # D-05: no Normal/Comfort periods at all → apply Reduced (presence fills nothing)
        return period_temperatures[PERIOD_REDUCED]

    # Occupied window: from start of first N/C to end of last N/C (= start of next period or midnight)
    first_nc_start = _parse_time(nc_periods[0]["start"])
    last_nc_start = _parse_time(nc_periods[-1]["start"])

    # Find end of last N/C period: the start of the next period after it, or midnight
    last_nc_idx = today_periods.index(nc_periods[-1])
    if last_nc_idx + 1 < len(today_periods):
        occupied_end = _parse_time(today_periods[last_nc_idx + 1]["start"])
    else:
        occupied_end = datetime.time(23, 59, 59)  # effectively midnight

    # Before the occupied window → Reduced
    if current_time < first_nc_start:
        return period_temperatures[PERIOD_REDUCED]

    # After the occupied window → Reduced
    if current_time > occupied_end:
        return period_temperatures[PERIOD_REDUCED]

    # Within the occupied window: evaluate active period with gap-fill
    # Walk periods in reverse to find the last period whose start <= current_time
    active_mode = None
    last_nc_mode_seen = None
    for period in today_periods:
        pstart = _parse_time(period["start"])
        if pstart > current_time:
            break
        if period["mode"] in nc_modes:
            last_nc_mode_seen = period["mode"]
        active_mode = period["mode"]

    # PERSON-08: if active_mode is Reduced/Frost but we're in the occupied window,
    # use the temperature of the preceding N/C period (gap-fill)
    if active_mode not in nc_modes and last_nc_mode_seen is not None:
        active_mode = last_nc_mode_seen

    return period_temperatures.get(active_mode, period_temperatures[PERIOD_REDUCED])
```

### Pattern 6: 7-Day Coverage Validator (D-06)

```python
# schedule.py
ALL_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

def validate_7day_coverage(weekday_groups: list[dict]) -> tuple[bool, str]:
    """Validate that exactly all 7 days are covered, with no duplicates.

    Returns (True, "") if valid, (False, error_message) if invalid.
    Called at config save time (Phase 3 WebSocket handler) and in tests.
    """
    covered = []
    for group in weekday_groups:
        covered.extend(group.get("days", []))

    covered_set = set(covered)
    if len(covered) != len(covered_set):
        return False, "Duplicate day assignment in weekday groups"
    if covered_set != ALL_DAYS:
        missing = ALL_DAYS - covered_set
        extra = covered_set - ALL_DAYS
        msg = []
        if missing:
            msg.append(f"Missing days: {sorted(missing)}")
        if extra:
            msg.append(f"Unknown days: {sorted(extra)}")
        return False, "; ".join(msg)
    return True, ""
```

### Pattern 7: Presence Resolver

```python
# schedule.py
from .const import PRESENCE_AUTOMATIC, PRESENCE_PRESENT, PRESENCE_ABSENT

def resolve_presence(person_config: dict, now: datetime.datetime) -> bool:
    """Return True if person is currently present.

    PERSON-02: Present mode → always True.
    PERSON-03: Absent mode → always False.
    PERSON-04: Automatic → evaluate person's schedule.
    PERSON-05: Automatic + no schedule → False (absent by default).
    """
    mode = person_config.get("mode", "automatic")
    if mode == "present":
        return True
    if mode == "absent":
        return False
    # Automatic: evaluate periodic schedule
    schedule = person_config.get("schedule", {})
    weekday_groups = schedule.get("weekday_groups", [])
    if not weekday_groups:
        return False  # PERSON-05: no schedule → absent

    today = now.weekday()
    current_time = now.time()

    for group in weekday_groups:
        days = [DAY_TO_WEEKDAY[d] for d in group["days"]]
        if today not in days:
            continue
        periods = sorted(group["periods"], key=lambda p: p["start"])
        active_state = "absent"  # default if no period starts yet
        for period in periods:
            pstart = _parse_time(period["start"])
            if current_time >= pstart:
                active_state = period["state"]
            else:
                break
        return active_state == "present"

    return False  # No group covers today
```

### Anti-Patterns to Avoid

- **Using the UTC datetime passed to async_evaluate:** `async_track_time_interval` passes a UTC datetime as the callback argument. Never use it for local time. Always call `dt_util.now()` inside the callback.
- **Storing cancel callback in a plain variable instead of runtime_data:** Store it on `ClimateManagerData.cancel_scheduler` so `async_unload_entry` can reliably access and call it.
- **Pre-scheduling boundary times:** Do not use `async_track_time_change` or pre-compute when the next period transition occurs. Always re-derive the active period from `dt_util.now()` on each tick — this is the DST-safe approach (INFRA-05).
- **Accessing runtime_config from the coordinator's own copy:** The coordinator must read from `self._data.runtime_config` (shared reference). When Phase 3 saves new config, it updates `runtime_data.runtime_config` in place — the coordinator sees the new values on the next tick without needing a restart.
- **Assuming `state.attributes.get("temperature")` returns float:** It may return None (TRV hasn't reported yet) or an int. Always guard with `if reported is not None` and `float(reported)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DST-safe wall-clock time | Custom timezone conversion | `dt_util.now()` | HA sets `DEFAULT_TIME_ZONE` from config; `dt_util.now()` handles all DST logic |
| Minute polling | asyncio.sleep loop, threading.Timer | `async_track_time_interval` | HA's event loop integration; returns cancel callback; correct async behavior |
| TRV two-call sequence | Inline service calls | `trv.set_trv_temperature()` | Already implemented in Phase 1; availability guard included |
| Config persistence | File I/O, raw JSON | `ClimateManagerStore` | Already implemented in Phase 1; sparse-merge loading included |
| Room/person discovery | Hardcoded entity lists | `discover_rooms()` / `discover_persons()` | Already implemented in Phase 1; uses HA registry APIs |

---

## Common Pitfalls

### Pitfall 1: Ghost Listener on Unload
**What goes wrong:** `async_track_time_interval` is not cancelled when the config entry is unloaded. HA continues calling `async_evaluate` after unload; accessing `entry.runtime_data` raises `AttributeError`.
**Why it happens:** The cancel callback (return value of `async_track_time_interval`) must be stored and called explicitly — HA does not auto-cancel with `cancel_on_shutdown=None` (the default).
**How to avoid:** Store return value in `ClimateManagerData.cancel_scheduler`. Call it first thing in `async_unload_entry`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'runtime_data'` in HA logs after unload/reload.

### Pitfall 2: Callback Argument is UTC, Not Local Time
**What goes wrong:** The `action` passed to `async_track_time_interval` receives a UTC datetime as its argument (line 1660: `self.hass.async_run_hass_job(self._run_job, dt_util.utcnow(),...)`). Using it for weekday/time resolution gives wrong results in non-UTC timezones.
**Why it happens:** HA fires callbacks with UTC time for consistency.
**How to avoid:** Define `async_evaluate(self, _utc_now=None)` and immediately call `now = dt_util.now()`. Ignore the argument entirely.
**Warning signs:** Period transitions firing at wrong local times; tests pass in UTC but fail with a real timezone.

### Pitfall 3: Manual Override Hold Never Lifting
**What goes wrong:** The hold check compares `reported_target != _last_pushed`. If `_last_pushed[entity_id]` is None (first tick after startup), the condition fails unexpectedly.
**Why it happens:** On startup, `_last_pushed` is empty — `_last_pushed.get(entity_id)` returns `None`.
**How to avoid:** Check `if last is not None` before comparing. The full guard: `if last is not None and reported is not None and float(reported) != last: return`. On startup (last=None), always push.
**Warning signs:** TRVs not receiving the startup push (INFRA-03 test fails).

### Pitfall 4: Period Evaluation Off-By-One at Period Boundary
**What goes wrong:** A period defined as `{"start": "08:00", "mode": "normal"}` should be active at exactly 08:00. Using `>` instead of `>=` misses the boundary minute.
**Why it happens:** Simple fence-post error.
**How to avoid:** Use `current_time >= period_start` in all period comparisons.
**Warning signs:** Period transitions fire one minute late.

### Pitfall 5: Mutable Default in Dataclass
**What goes wrong:** Adding `coordinator: ClimateManagerCoordinator = None` without `field(default=None)` raises `ValueError: mutable default ... is not allowed`.
**Why it happens:** Python dataclass restriction on mutable defaults.
**How to avoid:** Use `coordinator: ClimateManagerCoordinator | None = field(default=None)` for all optional fields added in Phase 2.

### Pitfall 6: Confused ATTR_TEMPERATURE vs ATTR_CURRENT_TEMPERATURE
**What goes wrong:** Manual override detection reads `state.attributes.get("current_temperature")` instead of `state.attributes.get("temperature")`. These are different: `current_temperature` is the sensor reading; `temperature` is the thermostat setpoint.
**Why it happens:** Both attributes exist on climate entities; naming is confusing.
**How to avoid:** Use `state.attributes.get("temperature")` — the setpoint attribute — for override detection. Constants: `ATTR_TEMPERATURE = "temperature"` from `homeassistant.const`; `ATTR_CURRENT_TEMPERATURE = "current_temperature"` from `homeassistant.components.climate.const`.

### Pitfall 7: Presence Mode Constants Not Defined in const.py
**What goes wrong:** Presence modes ("automatic", "present", "absent") are strings in the storage schema but not defined as constants in `const.py`. Phase 2 introduces string comparisons scattered across `coordinator.py` and `schedule.py`.
**Why it happens:** Phase 1 schema defined the string values but didn't add constants for them.
**How to avoid:** Add `PRESENCE_AUTOMATIC`, `PRESENCE_PRESENT`, `PRESENCE_ABSENT` to `const.py` in Phase 2 Wave 1. All string comparisons use these constants.

---

## Code Examples

### Freezing Time in Tests (freezegun 1.5.1 — already installed)

```python
# Source: pytest_freezer.py (installed) + pytest-homeassistant-custom-component patch_time.py
# The HA test harness patches dt_util.utcnow to be interceptable by freezegun.
# Use @pytest.mark.freeze_time for declarative freezing, or freezegun.freeze_time() as context manager.

import pytest
from freezegun import freeze_time
from homeassistant.util import dt as dt_util

@pytest.mark.freeze_time("2026-01-05 08:30:00")  # Monday 08:30 UTC
async def test_schedule_evaluation_monday_morning(hass):
    # dt_util.now() returns 08:30 in whatever DEFAULT_TIME_ZONE is (UTC in tests)
    now = dt_util.now()
    assert now.weekday() == 0  # Monday

# Or: pure Python unit test (no hass needed) — just pass datetime directly
def test_evaluate_schedule_finds_active_period():
    import datetime
    from custom_components.climate_manager.schedule import evaluate_schedule

    now = datetime.datetime(2026, 1, 5, 8, 30, tzinfo=datetime.UTC)  # Monday 08:30
    weekday_groups = [{
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "periods": [
            {"start": "07:00", "mode": "normal"},
            {"start": "22:00", "mode": "reduced"},
        ]
    }, {
        "days": ["sat", "sun"],
        "periods": [{"start": "00:00", "mode": "frost_protection"}]
    }]
    assert evaluate_schedule(weekday_groups, now) == "normal"
```

### Testing Coordinator with MockConfigEntry

```python
# Source: existing pattern from test_init.py + test_trv.py
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service
from custom_components.climate_manager.const import DOMAIN

async def test_coordinator_pushes_on_startup(hass):
    """INFRA-03: coordinator calls set_trv_temperature immediately on setup."""
    # Add a climate entity state to hass
    hass.states.async_set("climate.bedroom_trv", "heat", {"temperature": 20.0})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Coordinator should have pushed at least once (INFRA-03)
    assert len(temp_calls) >= 1
```

### Testing Clean Unload (No Ghost Listeners)

```python
async def test_unload_cancels_scheduler(hass):
    """Scheduler is cancelled on unload — no ghost listeners."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.cancel_scheduler is not None

    result = await hass.config_entries.async_unload(entry.entry_id)
    assert result is True
    # After unload, cancel_scheduler should have been called (not possible to assert
    # directly, but no ghost listener errors in the hass fixture teardown)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hass.data[DOMAIN]` global dict | `entry.runtime_data` typed dataclass | HA 2024.x | Cleaner lifecycle; auto-cleaned on unload |
| `async_get_registry()` (deprecated) | `ar.async_get(hass)` / `er.async_get(hass)` | HA 2022+ | Synchronous; discovery.py already uses correct API |
| `DataUpdateCoordinator` for control loops | Custom coordinator class | N/A | `DataUpdateCoordinator` is for polling external data sources; a control loop doesn't fit the pattern |

**On `DataUpdateCoordinator`:** [ASSUMED] This class is designed for polling external APIs and notifying entities. A pure control-loop coordinator (no entities to notify, no external data to fetch) is better implemented as a plain class. The `async_track_time_interval` pattern used by HA's own components (wiffi, starline, yeelight) is the canonical approach for periodic internal actions.

---

## Runtime State Inventory

> Skipped — Phase 2 is a greenfield implementation, not a rename/refactor/migration.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Integration runtime | ✓ | 3.12 (venv) | — |
| pytest | Test execution | ✓ | (via venv) | — |
| pytest-homeassistant-custom-component | HA test harness | ✓ | 0.13.195 | — |
| freezegun | Time mocking in tests | ✓ | 1.5.1 | — |
| homeassistant (HA core libs) | Integration APIs | ✓ | 2024.12.5 | — |

**No missing dependencies.** All required packages are present in the `.venv`.

Note: The installed HA version is 2024.12.5 (venv), not 2025.x as stated in CLAUDE.md. The APIs used (`async_track_time_interval`, `dt_util.now()`, `entry.runtime_data`, `hass.states.get()`) are stable and have not changed between 2024.12 and 2025.x. [VERIFIED: source inspection of installed venv]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `DataUpdateCoordinator` is not appropriate for a pure control loop (no entity notification needed) | State of the Art | Low — custom class is strictly simpler; using DataUpdateCoordinator would work but add unnecessary complexity |
| A2 | `runtime_config` updates from Phase 3 WebSocket handlers will mutate the dict in-place, and the coordinator reads it on the next tick | Architecture Patterns (Pattern 3) | Medium — if Phase 3 replaces the dict reference instead of mutating it, coordinator sees stale config. Phase 3 must update `entry.runtime_data.runtime_config` in-place or coordinator must re-read from store each tick |
| A3 | `cancel_on_shutdown=None` (default) means the scheduler is NOT auto-cancelled on HA shutdown | Standard Stack (async_track_time_interval) | Low — the ghost listener pitfall already established; explicit cancellation in unload handles this correctly |

---

## Open Questions

1. **Rooms not associated with any person in MODE_TIME_PROGRAM_PRESENCES**
   - What we know: PERSON-06 defines rooms per person. MODE_TIME_PROGRAM_PRESENCES mode focuses on persons.
   - What's unclear: If a room has climate entities but is not in any person's `room_ids`, should it be controlled in TIME_PROGRAM_PRESENCES mode (using the time program, ignoring presence)?
   - Recommendation: Yes — evaluate all rooms via their time program regardless, then additionally apply presence overrides for person-associated rooms. Rooms with no person association behave like TIME_PROGRAM mode. This matches the spec intent ("rooms are warmed up depending on time program defined and on persons presences").

2. **Coordinator ticks while config is being saved (Phase 3 race)**
   - What we know: Phase 3 WebSocket handlers will update `runtime_data.runtime_config`. The coordinator reads it every minute.
   - What's unclear: Is there a race condition between a tick evaluating config mid-save?
   - Recommendation: Python's GIL and HA's single-threaded async event loop make this safe — a WebSocket handler coroutine and the coordinator tick cannot interleave at the Python statement level. Document this assumption for the Phase 3 researcher.

3. **Day-string canonicalization in storage**
   - What we know: Storage schema uses lowercase 3-letter day names ("mon", "tue", etc.).
   - What's unclear: The specs.md uses "Monday to Friday" — is "mon"/"tue" the canonical form?
   - Recommendation: Yes — const.py schema docs use "mon", "tue", etc. Treat these as canonical. The 7-day validator (D-06) validates against `{"mon", "tue", "wed", "thu", "fri", "sat", "sun"}`.

---

## Sources

### Primary (HIGH confidence — source-verified in installed venv)
- `homeassistant/helpers/event.py` (HA 2024.12.5) — `async_track_time_interval` signature, return type, callback argument (UTC datetime)
- `homeassistant/util/dt.py` (HA 2024.12.5) — `dt_util.now()` signature, `DEFAULT_TIME_ZONE` behavior
- `homeassistant/const.py` (HA 2024.12.5) — `ATTR_TEMPERATURE = "temperature"`
- `homeassistant/components/climate/const.py` (HA 2024.12.5) — `ATTR_CURRENT_TEMPERATURE = "current_temperature"`
- `pytest_homeassistant_custom_component/patch_time.py` — freezegun integration with `dt_util.utcnow`
- `pytest_homeassistant_custom_component/common.py` — `async_test_home_assistant` sets timezone "US/Pacific"
- `pytest_freezer.py` (1.5.1) — `@pytest.mark.freeze_time` decorator pattern
- HA source components (wiffi, starline, yeelight) — canonical cancel callback pattern: store return of `async_track_time_interval`, call it in cleanup

### Secondary (MEDIUM confidence — established project patterns)
- `custom_components/climate_manager/trv.py` — set_trv_temperature two-call pattern (Phase 1)
- `custom_components/climate_manager/storage.py` — ClimateManagerStore (Phase 1)
- `custom_components/climate_manager/__init__.py` — ClimateManagerData dataclass pattern (Phase 1)
- `tests/test_trv.py` — async_mock_service pattern, hass.states.async_set pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack (API signatures): HIGH — verified in installed venv source
- Architecture patterns: HIGH — derived from CONTEXT.md locked decisions + verified API behavior
- Schedule evaluation algorithm: HIGH — pure Python datetime arithmetic, no ambiguity
- PERSON-07/08/09 gap-fill algorithm: MEDIUM — logic derived from spec interpretation; edge cases (e.g., room not in any person) need planner confirmation
- Test approach: HIGH — freezegun + pytest-homeassistant-custom-component verified installed

**Research date:** 2026-05-16
**Valid until:** 2026-08-16 (90 days — HA helpers API is stable; dt_util and event helpers rarely change)
