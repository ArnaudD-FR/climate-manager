# Phase 11: Calendar Presence Backend — Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 8
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `custom_components/climate_manager/const.py` | config | transform | self (additive) | exact |
| `custom_components/climate_manager/schedule.py` | utility | transform | self (additive) | exact |
| `custom_components/climate_manager/coordinator.py` | service | async/event-driven | self (additive + new method) | exact |
| `custom_components/climate_manager/websocket.py` | controller | request-response | `_make_ws_set_person_config` (lines 451–500) | exact |
| `frontend/src/types.ts` | config | transform | self (additive) | exact |
| `frontend/src/components/person-card.ts` | component | event-driven | self (additive + reorder) | exact |
| `frontend/src/components/persons-tab.ts` | component | request-response | self (minimal additive) | exact |
| `tests/test_calendar.py` | test | batch | `tests/test_schedule.py` + `tests/test_coordinator.py` | role-match |

---

## Pattern Assignments

### `custom_components/climate_manager/const.py` (config, transform)

**Analog:** self — additive-only extension

**Existing constant block pattern** (lines 38–44):
```python
# ---------------------------------------------------------------------------
# Presence mode constants (PERSON-01; Pitfall 7 — define before use in
# schedule.py; D-21)
# ---------------------------------------------------------------------------

PRESENCE_AUTOMATIC = "scheduled"
PRESENCE_PRESENT = "force_present"
PRESENCE_ABSENT = "force_absent"
PRESENCE_HA = "ha"
```

**What to add — new constant after `PRESENCE_HA`:**
```python
PRESENCE_CALENDAR = "calendar"
```

**Default values block pattern** (lines 56–64):
```python
DEFAULT_GLOBAL_MODE = MODE_TIME_PROGRAM

DEFAULT_PERIOD_TEMPERATURES: dict[str, float] = {
    PERIOD_FROST_PROTECTION: 5.0,
    PERIOD_REDUCED: 18.0,
    PERIOD_NORMAL: 20.0,
    PERIOD_COMFORT: 22.0,
}
```

**What to add — new default after `DEFAULT_GLOBAL_MODE`:**
```python
DEFAULT_PREHEAT_LEAD_MINUTES: int = 60
```

**Schema comment block to extend** (lines 130–151):
```python
# Persons sub-schema (keyed by person.* entity_id — D-15):
#   {
#     "person.<name>": {
#       "mode": "<presence_mode>",
#         # "scheduled" | "force_present" | "force_absent" | "ha"
#       "room_ids": ["<area_id>", ...],
#       "schedule": { ... },
#       "schedule_type": "single" | "even_odd",
#       "schedule_even": { ... },
#       "schedule_odd":  { ... },
#     }
#   }
```

Add after `schedule_odd` comment:
```python
#       "calendar_config": {       # absent when not using Calendar mode (D-09)
#         "entity_id": "calendar.*",
#         "event_means": "absent" | "present",  # default "absent" (D-08)
#       },
#       "preheat_lead_minutes": 60,  # int, default 60 (D-10), absent = default
```

---

### `custom_components/climate_manager/schedule.py` (utility, transform)

**Analog:** self — additive extension

**Existing imports to add to** (lines 29–37):
```python
from .const import (
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
    PRESENCE_ABSENT,
    PRESENCE_AUTOMATIC,
    PRESENCE_PRESENT,
)
```

Add `PRESENCE_CALENDAR` to this import block.

**Module docstring contract** (lines 1–5):
```python
"""Climate Manager schedule and presence evaluation engine.

Pure Python — no Home Assistant imports.
All functions accept datetime objects directly; callers supply dt_util.now().
```

This "pure Python" contract MUST be preserved. The new
`_resolve_calendar_presence()` helper takes an already-fetched `events: list[dict]`
— NOT a `hass` object — so no HA imports are needed.

**Existing period walk pattern** (lines 168–179) — the pattern to extend for
`"calendar"` period state:
```python
sorted_periods = sorted(periods, key=lambda p: _parse_time(p["start"]))
active_state = "absent"  # default before first period
for period in sorted_periods:
    period_start = _parse_time(period["start"])
    if current_time >= period_start:
        active_state = period["state"]
    else:
        break
# Note: period schedule states are binary literals "present"/"absent"
return active_state == "present"
```

**New helper to add (pure Python, below `_parse_time`):**
```python
def _parse_calendar_dt(s: str) -> datetime.datetime:
    """Parse ISO date or datetime string to aware datetime.

    Timed events carry the offset ('2026-06-01T08:00:00+02:00').
    All-day events are date-only ('2026-06-02') — converted to local
    midnight via dt_util.start_of_local_day to remain offset-aware.

    Caller must import dt_util from homeassistant.util — NOT imported
    at module level to preserve the pure-Python contract.  Pass the
    result of dt_util.start_of_local_day as a callable instead, e.g.:

        _parse_calendar_dt(s, start_of_local_day=dt_util.start_of_local_day)
    """
```

**Note on tz-awareness:** `dt_util.now()` is timezone-aware. Landmine 3 from
RESEARCH.md: `datetime.datetime.fromisoformat("2026-06-02")` returns a naive
datetime in Python 3.12 — comparing it with `dt_util.now()` raises `TypeError`.
The `_parse_calendar_dt` helper must detect `"T"` absence and call
`dt_util.start_of_local_day(datetime.date.fromisoformat(s))` instead.

**New public helper signature (pure, synchronous):**
```python
def resolve_calendar_presence(
    events: list[dict],
    event_means: str,  # "absent" | "present"
    now: datetime.datetime,
    preheat_lead_minutes: int = 60,
) -> bool:
    """Return True if person should be considered present.

    Called by coordinator after _prefetch_calendars() populates
    _calendar_cache. events is already fetched — no async calls here.
    """
```

**Existing `resolve_presence()` signature to extend** (lines 123–126):
```python
def resolve_presence(
    person_config: dict,
    now: datetime.datetime,
) -> bool:
```

Add optional `calendar_cache: dict | None = None` parameter (per RESEARCH
Open Question 2 Option A) so period walk can resolve `"calendar"` period
states using the pre-fetched cache without touching async code.

---

### `custom_components/climate_manager/coordinator.py` (service, async/event-driven)

**Analog:** self — additive extension

**Existing imports** (lines 41–71):
```python
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    MODE_OFF,
    ...
    PRESENCE_HA,
    ...
)
from .schedule import compute_occupied_temp, evaluate_schedule, resolve_presence
```

Add to `from .const import (...)`: `PRESENCE_CALENDAR`
Add to top-level imports: `from homeassistant.exceptions import HomeAssistantError`

**Existing `__init__` instance vars pattern** (lines 102–123):
```python
self._last_pushed: dict[str, float | str] = {}
self._last_active_period: str | None = None
self._last_present_persons: list[str] = []
self._last_room_periods: dict[str, str] = {}
self._calibration_last_changed: dict[str, str] = {}
self._calibration_last_delta: dict[str, float] = {}
self._calibration_last_offset: dict[str, float] = {}
self._ha_tracker_listeners: dict[str, list] = {}
```

Add after `_ha_tracker_listeners`:
```python
# Per-evaluate-cycle calendar event cache (D-13).
# Keyed by calendar entity_id → list[event_dict].
# Reset at the start of each async_evaluate call; never persisted.
self._calendar_cache: dict[str, list] = {}
```

**Existing `async_evaluate()` structure** (lines 124–180):
```python
async def async_evaluate(self, _utc_now: datetime | None = None) -> None:
    now = dt_util.now()
    config = self._data.runtime_config
    period_temperatures: dict[str, float] = config["period_temperatures"]
    rooms: dict[str, list[str]] = self._data.rooms

    # Presence list computed once
    self._last_present_persons = self._compute_present_persons(config, now)
    ...
```

Pattern to follow — insert cache reset and prefetch BEFORE presence pass:
```python
async def async_evaluate(self, _utc_now: datetime | None = None) -> None:
    now = dt_util.now()
    config = self._data.runtime_config
    period_temperatures: dict[str, float] = config["period_temperatures"]
    rooms: dict[str, list[str]] = self._data.rooms

    # D-13: reset and prefetch calendar events before presence pass.
    self._calendar_cache = {}
    await self._prefetch_calendars(config, now)

    # Presence list computed once — uses _calendar_cache
    self._last_present_persons = self._compute_present_persons(config, now)
    ...
```

**Existing `asyncio.gather()` pattern** (lines 352–370) — model for
`_prefetch_calendars`:
```python
await asyncio.gather(
    *(
        self._push_safely(entity_id, ...)
        for area_id, entity_ids in rooms.items()
        for entity_id in entity_ids
        if ...
    )
)
```

**New `_prefetch_calendars` method signature:**
```python
async def _prefetch_calendars(
    self, config: dict, now: datetime
) -> None:
    """Prefetch get_events for all unique calendar entity IDs.

    Populates self._calendar_cache. Called at the top of async_evaluate()
    so all downstream presence resolution uses cached results (D-13).

    Uses asyncio.gather() — established pattern in _push_temperatures.
    Catches HomeAssistantError per RESEARCH Landmine 1 (must pass
    blocking=True, return_response=True to calendar.get_events).
    """
```

**HA service call pattern — calendar.get_events (from RESEARCH.md):**
```python
result = await self._hass.services.async_call(
    "calendar",
    "get_events",
    service_data={
        "start_date_time": now,
        "end_date_time": now + timedelta(hours=24),
    },
    target={"entity_id": eid},
    blocking=True,         # required for return_response=True
    return_response=True,  # required for SupportsResponse.ONLY
)
events = (result or {}).get(eid, {}).get("events", [])
```

**Error handling pattern — silent fallback (RESEARCH D-04):**
```python
try:
    ...
except HomeAssistantError:
    _LOGGER.warning(
        "Calendar entity %s unavailable — falling back to absent", eid
    )
    self._calendar_cache[eid] = []
```

**Existing `_compute_present_persons()` pattern to extend** (lines 596–623):
```python
def _compute_present_persons(
    self, config: dict, now: datetime
) -> list[str]:
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

Add a new `elif` branch for `PRESENCE_CALENDAR` before the `else`:
```python
elif person_config.get("mode") == PRESENCE_CALENDAR:
    cal_cfg = person_config.get("calendar_config") or {}
    eid = cal_cfg.get("entity_id", "")
    events = self._calendar_cache.get(eid, [])
    preheat = person_config.get("preheat_lead_minutes", 60)
    if resolve_calendar_presence(
        events, cal_cfg.get("event_means", "absent"), now, preheat
    ):
        present.append(person_id)
else:
    if resolve_presence(person_config, now,
                        calendar_cache=self._calendar_cache):
        present.append(person_id)
```

**Existing `_apply_presence_overrides()` pattern** (lines 281–344):
```python
for _person_id, person_config in config.get("persons", {}).items():
    room_ids: list[str] = person_config.get("room_ids", [])
    if not room_ids:
        continue

    is_present = resolve_presence(person_config, now)
```

This method also calls `resolve_presence()` directly — it must pass
`calendar_cache=self._calendar_cache` and handle the calendar mode the same
way as `_compute_present_persons()`. Landmine 5 from RESEARCH.md.

---

### `custom_components/climate_manager/websocket.py` (controller, request-response)

**Analog:** `_make_ws_set_person_config` (lines 451–500) — exact match

**Full existing handler** (lines 451–500):
```python
def _make_ws_set_person_config(entry: ClimateManagerConfigEntry):
    """Factory: create set_person_config handler."""

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_person_config",
            vol.Required("person_id"): str,
            vol.Required("config"): dict,
        }
    )
    @websocket_api.async_response
    async def ws_set_person_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        """Sparse-merge config into persons[person_id] without wiping other persons.

        T-03-09: same setdefault + update pattern as set_room_config.
        """
        incoming = msg["config"]
        if incoming.get("schedule_type") == "even_odd":
            current_person = entry.runtime_data.runtime_config.get(
                "persons", {}
            ).get(msg["person_id"], {})
            if "schedule_even" not in current_person:
                incoming.setdefault(
                    "schedule_even",
                    copy.deepcopy(current_person.get("schedule", {})),
                )
                incoming.setdefault(
                    "schedule_odd",
                    copy.deepcopy(current_person.get("schedule", {})),
                )
        (
            entry.runtime_data.runtime_config.setdefault("persons", {})
            .setdefault(msg["person_id"], {})
            .update(msg["config"])
        )
        await entry.runtime_data.store.async_save(
            entry.runtime_data.runtime_config
        )
        connection.send_result(msg["id"], {"success": True})
        hass.async_create_task(
            entry.runtime_data.coordinator.async_evaluate()
        )

    return ws_set_person_config
```

**What to add:** `calendar_config` and `preheat_lead_minutes` pass through the
existing sparse-merge `update(msg["config"])` unchanged — no new vol schema
fields required because `vol.Required("config"): dict` already accepts any dict.

Document the new accepted keys in the handler's docstring:
```python
"""Sparse-merge config into persons[person_id].

Accepted keys (all optional, sparse):
  mode: str
  room_ids: list[str]
  schedule / schedule_even / schedule_odd: DailyProgram
  schedule_type: "single" | "even_odd"
  calendar_config: {"entity_id": str, "event_means": "absent"|"present"}
  preheat_lead_minutes: int  (0–480)
"""
```

Input validation for `calendar_config.entity_id`: optionally add a prefix check
`entity_id.startswith("calendar.")` before `update()` to reject invalid entity
IDs early (RESEARCH Security Domain V5).

**Write-then-evaluate pattern** (all write handlers follow this):
```python
await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
connection.send_result(msg["id"], {"success": True})
hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
```

---

### `frontend/src/types.ts` (config, transform)

**Analog:** self — additive extension

**Existing `PersonConfig` interface** (lines 42–50):
```typescript
export interface PersonConfig {
  mode?: string;
  room_ids?: string[];
  schedule?: DailyProgram;
  schedule_type?: "single" | "even_odd";
  schedule_even?: DailyProgram;
  schedule_odd?: DailyProgram;
}
```

**Fields to add:**
```typescript
export interface PersonConfig {
  mode?: string;
  room_ids?: string[];
  schedule?: DailyProgram;
  schedule_type?: "single" | "even_odd";
  schedule_even?: DailyProgram;
  schedule_odd?: DailyProgram;
  // Phase 11: calendar presence mode (D-08, D-09)
  calendar_config?: {
    entity_id: string;
    event_means: "absent" | "present";
  };
  // Phase 11: pre-heat lead time in minutes (D-10); absent = 60
  preheat_lead_minutes?: number;
}
```

**Existing `PRESENCE_COLORS` object** (lines 170–173):
```typescript
export const PRESENCE_COLORS: Record<string, string> = {
  present: "#2E7D32",
  absent: "#9E9E9E",
};
```

Add calendar color:
```typescript
export const PRESENCE_COLORS: Record<string, string> = {
  present: "#2E7D32",
  absent: "#9E9E9E",
  calendar: "#5C6BC0",  // Phase 11 — UI-SPEC calendar color
};
```

**Existing `PERIOD_LABELS` object** (lines 176–183):
```typescript
export const PERIOD_LABELS: Record<string, string> = {
  frost_protection: "F",
  reduced: "R",
  normal: "N",
  comfort: "C",
  present: "P",
  absent: "A",
};
```

Add: `calendar: "C",`

**Existing `PERIOD_DISPLAY_NAMES` object** (lines 186–193):
```typescript
export const PERIOD_DISPLAY_NAMES: Record<string, string> = {
  frost_protection: "Frost protection",
  reduced: "Reduced",
  normal: "Normal",
  comfort: "Comfort",
  present: "Present",
  absent: "Absent",
};
```

Add: `calendar: "Calendar",`

---

### `frontend/src/components/person-card.ts` (component, event-driven)

**Analog:** self — additive + layout reorder

**Existing presence mode constants** (lines 40–45):
```typescript
const PRESENCE_MODE_SCHEDULED = "scheduled";
const PRESENCE_MODE_HA = "ha";
const PRESENCE_MODE_FORCE_PRESENT = "force_present";
const PRESENCE_MODE_FORCE_ABSENT = "force_absent";
```

Add:
```typescript
const PRESENCE_MODE_CALENDAR = "calendar";
```

**Existing `_getBadgeInfo()` switch** (lines 511–523):
```typescript
private _getBadgeInfo(): { cls: string; text: string } {
  const mode = this.config?.mode ?? PRESENCE_MODE_SCHEDULED;
  switch (mode) {
    case PRESENCE_MODE_FORCE_PRESENT:
      return { cls: "force-present", text: "Force Present" };
    case PRESENCE_MODE_FORCE_ABSENT:
      return { cls: "force-absent", text: "Force Absent" };
    case PRESENCE_MODE_HA:
      return { cls: "ha", text: haOptionLabel(this.hasDeviceTrackers) };
    default:
      return { cls: "scheduled", text: "Scheduled" };
  }
}
```

Add before `default`:
```typescript
case PRESENCE_MODE_CALENDAR:
  return { cls: "calendar", text: "Calendar" };
```

Add CSS for `.mode-badge.calendar` (same style as `.mode-badge.scheduled`,
lines 220–224):
```css
.mode-badge.calendar {
  background: var(--secondary-background-color, #f5f5f5);
  color: var(--secondary-text-color, #757575);
}
```

**Existing `_onModeChange` handler** (lines 320–342) — auto-save on `change`,
no Save button:
```typescript
private async _onModeChange(e: Event) {
  const newMode = (e.target as HTMLSelectElement).value;
  if (!newMode) return;
  try {
    ...
    await this.ws.setPersonConfig(this.personId, { mode: newMode });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

Copy this pattern for new calendar config save handlers:
```typescript
private async _onCalendarEntityChange(e: Event) {
  const entityId = (e.target as HTMLSelectElement).value;
  const currentMeans =
    this.config?.calendar_config?.event_means ?? "absent";
  try {
    await this.ws.setPersonConfig(this.personId, {
      calendar_config: { entity_id: entityId, event_means: currentMeans },
    });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}

private async _onEventMeansChange(e: Event) {
  const means = (e.target as HTMLSelectElement).value as "absent" | "present";
  const currentEntityId = this.config?.calendar_config?.entity_id ?? "";
  try {
    await this.ws.setPersonConfig(this.personId, {
      calendar_config: {
        entity_id: currentEntityId,
        event_means: means,
      },
    });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}

private async _onPreheatChange(e: Event) {
  const val = parseInt((e.target as HTMLInputElement).value, 10);
  if (!isNaN(val) && val >= 0 && val <= 480) {
    try {
      await this.ws.setPersonConfig(this.personId, {
        preheat_lead_minutes: val,
      });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }
}
```

**Existing mode `<select>` in render()** (lines 599–626):
```typescript
<select class="mode-select" @change=${this._onModeChange}>
  <option value=${PRESENCE_MODE_SCHEDULED} ?selected=${...}>Scheduled</option>
  <option value=${PRESENCE_MODE_HA} ?selected=${...}>
    ${haOptionLabel(this.hasDeviceTrackers)}
  </option>
  <option value=${PRESENCE_MODE_FORCE_PRESENT} ?selected=${...}>Force Present</option>
  <option value=${PRESENCE_MODE_FORCE_ABSENT} ?selected=${...}>Force Absent</option>
</select>
```

Add `<option value=${PRESENCE_MODE_CALENDAR} ...>Calendar</option>` after
`PRESENCE_MODE_HA`.

**D-14 layout reorder:** The current render order in the expanded section is:
1. Presence mode label + select (lines 592–651)
2. Room associations (lines 652–696)
3. Presence schedule section (lines 698–775)

Required new order per D-14:
1. Presence mode label + select
2. `schedule-hint` paragraph
3. Calendar config block (new — visible only when `currentMode === PRESENCE_MODE_CALENDAR`)
4. Presence schedule section (visible when `currentMode === PRESENCE_MODE_SCHEDULED`)
5. Room associations (moved last)

**Calendar entity picker pattern** — from RESEARCH.md and `persons-tab.ts`
(lines 110–112):
```typescript
// hass.states filtering pattern (from persons-tab.ts render())
const hassPersonIds = Object.keys(this.hass?.states ?? {}).filter((k) =>
  k.startsWith("person."),
);
```

Applied to calendar entities:
```typescript
const calendarEntityIds = Object.keys(this.panel.hass?.states ?? {})
  .filter((id) => id.startsWith("calendar."))
  .sort();
```

Friendly name:
```typescript
this.panel.hass?.states[id]?.attributes?.friendly_name ?? id
```

**Calendar config block template (new):**
```typescript
${currentMode === PRESENCE_MODE_CALENDAR ? html`
  <div class="section-label" title="Calendar entity for presence">
    Calendar source
  </div>
  <div class="select-wrapper">
    <select class="mode-select" @change=${this._onCalendarEntityChange}>
      <option value="">— Select calendar —</option>
      ${calendarEntityIds.map((id) => html`
        <option
          value=${id}
          ?selected=${this.config?.calendar_config?.entity_id === id}
        >
          ${this.panel.hass?.states[id]?.attributes?.friendly_name ?? id}
        </option>
      `)}
    </select>
  </div>
  <div class="section-label">Event means</div>
  <div class="select-wrapper">
    <select class="mode-select" @change=${this._onEventMeansChange}>
      <option
        value="absent"
        ?selected=${(this.config?.calendar_config?.event_means ?? "absent") === "absent"}
      >Absent during events</option>
      <option
        value="present"
        ?selected=${this.config?.calendar_config?.event_means === "present"}
      >Present during events</option>
    </select>
  </div>
  <div class="section-label">Pre-heat lead time</div>
  <div class="select-wrapper">
    <input
      type="number" min="0" max="480" step="5"
      .value=${String(this.config?.preheat_lead_minutes ?? 60)}
      @change=${this._onPreheatChange}
    />
    <span> min before return</span>
  </div>
` : ""}
```

---

### `frontend/src/components/persons-tab.ts` (component, request-response)

**Analog:** self — minimal additive change

The only modification needed is to propagate `this.hass` into `PersonCard` if
the card needs `panel.hass` to filter calendar entities. Currently `PersonCard`
receives `panel` (the root element) and accesses `this.panel.hass` — no new
prop binding is needed in `persons-tab.ts` as long as `panel` is already
passed (line 165):
```typescript
.panel=${this.panel}
```

The `hass` object used for filtering calendar entities in `person-card.ts`
comes from `this.panel.hass`, which is already available. No change needed in
`persons-tab.ts` unless `panel.hass` is not reliable — in that case add:
```typescript
.hass=${this.hass}
```

**Existing `hass.states` filter pattern** (lines 110–112):
```typescript
const hassPersonIds = Object.keys(this.hass?.states ?? {}).filter((k) =>
  k.startsWith("person."),
);
```

Copy this pattern in `person-card.ts` for calendar entities:
```typescript
const calendarEntityIds = Object.keys(this.panel.hass?.states ?? {})
  .filter((id) => id.startsWith("calendar."))
  .sort();
```

---

### `tests/test_calendar.py` (test, batch)

**Analog:** `tests/test_schedule.py` (pure unit tests) + `tests/test_coordinator.py`
(integration tests with hass fixture)

**File header / module docstring pattern** (from `test_schedule.py` lines 1–10):
```python
"""Tests for schedule.py — pure Python schedule evaluation functions.

No hass fixture needed. Functions accept datetime objects directly.
Tests:
- evaluate_schedule: ...
- resolve_presence: ...
"""
```

Applied to new file:
```python
"""Tests for calendar presence logic — Phase 11 (CAL-01..CAL-04).

Two sections:
1. Pure unit tests for _resolve_calendar_presence() — no hass fixture needed.
   Uses freeze_time for deterministic datetime comparison.
2. Integration tests for coordinator._prefetch_calendars() and cache behavior
   — requires hass fixture and async_mock_service.
"""
```

**Pure test structure** (from `test_schedule.py` lines 112–130):
```python
import datetime

from custom_components.climate_manager.schedule import (
    resolve_presence,
    ...
)
from custom_components.climate_manager.const import (
    PRESENCE_AUTOMATIC,
    PRESENCE_PRESENT,
    ...
)
```

**`freeze_time` pattern** (from RESEARCH.md):
```python
@pytest.mark.freeze_time("2026-06-01 12:00:00")
def test_active_event_absent_by_default():
    events = [
        {
            "start": "2026-06-01T08:00:00+02:00",
            "end": "2026-06-01T17:00:00+02:00",
            "summary": "School",
        }
    ]
    now = dt_util.now()
    assert _resolve_calendar_presence(events, "absent", now, 60) is False
```

**`async_mock_service` pattern** (from RESEARCH.md + `test_coordinator.py` lines 19–21):
```python
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)
```

Service mock with response (RESEARCH.md):
```python
from homeassistant.core import SupportsResponse

mock_events = [
    {
        "start": "2026-06-01T08:00:00+02:00",
        "end": "2026-06-01T17:00:00+02:00",
        "summary": "School",
    }
]
calendar_calls = async_mock_service(
    hass,
    "calendar",
    "get_events",
    response={"calendar.pronote_jean": {"events": mock_events}},
    supports_response=SupportsResponse.ONLY,
)
```

**`_make_runtime_config` helper pattern** (from `test_coordinator.py` lines
86–105):
```python
def _make_runtime_config(
    global_mode: str = MODE_TIME_PROGRAM,
    daily_program: dict | None = None,
    rooms_config: dict | None = None,
    persons_config: dict | None = None,
    zones_config: dict | None = None,
) -> dict:
    """Build a runtime_config dict suitable for coordinator tests."""
    return {
        "version": 2,
        "global_mode": global_mode,
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "global_time_program": daily_program if daily_program is not None
                               else ALL_DAYS_NORMAL_PROGRAM,
        "rooms": rooms_config or {},
        "persons": persons_config or {},
        "zones": zones_config or {},
        "default_zone_name": "Home",
    }
```

Copy and extend for calendar tests — add `calibration_enabled: False` (as
coordinator now reads it).

**Test naming convention** (from RESEARCH.md Validation Architecture table):
```
test_calendar_mode_absent_during_event
test_calendar_mode_present_no_event
test_calendar_fallback_on_error
test_calendar_cache_deduplication
test_calendar_cache_reset_per_cycle
test_calendar_period_state_resolves
test_preheat_triggers_at_boundary
test_preheat_no_trigger_before_boundary
```

**`asyncio_mode = "auto"` note:** `pyproject.toml` sets `asyncio_mode = "auto"`.
All `async def test_*` functions run automatically without `@pytest.mark.asyncio`.
No decorator needed for async tests.

**Error simulation pattern** (RESEARCH.md):
```python
from homeassistant.exceptions import HomeAssistantError

async_mock_service(
    hass,
    "calendar",
    "get_events",
    raise_exception=HomeAssistantError("No entities matched"),
    supports_response=SupportsResponse.ONLY,
)
```

---

## Shared Patterns

### Sparse Config / Additive Schema
**Source:** Multiple existing files — `const.py` docstring (lines 104–178),
`websocket.py` `_make_ws_set_person_config` (lines 489–493).
**Apply to:** All new fields (`calendar_config`, `preheat_lead_minutes`).
```python
# Absent key = default. Never write None. Never populate DEFAULT_CONFIG.
# Sparse-merge via setdefault + update in websocket handler.
entry.runtime_data.runtime_config.setdefault("persons", {}) \
    .setdefault(msg["person_id"], {}) \
    .update(msg["config"])
```

### Write-Then-Evaluate Pattern
**Source:** `websocket.py` — every write handler (e.g., lines 304–309).
**Apply to:** Any new websocket write path.
```python
await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
connection.send_result(msg["id"], {"success": True})
hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
```

### Auto-Save on Change (no Save button)
**Source:** `person-card.ts` — `_onModeChange`, `_onScheduleTypeChange`
(lines 320–372).
**Apply to:** Calendar entity picker, event_means select, preheat input.
```typescript
@change=${this._onCalendarEntityChange}  // → ws.setPersonConfig + reloadConfig
```

### Silent Fallback on Calendar Error
**Source:** RESEARCH.md D-04 + coordinator `_compute_present_persons`
(lines 614–618).
**Apply to:** `_prefetch_calendars()` catch block.
```python
except HomeAssistantError:
    _LOGGER.warning(
        "Calendar entity %s unavailable — falling back to absent", eid
    )
    self._calendar_cache[eid] = []
```

### WebSocket Factory Pattern
**Source:** `websocket.py` — every handler (lines 129–500).
**Apply to:** Any new WS command if needed.
```python
def _make_ws_<command>(entry: ClimateManagerConfigEntry):
    @websocket_api.websocket_command({...})
    @websocket_api.async_response
    async def ws_<command>(hass, connection, msg) -> None:
        ...
    return ws_<command>
```

### Pure Python Module Contract
**Source:** `schedule.py` module docstring (lines 1–6).
**Apply to:** All additions to `schedule.py`.
No `homeassistant` imports. New helpers accept `events: list[dict]`,
not `hass`. Keeps existing `test_schedule.py` valid without HA mock infra.

### `asyncio.gather()` Concurrent Async Pattern
**Source:** `coordinator.py` `_push_temperatures` (lines 352–370).
**Apply to:** `_prefetch_calendars()` — one `get_events` call per unique entity.
```python
await asyncio.gather(*[_fetch_one(eid) for eid in entity_ids])
```

---

## No Analog Found

All files have close analogs in the codebase. No entries in this section.

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `frontend/src/`,
`tests/`
**Files scanned:** 9 source files + 2 test files
**Pattern extraction date:** 2026-06-02
