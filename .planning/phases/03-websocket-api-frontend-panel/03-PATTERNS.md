# Phase 3: WebSocket API & Frontend Panel - Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 11 (3 new, 8 modified)
**Analogs found:** 9 / 11 (2 files have no codebase analog — new tech for this project)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `custom_components/climate_manager/const.py` | config | transform | `custom_components/climate_manager/const.py` (self) | self-refactor |
| `custom_components/climate_manager/schedule.py` | service | transform | `custom_components/climate_manager/schedule.py` (self) | self-refactor |
| `custom_components/climate_manager/coordinator.py` | service | event-driven | `custom_components/climate_manager/coordinator.py` (self) | self-refactor |
| `custom_components/climate_manager/websocket.py` | controller | request-response | `.venv/…/homeassistant/components/weather/websocket_api.py` | role-match |
| `custom_components/climate_manager/__init__.py` | config | request-response | `custom_components/climate_manager/__init__.py` (self) | self-extend |
| `custom_components/climate_manager/www/panel.js` | — | — | none | no analog (build artifact) |
| `frontend/src/main.ts` | component | request-response | `.venv/…/assist_satellite/websocket_api.py` (pattern only) | no frontend analog |
| `frontend/src/components/time-bar.ts` | component | event-driven | none | no analog |
| `tests/test_schedule.py` | test | transform | `tests/test_schedule.py` (self) | self-refactor |
| `tests/test_coordinator.py` | test | event-driven | `tests/test_coordinator.py` (self) | self-refactor |
| `tests/test_websocket.py` | test | request-response | `tests/test_coordinator.py` | role-match |

---

## Pattern Assignments

### `custom_components/climate_manager/const.py` (config, transform) — Wave 1 refactor

**Analog:** self (`custom_components/climate_manager/const.py`)

**Current pattern to replace** (lines 104–116):
```python
DEFAULT_CONFIG: dict = {
    "version": STORAGE_VERSION,
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": {
        PERIOD_FROST_PROTECTION: 7.0,
        PERIOD_REDUCED: 18.0,
        PERIOD_NORMAL: 20.0,
        PERIOD_COMFORT: 22.0,
    },
    "global_time_program": {"weekday_groups": []},
    "rooms": {},
    "persons": {},
}
```

**Target pattern** (replace `"weekday_groups": []` with per-day structure throughout):
```python
import copy

_DAYS_ORDERED = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_EMPTY_DAILY_PROGRAM: dict = {day: [] for day in _DAYS_ORDERED}

STORAGE_VERSION = 2  # bump for schema migration (no stored users yet)

DEFAULT_CONFIG: dict = {
    "version": STORAGE_VERSION,
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": {
        PERIOD_FROST_PROTECTION: 7.0,
        PERIOD_REDUCED: 18.0,
        PERIOD_NORMAL: 20.0,
        PERIOD_COMFORT: 22.0,
    },
    "global_time_program": copy.deepcopy(_EMPTY_DAILY_PROGRAM),
    "rooms": {},    # room entry: {"time_program": copy.deepcopy(_EMPTY_DAILY_PROGRAM)}
    "persons": {},  # person entry: {"mode": ..., "room_ids": [], "schedule": copy.deepcopy(_EMPTY_DAILY_PROGRAM)}
}
```

**Module-level docstring comment to update** (lines 57–78): remove all `weekday_groups` references from the sub-schema documentation block; replace with per-day format docs matching the new schema.

---

### `custom_components/climate_manager/schedule.py` (service, transform) — Wave 1 refactor

**Analog:** self (`custom_components/climate_manager/schedule.py`)

**Existing import pattern** (lines 27–35) — unchanged, keep as-is:
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

**Existing reverse-lookup pattern to add** after `DAY_TO_WEEKDAY` (line 42–49):
```python
# Reverse mapping for per-day schema: weekday() int → day name string
WEEKDAY_TO_DAY: dict[int, str] = {v: k for k, v in DAY_TO_WEEKDAY.items()}
```

**`evaluate_schedule` signature change** (lines 75–112): parameter `weekday_groups: list[dict]` → `daily_program: dict[str, list]`. Core lookup changes from a linear group scan to a direct dict access:
```python
def evaluate_schedule(
    daily_program: dict[str, list],
    now: datetime.datetime,
) -> str:
    day_name = WEEKDAY_TO_DAY[now.weekday()]  # e.g. "mon"
    periods = daily_program.get(day_name, [])
    # ... sort + walk periods identically to current logic ...
    # Return active mode or PERIOD_FROST_PROTECTION if no period started yet
```

**`resolve_presence` change** (lines 115–159): `schedule.get("weekday_groups", [])` → `schedule` is now the per-day dict directly. Day access:
```python
schedule = person_config.get("schedule", {})
day_name = WEEKDAY_TO_DAY[now.weekday()]
periods = schedule.get(day_name, [])
if not periods:
    return False  # PERSON-05: no periods today → absent
# ... walk periods as before ...
```

**`compute_occupied_temp` change** (lines 162–238): same signature change, `weekday_groups: list[dict]` → `daily_program: dict[str, list]`. Finding today's periods becomes:
```python
day_name = WEEKDAY_TO_DAY[now.weekday()]
today_periods = sorted(daily_program.get(day_name, []), key=lambda p: p["start"])
```
(Remove the entire `for group in weekday_groups: if today in days: today_periods = ...` loop.)

**`validate_7day_coverage` replacement** (lines 241–273): old signature `validate_7day_coverage(weekday_groups: list[dict])` → new signature `validate_daily_program(daily_program: dict[str, list])`:
```python
def validate_daily_program(daily_program: dict[str, list]) -> tuple[bool, str]:
    """Validate that all 7 day keys are present in the per-day dict."""
    missing = ALL_DAYS - set(daily_program.keys())
    extra = set(daily_program.keys()) - ALL_DAYS
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"Missing days: {sorted(missing)}")
        if extra:
            parts.append(f"Unknown days: {sorted(extra)}")
        return False, "; ".join(parts)
    return True, ""
```

---

### `custom_components/climate_manager/coordinator.py` (service, event-driven) — Wave 1 refactor + Wave 2 addition

**Analog:** self (`custom_components/climate_manager/coordinator.py`)

**Import addition** for bus event firing (add to existing imports, lines 44–51):
```python
from .const import (
    DOMAIN,           # add this
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
)
```

**Per-day access pattern** — replace all three `weekday_groups` access paths:

Current pattern (line 137, 184, 195–196, 228–232):
```python
global_weekday_groups = config["global_time_program"]["weekday_groups"]
# ...
room_weekday_groups = (
    room_configs.get(area_id, {})
    .get("time_program", {})
    .get("weekday_groups")
)
weekday_groups = room_weekday_groups if room_weekday_groups else global_weekday_groups
period_mode = evaluate_schedule(weekday_groups, now)
```

New per-day pattern (replace in `_evaluate_time_program` and `_evaluate_time_program_presences`):
```python
global_daily_program: dict = config["global_time_program"]  # IS the per-day dict now
# ...
room_daily_program = (
    room_configs.get(area_id, {})
    .get("time_program")
)
daily_program = room_daily_program if room_daily_program else global_daily_program
period_mode = evaluate_schedule(daily_program, now)
```

**Status push addition** — add at the end of `async_evaluate` (after all TRV pushes, line ~300):
```python
# Wave 2: push status to all subscribed panel instances
self._hass.bus.async_fire(
    f"{DOMAIN}_status_update",
    self._build_status_payload(),
)

def _build_status_payload(self) -> dict:
    """Build the status dict pushed to subscribed panel connections."""
    return {
        "global_mode": self._data.runtime_config["global_mode"],
        "active_period": getattr(self, "_last_active_period", None),
        "present_persons": getattr(self, "_last_present_persons", []),
    }
```

---

### `custom_components/climate_manager/websocket.py` (controller, request-response) — NEW Wave 2

**Analog:** `.venv/lib/python3.12/site-packages/homeassistant/components/weather/websocket_api.py`

**Imports pattern** (weather analog lines 1–14, adapted):
```python
"""Climate Manager WebSocket command handlers."""

from __future__ import annotations

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

from . import ClimateManagerConfigEntry
from .const import (
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
    PERIOD_REDUCED,
    PERIOD_NORMAL,
    PERIOD_COMFORT,
)
from .schedule import validate_daily_program

VALID_MODES = [MODE_OFF, MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES]
```

**Registration function pattern** (weather analog lines 24–28, assist_satellite lines 29–34):
```python
def async_register_commands(
    hass: HomeAssistant, entry: ClimateManagerConfigEntry
) -> None:
    """Register all Climate Manager WebSocket commands."""
    websocket_api.async_register_command(hass, _make_ws_get_status(entry))
    websocket_api.async_register_command(hass, _make_ws_get_config(entry))
    websocket_api.async_register_command(hass, _make_ws_set_global_mode(entry))
    websocket_api.async_register_command(hass, _make_ws_set_period_temperatures(entry))
    websocket_api.async_register_command(hass, _make_ws_set_time_program(entry))
    websocket_api.async_register_command(hass, _make_ws_set_room_config(entry))
    websocket_api.async_register_command(hass, _make_ws_set_person_config(entry))
    websocket_api.async_register_command(hass, _make_ws_subscribe_status(entry))
```

**Request-response command factory pattern** (weather analog lines 46–43 adapted; RESEARCH.md Pattern 1):
```python
def _make_ws_get_config(entry: ClimateManagerConfigEntry):
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/get_config",
    })
    @websocket_api.async_response
    async def ws_get_config(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        connection.send_result(msg["id"], entry.runtime_data.runtime_config)
    return ws_get_config
```

**Write command pattern** — mutate + save + evaluate (RESEARCH.md Pattern 1):
```python
def _make_ws_set_global_mode(entry: ClimateManagerConfigEntry):
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/set_global_mode",
        vol.Required("mode"): vol.In(VALID_MODES),
    })
    @websocket_api.async_response
    async def ws_set_global_mode(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        entry.runtime_data.runtime_config["global_mode"] = msg["mode"]
        await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
        await entry.runtime_data.coordinator.async_evaluate()
        connection.send_result(msg["id"], {"success": True})
    return ws_set_global_mode
```

**Subscription command pattern** (weather analog lines 80–99; RESEARCH.md Pattern 2):
```python
def _make_ws_subscribe_status(entry: ClimateManagerConfigEntry):
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/subscribe_status",
    })
    @callback
    def ws_subscribe_status(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict,
    ) -> None:
        msg_id = msg["id"]

        @callback
        def _forward_status(event) -> None:
            connection.send_message(
                websocket_api.event_message(msg_id, event.data)
            )

        # HA auto-calls unsub on connection close (RESEARCH.md A3, verified)
        connection.subscriptions[msg_id] = hass.bus.async_listen(
            f"{DOMAIN}_status_update", _forward_status
        )
        connection.send_message(websocket_api.result_message(msg_id))
    return ws_subscribe_status
```

**Error response pattern** (assist_satellite analog lines 53–56):
```python
connection.send_error(
    msg["id"],
    websocket_api.ERR_NOT_FOUND,
    "Human-readable error description",
)
return
```

---

### `custom_components/climate_manager/__init__.py` (config, request-response) — Wave 2 extension

**Analog:** self (`custom_components/climate_manager/__init__.py`)

**New imports to add** (after existing imports, lines 21–31):
```python
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components import panel_custom

from . import websocket as cm_ws  # new module

PANEL_URL = "/climate_manager_panel"
PANEL_COMPONENT_NAME = "climate-manager-panel"  # must match customElements.define() in panel.js
```

**Addition to `async_setup_entry`** — append after the scheduler registration (after line 114):
```python
# Wave 2: register WebSocket commands (auto-unregister on entry unload)
cm_ws.async_register_commands(hass, entry)

# Wave 3: serve www/ directory and register sidebar panel
www_path = Path(__file__).parent / "www"
await hass.http.async_register_static_paths([
    StaticPathConfig(PANEL_URL, str(www_path), cache_headers=False)
])
await panel_custom.async_register_panel(
    hass,
    frontend_url_path=DOMAIN,
    webcomponent_name=PANEL_COMPONENT_NAME,
    sidebar_title="Climate Manager",
    sidebar_icon="mdi:thermometer",
    module_url=f"{PANEL_URL}/panel.js",
    embed_iframe=False,
    require_admin=False,
)
```

**`async_unload_entry` unchanged** — WebSocket commands auto-unregister with the config entry; no explicit cleanup needed (RESEARCH.md Pattern 3).

---

### `frontend/src/main.ts` (component, request-response) — NEW Wave 3

**Analog:** RESEARCH.md Pattern 5 (no codebase analog — first frontend file in project)

**File structure and Lit component skeleton** (RESEARCH.md Pattern 5):
```typescript
import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

// HA passes hass, narrow, panel to any registered custom panel element
class ClimateManagerPanel extends LitElement {
  @property({ attribute: false }) hass!: any;  // HomeAssistant from home-assistant-js-websocket
  @property({ type: Boolean }) narrow = false;
  @property({ attribute: false }) panel: unknown = null;

  @state() private _config: Record<string, unknown> | null = null;
  @state() private _status: Record<string, unknown> | null = null;
  @state() private _activeTab = "global";
  @state() private _unsubStatus: Promise<() => void> | null = null;

  connectedCallback() {
    super.connectedCallback();
    this._loadConfig();
    this._subscribeStatus();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._unsubStatus?.then((unsub) => unsub());
  }

  private async _loadConfig() {
    this._config = await this.hass.connection.sendMessagePromise({
      type: "climate_manager/get_config",
    });
  }

  private _subscribeStatus() {
    this._unsubStatus = this.hass.connection.subscribeMessage(
      (msg: unknown) => { this._status = msg as Record<string, unknown>; },
      { type: "climate_manager/subscribe_status" }
    );
  }
}

customElements.define("climate-manager-panel", ClimateManagerPanel);
```

**Auto-save helper pattern** (used for every field-change handler):
```typescript
private async _save(type: string, payload: Record<string, unknown>) {
  try {
    await this.hass.connection.sendMessagePromise({ type, ...payload });
    this._showToast("Saved", false);
  } catch {
    this._showToast("Save failed — retrying...", true);
  }
}
```

**Vite config** (`frontend/vite.config.ts`, RESEARCH.md Pattern 6):
```typescript
import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, "src/main.ts"),
      name: "ClimateManagerPanel",
      fileName: "panel",
      formats: ["es"],
    },
    outDir: "../custom_components/climate_manager/www",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,   // single file — no chunks (Pitfall 8)
        entryFileNames: "panel.js",
      },
    },
    cssCodeSplit: false,
  },
});
```

---

### `frontend/src/components/time-bar.ts` (component, event-driven) — NEW Wave 3

**Analog:** none in codebase. Pattern from RESEARCH.md Time Bar Component Design.

**Lit component interface**:
```typescript
import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

// mode "schedule": 4-color period bar; mode "presence": 2-color presence bar
class ClimateManagerTimeBar extends LitElement {
  @property({ type: Array }) days: Array<Array<{start: string; mode: string}>> = [];
  @property({ type: String }) mode: "schedule" | "presence" = "schedule";
  // Fired when a day's periods array changes (parent handles WS save)
  // CustomEvent: detail = { dayIndex: number, periods: Array<Period> }
}

customElements.define("climate-manager-time-bar", ClimateManagerTimeBar);
```

**15-min snap pattern**:
```typescript
private _snapToMinutes(rawMinutes: number): number {
  return Math.round(rawMinutes / 15) * 15;
}

private _pixelToMinutes(x: number, barWidth: number): number {
  return (x / barWidth) * 1440;
}
```

**Pointer drag pattern** (save fires on `pointerup`, not during drag):
```typescript
private _onPointerDown(e: PointerEvent, dayIndex: number, segIndex: number) {
  (e.target as HTMLElement).setPointerCapture(e.pointerId);
  this._dragging = { dayIndex, segIndex, startX: e.clientX };
}

private _onPointerMove(e: PointerEvent) {
  if (!this._dragging) return;
  // Update tooltip display only — do not fire save
  this._dragTooltipTime = this._snapToMinutes(/* ... */);
}

private _onPointerUp(e: PointerEvent) {
  if (!this._dragging) return;
  const newMinutes = this._snapToMinutes(/* ... */);
  const updatedPeriods = this._applyBoundaryChange(this._dragging, newMinutes);
  this.dispatchEvent(new CustomEvent("periods-changed", {
    detail: { dayIndex: this._dragging.dayIndex, periods: updatedPeriods },
    bubbles: true, composed: true,
  }));
  this._dragging = null;
}
```

---

### `tests/test_schedule.py` (test, transform) — Wave 1 refactor

**Analog:** self (`tests/test_schedule.py`)

**Module constant pattern to replace** (lines 39–90) — convert fixtures from `weekday_groups` list-of-dicts to per-day dict format:
```python
# Replace WEEKDAY_PROGRAM list-of-groups with per-day dict
WEEKDAY_PROGRAM: dict = {
    "mon": [{"start": "07:00", "mode": "normal"}, {"start": "22:00", "mode": "reduced"}],
    "tue": [{"start": "07:00", "mode": "normal"}, {"start": "22:00", "mode": "reduced"}],
    "wed": [{"start": "07:00", "mode": "normal"}, {"start": "22:00", "mode": "reduced"}],
    "thu": [{"start": "07:00", "mode": "normal"}, {"start": "22:00", "mode": "reduced"}],
    "fri": [{"start": "07:00", "mode": "normal"}, {"start": "22:00", "mode": "reduced"}],
    "sat": [{"start": "08:00", "mode": "comfort"}, {"start": "23:00", "mode": "reduced"}],
    "sun": [{"start": "08:00", "mode": "comfort"}, {"start": "23:00", "mode": "reduced"}],
}

# Replace PERSON_SCHEDULE weekday_groups with per-day dict
PERSON_SCHEDULE: dict = {
    "mon": [{"start": "00:00", "state": "absent"}, {"start": "08:00", "state": "present"}, {"start": "22:00", "state": "absent"}],
    "tue": [...],  # same as mon
    # ...
    "sat": [{"start": "00:00", "state": "absent"}],
    "sun": [{"start": "00:00", "state": "absent"}],
}
```

**Test call-site changes** (all `evaluate_schedule(WEEKDAY_PROGRAM, now)` calls remain identical in call signature). Only the fixture shape changes.

**`validate_7day_coverage` → `validate_daily_program`**: update all 6 `validate_7day_coverage(...)` call sites and import name. The new function accepts a `dict` instead of a `list` — fixture args simplify to passing the per-day dict directly.

**Test body pattern preserved** (keep all assertion logic, datetime construction, docstrings unchanged):
```python
def test_evaluate_schedule_returns_normal_at_0830_monday():
    now = datetime.datetime(2026, 1, 5, 8, 30, tzinfo=datetime.timezone.utc)
    assert now.weekday() == 0
    result = evaluate_schedule(WEEKDAY_PROGRAM, now)  # same call, new fixture shape
    assert result == PERIOD_NORMAL
```

---

### `tests/test_coordinator.py` (test, event-driven) — Wave 1 refactor

**Analog:** self (`tests/test_coordinator.py`)

**`_make_runtime_config` helper change** (lines 60–76) — remove `weekday_groups` parameter, replace with `daily_program`:
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

**Module-level program fixtures** (lines 37–57) — convert to per-day dict:
```python
ALL_DAYS_NORMAL_PROGRAM: dict = {
    day: [{"start": "00:00", "mode": PERIOD_NORMAL}]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}

TYPICAL_WEEKDAY_PROGRAM: dict = {
    day: [
        {"start": "00:00", "mode": PERIOD_REDUCED},
        {"start": "07:00", "mode": PERIOD_NORMAL},
        {"start": "22:00", "mode": PERIOD_REDUCED},
    ]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}
```

**Persons config fixture change** (line 286–297) — replace `schedule: {"weekday_groups": []}` with `schedule: {}`:
```python
persons_config = {
    "person.alice": {
        "mode": "present",
        "room_ids": ["lounge"],
        "schedule": {},  # per-day: empty dict = no schedule
    },
    "person.bob": {
        "mode": "absent",
        "room_ids": ["lounge"],
        "schedule": {},
    },
}
```

**All test assertions and async patterns preserved unchanged.**

---

### `tests/test_websocket.py` (test, request-response) — NEW Wave 2

**Analog:** `tests/test_coordinator.py` (closest existing test — same setup scaffold)

**Setup scaffold pattern** (from `test_coordinator.py` lines 84–127):
```python
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.climate_manager.const import DOMAIN, MODE_OFF, MODE_TIME_PROGRAM

async def test_ws_set_global_mode_persists_and_evaluates(hass):
    """WS set_global_mode mutates runtime_config, saves, and triggers evaluate."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass.test_websocket_client()
    await client.send_json({"id": 1, "type": "climate_manager/set_global_mode", "mode": MODE_OFF})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert entry.runtime_data.runtime_config["global_mode"] == MODE_OFF
```

**WebSocket client fixture pattern** — use `hass.test_websocket_client()` (provided by `pytest-homeassistant-custom-component`):
```python
async def test_ws_get_config_returns_runtime_config(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass.test_websocket_client()
    await client.send_json({"id": 1, "type": "climate_manager/get_config"})
    msg = await client.receive_json()

    assert msg["success"] is True
    assert "global_mode" in msg["result"]
```

**autouse conftest fixture** (from `tests/conftest.py` lines 8–14) — already in place, inherited automatically by new test file:
```python
# conftest.py auto_enable_custom_integrations fixture applies to all test files
# No additional fixture setup needed in test_websocket.py
```

---

## Shared Patterns

### Runtime data access (all WS handlers)
**Source:** `custom_components/climate_manager/__init__.py` lines 38–68
**Apply to:** `websocket.py` — all command handlers
```python
# Access via closure — entry passed at registration time (RESEARCH.md anti-pattern 3)
# Never use hass.data[DOMAIN]
entry.runtime_data.store          # ClimateManagerStore
entry.runtime_data.runtime_config # merged config dict (shared reference)
entry.runtime_data.coordinator    # ClimateManagerCoordinator
entry.runtime_data.rooms          # {area_id: [entity_id, ...]}
entry.runtime_data.persons        # [person entity_ids]
```

### Sparse-safe mutation pattern (all write WS handlers)
**Source:** `custom_components/climate_manager/storage.py` lines 63–68 + RESEARCH.md Pitfall 5
**Apply to:** all `ws_set_*` handlers in `websocket.py`
```python
# CORRECT: mutate the sub-key in-place, then save
entry.runtime_data.runtime_config["global_mode"] = msg["mode"]
await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
# Never do: await store.async_save(copy.deepcopy(DEFAULT_CONFIG | runtime_config))
# The store writes exactly what it receives — no de-defaulting step exists
```

### Write-then-evaluate pattern
**Source:** `custom_components/climate_manager/coordinator.py` line 83 (signature) + RESEARCH.md Pitfall 4
**Apply to:** all `ws_set_*` handlers in `websocket.py`
```python
await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
await entry.runtime_data.coordinator.async_evaluate()  # immediate TRV push — do not omit
connection.send_result(msg["id"], {"success": True})
```

### Schedule evaluation call pattern (coordinator after schema refactor)
**Source:** `custom_components/climate_manager/coordinator.py` lines 148–149 (current — will change)
**Apply to:** `coordinator.py` Wave 1 refactor (both `_evaluate_time_program` and `_evaluate_time_program_presences`)
```python
# Post-refactor: daily_program IS the per-day dict — pass directly
period_mode = evaluate_schedule(daily_program, now)
# No more .get("weekday_groups") unwrap needed
```

### Test entry setup scaffold
**Source:** `tests/test_coordinator.py` lines 85–120
**Apply to:** `tests/test_websocket.py` — every test function
```python
entry = MockConfigEntry(domain=DOMAIN, data={})
entry.add_to_hass(hass)
await hass.config_entries.async_setup(entry.entry_id)
await hass.async_block_till_done()
# Then override runtime_data fields as needed before calling the function under test
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `custom_components/climate_manager/www/panel.js` | build artifact | — | Generated by Vite; not hand-written; no JS/TS files exist in the project yet |
| `frontend/src/components/time-bar.ts` | component | event-driven | No frontend components exist yet; no drag-interaction pattern in codebase; use RESEARCH.md Time Bar Component Design section |

For these files, the planner must rely exclusively on RESEARCH.md Patterns 5 and 6 and the Time Bar Component Design section.

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `tests/`, `.venv/lib/python3.12/site-packages/homeassistant/components/`
**Files scanned:** 16 source files + 2 HA venv WS API examples
**Pattern extraction date:** 2026-05-17
