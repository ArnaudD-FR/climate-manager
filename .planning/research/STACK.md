# Technology Stack

**Project:** Climate Manager — Home Assistant Custom Integration
**Researched:** 2026-05-15
**Overall confidence:** MEDIUM-HIGH (Python/HA backend HIGH; frontend panel MEDIUM due to sparse official examples)

---

## Recommended Stack

### Python Backend (HA Integration)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Integration language | HA 2025.x requires Python 3.12; target latest only per PROJECT.md constraint |
| `homeassistant.config_entries.ConfigEntry` | HA 2025.x | Persistent config store | Canonical HA mechanism for UI-editable, restart-persistent config; required for HACS-quality integrations |
| `homeassistant.config_entries.ConfigFlow` | HA 2025.x | Initial setup wizard | Provides the UI setup flow shown when user adds the integration from the Integrations page |
| `homeassistant.config_entries.OptionsFlow` | HA 2025.x | UI-editable options | For config users change after initial setup — global modes, temperature setpoints |
| `homeassistant.helpers.storage.Store` | HA 2025.x | Large/complex persistent data | For schedule data, room configs, person configs too complex for ConfigEntry.data |
| `homeassistant.helpers.update_coordinator.DataUpdateCoordinator` | HA 2025.x | State coordination hub | Ensures all entities share one refresh cycle; feeds CoordinatorEntity subclasses |
| `homeassistant.components.climate` | HA 2025.x | TRV control target | Standard climate entity domain — set_temperature + set_hvac_mode are the only service calls issued |
| `homeassistant.core.ServiceCall` / `hass.services.async_call` | HA 2025.x | Calling climate services | Issues climate.set_temperature and climate.set_hvac_mode on target TRV entities |
| `homeassistant.helpers.event.async_track_time_interval` | HA 2025.x | Periodic schedule evaluation | Fires the schedule evaluator at configurable intervals without busy-polling |
| `homeassistant.components.websocket_api` | HA 2025.x | Panel ↔ backend protocol | Custom WebSocket commands expose integration state and mutations to the frontend panel |

### Frontend Panel

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Lit (LitElement) | 3.x | Panel web component framework | HA's own frontend is built on Lit; HA exposes `<ha-*>` web components composable natively from Lit; other frameworks require custom-element wrapping with no benefit |
| TypeScript | 5.x | Panel language | Type-safety for the hass object shape and WebSocket message contracts; standard in HA frontend tooling |
| Vite | 5.x | Build tool | Bundles the panel JS into a single module file; Vite 5 is stable |
| `home-assistant-js-websocket` | latest | WS client in panel | Official HA JS library; provides hass.connection.subscribeMessage, sendMessagePromise — the canonical way for a panel to call custom backend commands |
| `frontend.async_register_panel` (Python) | HA 2025.x | Panel registration | Called in async_setup_entry; registers the built JS module as a sidebar panel with module_url |

### Infrastructure / Tooling

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `ludeeus/integration_blueprint` | latest | Scaffold reference | HA-endorsed starting point; correct file layout, GitHub Actions CI, pytest structure, HACS-compatible out of the box |
| pytest-homeassistant-custom-component | latest | Test harness | Only supported way to run HA integration tests outside the core repo; provides hass fixture |
| `uv` | latest | Python dependency management | Modern, fast; used in the 2025-era blueprint; replaces pip/poetry |
| GitHub Actions | — | CI/CD | Required for HACS Default store inclusion; validates hassfest + HACS action on every PR |

---

## Configuration Storage — Two Layers

**Layer 1 — ConfigEntry.data / ConfigEntry.options (via OptionsFlow)**
Store integration-level settings the user edits via the HA Integrations UI (e.g., global mode, default period temperatures). OptionsFlow surfaces these in the standard HA UI without any custom panel. Changes trigger the async_unload_entry / async_setup_entry lifecycle correctly.

**Layer 2 — homeassistant.helpers.storage.Store**
Store structured schedule data (rooms, time programs, person schedules) — JSON objects too complex and too frequently mutated to fit in ConfigEntry options. Store writes to `.storage/<domain>` JSON files, survives restarts, and is read/written from async context. As of November 2025, set `serialize_in_event_loop=False` for large nested objects to offload JSON serialization to a thread.

**Anti-pattern:** Do not use `hass.data[DOMAIN]` as a persistence layer. It is in-memory only and does not survive restarts.

---

## Frontend Panel Registration

Panels are registered from Python in `async_setup_entry`:

```python
from homeassistant.components.frontend import async_register_panel

async_register_panel(
    hass,
    component_name="custom",
    sidebar_title="Climate Manager",
    sidebar_icon="mdi:radiator",
    frontend_url_path="climate-manager",
    config={},
    require_admin=False,
    module_url="/local/climate_manager/panel.js",
)
```

The built `panel.js` must export a Lit-based custom element. HA instantiates it and injects a `hass` property (the live HA JS object) and a `panel` property. All backend communication goes through `hass.connection` — never raw fetch or external HTTP.

**Serving strategy:** Copy built `panel.js` into `custom_components/<domain>/www/` and register the static path in `async_setup`. HA serves files from `www/` at `/local/<domain>/`.

---

## HACS Compatibility Requirements

Minimum required files:

```
repo root/
  hacs.json                    # { "name": "Climate Manager", "zip_release": true }
  custom_components/
    climate_manager/
      manifest.json            # name, domain, version (SemVer), codeowners, iot_class
      __init__.py
      config_flow.py
```

`manifest.json` must include:
- `"version"`: SemVer (e.g., "1.0.0") — required for custom integrations
- `"domain"`: must match directory name
- `"iot_class"`: `"local_push"` — schedule-driven, integration pushes state to TRVs
- `"config_flow": true` — required for UI config
- `"requirements": []` — no external PyPI deps in v1

HACS also requires GitHub releases with version tags matching manifest.json version.

---

## Climate Entity Interface

This integration controls climate entities, not creates them. TRVs are registered by the Matter integration.

Two service calls are issued sequentially (not combined) due to Tado X / Matter reliability:

```python
# Step 1: Ensure heat mode (Matter auto mode is broken on Tado X)
await hass.services.async_call(
    "climate", "set_hvac_mode",
    {"entity_id": entity_id, "hvac_mode": "heat"},
    blocking=True,
)

# Step 2: Set target temperature
await hass.services.async_call(
    "climate", "set_temperature",
    {"entity_id": entity_id, "temperature": target_temp},
    blocking=True,
)
```

Entity state reading uses `hass.states.get(entity_id)` — no polling coordinator needed for the climate entities since this integration is schedule-driven, not sensor-driven.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Panel framework | Lit 3.x | React | Must be wrapped as custom element anyway; adds 40 KB+ bundle overhead; ha-* components don't compose cleanly from React |
| Panel framework | Lit 3.x | Vanilla JS | Viable for trivial panels; complex reactive state (schedule grids, person associations) needs Lit's reactive properties |
| Build tool | Vite 5.x | Rollup directly | Vite wraps Rollup with better DX, HMR, and TS support; no reason for raw Rollup |
| Complex data storage | Store helper | ConfigEntry.options only | config_entries registry is not designed for large mutable nested structures |
| Complex data storage | Store helper | SQLite / recorder | Recorder is for time-series telemetry; not the HA pattern |
| Panel communication | hass.connection WebSocket | REST API | WebSocket already established for panel session; REST requires auth token management from JS |
| Python deps | uv | pip / poetry | uv is faster and aligns with current HA core tooling |

---

## Roadmap Implications

- **Phase 1 (Python backend skeleton):** ConfigEntry + ConfigFlow + OptionsFlow + Store can be wired up before any frontend work. The DataUpdateCoordinator is the integration's spine — get this right first.
- **Phase 2 (Climate control logic):** Schedule evaluation engine and the two-call TRV control pattern are self-contained once the coordinator exists.
- **Phase 3 (Frontend panel):** Requires Phase 1 WebSocket API contracts to be defined first. Frontend is a separate build artifact (Vite + Lit + TypeScript) that communicates exclusively over WebSocket.
- **No external PyPI dependencies** in v1 simplifies HACS publishing and HA review significantly.

---

## Open Questions

- `async_register_panel` signature may have changed post-HA 2025.x — verify against HA core source at build time.
- Static file serving from `www/` directory: confirm whether `hass.http.async_register_static_paths` is still required or if placing files in `www/` is auto-detected.
- Vite config for single-file output with Lit 3 external vs. bundled: whether to bundle Lit into `panel.js` or rely on HA's own Lit instance. Bundling is safer (avoids version conflicts) but increases file size.

---

## Sources

- [Config flow | HA Developer Docs](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)
- [Options flow | HA Developer Docs](https://developers.home-assistant.io/docs/config_entries_options_flow_handler/)
- [Fetching data / DataUpdateCoordinator | HA Developer Docs](https://developers.home-assistant.io/docs/integration_fetching_data/)
- [Creating custom panels | HA Developer Docs](https://developers.home-assistant.io/docs/frontend/custom-ui/creating-custom-panels/)
- [Extending the WebSocket API | HA Developer Docs](https://developers.home-assistant.io/docs/frontend/extending/websocket-api/)
- [Climate entity | HA Developer Docs](https://developers.home-assistant.io/docs/core/entity/climate/)
- [Integration manifest | HA Developer Docs](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [HACS Integration publish requirements](https://www.hacs.xyz/docs/publish/integration/)
- [integration_blueprint | ludeeus/integration_blueprint](https://github.com/ludeeus/integration_blueprint)
