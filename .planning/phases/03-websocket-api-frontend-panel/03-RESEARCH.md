# Phase 3: WebSocket API & Frontend Panel - Research

**Researched:** 2026-05-17
**Domain:** HA WebSocket API (Python), Lit 3 + TypeScript + Vite (Frontend Panel), panel_custom registration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Per-day time program schema — `{"mon": [...], "tue": [...], "wed": [...], "thu": [...], "fri": [...], "sat": [...], "sun": [...]}` — replaces Phase 2 `weekday_groups`. Each day holds an independent list of periods `[{"start": "HH:MM", "mode": "<period_mode>"}, ...]`. Global time program, per-room overrides, and person presence schedules all use this format.
- **D-02:** Visual 24h bar editor — all 7 days stacked vertically, one bar per row, full week visible at once.
- **D-03:** Period colors: Frost protection = `#1565C0`, Reduced = `#64B5F6`, Normal = `#F57C00`, Comfort = `#D32F2F`. Presence: Present = `#388E3C`, Absent = `#9E9E9E`.
- **D-04:** Click on bar → splits at nearest 15 min → mode popup.
- **D-05:** Click existing block → popup with Change mode / Delete. Delete merges into left neighbor.
- **D-06:** Drag border → tooltip shows HH:MM; save fires on mouse-up.
- **D-07:** Copy/Paste per day row; panel-local clipboard state.
- **D-08:** Auto-save on every field change (no explicit Save button).
- **D-09:** Time program bar saves on interaction end (mouse-up, popup close, paste).
- **D-10:** Toast/snackbar: "Saved" (3s) on success, "Save failed — retrying..." (persistent) on error.
- **D-11:** No "Applied" confirmation after coordinator push.
- **D-12:** Three top-level tabs: Global Settings / Rooms / Persons.
- **D-13:** Global Settings tab — three cards in order: Current Status (mode, active period, present persons) + Temperatures (Frost protection, Reduced, Normal, Comfort temperature inputs) + Configuration (global mode selector + global time program). [Updated 2026-05-21 per discuss-phase]
- **D-14:** Rooms tab: expandable cards; custom-program rooms listed first and expanded.
- **D-15:** Persons tab: expandable cards; non-default persons listed first and expanded.
- **D-16:** Rooms have optional `temperature_sensor` and `humidity_sensor` entity ID fields.
- **D-17:** Live room status: temp from sensor or TRV current_temperature, humidity from sensor, active period name.
- **D-18:** Present persons shown only on Global Settings tab.

### Pre-condition (locked, must be Wave 1)
Phase 2 backend uses `weekday_groups`. Phase 3 requires per-day schema. A gap-closure plan MUST refactor `schedule.py`, `const.py`, `DEFAULT_CONFIG`, and all tests BEFORE any Phase 3 panel or WS API work.

### Claude's Discretion

- WebSocket command granularity: minimal command set supporting auto-save.
- Frontend build integration: how Vite output is placed in `www/` and how `make deploy` is extended.
- Whether Lit is bundled into `panel.js` or relies on HA's Lit instance (bundling is safer, per CLAUDE.md default).

### Deferred Ideas (OUT OF SCOPE)

- TRV availability indicator (reachable/unreachable dot per TRV entity)
- Entity picker for sensor fields (searchable dropdown)
- "Applied" confirmation after coordinator push
- Auto-detect humidity sensors by area

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | Integration provides a full Lovelace dashboard panel accessible from HA sidebar | panel_custom.async_register_panel + hass.http.async_register_static_paths verified in installed HA 2024.12.5 |
| UI-02 | Panel has Global Settings section: global mode, default temperatures, global time program | WebSocket get_config + set_global_mode + set_period_temperatures + set_time_program commands; per-day schema design |
| UI-03 | Panel has Rooms section: per-room time program (or inherit global), climate entity management | set_room_config WS command; room sensor optional fields; per-day room program override |
| UI-04 | Panel has Persons section: presence mode, room associations, presence schedule | set_person_config WS command; per-day presence schedule; presence bar component |

</phase_requirements>

---

## Summary

Phase 3 has three separable work streams that must be sequenced: (1) Wave 1 gap-closure — refactor the Phase 2 `weekday_groups` backend to the per-day schema required by all Panel and WebSocket API code; (2) Wave 2 Python WebSocket API — 7 commands registered in `async_setup_entry` via `websocket_api.async_register_command`, one subscription command using `connection.subscriptions`; (3) Wave 3 Lit/TypeScript panel — Vite library-mode build producing a single `panel.js` file served via `hass.http.async_register_static_paths` and registered via `panel_custom.async_register_panel`.

All three HA Python APIs required for this phase (`websocket_api`, `panel_custom.async_register_panel`, `StaticPathConfig + async_register_static_paths`) are confirmed present in the installed HA 2024.12.5 venv with exact, verified signatures. The `home-assistant-js-websocket` library's `hass.connection.subscribeMessage` / `sendMessagePromise` API is confirmed via Context7. Vite library-mode with `inlineDynamicImports: true` produces a single ES module file suitable for HA panel loading.

The per-day schema refactor is the most invasive pre-condition: 8 files touch `weekday_groups` (3 source, 5 test). The refactor is localized and mechanical — the new schema is simpler (direct dict lookup by day name replaces group-search loop), but every function signature in `schedule.py`, all coordinator access paths, `const.py` defaults, and all test fixtures must be updated together.

**Primary recommendation:** Execute Wave 1 (schema refactor) as a self-contained plan with its own test gate before starting any Wave 2 or Wave 3 work.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Panel registration & static file serving | Backend (Python HA integration) | — | HA uses Python APIs to register the panel URL and serve the JS file; the frontend only consumes what Python exposes |
| Config read / write (all 7 WS commands) | Backend (Python HA integration) | — | Data lives in Store + runtime_config; only Python can mutate it safely from within the HA event loop |
| Status push (subscribe_status) | Backend (Python HA integration) | — | Coordinator lives in backend; it fires events that the WS handler relays to subscribed connections |
| Panel UI rendering & state management | Frontend (Lit panel, browser) | — | The entire panel is a web component running in the HA Lovelace page; no SSR |
| Time bar drag/interaction logic | Frontend (Lit panel, browser) | — | All pointer events, 15-min snapping, segment splitting, copy/paste clipboard are purely client-side |
| Auto-save debouncing | Frontend (Lit panel, browser) | — | The panel decides when each interaction ends (blur, mouse-up, popup close) and fires the WS call |
| Live status display | Backend supplies data; Frontend renders | — | Backend computes active period + present persons; Frontend subscribes and renders updates |

---

## Standard Stack

### Core (verified versions)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.components.websocket_api` | HA 2024.12.5 (installed) | Custom WS command registration | Canonical HA pattern; `@websocket_command` decorator + `async_register_command` |
| `homeassistant.components.panel_custom` | HA 2024.12.5 (installed) | Panel registration | `async_register_panel` is the documented programmatic API for custom panels |
| `homeassistant.components.http.StaticPathConfig` | HA 2024.12.5 (installed) | Async static file serving | Replaces deprecated `register_static_path` (removed in HA 2025.7) |
| `lit` | 3.3.3 (npm registry) | Web component base class for panel | HA's own frontend is built on Lit; ha-* components compose natively |
| `typescript` | 6.0.3 (npm registry) | Type-safe panel code | Types for hass object shape and WS message contracts |
| `vite` | 8.0.13 (npm registry) | Panel build tool | Single-file ES module output via library mode; fast dev HMR |
| `home-assistant-js-websocket` | 9.6.0 (npm registry) | Panel-side WS client | Official HA library; `sendMessagePromise` + `subscribeMessage` |

[VERIFIED: npm registry for npm versions; venv inspection for HA version]

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `voluptuous` | HA built-in | WS command schema validation | All WS command handlers use `vol.Required`/`vol.Optional` |
| `pathlib.Path` | Python stdlib | Locating `www/` directory at runtime | `Path(__file__).parent / "www"` — portable across deploy paths |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `panel_custom.async_register_panel` | `configuration.yaml panel_custom:` entry | YAML approach requires user to manually configure; programmatic is self-contained within the integration |
| Bundled Lit in panel.js | Share HA's Lit instance via importmap | Sharing avoids bundle size but risks version conflict if HA upgrades Lit; bundling is safer per CLAUDE.md |
| `vite` library mode | Rollup directly | Vite wraps Rollup with better DX; no reason for raw Rollup |

**Installation (frontend):**
```bash
npm install lit typescript vite home-assistant-js-websocket
```

---

## Architecture Patterns

### System Architecture Diagram

```
Panel (browser / Lovelace page)               HA Python Backend
┌──────────────────────────────┐              ┌────────────────────────────┐
│ <climate-manager-panel>      │              │ async_setup_entry          │
│  ├── Global Settings tab     │  WS connect  │  ├── ClimateManagerStore   │
│  ├── Rooms tab               │◄────────────►│  ├── runtime_config (dict) │
│  └── Persons tab             │              │  ├── coordinator           │
│       │                      │              │  └── WS commands (×7)      │
│  ┌────▼──────────────────┐   │  get_config  │       │                    │
│  │ hass.connection       │──────────────────►  ws_get_config()           │
│  │ sendMessagePromise()  │◄──────────────────  → runtime_config slice    │
│  │                       │  set_*_config   │       │                    │
│  │ subscribeMessage()    │──────────────────►  ws_set_*() → store.save  │
│  └────────────────────┘   │              │  → coordinator.evaluate()    │
│                            │  subscribe   │       │                    │
│  ┌─────────────────────┐   │  _status    │  ws_subscribe_status()      │
│  │ Status strip        │◄──────────────────  connection.subscriptions   │
│  │ (push updates)      │  push event    │  ← hass.bus event listener   │
│  └─────────────────────┘   │              │  ← coordinator fires event  │
│                            │              └────────────────────────────┘
│  <climate-manager-time-bar>│
│  (7 days, drag/split/copy) │
└──────────────────────────────┘
        ▲ built by Vite → panel.js
        ▼ served at /climate_manager_panel/panel.js
```

### Recommended Project Structure

```
frontend/               ← Vite project root (new directory at repo root)
├── src/
│   ├── climate-manager-panel.ts    ← root custom element
│   ├── global-settings-tab.ts
│   ├── rooms-tab.ts
│   ├── persons-tab.ts
│   ├── climate-manager-time-bar.ts ← shared 7-bar component
│   ├── room-card.ts
│   ├── person-card.ts
│   ├── toast.ts
│   ├── ws-client.ts                ← thin wrapper over hass.connection
│   └── types.ts                    ← hass, config, WS message types
├── vite.config.ts
├── tsconfig.json
└── package.json

custom_components/climate_manager/
├── www/
│   └── panel.js                    ← Vite build output (git-ignored, generated by make build)
├── websocket_api.py                ← new: all 7 WS command handlers
├── __init__.py                     ← add panel + static path registration
├── const.py                        ← refactored: per-day schema (Wave 1)
├── schedule.py                     ← refactored: per-day API (Wave 1)
└── coordinator.py                  ← refactored: per-day lookups (Wave 1)
```

### Pattern 1: WebSocket Command Handler (request-response)

```python
# Source: homeassistant/components/websocket_api/__init__.py (venv verified)
# and homeassistant/components/sensor/websocket_api.py (HA core)
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

@websocket_api.websocket_command({
    vol.Required("type"): "climate_manager/set_global_mode",
    vol.Required("mode"): str,
})
@websocket_api.async_response
async def ws_set_global_mode(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Set global mode and persist."""
    # Access integration state via config entry (never hass.data[DOMAIN])
    entry = _get_entry(hass)
    entry.runtime_data.runtime_config["global_mode"] = msg["mode"]
    await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
    await entry.runtime_data.coordinator.async_evaluate()
    connection.send_result(msg["id"], {"success": True})
```

[VERIFIED: venv inspection of `homeassistant/components/websocket_api/__init__.py`]

### Pattern 2: WebSocket Subscription Command (backend push)

```python
# Source: homeassistant/components/websocket_api/commands.py (venv verified)
# Canonical pattern from handle_subscribe_entities in installed HA 2024.12.5
@websocket_api.websocket_command({
    vol.Required("type"): "climate_manager/subscribe_status",
})
@callback
def ws_subscribe_status(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Subscribe to coordinator status push events."""
    msg_id = msg["id"]

    @callback
    def _forward_status(event) -> None:  # noqa: ANN001
        connection.send_event(msg_id, event.data)

    # Store the unsubscribe callable — HA calls it automatically on connection close
    connection.subscriptions[msg_id] = hass.bus.async_listen(
        "climate_manager_status_update",
        _forward_status,
    )
    # Acknowledge the subscription immediately; push initial status
    connection.send_result(msg_id)
    # Optionally: connection.send_event(msg_id, _build_status(hass))
```

The coordinator calls `hass.bus.async_fire("climate_manager_status_update", status_dict)` after each `async_evaluate()` call to notify all subscribed panel instances.

[VERIFIED: venv inspection of `homeassistant/components/websocket_api/commands.py`]

### Pattern 3: Registering All WS Commands in async_setup_entry

```python
# Source: homeassistant/components/recorder/websocket_api.py (HA core)
# Register all commands once during entry setup; they auto-unregister on entry unload
from homeassistant.components import websocket_api
from . import websocket_api as cm_ws

async def async_setup_entry(hass, entry):
    # ... (existing store/discovery/coordinator setup) ...
    websocket_api.async_register_command(hass, cm_ws.ws_get_status)
    websocket_api.async_register_command(hass, cm_ws.ws_get_config)
    websocket_api.async_register_command(hass, cm_ws.ws_set_global_mode)
    websocket_api.async_register_command(hass, cm_ws.ws_set_period_temperatures)
    websocket_api.async_register_command(hass, cm_ws.ws_set_time_program)
    websocket_api.async_register_command(hass, cm_ws.ws_set_room_config)
    websocket_api.async_register_command(hass, cm_ws.ws_set_person_config)
    websocket_api.async_register_command(hass, cm_ws.ws_subscribe_status)
    # ... (panel registration below) ...
```

[VERIFIED: venv inspection; `async_register_command` signature confirmed]

### Pattern 4: Panel Registration + Static File Serving

```python
# Source: homeassistant/components/http/__init__.py (venv verified — StaticPathConfig)
# Source: homeassistant/components/panel_custom/__init__.py (venv verified — async_register_panel)
from pathlib import Path
from homeassistant.components.http import StaticPathConfig
from homeassistant.components import panel_custom

PANEL_URL = "/climate_manager_panel"
PANEL_COMPONENT_NAME = "climate-manager-panel"  # must match customElements.define() name

async def async_setup_entry(hass, entry):
    # ... (WS command registration) ...

    www_path = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths([
        StaticPathConfig(PANEL_URL, str(www_path), cache_headers=False)
    ])

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=DOMAIN,           # sidebar nav path = /climate_manager
        webcomponent_name=PANEL_COMPONENT_NAME,
        sidebar_title="Climate Manager",
        sidebar_icon="mdi:thermometer",
        module_url=f"{PANEL_URL}/panel.js",  # URL HA frontend loads as ES module
        embed_iframe=False,
        require_admin=False,
    )
```

`async_register_panel` is `async` (confirmed in venv). `StaticPathConfig` takes `(url_path, path, cache_headers)`. `cache_headers=False` is required during development to avoid stale panel.js.

[VERIFIED: venv inspection of both modules]

### Pattern 5: Frontend Panel — Lit Component Skeleton

```typescript
// Source: https://developers.home-assistant.io/docs/frontend/custom-ui/creating-custom-panels/
// Source: Context7 /lit/lit.dev reactive properties
import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";
import type { HomeAssistant } from "home-assistant-js-websocket";

class ClimateManagerPanel extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: Boolean }) narrow = false;
  @property({ attribute: false }) panel: unknown = null;

  @state() private _config: Record<string, unknown> | null = null;
  @state() private _activeTab = "global";

  connectedCallback() {
    super.connectedCallback();
    this._loadConfig();
    this._subscribeStatus();
  }

  private async _loadConfig() {
    this._config = await this.hass.connection.sendMessagePromise({
      type: "climate_manager/get_config",
    });
  }

  private _subscribeStatus() {
    this.hass.connection.subscribeMessage(
      (msg) => { /* update status display */ },
      { type: "climate_manager/subscribe_status" }
    );
  }

  render() { /* ... ha-tabs, ha-card, etc. ... */ }
}

customElements.define("climate-manager-panel", ClimateManagerPanel);
```

[VERIFIED: Context7 /home-assistant/home-assistant-js-websocket for sendMessagePromise + subscribeMessage; Context7 /lit/lit.dev for @property/@state]

### Pattern 6: Vite Config for Single-File Panel Build

```typescript
// frontend/vite.config.ts
// Source: Context7 /vitejs/vite build library mode docs
import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, "src/climate-manager-panel.ts"),
      name: "ClimateManagerPanel",
      fileName: "panel",
      formats: ["es"],  // ES module output; HA loads panels as ES modules
    },
    outDir: "../custom_components/climate_manager/www",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,  // single file — no chunks
        entryFileNames: "panel.js",
      },
    },
    cssCodeSplit: false,  // inline any CSS into panel.js
  },
});
```

This produces `custom_components/climate_manager/www/panel.js` — a single ES module file with Lit bundled. No external dependencies at runtime.

[VERIFIED: Context7 /vitejs/vite — `rollupOptions.output.inlineDynamicImports: true` produces single file for single-entry builds]

### Anti-Patterns to Avoid

- **Using `hass.data[DOMAIN]` in WS handlers:** All integration state lives on `entry.runtime_data`. WS handlers must resolve the config entry via `hass.config_entries.async_entries(DOMAIN)[0]` or pass `entry` into handler closures.
- **Calling `hass.http.register_static_path` (sync):** Deprecated in HA 2024, removed in HA 2025.7. Use `await hass.http.async_register_static_paths([StaticPathConfig(...)])`.
- **Using `js_url` instead of `module_url` in panel registration:** `js_url` loads as a classic script; `module_url` loads as an ES module (required for Lit imports to work correctly).
- **Saving DEFAULT_CONFIG on every mutation:** WS handlers must read current sparse `runtime_config`, apply the delta, and write back. Never flatten to full DEFAULT_CONFIG.
- **Firing `hass.bus.async_fire` in a sync callback:** Must be `@callback` decorated or run in the event loop. Coordinator's `async_evaluate` is already `async` — fire after the push.
- **Sharing HA's Lit instance:** HA's internal Lit instance is not guaranteed to be the same version. Bundle Lit into panel.js.
- **Not setting `cache_headers=False`:** During development, stale `panel.js` will be served from browser cache. Set `cache_headers=False` for the www/ static path.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WS command schema validation | Custom validator | `vol.Required`/`vol.Optional` with `@websocket_command({...})` | Built into HA's WS API dispatch; invalid messages are rejected before handler runs |
| Static file serving (async) | aiohttp route manually | `hass.http.async_register_static_paths` + `StaticPathConfig` | HA HTTP server is already running; adding routes is 2 lines |
| Panel loading | Custom HTTP endpoint | `panel_custom.async_register_panel` + `module_url` | HA's panel loader handles auth, Lovelace routing, and sidebar registration |
| WS subscription cleanup | Manual unsubscribe tracking | `connection.subscriptions[msg_id] = unsub_fn` | HA calls all `connection.subscriptions` values automatically on connection close |
| Frontend build / bundling | Manual rollup config | Vite library mode with `inlineDynamicImports: true` | Handles TS compilation, tree-shaking, source maps |
| Type definitions for hass object | Write from scratch | `home-assistant-js-websocket` TypeScript types | Official HA types for `HomeAssistant`, `HassEntity`, `Connection` |

**Key insight:** HA's WS subscription cleanup is automatic — storing `unsub = hass.bus.async_listen(...)` in `connection.subscriptions[msg_id]` is sufficient. HA calls `unsub()` for all stored callables when the connection closes.

---

## Per-Day Schema Refactor (Wave 1 Scope)

This is the mandatory pre-condition. Every file that references `weekday_groups` must be updated.

### Files to Refactor

| File | Change | Notes |
|------|--------|-------|
| `const.py` | `"global_time_program": {"weekday_groups": []}` → `"global_time_program": {"mon": [], "tue": [], ..., "sun": []}` | Same for room time_program and person schedule sub-schemas |
| `schedule.py` | `evaluate_schedule(weekday_groups, now)` → `evaluate_schedule(daily_program, now)` | Lookup changes from `for group in groups: if today in group["days"]` to `daily_program[day_name]` |
| `schedule.py` | `resolve_presence(person_config, now)` → reads `schedule["mon"]` etc. directly | Same pattern: `schedule.get("weekday_groups", [])` → `schedule.get(day_name, [])` |
| `schedule.py` | `compute_occupied_temp(weekday_groups, ...)` → `compute_occupied_temp(daily_program, ...)` | Same |
| `schedule.py` | `validate_7day_coverage(weekday_groups)` → validate per-day dict (all 7 keys present) | New validation: check all 7 day keys exist in the dict |
| `coordinator.py` | All 3 `weekday_groups` access paths | `config["global_time_program"]["weekday_groups"]` → `config["global_time_program"]` (the dict IS the per-day map) |
| `test_schedule.py` | All test fixtures using `weekday_groups` structure | Convert `WEEKDAY_PROGRAM` list-of-groups to `{"mon": [...], "tue": [...], ...}` format |
| `test_coordinator.py` | All `weekday_groups=` fixtures | Same conversion |
| `test_storage.py` | `{"time_program": {"weekday_groups": []}}` references | Update to per-day structure |

### Schema Comparison

**Current (weekday_groups):**
```python
{
  "global_time_program": {
    "weekday_groups": [
      {"days": ["mon", "tue", "wed", "thu", "fri"], "periods": [{"start": "07:00", "mode": "normal"}]},
      {"days": ["sat", "sun"], "periods": [{"start": "08:00", "mode": "comfort"}]},
    ]
  }
}
```

**Target (per-day):**
```python
{
  "global_time_program": {
    "mon": [{"start": "07:00", "mode": "normal"}],
    "tue": [{"start": "07:00", "mode": "normal"}],
    "wed": [{"start": "07:00", "mode": "normal"}],
    "thu": [{"start": "07:00", "mode": "normal"}],
    "fri": [{"start": "07:00", "mode": "normal"}],
    "sat": [{"start": "08:00", "mode": "comfort"}],
    "sun": [{"start": "08:00", "mode": "comfort"}],
  }
}
```

The per-day schema is simpler to evaluate: `daily_program[day_name]` is an O(1) lookup instead of a linear scan through groups. The `DAY_TO_WEEKDAY` mapping in `schedule.py` can be used in reverse: `WEEKDAY_TO_DAY = {v: k for k, v in DAY_TO_WEEKDAY.items()}` to get the day name from `now.weekday()`.

### Presence Schedule (same pattern)

**Current:**
```python
"schedule": {"weekday_groups": [{"days": ["mon",...], "periods": [{"start": "08:00", "state": "present"}]}]}
```

**Target:**
```python
"schedule": {"mon": [{"start": "08:00", "state": "present"}], "tue": [...], ...}
```

### DEFAULT_CONFIG Update

```python
# const.py — new empty per-day structure
_EMPTY_DAILY_PROGRAM = {day: [] for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]}

DEFAULT_CONFIG: dict = {
    "version": STORAGE_VERSION,
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": { ... },  # unchanged
    "global_time_program": copy.deepcopy(_EMPTY_DAILY_PROGRAM),
    "rooms": {},
    "persons": {},
}
```

Rooms and persons sub-schemas follow the same pattern. The sparse storage model is unchanged — a room entry only appears if it has a custom program.

[VERIFIED: codebase grep of all `weekday_groups` occurrences; schema change is self-contained to these 8 files]

---

## WebSocket Command Set

The 7-command minimal set agreed in 03-UI-SPEC.md. All commands use the `climate_manager/` prefix.

| Command | Handler type | Payload | Backend action |
|---------|-------------|---------|----------------|
| `get_status` | `@async_response` | `{}` | Read coordinator last result + hass.states for sensors |
| `get_config` | `@async_response` | `{}` | Return `entry.runtime_data.runtime_config` |
| `set_global_mode` | `@async_response` | `{mode: str}` | Mutate runtime_config + store.async_save + coordinator.async_evaluate |
| `set_period_temperatures` | `@async_response` | `{temperatures: {frost_protection, reduced, normal, comfort}}` | Same pattern |
| `set_time_program` | `@async_response` | `{program: {mon: [], ...}}` | Validates all 7 keys present; mutates global_time_program |
| `set_room_config` | `@async_response` | `{room_id: str, config: {temperature_sensor?, humidity_sensor?, time_program?}}` | Sparse-merge into rooms[room_id] |
| `set_person_config` | `@async_response` | `{person_id: str, config: {mode?, room_ids?, schedule?}}` | Sparse-merge into persons[person_id] |
| `subscribe_status` | `@callback` (sync) | `{}` | Register hass.bus listener in connection.subscriptions |

**Accessing the config entry from WS handlers:**

```python
# Pattern: pass entry as closure variable when registering commands in async_setup_entry
def _register_websocket_commands(hass: HomeAssistant, entry: ClimateManagerConfigEntry) -> None:
    @websocket_api.websocket_command({vol.Required("type"): "climate_manager/get_config"})
    @websocket_api.async_response
    async def ws_get_config(hass, connection, msg):
        connection.send_result(msg["id"], entry.runtime_data.runtime_config)
    websocket_api.async_register_command(hass, ws_get_config)
    # ... same for each command
```

Alternatively, pass entry via a helper that retrieves `hass.config_entries.async_entries(DOMAIN)[0]`. The closure pattern is simpler and avoids a runtime lookup.

[ASSUMED: The closure pattern is the preferred approach for config-entry-scoped WS commands. No official HA documentation explicitly states the canonical method — both closures and `hass.config_entries.async_entries` are used in community examples.]

---

## Frontend Architecture

### `hass` Object Access in Panel

The HA Lovelace frontend automatically passes three properties to any registered custom panel element [CITED: developers.home-assistant.io/docs/frontend/custom-ui/creating-custom-panels]:
- `hass` — the full HomeAssistant object (includes `hass.connection`, `hass.states`, `hass.user`)
- `narrow` — Boolean, true on mobile
- `panel` — the panel config dict passed at registration

`hass.connection` is the active WebSocket connection. Call `hass.connection.sendMessagePromise({type: "climate_manager/get_config"})` to send a command and receive the response as a Promise.

### Subscription on Panel Mount

```typescript
// Source: Context7 /home-assistant/home-assistant-js-websocket
// subscribeMessage returns Promise<unsubscribe function>
connectedCallback() {
  super.connectedCallback();
  this._unsubStatus = this.hass.connection.subscribeMessage(
    (statusUpdate) => { this._status = statusUpdate; },
    { type: "climate_manager/subscribe_status" }
  );
}

disconnectedCallback() {
  super.disconnectedCallback();
  this._unsubStatus?.then((unsub) => unsub());
}
```

`subscribeMessage` automatically re-establishes the subscription after a reconnect unless `options.resubscribe: false`. [VERIFIED: Context7 /home-assistant/home-assistant-js-websocket]

### ha-* Components in Lit Panel

The following ha-* components are referenced in 03-UI-SPEC.md. They are lazy-loaded by HA Lovelace:

| Component | Usage | Load guarantee |
|-----------|-------|----------------|
| `ha-card` | Room/person card wrappers, status strip | Always loaded in Lovelace |
| `ha-tabs` | Top-level tab navigation | [ASSUMED: loaded by Lovelace when ha-tabs is used in a panel; some community panels use `@kipk/load-ha-components` as a fallback] |
| `ha-textfield` | Temperature inputs, entity ID inputs | [ASSUMED: available when the integration page is open; lazy-loaded by HA if not already present] |
| `ha-switch` | "Override global time program" toggle | [ASSUMED: same as ha-textfield] |
| `ha-select` | Global mode dropdown | [ASSUMED: same] |
| `ha-icon-button` | Copy/Paste bar buttons | [ASSUMED: same] |
| `ha-circular-progress` | Loading spinner | [ASSUMED: same] |

**Mitigation for lazy-loading:** Define `<ha-*>` custom elements in the panel's `render()` only after the `hass` object is available. In practice, HA ensures core MDC components (`ha-card`, `ha-textfield`, etc.) are loaded before a panel renders. This is [ASSUMED] based on community patterns — verify during implementation that `ha-tabs` is available without explicit preloading.

### Time Bar Component Design

The `<climate-manager-time-bar>` must:
1. Accept `days` property (7-element array of day period arrays) and `mode` ("schedule" | "presence")
2. Convert time strings to pixel offsets: `offset = (totalMinutes / 1440) * barWidth`
3. Handle pointer events for drag: `pointerdown` → `pointermove` (snap to 15-min) → `pointerup` (save)
4. Snap logic: `Math.round(rawMinutes / 15) * 15`
5. Show mode-selection popup using a floating div positioned at click coordinates

The bar must always be fully covered — ensure periods array for each day always starts at "00:00" (or fill implicitly).

---

## Common Pitfalls

### Pitfall 1: register_static_path vs async_register_static_paths

**What goes wrong:** Using the deprecated `hass.http.register_static_path(url, path, cache)` logs a deprecation warning in HA 2024 and breaks in HA 2025.7.
**Why it happens:** Old community examples use the sync API.
**How to avoid:** Always use `await hass.http.async_register_static_paths([StaticPathConfig(url, path, cache_headers)])`.
**Warning signs:** HA logs "deprecated: calls hass.http.register_static_path" at startup.

[VERIFIED: HA developer blog post + venv inspection of http/__init__.py]

### Pitfall 2: webcomponent_name mismatch

**What goes wrong:** Panel shows a blank white page with no error. HA loads the JS file but the custom element is not defined.
**Why it happens:** `webcomponent_name` in `async_register_panel` must exactly match the string in `customElements.define("name", ...)` in the JS file.
**How to avoid:** Define the element name as a constant and use it in both places.
**Warning signs:** Browser console: "customElements.get('your-name') is undefined".

[ASSUMED: based on HA panel registration mechanics]

### Pitfall 3: WS handler accessing entry via hass.data[DOMAIN]

**What goes wrong:** `KeyError` if key not set, or stale data if multiple config entries exist.
**Why it happens:** Phase 1/2 explicitly avoided `hass.data[DOMAIN]`; WS handlers must follow the same pattern.
**How to avoid:** Pass `entry` into command handlers as a closure variable when registering in `async_setup_entry`.
**Warning signs:** `KeyError: 'climate_manager'` in WS handler.

[VERIFIED: codebase — __init__.py explicitly avoids hass.data[DOMAIN]]

### Pitfall 4: Mutation without re-evaluation

**What goes wrong:** Config is saved to store but TRVs are not updated until the next minute poll.
**Why it happens:** Forgetting to call `await coordinator.async_evaluate()` after saving.
**How to avoid:** All write WS handlers must call `coordinator.async_evaluate()` after `store.async_save()`.
**Warning signs:** TRV temperature does not change for up to 60 seconds after a panel config change.

[VERIFIED: coordinator.py — evaluate() is the push trigger]

### Pitfall 5: Sparse storage corruption on WS mutation

**What goes wrong:** A WS handler that saves the full `runtime_config` (including all DEFAULT_CONFIG keys) corrupts the sparse storage model — future reads will have bloated stored data.
**Why it happens:** `runtime_config` is the merged result (defaults + stored). Writing it back stores the defaults too.
**How to avoid:** Read-modify-write only the specific sub-key. For rooms: `entry.runtime_data.runtime_config["rooms"][room_id] = new_config`, then save. Never save `copy.deepcopy(runtime_config)` wholesale unless the storage layer handles de-defaulting (it currently does not).

[ASSUMED: Based on existing sparse storage model in storage.py. The current async_save writes exactly what it receives — no de-defaulting step exists. Confirmed by reading storage.py.]

### Pitfall 6: panel.js served with cache_headers=True during development

**What goes wrong:** After rebuilding with `make build`, the browser serves the old panel.js from cache.
**Why it happens:** `StaticPathConfig` defaults `cache_headers=True` (aggressive caching).
**How to avoid:** Set `cache_headers=False` for the www/ path. Only set `True` for production if cache-busting via URL versioning is implemented.
**Warning signs:** Panel changes are not reflected after rebuild despite successful Vite build.

[VERIFIED: venv inspection of StaticPathConfig dataclass — `cache_headers: bool = True`]

### Pitfall 7: async_register_panel called before hass.http is ready

**What goes wrong:** `AttributeError: 'NoneType' object has no attribute 'async_register_static_paths'`.
**Why it happens:** `hass.http` is set up during HA boot; if called too early it may be None.
**How to avoid:** Call both `async_register_static_paths` and `async_register_panel` inside `async_setup_entry` (not `async_setup`). Config entries are set up after all component dependencies are loaded.
**Warning signs:** Error occurs only on fresh HA start, not on integration reload.

[ASSUMED: Based on HA dependency loading order. manifest.json will need `"dependencies": ["http", "frontend", "panel_custom"]` to guarantee ordering.]

### Pitfall 8: Vite outputs multiple chunks instead of single panel.js

**What goes wrong:** HA loads `panel.js` but it imports other chunk files that return 404 (HA doesn't know about them).
**Why it happens:** Vite code-splits by default. `inlineDynamicImports: true` only works for single-entry builds.
**How to avoid:** Ensure `build.lib` has a single `entry` and `rollupOptions.output.inlineDynamicImports: true`. Verify build output has exactly one JS file.
**Warning signs:** Browser network tab shows 404 for `.js` chunk files.

[VERIFIED: Context7 /vitejs/vite — inlineDynamicImports limitation for single-entry documented]

---

## Code Examples

### Complete WS Command Registration (websocket_api.py)

```python
# Source: pattern from homeassistant/components/websocket_api/__init__.py (venv) +
#         homeassistant/components/websocket_api/commands.py (venv) +
#         homeassistant/components/sensor/websocket_api.py (HA core)
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
import voluptuous as vol

from . import ClimateManagerConfigEntry
from .const import DOMAIN, MODE_OFF, MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES

VALID_MODES = [MODE_OFF, MODE_TIME_PROGRAM, MODE_TIME_PROGRAM_PRESENCES]


def async_register_commands(
    hass: HomeAssistant, entry: ClimateManagerConfigEntry
) -> None:
    """Register all Climate Manager WebSocket commands."""
    websocket_api.async_register_command(hass, _make_ws_get_config(entry))
    websocket_api.async_register_command(hass, _make_ws_set_global_mode(entry))
    # ... one factory function per command ...
    websocket_api.async_register_command(hass, _make_ws_subscribe_status(hass, entry))


def _make_ws_set_global_mode(entry: ClimateManagerConfigEntry):
    @websocket_api.websocket_command({
        vol.Required("type"): f"{DOMAIN}/set_global_mode",
        vol.Required("mode"): vol.In(VALID_MODES),
    })
    @websocket_api.async_response
    async def ws_set_global_mode(hass, connection, msg):
        entry.runtime_data.runtime_config["global_mode"] = msg["mode"]
        await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
        await entry.runtime_data.coordinator.async_evaluate()
        connection.send_result(msg["id"], {"success": True})
    return ws_set_global_mode
```

### Subscription Push from Coordinator

```python
# In coordinator.py — add after each async_evaluate() call:
async def async_evaluate(self, _utc_now=None):
    # ... existing evaluation logic ...
    # Push updated status to all subscribed panel instances
    self._hass.bus.async_fire(
        f"{DOMAIN}_status_update",
        self._build_status_payload(),
    )

def _build_status_payload(self) -> dict:
    return {
        "global_mode": self._data.runtime_config["global_mode"],
        "active_period": self._last_active_period,   # new field to track
        "present_persons": self._last_present_persons, # new field to track
    }
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hass.http.register_static_path` (sync) | `await hass.http.async_register_static_paths([StaticPathConfig(...)])` | HA 2024.6 (removed 2025.7) | Must use async API |
| Frontend panels via YAML `panel_custom:` | `panel_custom.async_register_panel` (programmatic, from Python) | Available since HA 2021.x | No user YAML required |
| `hass.data[DOMAIN]` global dict | `entry.runtime_data` typed dataclass (modern pattern) | HA 2024 blog (April 2024) | WS handlers use `entry.runtime_data` |
| `@property` decorator for WS command type | `@websocket_api.websocket_command({vol.Required("type"): "..."})` | Current HA pattern | Decorator-based schema validation |

**Deprecated/outdated:**
- `hass.http.register_static_path`: removed in HA 2025.7. Do not use.
- `async_register_built_in_panel` called directly: use `panel_custom.async_register_panel` which wraps it correctly with the `"custom"` component name.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ha-tabs`, `ha-textfield`, `ha-switch`, `ha-select`, `ha-icon-button`, `ha-circular-progress` are available in Lovelace without explicit preloading when used in a custom panel | Frontend Architecture — ha-* Components | Panel may render blank or throw "undefined element" errors; mitigation: `@kipk/load-ha-components` or `customElements.whenDefined()` guard |
| A2 | Closure pattern (passing `entry` into WS command factories) is the correct approach for config-entry-scoped WS commands | WS Command Set — Accessing config entry | Alternative: `hass.config_entries.async_entries(DOMAIN)[0]` — both work; closure is simpler |
| A3 | Storing `subscriptions[msg_id] = hass.bus.async_listen(...)` is sufficient for cleanup — HA calls all subscription values on connection close | Pattern 2 — WS Subscription | If cleanup is not automatic, ghost listeners will fire after panel disconnect; verify from venv confirms this is the correct pattern |
| A4 | `manifest.json` requires `"dependencies": ["http", "frontend", "panel_custom"]` to guarantee `hass.http` and `panel_custom` are available during `async_setup_entry` | Pattern 4 — Panel Registration | Without correct dependencies, `async_setup_entry` may fail at startup with AttributeError |
| A5 | The coordinator can call `hass.bus.async_fire(...)` after each evaluation without performance issues given ~1 event/minute fire rate | Subscribe_status implementation | At 1 fire/min this is trivially safe; no risk |

[A3 is actually VERIFIED from venv inspection of `connection.py` lines 246–254: `async_handle_close` iterates `self.subscriptions.values()` and calls each as `unsub()`.]

**Revised A3:** VERIFIED — `connection.subscriptions` cleanup is confirmed in installed HA 2024.12.5.

---

## Open Questions (RESOLVED)

1. **ha-* component lazy-loading in panels**
   - What we know: HA Lovelace lazy-loads components; core MDC components are generally available
   - What's unclear: Whether `ha-tabs` specifically needs explicit loading in a panel context vs. a card context
   - Recommendation: In Wave 0 of the frontend build plan, test a minimal `<ha-tabs>` render and verify it appears. If not, add `customElements.whenDefined("ha-tabs")` guard or import `@kipk/load-ha-components`.
   - **RESOLVED (2026-05-20):** `ha-select`, `ha-textfield`, and `ha-tabs`/`paper-tab` are all broken or removed in HA 2026.x. No lazy-loading needed — replaced with native `<select>`, `<input type="number">`, and CSS button tabs throughout the frontend. Project memory updated with these constraints.

2. **hass.bus.async_fire from coordinator thread safety**
   - What we know: `async_evaluate` runs in the HA event loop (it's `async`); `hass.bus.async_fire` is a `@callback` (sync, event-loop-safe)
   - What's unclear: Whether firing from inside `async_evaluate` adds latency to TRV push
   - Recommendation: Call `hass.bus.async_fire` after all TRV push calls complete. No concern on latency — it's a single dict copy.
   - **RESOLVED:** Confirmed safe — `async_fire` called after all TRV push calls complete in `async_evaluate`; no observed latency issue.

3. **Storage version bump for per-day schema migration**
   - What we know: `STORAGE_VERSION = 1` is the current version; changing schema technically requires a migration
   - What's unclear: Whether any stored data exists that uses weekday_groups format (no users yet — dev-only)
   - Recommendation: Since this is a development integration with no existing users, simply increment `STORAGE_VERSION = 2` and delete any existing `.storage/climate_manager` file. No migration function needed for v0→v2.
   - **RESOLVED (2026-05-20):** `STORAGE_VERSION = 2` set in const.py; no migration function written (dev-only integration, no existing users). Existing `.storage/climate_manager` deleted manually during deployment.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | HA integration tests | ✓ | 3.12 (venv) | — |
| Node.js | Vite frontend build | ✓ | v25.9.0 | — |
| npm | Frontend package install | ✓ | 11.12.1 | — |
| uv | Python dep management | ✓ | 0.11.2 | pip |
| pytest-homeassistant-custom-component | WS handler tests | ✓ | 0.13.195 | — |
| homeassistant (test venv) | Test fixture | ✓ | 2024.12.5 | — |
| SSH / rsync (deploy) | `make deploy` | [ASSUMED: available on dev machine] | — | — |

**Missing dependencies with no fallback:** None identified.

**Note on HA version gap:** The test venv has HA 2024.12.5. The production target is "latest HA" (which is HA 2025.x). All APIs used (`async_register_static_paths`, `panel_custom.async_register_panel`, `websocket_api`) are confirmed present in 2024.12.5 and are not deprecated — they should be stable in 2025.x. The `register_static_path` removal in 2025.7 is already avoided by using the async API.

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Panel access controlled by HA auth (the hass WebSocket connection is already authenticated) |
| V3 Session Management | No | HA manages the WebSocket session; no custom session state |
| V4 Access Control | Partial | `require_admin=False` in panel registration — panel is accessible to all HA users. WS handlers do not need `@websocket_api.require_admin` since all users should be able to configure the integration. Consider `require_admin=True` for write commands if the integration is multi-user. |
| V5 Input Validation | Yes | `vol.Required`/`vol.Optional`/`vol.In` schema validation on all WS command payloads via `@websocket_command` decorator |
| V6 Cryptography | No | No custom crypto; HA's HTTPS/auth handles transport security |

| Threat Pattern | STRIDE | Mitigation |
|----------------|--------|------------|
| Malformed WS payload (invalid mode string, non-numeric temperature) | Tampering | `vol.In(VALID_MODES)` + `vol.Coerce(float)` in WS command schemas |
| Unauthorized config mutation | Elevation of Privilege | HA WS auth gate — unauthenticated connections cannot call any registered command |
| Stale panel.js served after update | Tampering (indirect) | `cache_headers=False` on static path prevents cached attack surface |

---

## Sources

### Primary (HIGH confidence)
- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/homeassistant/components/panel_custom/__init__.py` — `async_register_panel` complete signature verified
- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/homeassistant/components/http/__init__.py` — `StaticPathConfig` dataclass + `async_register_static_paths` signature verified
- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/homeassistant/components/websocket_api/__init__.py` — `async_register_command`, `@websocket_command`, `@async_response` confirmed
- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/homeassistant/components/websocket_api/connection.py` — `ActiveConnection.subscriptions`, `send_result`, `send_event`, cleanup in `async_handle_close`
- `/home/arnaud/dev/climate_manager/.venv/lib/python3.12/site-packages/homeassistant/components/websocket_api/commands.py` — `handle_subscribe_entities` subscription pattern
- Context7 `/home-assistant/home-assistant-js-websocket` — `sendMessagePromise`, `subscribeMessage`, `subscribeEvents` API
- Context7 `/lit/lit.dev` — `@property`, `@state`, LitElement lifecycle
- Context7 `/vitejs/vite` — library mode, `rollupOptions.output.inlineDynamicImports: true`
- npm registry — lit@3.3.3, vite@8.0.13, home-assistant-js-websocket@9.6.0, typescript@6.0.3

### Secondary (MEDIUM confidence)
- [HA Developer Docs: WebSocket API extension](https://developers.home-assistant.io/docs/frontend/extending/websocket-api/) — command registration pattern
- [HA Developer Docs: Creating custom panels](https://developers.home-assistant.io/docs/frontend/custom-ui/creating-custom-panels/) — hass object properties
- [HA Developer Blog: async_register_static_paths](https://developers.home-assistant.io/blog/2024/06/18/async_register_static_paths/) — migration guide and deprecation timeline
- Community thread [How to Add a Sidebar Panel](https://community.home-assistant.io/t/how-to-add-a-sidebar-panel-to-a-home-assistant-integration/981585) — complete panel registration code example

### Tertiary (LOW confidence)
- [HA frontend discussion: ha-* component lazy loading](https://community.home-assistant.io/t/use-of-ha-web-components-in-custom-ui/379296) — lazy loading behavior (unverified for panels specifically)

---

## Metadata

**Confidence breakdown:**
- Per-day schema refactor scope: HIGH — all 8 files grep-verified; change is mechanical
- WS API patterns: HIGH — all APIs verified against installed venv source
- Panel registration: HIGH — `async_register_panel` signature verified in venv; `StaticPathConfig` verified in venv
- Vite single-file config: HIGH — verified via Context7
- ha-* component availability: MEDIUM (A1 assumption) — generally true but lazy-loading behavior in panels is unverified

**Research date:** 2026-05-17
**Valid until:** 2026-08-17 (stable HA APIs; Vite/Lit APIs stable; 90-day estimate)
