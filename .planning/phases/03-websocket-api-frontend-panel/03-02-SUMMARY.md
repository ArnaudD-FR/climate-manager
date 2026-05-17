---
phase: 03-websocket-api-frontend-panel
plan: "02"
subsystem: websocket-api
tags: [websocket, panel-registration, backend, tests]
dependency_graph:
  requires: [per-day-schema-D01, validate_daily_program, STORAGE_VERSION_2]
  provides: [websocket-api-8-commands, subscribe-status-push, panel-registration, static-path]
  affects: [03-03-frontend-panel]
tech_stack:
  added: [homeassistant.components.websocket_api, homeassistant.components.panel_custom, homeassistant.components.http.StaticPathConfig]
  patterns: [closure-factory-ws-commands, write-then-evaluate, sparse-safe-mutation, coordinator-status-push, hass-bus-async-fire]
key_files:
  created:
    - custom_components/climate_manager/websocket.py
    - tests/test_websocket.py
  modified:
    - custom_components/climate_manager/coordinator.py
    - custom_components/climate_manager/__init__.py
    - custom_components/climate_manager/manifest.json
    - tests/conftest.py
decisions:
  - "TYPE_CHECKING guard used in websocket.py for ClimateManagerConfigEntry import to avoid circular import (websocket.py imported FROM __init__.py)"
  - "hass_frontend mocked in conftest.py — test venv does not have hass-frontend package installed; frontend component requires it at setup time"
  - "filter_aiohttp_shutdown_threads conftest fixture suppresses aiohttp _run_safe_shutdown_loop daemon thread teardown false-positive in pytest-homeassistant-custom-component verify_cleanup"
  - "www/ directory created via hass.async_add_executor_job to avoid blocking event loop (Pitfall 2)"
metrics:
  duration: "~35 minutes"
  completed: "2026-05-18"
  tasks: 2
  files: 6
---

# Phase 3 Plan 2: WebSocket API Layer + Panel Registration Summary

8-command WebSocket API with coordinator status push, static path serving, and sidebar panel registration via `panel_custom.async_register_panel` — enabling the Phase 3 frontend panel (Wave 3) to read/write all integration config through a fully validated Python backend.

## What Was Built

### Task 1: websocket.py + coordinator status push

**websocket.py (new):**
- `async_register_commands(hass, entry)` — registers all 8 commands via `websocket_api.async_register_command`
- `_make_ws_get_status(entry)` — returns global_mode, active_period, present_persons, rooms_status (per-room temperature/humidity from configured sensors, with `None` guard on every `hass.states.get()` call)
- `_make_ws_get_config(entry)` — returns full `entry.runtime_data.runtime_config` unchanged
- `_make_ws_set_global_mode(entry)` — `vol.In(VALID_MODES)` schema gate; write-then-evaluate pattern
- `_make_ws_set_period_temperatures(entry)` — `vol.Coerce(float)` on all 4 period temperature keys; sparse-safe key-by-key update
- `_make_ws_set_time_program(entry)` — `validate_daily_program` gate; `send_error` + `return` BEFORE any `async_save`/`async_evaluate` on invalid input (T-03-05)
- `_make_ws_set_room_config(entry)` — `setdefault("rooms", {}).setdefault(room_id, {}).update(config)` sparse-safe merge
- `_make_ws_set_person_config(entry)` — same pattern keyed on `person_id` into `persons`
- `_make_ws_subscribe_status(entry)` — `@callback` sync handler; registers `hass.bus.async_listen` in `connection.subscriptions[msg_id]` for automatic cleanup on close (RESEARCH A3 — verified); forwards events via `websocket_api.event_message`

**coordinator.py changes:**
- `__init__`: added `_last_active_period: str | None = None` and `_last_present_persons: list[str] = []` tracking fields
- `async_evaluate`: fires `f"{DOMAIN}_status_update"` via `hass.bus.async_fire` after every evaluation (MODE_OFF resets tracking to None/[])
- `_evaluate_time_program`: records global period mode into `_last_active_period`; sets `_last_present_persons = []` (no presence mode)
- `_evaluate_time_program_presences`: tracks present persons per tick into `present_persons_this_tick`; stores into `_last_present_persons` before Step 4 push
- `_build_status_payload()`: returns dict with global_mode, active_period, present_persons for status push and `get_status` WS command

### Task 2: __init__.py wiring + manifest deps + test_websocket.py

**__init__.py:**
- Added imports: `pathlib.Path`, `StaticPathConfig`, `panel_custom`, `cm_ws` (websocket module), `DOMAIN`
- Added `PANEL_URL = "/climate_manager_panel"` and `PANEL_COMPONENT_NAME = "climate-manager-panel"` constants
- `async_setup_entry`: after scheduler registration, adds:
  1. `cm_ws.async_register_commands(hass, entry)` — WS commands registered (auto-unregister on unload)
  2. `www_path.mkdir` via `hass.async_add_executor_job` to create `www/` before panel.js exists
  3. `await hass.http.async_register_static_paths([StaticPathConfig(PANEL_URL, str(www_path), False)])` with `cache_headers=False` (Pitfall 6)
  4. `await panel_custom.async_register_panel(...)` with `module_url=f"{PANEL_URL}/panel.js"`

**manifest.json:**
- `"dependencies": ["http", "frontend", "panel_custom"]` — guarantees dependency load order (Pitfall 7)

**tests/test_websocket.py (new):**
- `test_ws_get_config_returns_runtime_config` — asserts "global_mode" in result
- `test_ws_set_global_mode_persists_and_evaluates` — sends `set_global_mode mode=off`; asserts success + runtime_config["global_mode"] == MODE_OFF
- `test_ws_set_time_program_rejects_partial` — sends partial program `{"mon": []}`; asserts error response + `global_time_program` unchanged

**tests/conftest.py (modified):**
- `mock_hass_frontend` fixture: mocks `hass_frontend` module (not installed in test venv); required by `frontend` component dependency chain
- `filter_aiohttp_shutdown_threads` fixture: patches `threading.enumerate()` to exclude `_run_safe_shutdown_loop` daemon threads — prevents false-positive teardown errors from `pytest-homeassistant-custom-component`'s `verify_cleanup` when `hass_ws_client` starts the aiohttp HTTP server

## Test Results

```
pytest tests/ -q
61 passed in 1.67s

pytest tests/test_websocket.py tests/test_init.py tests/test_coordinator.py -q
15 passed in 1.00s

manifest.json dependencies == ["http", "frontend", "panel_custom"] ✓
websocket.py defines async_register_commands + all 8 _make_ws_* factories (AST check) ✓
coordinator fires DOMAIN_status_update after every evaluation ✓
set_time_program: validate_daily_program gate + send_error before save (T-03-05) ✓
DEFAULT_CONFIG NOT imported in websocket.py ✓
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import between __init__.py and websocket.py**
- **Found during:** Task 2 — initial test run after adding `from . import websocket as cm_ws` to `__init__.py`
- **Issue:** `websocket.py` imported `ClimateManagerConfigEntry` from `__init__.py` directly, but `__init__.py` imports `websocket.py`, creating a circular import (`ImportError: cannot import name 'ClimateManagerConfigEntry' from partially initialized module`)
- **Fix:** Wrapped the import in `if TYPE_CHECKING:` guard in `websocket.py`. Type annotations with `from __future__ import annotations` work correctly at runtime; the TYPE_CHECKING guard prevents circular import at module load time.
- **Files modified:** `custom_components/climate_manager/websocket.py`
- **Commit:** 1cd93cf

**2. [Rule 3 - Blocking] hass_frontend module not installed in test venv**
- **Found during:** Task 2 — running tests after adding `"frontend"` to manifest dependencies
- **Issue:** `homeassistant.components.frontend.__init__.py` imports `hass_frontend` at setup time. The test venv has only `pytest-homeassistant-custom-component`; the actual `hass-frontend` bundle is not installed. Without a mock, the `frontend` dependency failed to load, causing all tests to fail with `ModuleNotFoundError: No module named 'hass_frontend'`.
- **Fix:** Added `mock_hass_frontend` autouse fixture to `tests/conftest.py` that patches `sys.modules["hass_frontend"]` with a minimal mock providing `where() -> Path`. The mock returns a `Path` object (not a string) because `frontend/__init__.py` uses `root_path / subpath` path arithmetic.
- **Files modified:** `tests/conftest.py`
- **Commit:** 1cd93cf

**3. [Rule 3 - Blocking] aiohttp _run_safe_shutdown_loop daemon thread causes teardown failure**
- **Found during:** Task 2 — running `tests/test_websocket.py` which uses `hass_ws_client` fixture
- **Issue:** `hass_ws_client` starts the aiohttp HTTP server (required for WebSocket connections). aiohttp spawns a daemon thread named `Thread-1 (_run_safe_shutdown_loop)` for graceful shutdown. `pytest-homeassistant-custom-component`'s `verify_cleanup` fixture only allows `threading._DummyThread` instances and `waitpid-*` threads — rejecting `_run_safe_shutdown_loop` with an assertion error. Tests passed (3/3) but exit code was 1.
- **Fix:** Added `filter_aiohttp_shutdown_threads` autouse fixture to `tests/conftest.py` that patches `threading.enumerate()` to exclude daemon threads whose name contains `_run_safe_shutdown_loop`. This is a targeted filter that does not suppress real thread leak detection.
- **Files modified:** `tests/conftest.py`
- **Commit:** 1cd93cf

## Known Stubs

None — all 8 WS commands are fully implemented. `get_status` reads live sensor states and coordinator tracking fields. The `www/` directory is created by `async_setup_entry`; `panel.js` does not exist yet (Wave 3 deliverable) but the integration loads cleanly without it.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| threat_flag: tampering | custom_components/climate_manager/websocket.py | 8 new WS command endpoints that accept user input. Mitigated by plan threat model: T-03-04 (vol.In/vol.Coerce schema validation), T-03-05 (validate_daily_program gate with early return), T-03-06 (HA auth gate), T-03-07 (sensor id never from payload), T-03-09 (sparse mutation pattern). All mitigations implemented as specified. |
| threat_flag: information-disclosure | custom_components/climate_manager/websocket.py | get_config returns full runtime_config to any authenticated HA user. Accepted per T-03-08: require_admin=False is the locked design; runtime_config contains no secrets. |

## Self-Check: PASSED

- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-af4cdace6dbdc44c6/custom_components/climate_manager/websocket.py` — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-af4cdace6dbdc44c6/custom_components/climate_manager/coordinator.py` — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-af4cdace6dbdc44c6/custom_components/climate_manager/__init__.py` — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-af4cdace6dbdc44c6/custom_components/climate_manager/manifest.json` — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-af4cdace6dbdc44c6/tests/test_websocket.py` — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-af4cdace6dbdc44c6/tests/conftest.py` — FOUND
- Commit bc5c411 — FOUND (Task 1: websocket.py + coordinator.py)
- Commit 1cd93cf — FOUND (Task 2: __init__.py + manifest.json + websocket.py fix + conftest.py + test_websocket.py)
- `pytest tests/test_websocket.py tests/test_init.py tests/test_coordinator.py -q` — 15 passed
- manifest.json dependencies == ["http", "frontend", "panel_custom"] ✓
- websocket.py AST check — 9 required names found ✓
- coordinator fires _status_update ✓
