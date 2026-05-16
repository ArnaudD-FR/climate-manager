# Phase 1: Foundation - Research

**Researched:** 2026-05-16
**Domain:** Home Assistant custom integration scaffold — ConfigEntry, ConfigFlow, Store, area/entity registry discovery, TRV service calls, pytest-homeassistant-custom-component
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Start from `ludeeus/integration_blueprint` as the structural reference — correct file layout, pytest scaffold. Strip GitHub Actions CI and anything not needed for local development.
- **D-02:** Flat repo layout — `custom_components/climate_manager/` at the repo root alongside `.planning/`, `specs.md`, and `frontend/` (future).
- **D-03:** No GitHub Actions CI in Phase 1 — no publishing planned; CI adds friction with no benefit yet.
- **D-04:** Minimal config flow — single step, pre-filled integration name, user clicks Submit. All real configuration is in the panel (Phase 3).
- **D-05:** Single instance only — `async_setup` must reject a second installation attempt. One climate manager per HA instance.
- **D-06:** `Makefile` for deploy workflow — `make deploy` runs rsync to copy `custom_components/climate_manager/` to the HA host, then SSH-restarts HA with `ha core restart`.
- **D-07:** HA restart triggered via SSH (`ha core restart`) — works with HA OS / supervised.
- **D-08:** `pytest` from day one using `pytest-homeassistant-custom-component` — set up the test harness in Phase 1 even if only a smoke test (integration loads without errors).
- **D-09:** Define the **full schema** in Phase 1 — rooms, persons, global config, time programs, period temperatures. Phase 2 reads/writes to this schema without changes.
- **D-10:** Schema **version field** from day one: `{ "version": 1, ... }`. Enables safe migration if schema changes later.
- **D-11:** **Sparse storage** — only store values that differ from defaults. If a room uses the global time program → nothing stored for that room. If global mode is at its default → nothing stored.
- **D-12:** **Rooms are auto-discovered** — query entity registry for all `climate.*` entities → look up each entity's `area_id` → each HA area with at least one climate entity becomes a managed room.
- **D-13:** **Room ID = HA `area_id`** from the area registry.
- **D-14:** **Persons are auto-discovered** using all `person.*` entities.
- **D-15:** **Person ID = `person.*` entity_id** (e.g., `person.john`).
- **D-16:** No explicit opt-in — all discovered entities are managed. Non-default config is stored; default = nothing stored.
- **D-17:** Rooms tab — rooms with non-default configuration listed first (locked for Phase 3, relevant to data model shape).
- **D-18:** Persons tab — persons with any non-default setting listed first (locked for Phase 3, relevant to data model shape).

### Claude's Discretion

- Integration blueprint cleanup: which blueprint files to keep vs. remove — keep what HA requires, strip CI and anything publishing-specific.
- Exact Makefile targets beyond `deploy`: additional targets (e.g., `make logs`, `make test`) at the implementer's discretion.
- Storage file name: use standard `climate_manager` as the Store key (matches the domain).

### Deferred Ideas (OUT OF SCOPE)

- Auto-restart watcher (watch for file changes and auto-deploy)
- Frontend build step in Makefile (`make build && make deploy`) — relevant in Phase 3 only
- `make logs` target (tail HA logs via SSH)

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Correct HA custom integration structure (manifest.json with required fields, config flow, no external PyPI deps); deploys via SSH/rsync to `/config/custom_components/` | Manifest fields verified against HA dev docs; file structure from integration_blueprint; Makefile deploy pattern confirmed |
| INFRA-02 | All configuration persists across HA restarts (stored via `homeassistant.helpers.storage.Store`) | Store API verified: `async_load` / `async_save`, `serialize_in_event_loop=False` for large objects; migration via `_async_migrate_func` |
| INFRA-04 | TRVs controlled via two sequential service calls: `climate.set_hvac_mode(heat)` then `climate.set_temperature` — auto mode never used | Two-call pattern confirmed in existing STACK.md; service call API unchanged in HA 2025.x |
| ROOM-01 | User can configure rooms; each room has a name and one or more associated HA climate entity IDs | Area registry `async_list_areas()` + entity registry `get_entries_for_area_id()` API confirmed; room storage schema defined in D-09 |
| ROOM-02 | Rooms without a climate entity association are ignored by the system | Discovery filter: areas → only those containing `climate.*` entities pass; verified against entity_registry API |
| ROOM-03 | When a room has multiple TRVs and one becomes unavailable, the system continues sending commands to the remaining available TRVs | Per-entity availability check via `hass.states.get(entity_id).state != "unavailable"` before each service call; ROOM-03 is a runtime guard, Phase 1 only needs the storage model to support multiple entity IDs per room |

</phase_requirements>

---

## Summary

Phase 1 builds the loadable skeleton of the Climate Manager HA integration: the correct HACS-compatible file structure, a minimal single-step config flow, the full two-layer storage schema, auto-discovery of rooms and persons from HA registries, and a verified TRV two-call service sequence. No scheduling logic, no UI panel — only the foundation that Phase 2 and Phase 3 depend on.

The integration blueprint (ludeeus/integration_blueprint) provides the correct scaffold pattern but must be stripped of its GitHub Actions CI, cloud-API coordinator, and username/password config flow. The result is a far simpler structure: `__init__.py`, `config_flow.py`, `const.py`, `storage.py`, `manifest.json`, `hacs.json`, and a `tests/` directory with a smoke test.

The most critical Phase 1 decisions that cannot be changed later are: (1) the full storage schema defined in `storage.py` (Phase 2 reads/writes it without schema changes), (2) `single_config_entry: true` in manifest.json to enforce one-instance-only at the HA level, and (3) the use of `entry.runtime_data` (modern pattern) rather than `hass.data[DOMAIN]` for in-memory state.

**Primary recommendation:** Build in this order: manifest.json → const.py → config_flow.py → storage.py (schema + load/save) → __init__.py (setup_entry wiring) → smoke test → Makefile. Defer the coordinator entirely to Phase 2.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Integration lifecycle (setup/unload) | Python backend (`__init__.py`) | — | HA entry point; all config entry lifecycle lives here |
| Config flow UI (single step) | Python backend (`config_flow.py`) | HA frontend (native UI) | ConfigFlow renders via HA's own flow UI; no custom panel needed |
| Persistent data storage | Python backend (`storage.py`) | HA `.storage/` filesystem | Store helper owns serialization/deserialization |
| Room/person discovery | Python backend (`__init__.py` or `storage.py`) | HA area + entity registry | Registries are the source of truth; integration reads, never writes |
| TRV service calls | Python backend (coordinator, Phase 2) | HA climate domain | `hass.services.async_call` — backend calls HA services directly |
| In-memory runtime state | Python backend (`entry.runtime_data`) | — | Modern pattern replaces `hass.data[DOMAIN]` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12+ | Integration language | HA 2025.x requirement; system Python 3.13 available locally [VERIFIED: bash] |
| `homeassistant.config_entries.ConfigFlow` | HA 2025.x | Initial setup wizard | Required for `config_flow: true` in manifest; renders in HA Integrations UI |
| `homeassistant.config_entries.ConfigEntry` | HA 2025.x | Config persistence + runtime_data carrier | Modern `entry.runtime_data` pattern replaces `hass.data` [VERIFIED: developers.home-assistant.io] |
| `homeassistant.helpers.storage.Store` | HA 2025.x | Complex nested data persistence | Purpose-built for this pattern; `async_load`/`async_save`; migration support [VERIFIED: github.com/home-assistant/core] |
| `homeassistant.helpers.area_registry` | HA 2025.x | Room discovery source of truth | `async_get(hass).async_list_areas()` returns all `AreaEntry` objects [VERIFIED: github.com/home-assistant/core] |
| `homeassistant.helpers.entity_registry` | HA 2025.x | Climate entity → area mapping | `async_get(hass).entities.get_entries_for_area_id(area_id)` filters by area [VERIFIED: github.com/home-assistant/core] |
| `homeassistant.core` (`hass.services.async_call`) | HA 2025.x | TRV service calls | Issues `climate.set_hvac_mode` + `climate.set_temperature` sequentially [VERIFIED: STACK.md] |

### Supporting (Phase 1 toolchain)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-homeassistant-custom-component` | 0.13.316 (latest) | Test harness; provides `hass` fixture | All tests; the only way to test outside HA core [VERIFIED: pip index] |
| `uv` | 0.11.2 (installed) | Python dependency management | `uv venv` + `uv pip install` for dev environment [VERIFIED: bash] |
| `pytest` | 8.3.5 (installed) | Test runner | Already installed; `asyncio_mode = auto` required in config [VERIFIED: bash] |
| `rsync` | system | Deploy to HA host | Already installed; used in Makefile `make deploy` [VERIFIED: bash] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `entry.runtime_data` | `hass.data[DOMAIN]` | `hass.data` is the old pattern; not typed, not auto-cleaned on unload; do not use |
| `Store` for schema | `ConfigEntry.options` only | ConfigEntry.options not designed for large mutable nested objects; corruption risk on concurrent writes |
| `single_config_entry: true` in manifest | `_abort_if_unique_id_configured()` in flow | manifest field is cleaner (HA enforces before flow runs); both work but manifest is preferred |

**Installation (dev environment):**
```bash
uv venv .venv
uv pip install pytest-homeassistant-custom-component pytest-asyncio
```

---

## Architecture Patterns

### System Architecture Diagram

```
HA Startup
    │
    ▼
async_setup_entry (entry: ClimateManagerConfigEntry)
    │
    ├─► area_registry.async_list_areas()
    │       │
    │       └─► entity_registry.get_entries_for_area_id(area_id)
    │               filter: domain == "climate"
    │               → discovered_rooms: {area_id → [entity_ids]}
    │
    ├─► entity_registry.entities (filter: domain == "person")
    │       → discovered_persons: [entity_ids]
    │
    ├─► Store("climate_manager").async_load()
    │       → stored_config (sparse deltas from defaults)
    │       merge: defaults + stored_config = runtime_config
    │
    └─► entry.runtime_data = ClimateManagerData(
                store=Store,
                config=runtime_config,
                discovered_rooms=...,
                discovered_persons=...
            )

TRV Service Call (Phase 2 coordinator, but pattern locked in Phase 1)
    │
    ├─► hass.services.async_call("climate", "set_hvac_mode",
    │       {"entity_id": entity_id, "hvac_mode": "heat"}, blocking=True)
    │
    └─► hass.services.async_call("climate", "set_temperature",
            {"entity_id": entity_id, "temperature": target_temp}, blocking=True)

async_unload_entry
    └─► hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        (no scheduled callbacks in Phase 1 — coordinator not yet started)
```

### Recommended Project Structure

```
custom_components/
└── climate_manager/
    ├── __init__.py          # async_setup_entry, async_unload_entry, type alias
    ├── config_flow.py       # ClimateManagerFlowHandler (single step, single instance)
    ├── const.py             # DOMAIN, STORAGE_KEY, STORAGE_VERSION, DEFAULT_* constants
    ├── storage.py           # ClimateManagerStore: load, save, schema, defaults merge
    ├── manifest.json        # domain, name, version, iot_class, config_flow, single_config_entry
    └── hacs.json            # name, zip_release
tests/
├── conftest.py              # enable_custom_integrations fixture, asyncio_mode config
└── test_init.py             # smoke test: integration loads without errors
Makefile                     # make deploy, make test
pyproject.toml               # pytest asyncio_mode = auto
```

**Note:** No `coordinator.py`, `scheduler.py`, `presence.py`, or `websocket.py` in Phase 1. These are Phase 2/3 artifacts.

### Pattern 1: Minimal Single-Instance Config Flow

**What:** A one-step config flow that creates the entry immediately, with `single_config_entry: true` in manifest preventing a second instance before the flow even runs.
**When to use:** Every integration that has exactly one logical instance per HA installation.

```python
# Source: developers.home-assistant.io/docs/config_entries_config_flow_handler + manifest pattern
# config_flow.py
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from .const import DOMAIN

class ClimateManagerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Climate Manager."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(
                title="Climate Manager",
                data={},
            )
        return self.async_show_form(step_id="user")
```

```json
// manifest.json — single_config_entry enforces one instance at HA level
{
  "domain": "climate_manager",
  "name": "Climate Manager",
  "version": "1.0.0",
  "config_flow": true,
  "single_config_entry": true,
  "iot_class": "local_push",
  "codeowners": ["@arnaud"],
  "documentation": "",
  "issue_tracker": "",
  "requirements": []
}
```

### Pattern 2: Modern `entry.runtime_data` for In-Memory State

**What:** Store coordinator + store instance in `entry.runtime_data` using a typed dataclass, replacing the old `hass.data[DOMAIN]` pattern.
**When to use:** All modern HA integrations (current blueprint standard since April 2024).

```python
# Source: developers.home-assistant.io/blog/2024/04/30/store-runtime-data-inside-config-entry/
# __init__.py
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .storage import ClimateManagerStore

@dataclass
class ClimateManagerData:
    store: ClimateManagerStore
    runtime_config: dict  # defaults merged with stored sparse data

type ClimateManagerConfigEntry = ConfigEntry[ClimateManagerData]

async def async_setup_entry(hass: HomeAssistant, entry: ClimateManagerConfigEntry) -> bool:
    store = ClimateManagerStore(hass)
    runtime_config = await store.async_load()
    entry.runtime_data = ClimateManagerData(store=store, runtime_config=runtime_config)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ClimateManagerConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

### Pattern 3: Store with Schema Version and Sparse Defaults

**What:** `Store` initialized with `version=1`, loaded data merged with defaults at read time. Only non-default values are written.
**When to use:** All persistent data in this integration (rooms, persons, global config).

```python
# Source: github.com/home-assistant/core/blob/dev/homeassistant/helpers/storage.py
# storage.py
from homeassistant.helpers.storage import Store
from homeassistant.core import HomeAssistant
from .const import STORAGE_KEY, STORAGE_VERSION, DEFAULT_CONFIG

class ClimateManagerStore:
    def __init__(self, hass: HomeAssistant) -> None:
        self._store = Store(
            hass,
            version=STORAGE_VERSION,  # 1
            key=STORAGE_KEY,           # "climate_manager"
            serialize_in_event_loop=False,  # offload JSON serialization for large objects
        )

    async def async_load(self) -> dict:
        data = await self._store.async_load()
        if data is None:
            return dict(DEFAULT_CONFIG)  # fresh install: all defaults
        return {**DEFAULT_CONFIG, **data}  # sparse merge: stored values override defaults

    async def async_save(self, config: dict) -> None:
        await self._store.async_save(config)
```

### Pattern 4: Area + Entity Registry Discovery

**What:** On setup, query area registry for all areas, then filter entity registry by `area_id` and `domain == "climate"`. Areas with no climate entities are silently ignored (ROOM-02).
**When to use:** `async_setup_entry`, before coordinator starts.

```python
# Source: github.com/home-assistant/core/blob/dev/homeassistant/helpers/area_registry.py
#         github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity_registry.py
from homeassistant.helpers import area_registry as ar, entity_registry as er

async def discover_rooms(hass) -> dict[str, list[str]]:
    """Return {area_id: [climate_entity_ids]} for areas with >= 1 climate entity."""
    area_reg = ar.async_get(hass)
    entity_reg = er.async_get(hass)
    rooms = {}
    for area in area_reg.async_list_areas():
        climate_entries = [
            entry for entry in entity_reg.entities.get_entries_for_area_id(area.id)
            if entry.domain == "climate"
        ]
        if climate_entries:
            rooms[area.id] = [e.entity_id for e in climate_entries]
    return rooms

async def discover_persons(hass) -> list[str]:
    """Return all person.* entity_ids."""
    entity_reg = er.async_get(hass)
    return [
        entry.entity_id
        for entry in entity_reg.entities.values()
        if entry.domain == "person"
    ]
```

### Pattern 5: Two-Call TRV Service Sequence

**What:** Enforce heat mode first, then set temperature. Both calls use `blocking=True`. Never use auto mode.
**When to use:** Every time a TRV temperature is programmatically set (Phase 2 coordinator).

```python
# Source: .planning/research/STACK.md (verified against HA docs)
async def set_trv_temperature(hass, entity_id: str, temperature: float) -> None:
    """Issue two-call sequence: set_hvac_mode(heat) then set_temperature."""
    state = hass.states.get(entity_id)
    if state is None or state.state == "unavailable":
        return  # ROOM-03: silently skip unavailable TRVs
    await hass.services.async_call(
        "climate", "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": "heat"},
        blocking=True,
    )
    await hass.services.async_call(
        "climate", "set_temperature",
        {"entity_id": entity_id, "temperature": temperature},
        blocking=True,
    )
```

### Pattern 6: pytest Smoke Test Setup

**What:** Minimal conftest.py and smoke test that verifies the integration loads without errors.
**When to use:** Phase 1 test scaffold; extended in Phase 2 with logic tests.

```python
# Source: github.com/MatthewFlamm/pytest-homeassistant-custom-component README

# tests/conftest.py
import pytest

# pytest-homeassistant-custom-component provides `hass` and `enable_custom_integrations` automatically.
# No additional conftest fixtures needed for Phase 1 smoke test.

# tests/test_init.py
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.climate_manager.const import DOMAIN

async def test_setup_entry(hass, enable_custom_integrations):
    """Integration loads without errors."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state.value == "loaded"
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Anti-Patterns to Avoid

- **`hass.data[DOMAIN]` for storage:** In-memory only, lost on restart, not typed. Use `entry.runtime_data` for runtime state and `Store` for persistence.
- **Direct file I/O in async functions:** `open()`, `json.load()` in `async def` blocks the HA event loop. HA 2025+ detects this and crashes the integration. Use `Store` exclusively.
- **Storing schedule data in `ConfigEntry.options`:** Designed for immutable or simple UI-editable settings, not large mutable nested objects. Concurrent writes risk corruption.
- **`async_get_registry()` (deprecated):** Use `ar.async_get(hass)` and `er.async_get(hass)` — the old method was removed in HA 2024/2025.
- **`async_track_state_change` (deprecated):** Removed in HA 2025.5. Use `async_track_state_change_event` instead. (Not needed in Phase 1, but flag for Phase 2.)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON persistence with restarts | Custom file I/O | `homeassistant.helpers.storage.Store` | Handles async serialization, versioning, migration, atomic writes |
| Single-instance enforcement | Custom check in flow | `"single_config_entry": true` in manifest.json | HA enforces before flow runs; no code path to test |
| Test environment setup | Custom HA mock | `pytest-homeassistant-custom-component` | Extracts real HA test plugins; `hass` fixture is production-identical |
| Area listing | Custom entity scanning | `area_registry.async_get(hass).async_list_areas()` | Registry is authoritative; scanning states misses entities not yet loaded |
| Entity-to-area mapping | Custom lookup table | `entity_registry.entities.get_entries_for_area_id(area_id)` | Built-in indexed lookup; O(1) per area |

**Key insight:** HA's registry APIs are indexed and authoritative. Hand-rolling area/entity discovery via state scanning is fragile (entities may not be loaded at setup time) and slower.

---

## Common Pitfalls

### Pitfall 1: Missing `async_unload_entry`
**What goes wrong:** HACS / HA quality checker require `async_unload_entry` in `__init__.py`. Without it, HA marks the integration as non-reloadable and displays warnings. In Phase 1 with no platform entities and no scheduled callbacks, it's a trivial one-liner — but it must exist. [CITED: .planning/research/PITFALLS.md, M1]
**Why it happens:** Developers focus on setup and forget teardown.
**How to avoid:** Add it in Wave 0 before anything else.
**Warning signs:** HA logs `Integration does not support unloading` on reload.

### Pitfall 2: Blocking I/O in `async_setup_entry`
**What goes wrong:** Any synchronous file read or CPU-heavy operation in `async def` blocks the HA event loop. HA 2025+ detects and logs this; it can cause integration crash. [CITED: .planning/research/PITFALLS.md, C5]
**Why it happens:** `Store.async_load()` is correct but any direct `open()` is not.
**How to avoid:** Use `Store` for all persistence. Never call `json.load()` or file I/O directly. Set `serialize_in_event_loop=False` on the Store for large nested objects.
**Warning signs:** `RuntimeWarning: Detected blocking call` in HA logs.

### Pitfall 3: Schema stored in `ConfigEntry.options` instead of `Store`
**What goes wrong:** Rooms and persons schema is large and frequently mutated by the panel (Phase 3). `ConfigEntry.options` is designed for small UI-editable settings and triggers a full reload on every change. [CITED: .planning/research/PITFALLS.md, m4]
**Why it happens:** `ConfigEntry` is familiar and simple; `Store` requires extra wiring.
**How to avoid:** Schema goes in `storage.py` using `Store`. `ConfigEntry.data` holds only the integration name (empty for this integration). `ConfigEntry.options` may hold nothing or a simple "enabled" flag at most.
**Warning signs:** HA reloads the integration on every user action in the panel.

### Pitfall 4: Using deprecated registry API `async_get_registry()`
**What goes wrong:** `async_get_registry()` was deprecated in HA 2023 and removed in HA 2025. Any code using it will fail to import. [VERIFIED: community.home-assistant.io deprecation thread]
**Why it happens:** Old tutorials and Stack Overflow answers still reference the old API.
**How to avoid:** Use `homeassistant.helpers.area_registry.async_get(hass)` and `homeassistant.helpers.entity_registry.async_get(hass)` — both are the current `@callback` singletons.
**Warning signs:** `ImportError: cannot import name 'async_get_registry'` at startup.

### Pitfall 5: `single_config_entry` omitted, relying only on flow abort
**What goes wrong:** Without `"single_config_entry": true` in manifest.json, HA allows the user to start a second config flow. The flow's `_abort_if_unique_id_configured()` would catch it, but the flow runs unnecessarily and the abort reason must be translated. [VERIFIED: developers.home-assistant.io/docs/creating_integration_manifest]
**Why it happens:** Old integrations used the flow-level abort before the manifest field existed.
**How to avoid:** Use both: `"single_config_entry": true` in manifest (HA-level gate) AND a stable unique ID set in the flow (defense in depth for older HA versions).
**Warning signs:** The "Add Integration" button is still shown after first install, allowing a second attempt.

### Pitfall 6: Python 3.13 incompatibility (local dev environment)
**What goes wrong:** Local Python is 3.13.7 but `pytest-homeassistant-custom-component` pins to the HA Python version. If the HA target is Python 3.12, some 3.13-only syntax will work locally but fail on the HA host. [VERIFIED: bash, `python3 --version`]
**Why it happens:** Developer uses system Python, HA uses its own Python version.
**How to avoid:** Use `uv venv --python 3.12` to create the dev venv at the HA target version, not system Python. Keep `pyproject.toml` specifying `python_requires >= "3.12"`.
**Warning signs:** Tests pass locally but integration fails to load on HA.

---

## Code Examples

### Full `const.py`

```python
# Source: pattern from integration_blueprint, schema from CONTEXT.md specifics
DOMAIN = "climate_manager"
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

# Defaults — sparse storage stores only deviations from these
DEFAULT_GLOBAL_MODE = "time_program"
DEFAULT_PERIOD_TEMPERATURES = {
    "frost_protection": 7.0,
    "reduced": 18.0,
    "normal": 20.0,
    "comfort": 22.0,
}
DEFAULT_CONFIG = {
    "version": STORAGE_VERSION,
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": DEFAULT_PERIOD_TEMPERATURES,
    "global_time_program": {"weekday_groups": []},
    "rooms": {},    # {area_id: {time_program: ...}} — empty = all rooms use global
    "persons": {},  # {person.X: {mode: ..., room_ids: [], schedule: ...}} — empty = all default
}
```

### Minimal `manifest.json`

```json
{
  "domain": "climate_manager",
  "name": "Climate Manager",
  "version": "1.0.0",
  "config_flow": true,
  "single_config_entry": true,
  "iot_class": "local_push",
  "codeowners": [],
  "documentation": "",
  "issue_tracker": "",
  "requirements": [],
  "dependencies": []
}
```

### `hacs.json`

```json
{
  "name": "Climate Manager"
}
```

**Note:** `zip_release` is only needed for HACS Default Store submission. Since HACS publishing is out of scope for v1 (D-03), omit it for now.

### Makefile Deploy Target

```makefile
# Source: CONTEXT.md specifics section
HA_USER ?= root
HA_HOST ?= homeassistant.local
HA_COMPONENT_DIR = /config/custom_components/climate_manager
SRC_DIR = custom_components/climate_manager

deploy:
	rsync -av --delete $(SRC_DIR)/ $(HA_USER)@$(HA_HOST):$(HA_COMPONENT_DIR)/
	ssh $(HA_USER)@$(HA_HOST) "ha core restart"

test:
	uv run pytest tests/ -v

.PHONY: deploy test
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hass.data[DOMAIN]` for runtime state | `entry.runtime_data` typed dataclass | April 2024 (HA blog post) | Better type safety, auto-cleanup on unload |
| `async_get_registry()` | `ar.async_get(hass)` / `er.async_get(hass)` | HA 2023/2024 | Old API removed; breaking change |
| `async_track_state_change` | `async_track_state_change_event` | HA 2024 (removed 2025.5) | Phase 2 concern — not needed in Phase 1 |
| OptionsFlow for all config | OptionsFlow + Store (two-layer) | HA 2022+ best practice | Large structured config must go in Store |
| Manual unique_id abort in flow | `"single_config_entry": true` in manifest | HA 2024 | Cleaner gate before flow runs |

**Deprecated/outdated:**
- `hass.data[DOMAIN]`: Still works but generates type checker warnings; replaced by `entry.runtime_data`.
- `async_get_registry()`: Removed — any code using it is broken on HA 2025+.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `entity_registry.entities.get_entries_for_area_id(area_id)` returns entries with a `.domain` attribute usable to filter `climate.*` entities | Pattern 4: Area + Entity Registry Discovery | Discovery loop would need to filter by `entry.entity_id.split(".")[0]` instead — minor code change |
| A2 | `AreaEntry` objects from `async_list_areas()` have `.id` (area_id) and `.name` attributes | Pattern 4 | Attribute names might differ; verify against source at implementation time |
| A3 | `single_config_entry: true` in manifest.json is supported in all HA 2025.x versions | Pattern 1: Config Flow | If not supported in the user's exact HA version, fall back to `_abort_if_unique_id_configured()` in flow only |
| A4 | `serialize_in_event_loop=False` improves performance for the schema size (~few KB) and does not cause thread-safety issues for plain dicts | Pattern 3: Store | Default (`True`) is always safe; switching to `False` is an optimization that requires JSON-serializable data only (plain Python dicts — confirmed by schema shape) |

**Note:** A1 and A2 are easily verified by running a one-time check against the HA registry in the test environment. Recommend adding a unit test in Wave 0 that constructs a mock area + entity and verifies the attribute names.

---

## Open Questions

1. **`AreaEntry.name` vs user-facing room name**
   - What we know: `area_id` is the stable key (D-13); `area.name` is the display name.
   - What's unclear: In the schema, rooms are keyed by `area_id`. When the panel (Phase 3) displays rooms, it needs the human-readable name. Does `storage.py` need to cache `area.name` alongside the stored config, or is it always fetched fresh from the registry at read time?
   - Recommendation: Do not cache area names in the Store — always read from the registry at display time. Store only the `area_id` as the key. This avoids staleness if the user renames an area in HA.

2. **Person display name source**
   - What we know: Person ID = `person.john` entity_id. The display name might be in the entity state attributes.
   - What's unclear: Is `hass.states.get("person.john").attributes.get("friendly_name")` sufficient, or is there a persons registry with richer data?
   - Recommendation: Use `hass.states.get(person_id).attributes.get("friendly_name", person_id)` for display names. This is safe and sufficient for Phase 1.

3. **`RegistryEntry.domain` attribute vs `entity_id` prefix**
   - What we know: The entity registry returns `RegistryEntry` objects. The WebFetch showed a `.domain` field is used internally.
   - What's unclear: Whether `entry.domain` is a public attribute on `RegistryEntry` or whether filtering should use `entry.entity_id.startswith("climate.")`.
   - Recommendation: Use `entry.entity_id.split(".")[0] == "climate"` as the safe fallback. If `entry.domain` exists, prefer it. Verify at implementation time against the installed HA version.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | HA integration runtime | Partial — 3.13 local | 3.13.7 local | Use `uv venv --python 3.12` for dev; HA host has its own Python |
| uv | Dependency management | Yes | 0.11.2 | pip (slower) |
| pytest | Test runner | Yes | 8.3.5 | — |
| pytest-homeassistant-custom-component | Test harness | No (not installed) | 0.13.316 available | Must install via `uv pip install` |
| rsync | Makefile deploy | Yes | system | scp (slower) |
| ssh | HA restart trigger | Yes | system | — |

**Missing dependencies with no fallback:**
- `pytest-homeassistant-custom-component` — must be installed before tests can run. Wave 0 task: `uv pip install pytest-homeassistant-custom-component`.

**Missing dependencies with fallback:**
- System Python is 3.13, but `uv venv --python 3.12` solves this cleanly for dev.

---

## Security Domain

Phase 1 has no network-exposed endpoints, no authentication flows, no user input processing beyond the config flow (which accepts no user data — single click Submit). The TRV service calls go to local HA services over the event bus, not over a network.

Applicable ASVS categories for Phase 1:

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Config flow has no credentials |
| V3 Session Management | No | No user sessions in Phase 1 |
| V4 Access Control | No | HA handles integration access control natively |
| V5 Input Validation | Minimal | Config flow has no user-provided fields; no validation needed |
| V6 Cryptography | No | No secrets, no encryption in Phase 1 |

The primary security concern for this phase is **code quality** (no blocking I/O, no hass.data leaks) rather than authentication or access control. These become relevant in Phase 3 when the WebSocket API is introduced.

---

## Sources

### Primary (HIGH confidence)
- github.com/home-assistant/core/blob/dev/homeassistant/helpers/area_registry.py — `AreaEntry` fields, `async_list_areas()`, `async_get()` signature
- github.com/home-assistant/core/blob/dev/homeassistant/helpers/entity_registry.py — `get_entries_for_area_id()`, `get_entries_for_config_entry_id()`, entity registry structure
- github.com/home-assistant/core/blob/dev/homeassistant/helpers/storage.py — `Store.__init__()` signature, `async_load`, `async_save`, `serialize_in_event_loop`
- developers.home-assistant.io/blog/2024/04/30/store-runtime-data-inside-config-entry/ — `entry.runtime_data` pattern, TypeAlias, dataclass
- developers.home-assistant.io/docs/config_entries_config_flow_handler/ — ConfigFlow pattern, unique_id, `_abort_if_unique_id_configured`
- developers.home-assistant.io/docs/config_entries_options_flow_handler/ — OptionsFlow pattern (Phase 1 not using, but confirmed)
- developers.home-assistant.io/docs/creating_integration_manifest/ — `single_config_entry`, `integration_type`, required fields
- github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/README.md — test setup, `enable_custom_integrations` fixture, `asyncio_mode`
- pip index versions result — `pytest-homeassistant-custom-component` 0.13.316 is latest [VERIFIED]
- bash environment checks — uv 0.11.2, Python 3.13.7, pytest 8.3.5, rsync/ssh available [VERIFIED]

### Secondary (MEDIUM confidence)
- github.com/ludeeus/integration_blueprint — manifest.json fields, `__init__.py` structure, `entry.runtime_data` usage, `async_unload_entry` pattern (confirmed via WebFetch)
- .planning/research/STACK.md — two-call TRV service pattern, storage two-layer design, frontend registration (pre-existing project research)
- .planning/research/ARCHITECTURE.md — component map, layer diagram, data model shape
- .planning/research/PITFALLS.md — C5 blocking I/O, M1 HACS structure, M5 ghost listeners

### Tertiary (LOW confidence — flag for validation)
- community.home-assistant.io deprecation thread — `async_get_registry()` removal timeline (mentioned as deprecated; removal version not precisely verified)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all APIs verified against current HA core source on GitHub
- Architecture: HIGH — patterns confirmed against official HA developer docs and current blueprint
- Pitfalls: HIGH for structural (M1, C5), MEDIUM for registry API deprecation timeline
- Environment: HIGH — verified via bash

**Research date:** 2026-05-16
**Valid until:** 2026-06-16 (HA APIs are stable within minor versions; `pytest-homeassistant-custom-component` version may advance)
