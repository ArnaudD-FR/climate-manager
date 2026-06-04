# Phase 12: Predictive Pre-heat — Pattern Map

**Mapped:** 2026-06-02
**Files analyzed:** 9 (7 modified, 1 new backend, 1 new test)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `custom_components/climate_manager/schedule.py` | utility | transform | `schedule.py:resolve_presence()` (lines 276–367) | exact — same signature, same dispatch |
| `custom_components/climate_manager/coordinator.py` | service | event-driven | `coordinator.py:_async_calibrate()` (lines 501–560) + `_build_status_payload()` (lines 873–957) | exact |
| `custom_components/climate_manager/storage.py` | service | CRUD | `storage.py:async_load()` migration block (lines 129–138) | exact |
| `custom_components/climate_manager/const.py` | config | — | `const.py` existing constant block (lines 54–71) | exact |
| `custom_components/climate_manager/websocket.py` | middleware | request-response | `websocket.py:ws_get_status` (lines 129–242) + `ws_set_person_config` (lines 542–548) | exact |
| `custom_components/climate_manager/__init__.py` | config | CRUD | `__init__.py:ClimateManagerData` (lines 64–96) + `async_setup_entry` (lines 127–155) | exact |
| `frontend/src/types.ts` | model | — | `types.ts:RoomConfig` (lines 54–66), `RoomStatus` (lines 117–127), `PersonConfig` (lines 68–81) | exact |
| `frontend/src/components/room-card.ts` | component | request-response | `room-card.ts:_onZoneChange` (lines 421–433), `_renderRoomModeDescription` (lines 625–635) | exact |
| `tests/test_preheat.py` (NEW) | test | — | `tests/test_calendar.py` — same fixture and hass fixture patterns | role-match |

---

## Pattern Assignments

### `custom_components/climate_manager/schedule.py` — add `next_occupied_at()`

**Analog:** `schedule.py:resolve_presence()` lines 276–367

**Imports pattern** (lines 26–39 — unchanged, no new imports needed):
```python
import datetime
import logging
import re

from .const import (
    GAP_HANDLING_DAY_SPAN,
    GAP_HANDLING_THRESHOLD,
    PERIOD_COMFORT,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
    PRESENCE_ABSENT,
    PRESENCE_AUTOMATIC,
    PRESENCE_PRESENT,
)
```
Phase 12 also needs `PRESENCE_HA`, `PRESENCE_CALENDAR` from const.py — add to this
import block. `timedelta` is already imported via `datetime`.

**Core dispatch pattern** (lines 303–327 of `resolve_presence` — the mode branch):
```python
# resolve_presence() — exact model for next_occupied_at()
mode = person_config.get("mode", PRESENCE_AUTOMATIC)

if mode == PRESENCE_PRESENT:
    return True          # → next_occupied_at: return None (forced — no transition)
if mode == PRESENCE_ABSENT:
    return False         # → next_occupied_at: return None

# Automatic: evaluate periodic schedule (per-day dict, D-01)
schedule_type = person_config.get("schedule_type", "single")
if schedule_type == "even_odd":
    week_parity = now.date().isocalendar().week % 2
    schedule_key = "schedule_even" if week_parity == 0 else "schedule_odd"
    schedule = person_config.get(schedule_key, {})
else:
    schedule = person_config.get("schedule", {})
day_name = WEEKDAY_TO_DAY[now.weekday()]
periods = schedule.get(day_name, [])
```

`next_occupied_at()` must do this for **each day in a 7-day lookahead** instead of
only `now`'s day. Pattern for computing even/odd parity on future dates:
```python
# For each day_offset in range(7):
target_date = (now + datetime.timedelta(days=day_offset)).date()
parity = target_date.isocalendar().week % 2   # correct — not now's week
schedule_key = "schedule_even" if parity == 0 else "schedule_odd"
```

**Calendar dispatch pattern** (lines 346–362 of `resolve_presence`):
```python
# Handle period state "calendar"
if active_state == "calendar" and active_period is not None:
    cal_cfg = active_period.get("calendar_config") or {}
    entity_id = cal_cfg.get("entity_id", "")
    event_means = cal_cfg.get("event_means", "absent")
    events = (calendar_cache or {}).get(entity_id, [])
    preheat = person_config.get("preheat_lead_minutes", 60)
    return resolve_calendar_presence(
        events,
        event_means,
        now,
        gap_handling=cal_cfg.get("gap_handling", "exact"),
        gap_threshold_minutes=cal_cfg.get("gap_threshold_minutes", 0),
        preheat_lead_minutes=preheat,
        start_of_local_day=start_of_local_day,
    )
```

`next_occupied_at()` uses a simpler variant: for calendar-mode persons, look at
`_calendar_cache[entity_id]` events and return the next boundary (event end when
`event_means="absent"`; event start when `event_means="present"`).

**Aware datetime construction pattern** (lines 94–121 — `_parse_calendar_dt`):
```python
# Use this for calendar events; for schedule periods use:
datetime.datetime.combine(
    target_date,
    _parse_time(period["start"])
).replace(tzinfo=now.tzinfo)
# Never mix naive and aware datetimes (Pitfall 2 in RESEARCH.md)
```

**Function signature to match** (mirrors `resolve_presence` exactly):
```python
def next_occupied_at(
    person_config: dict,
    now: datetime.datetime,
    calendar_cache: dict | None = None,
    start_of_local_day=None,
) -> datetime.datetime | None:
```

---

### `custom_components/climate_manager/coordinator.py` — add `_async_preheat()` pass + status fields

**Analog:** `_async_calibrate()` (lines 501–560) for the pass structure;
`_build_status_payload()` (lines 873–957) + `ws_get_status` (lines 129–242) for
the status extension.

**Instance variable pattern** (lines 109–137 of `__init__` — add alongside existing):
```python
# Existing instance variables (pattern to copy):
self._calibration_last_changed: dict[str, str] = {}
self._calibration_last_delta: dict[str, float] = {}
self._calendar_cache: dict[str, list] = {}

# Phase 12 additions — same initialization style:
self._preheat_in_progress: dict[str, dict] = {}   # D-09
self._preheat_active: dict[str, bool] = {}         # D-10 — read by _build_status_payload
self._preheat_target: dict[str, float | None] = {} # D-10
self._preheat_suppressed: dict[str, bool] = {}     # D-10
```

**Pre-heat pass invocation** (line 202 — after `_async_calibrate`, mirroring it):
```python
# Calibration pass — D-01: runs after push pass and status fire.
await self._async_calibrate(config)
# Phase 12: pre-heat pass — runs last in evaluate cycle.
await self._async_preheat(config)
```

Note: RESEARCH Open Question 1 calls for moving `bus.async_fire()` to after the
pre-heat pass. The current call is at line 196–199. The planner should evaluate
whether to move it.

**`_async_calibrate` structure to copy** (lines 501–560 — exact template):
```python
async def _async_calibrate(self, config: dict) -> None:
    if not config.get("calibration_enabled", False):
        return
    from homeassistant.helpers import area_registry as ar  # noqa: PLC0415

    area_reg = ar.async_get(self._hass)
    rooms = self._data.rooms
    tasks = []
    for area_id, entity_ids in rooms.items():
        # ... per-room setup ...
        tasks.append(
            self._async_calibrate_room(area_id, entity_id, sensor_entity_id, config)
        )
    await asyncio.gather(*tasks)
```

`_async_preheat` uses the same structure with a guard on `preheat_enabled`:
```python
async def _async_preheat(self, config: dict) -> None:
    rooms = self._data.rooms
    tasks = [
        self._async_preheat_room(area_id, config)
        for area_id in rooms
    ]
    await asyncio.gather(*tasks)

async def _async_preheat_room(self, area_id: str, config: dict) -> None:
    room_config = config.get("rooms", {}).get(area_id, {})
    if not room_config.get("preheat_enabled", False):
        # Clear state when disabled — don't leave stale preheat_active=True
        self._preheat_active[area_id] = False
        self._preheat_suppressed[area_id] = False
        return
    # ... convergence check (D-09 step 1), discard (step 2), trigger (step 3) ...
```

**Status payload extension** (lines 890–897 of `_build_status_payload` — the
`room_entry` dict construction; extend by adding after `present_person_count`):
```python
room_entry: dict = {
    "area_id": area_id,
    "name": _area.name if _area else area_id,
    "active_period": self._last_room_periods.get(
        area_id, self._last_active_period
    ),
    "entity_ids": entity_ids,
}
# D-24: count persons assigned to this area who are currently present
room_entry["present_person_count"] = sum(...)

# Phase 12 additions — same location, same pattern:
room_entry["preheat_active"] = self._preheat_active.get(area_id, False)
room_entry["preheat_target"] = self._preheat_target.get(area_id, None)
room_entry["preheat_suppressed"] = self._preheat_suppressed.get(area_id, False)
```

**TRV `current_temperature` read pattern** (lines 927–933 of `_build_status_payload`
— reading measured temp from TRV state; same attribute key for convergence checks):
```python
trv_state = self._hass.states.get(entity_ids[0])
if trv_state is not None:
    current_temp = trv_state.attributes.get("current_temperature")
    # "current_temperature" = measured temp (sensor reading)
    # "temperature" = setpoint — DO NOT confuse (Pitfall 6 documented in module docstring)
```

**Preheat_lead_minutes rename** — three call sites currently read the old key:
- Line 414: `preheat = person_config.get("preheat_lead_minutes", 60)`
- Line 753: `preheat = person_config.get("preheat_lead_minutes", 60)`
Both must be updated to `wakeup_advance_minutes` with fallback:
```python
preheat = person_config.get(
    "wakeup_advance_minutes",
    person_config.get("preheat_lead_minutes", DEFAULT_PREHEAT_LEAD_MINUTES),
)
```

---

### `custom_components/climate_manager/storage.py` — add `wakeup_advance_minutes` migration

**Analog:** `storage.py:async_load()` migration block (lines 129–138)

**Existing migration pattern to copy** (lines 129–138):
```python
# Migration: rename person presence modes to current wire values.
for person_cfg in result.get("persons", {}).values():
    # Pre-D-21: "automatic" → "scheduled"
    if person_cfg.get("mode") == "automatic":
        person_cfg["mode"] = "scheduled"
    # D-21: "present" → "force_present", "absent" → "force_absent"
    elif person_cfg.get("mode") == "present":
        person_cfg["mode"] = "force_present"
    elif person_cfg.get("mode") == "absent":
        person_cfg["mode"] = "force_absent"
```

**Phase 12 addition** — append a second migration loop immediately after (or merge
into the same loop) running on the same `result` dict (post-merge):
```python
# D-02: rename preheat_lead_minutes → wakeup_advance_minutes.
# Must run AFTER the sparse-merge loop (on result, not stored).
for person_cfg in result.get("persons", {}).values():
    if (
        "preheat_lead_minutes" in person_cfg
        and "wakeup_advance_minutes" not in person_cfg
    ):
        person_cfg["wakeup_advance_minutes"] = person_cfg.pop(
            "preheat_lead_minutes"
        )
```

**Store instantiation pattern** (lines 77–83 — model for the second Store):
```python
class ClimateManagerStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store(
            hass,
            version=STORAGE_VERSION,
            key=STORAGE_KEY,
        )
```

The preheat Store is a raw `Store` instance (not a `ClimateManagerStore` subclass)
because it has no sparse-merge defaults:
```python
from homeassistant.helpers.storage import Store

preheat_store = Store(
    hass,
    version=1,
    key="climate_manager_preheat",
)
preheat_data: dict = await preheat_store.async_load() or {}
```

---

### `custom_components/climate_manager/const.py` — add PREHEAT_* constants

**Analog:** Existing constant block (lines 54–71)

**Existing pattern to copy** (lines 58–71):
```python
DEFAULT_GLOBAL_MODE = MODE_TIME_PROGRAM
DEFAULT_PREHEAT_LEAD_MINUTES: int = 60   # already exists (line 59)

DEFAULT_PERIOD_TEMPERATURES: dict[str, float] = {
    PERIOD_FROST_PROTECTION: 5.0,
    PERIOD_REDUCED: 18.0,
    PERIOD_NORMAL: 20.0,
    PERIOD_COMFORT: 22.0,
}
```

**Phase 12 additions** — new constants to add (same style):
```python
# Phase 12: per-room predictive pre-heat defaults (D-01, D-08)
DEFAULT_PREHEAT_MAX_LEAD_MINUTES: int = 120
PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD: int = 3   # min samples before learned lead used
PREHEAT_MAX_SAMPLES: int = 5                       # max stored samples per room
PREHEAT_CONVERGENCE_THRESHOLD: float = 0.2         # °C — D-09
```

Sparse comments for the room schema (lines 161–163 in const.py document similar
sparse keys for person config — follow same comment pattern):
```python
#   "<area_id>": {
#     ...existing keys...
#     "preheat_enabled": true,      # Phase 12 D-01: sparse — absent = not enabled
#     "preheat_max_lead_minutes": 120, # Phase 12 D-01: sparse — absent = 120
#   }
```

---

### `custom_components/climate_manager/websocket.py` — extend status handlers + migrate person key

**Analog 1:** `ws_get_status` (lines 129–242) — status builder
**Analog 2:** `ws_set_person_config` (lines 542–548) — clamping validation pattern

**Status extension in `ws_get_status`** (lines 214–228 — after `active_period` and
`present_person_count` entries, same position as in `_build_status_payload`):
```python
# Active period for this room — per-room value when available, global fallback
room_entry["active_period"] = coordinator._last_room_periods.get(
    area_id, active_period
)
# D-24: count persons assigned to this area who are currently present
room_entry["present_person_count"] = sum(...)
room_entry["has_trv"] = any(is_trv_entity(hass, eid) for eid in entity_ids)

# Phase 12 additions — same pattern, same location in room_entry building:
room_entry["preheat_active"] = coordinator._preheat_active.get(area_id, False)
room_entry["preheat_target"] = coordinator._preheat_target.get(area_id, None)
room_entry["preheat_suppressed"] = coordinator._preheat_suppressed.get(
    area_id, False
)
```

**Validation/clamping pattern** (lines 542–548 of `ws_set_person_config`):
```python
# T-11-07: clamp preheat_lead_minutes to 0-480 (drops if invalid).
if "preheat_lead_minutes" in incoming:
    val = incoming["preheat_lead_minutes"]
    if isinstance(val, int) and 0 <= val <= 480:
        pass  # valid — keep
    else:
        incoming.pop("preheat_lead_minutes")
```

Phase 12 renames the key — update this block and the docstring to use
`wakeup_advance_minutes`. Also add a clamp for room config (in `ws_set_room_config`
or in a separate room-config validation function):
```python
# Phase 12: clamp preheat_max_lead_minutes to 0-480.
if "preheat_max_lead_minutes" in incoming_config:
    val = incoming_config["preheat_max_lead_minutes"]
    if isinstance(val, int) and 0 <= val <= 480:
        pass  # valid
    else:
        incoming_config.pop("preheat_max_lead_minutes")
# preheat_enabled: ensure bool
if "preheat_enabled" in incoming_config:
    if not isinstance(incoming_config["preheat_enabled"], bool):
        incoming_config["preheat_enabled"] = bool(incoming_config["preheat_enabled"])
```

The `set_room_config` handler (lines 394–448) passes `incoming_config` through
`update()` without a key allowlist — confirmed at line 432. The clamp must be
added before the `update()` call.

---

### `custom_components/climate_manager/__init__.py` — add preheat_store to ClimateManagerData

**Analog:** `ClimateManagerData` dataclass (lines 64–96) + `async_setup_entry`
wiring (lines 127–155)

**Dataclass extension pattern** (lines 83–95 — add `field(default=None)` fields):
```python
@dataclass
class ClimateManagerData:
    store: ClimateManagerStore
    runtime_config: dict
    rooms: dict[str, list[str]]
    persons: list[str]
    room_auto_sensors: dict[str, dict[str, str]]
    # Phase 2 additions — use field(default=None) to avoid mutable default error:
    coordinator: "ClimateManagerCoordinator | None" = field(default=None)
    cancel_scheduler: "Callable[[], None] | None" = field(default=None)
    cancel_registry_listeners: "list[Callable[[], None]]" = field(
        default_factory=list
    )

    # Phase 12 additions — same pattern:
    preheat_store: "Store | None" = field(default=None)
    preheat_samples: "dict" = field(default_factory=dict)
```

**`async_setup_entry` wiring pattern** (lines 127–143 — after store load):
```python
store = ClimateManagerStore(hass)
runtime_config = await store.async_load()
rooms = await discover_rooms(hass)
# ...
entry.runtime_data = ClimateManagerData(
    store=store,
    runtime_config=runtime_config,
    rooms=rooms,
    persons=persons,
    room_auto_sensors=room_auto_sensors,
)

# Phase 12: construct and load preheat store
preheat_store = Store(hass, version=1, key="climate_manager_preheat")
preheat_samples = await preheat_store.async_load() or {}
entry.runtime_data.preheat_store = preheat_store
entry.runtime_data.preheat_samples = preheat_samples
```

The `Store` import is already present in `homeassistant.helpers.storage` (used
by `ClimateManagerStore`).

---

### `frontend/src/types.ts` — extend RoomConfig, RoomStatus, PersonConfig

**Analog:** Existing `RoomConfig` (lines 54–66), `RoomStatus` (lines 117–127),
`PersonConfig` (lines 68–81)

**RoomConfig extension pattern** (lines 54–66):
```typescript
/** Per-room configuration stored in ClimateConfig.rooms. */
export interface RoomConfig {
  room_mode?: "global" | "frost_protection" | "custom";
  time_program?: DailyProgram | null;
  zone_id?: string;
  // Phase 12 additions — sparse (absent = not enabled):
  preheat_enabled?: boolean;
  preheat_max_lead_minutes?: number;
}
```

**RoomStatus extension pattern** (lines 117–127):
```typescript
/** Per-room live status entry inside StatusPayload.rooms_status. */
export interface RoomStatus {
  area_id: string;
  name: string;
  entity_ids?: string[];
  temperature?: number | null;
  humidity?: number | null;
  active_period?: string | null;
  present_person_count: number;
  has_trv?: boolean;
  // Phase 12 additions (D-10):
  preheat_active?: boolean;
  preheat_target?: number | null;
  preheat_suppressed?: boolean;
}
```

**PersonConfig rename** (line 80 — rename the field, keep the comment):
```typescript
export interface PersonConfig {
  // ...
  // Phase 12: renamed from preheat_lead_minutes (D-02)
  wakeup_advance_minutes?: number;
  // preheat_lead_minutes is deprecated — use wakeup_advance_minutes
}
```

---

### `frontend/src/components/room-card.ts` — add pre-heat config block + status line

**Analog 1:** `_onZoneChange` (lines 421–433) — auto-save on change pattern
**Analog 2:** `_renderRoomModeDescription` (lines 625–635) — `schedule-hint` status line
**Analog 3:** `_renderTrvSection` (referenced at line 798) and zone picker (lines
741–764) — section-label + control block layout

**Auto-save on change pattern** (lines 421–433 — exact template to copy):
```typescript
private async _onZoneChange(e: Event) {
  const newZoneId = (e.target as HTMLSelectElement).value;
  const patch: Partial<RoomConfig> = newZoneId
    ? { zone_id: newZoneId }
    : { zone_id: null as unknown as string | undefined };
  try {
    await this.ws.setRoomConfig(this.roomId, patch);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

Pre-heat handlers follow the same shape:
```typescript
private async _onPreheatToggle(e: Event) {
  const enabled = (e.target as HTMLInputElement).checked;
  try {
    await this.ws.setRoomConfig(this.roomId, { preheat_enabled: enabled });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}

private async _onPreheatMaxLeadChange(e: Event) {
  const val = parseInt((e.target as HTMLInputElement).value, 10);
  if (isNaN(val) || val < 0 || val > 480) return;
  try {
    await this.ws.setRoomConfig(this.roomId, {
      preheat_max_lead_minutes: val,
    });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

**Status line pattern** (lines 625–635 — `schedule-hint` paragraph):
```typescript
private _renderRoomModeDescription(resolvedMode: string) {
  let text: string;
  if (resolvedMode === "frost_protection") {
    text = "Heating is disabled. Room kept at frost protection temperature.";
  } else if (resolvedMode === "custom") {
    text = "Room uses its own custom schedule. Zone Off mode still applies.";
  } else {
    text = "This room follows the zone's heating schedule.";
  }
  return html`<p class="schedule-hint">${text}</p>`;
}
```

Pre-heat status line uses the same `schedule-hint` CSS class:
```typescript
// Active pre-heat: "Pre-heating (→ XX.X°C)"
${preheatActive && preheatTarget != null
  ? html`<p class="schedule-hint">
      Pre-heating (→ ${preheatTarget.toFixed(1)}°C)
    </p>`
  : ""}
// Suppressed warning (only when enabled + suppressed):
${enabled && preheatSuppressed
  ? html`<p class="schedule-hint">
      Pre-heat disabled — presence cannot be scheduled
    </p>`
  : ""}
```

**Native HTML input pattern** (project memory: ha-textfield and ha-select broken
in HA 2026.x — use native elements; same as zone picker uses `<select>`):
```typescript
// Toggle:
<input
  type="checkbox"
  .checked=${enabled}
  @change=${this._onPreheatToggle}
/>
// Number input:
<input
  type="number"
  .value=${String(this.config?.preheat_max_lead_minutes ?? 120)}
  min="0" max="480" step="5"
  @change=${this._onPreheatMaxLeadChange}
  style="width:70px"
/>
```

**Section placement** — pre-heat block renders below the TRV list (line 798:
`${this._renderTrvSection()}`). Add immediately after:
```typescript
${this._renderTrvSection()}
${this._renderPreheatSection()}
```

---

### `tests/test_preheat.py` (NEW)

**Analog:** `tests/test_calendar.py` — same fixture-first structure, same
`hass_ws_client` pattern for WS tests, same person/room config dict shapes.

**Fixture pattern** (test_calendar.py lines 90–115 — person config dict):
```python
PERSON_CFG_SCHEDULED = {
    "mode": "scheduled",
    "room_ids": ["living_room"],
    "schedule_type": "single",
    "schedule": {
        "mon": [
            {"start": "00:00", "state": "absent"},
            {"start": "07:00", "state": "present"},
            {"start": "22:00", "state": "absent"},
        ],
        # ... other days ...
    },
    "preheat_lead_minutes": 60,   # rename to wakeup_advance_minutes after D-02
}
```

**WS test pattern** (test_calendar.py lines 739–755):
```python
async def test_ws_persists_preheat_lead_minutes(hass, hass_ws_client):
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({
        "type": "climate_manager/set_person_config",
        "person_id": "person.test",
        "config": {"preheat_lead_minutes": 90},
    })
    msg = await client.receive_json()
    assert msg["success"] is True
```

Phase 12 unit tests for `next_occupied_at()` are pure Python (no hass fixture):
```python
from custom_components.climate_manager.schedule import next_occupied_at
import datetime

def test_next_occupied_even_odd():
    now = datetime.datetime(2026, 6, 2, 10, 0, tzinfo=datetime.timezone.utc)
    person_cfg = {
        "mode": "scheduled",
        "schedule_type": "even_odd",
        "schedule_even": {...},
        "schedule_odd": {...},
    }
    result = next_occupied_at(person_cfg, now)
    assert result is None or isinstance(result, datetime.datetime)
```

---

## Shared Patterns

### asyncio.gather over rooms (all coordinator passes)

**Source:** `coordinator.py:_async_calibrate()` lines 516–560
**Apply to:** `_async_preheat()` — exact same structure
```python
tasks = []
for area_id, entity_ids in rooms.items():
    tasks.append(self._async_per_room_method(area_id, config))
await asyncio.gather(*tasks)
```

### Sparse config read with absent-equals-default

**Source:** All existing config reads in coordinator.py, e.g. line 511:
`config.get("calibration_enabled", False)`
**Apply to:** All pre-heat config reads:
```python
room_config.get("preheat_enabled", False)
room_config.get("preheat_max_lead_minutes", DEFAULT_PREHEAT_MAX_LEAD_MINUTES)
```

### Auto-save with toast feedback (frontend)

**Source:** `room-card.ts:_onZoneChange` lines 421–433
**Apply to:** `_onPreheatToggle`, `_onPreheatMaxLeadChange` handlers
Pattern: `try { await ws.setRoomConfig(...); await panel.reloadConfig(); panel.showToast("Saved", false); } catch { panel.showToast("Save failed...", true); }`

### Dual status payload update (both builders)

**Source:** `coordinator.py:_build_status_payload()` lines 873–957 AND
`websocket.py:ws_get_status` lines 129–242
**Apply to:** Every new room_entry field — must appear in BOTH builders.
Anchor: search for `present_person_count` in both files to find the insertion point.

### `field(default=None)` for optional dataclass fields

**Source:** `__init__.py:ClimateManagerData` lines 90–95
**Apply to:** `preheat_store` and `preheat_samples` on `ClimateManagerData`
```python
preheat_store: "Store | None" = field(default=None)
preheat_samples: "dict" = field(default_factory=dict)
```

### Native HTML form controls

**Source:** Project memory (ha-textfield broken in HA 2026.x); zone picker uses
`<select class="mode-select">` natively
**Apply to:** All pre-heat UI controls — `<input type="checkbox">` and
`<input type="number">` — never `<ha-textfield>` or `<ha-select>`

---

## No Analog Found

No files in this phase lack an analog. All patterns have exact matches in the
existing codebase.

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `frontend/src/`,
`tests/`
**Files scanned:** coordinator.py, schedule.py, storage.py, const.py,
websocket.py, __init__.py, frontend/src/types.ts,
frontend/src/components/room-card.ts, frontend/src/ws-client.ts,
tests/test_calendar.py
**Pattern extraction date:** 2026-06-02
