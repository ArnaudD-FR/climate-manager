---
phase: 01-foundation
reviewed: 2026-05-16T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - custom_components/climate_manager/__init__.py
  - custom_components/climate_manager/config_flow.py
  - custom_components/climate_manager/const.py
  - custom_components/climate_manager/discovery.py
  - custom_components/climate_manager/hacs.json
  - custom_components/climate_manager/manifest.json
  - custom_components/climate_manager/storage.py
  - custom_components/climate_manager/trv.py
  - tests/conftest.py
  - tests/test_discovery.py
  - tests/test_init.py
  - tests/test_storage.py
  - tests/test_trv.py
  - Makefile
  - pyproject.toml
  - .gitignore
findings:
  critical: 3
  warning: 5
  info: 3
  total: 11
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-16T00:00:00Z **Depth:** standard **Files Reviewed:** 16
**Status:** issues_found

## Summary

The Phase 1 foundation skeleton is lean and well-structured. The integration
entry point, config flow, storage layer, discovery helpers, and TRV control
helper are all logically sound. The test suite covers the key behaviours and the
TDD intent is clear throughout.

Three BLOCKER-level issues were identified: the storage merge logic silently
drops the stored schema version field (a latent data-corruption risk); disabled
entities are included in discovery without filtering (correctness gap); and the
test state-comparison for `runtime_config` will silently pass even when the
stored `version` field diverges from `DEFAULT_CONFIG["version"]` due to the
merge overwrite. Five warnings cover the conftest fixture yield gap, missing
`pytest_plugins` declaration, the Makefile `ha core restart` race, an
underscore-access of a private attribute in a test, and the missing
`minor_version` on the Store constructor. Three info items cover the string
comparison for entity domain filtering, empty `documentation`/`issue_tracker`
fields in the manifest, and the `entry.state.value == "loaded"` string
comparison that is more fragile than enum comparison.

## Critical Issues

### CR-01: Storage merge overwrites stored `version` with DEFAULT_CONFIG `version`, silently masking future schema mismatches

**File:** `custom_components/climate_manager/storage.py:53-55`

**Issue:** `async_load` builds `result = copy.deepcopy(DEFAULT_CONFIG)` and then
calls `result.update(stored)`. `DEFAULT_CONFIG` contains
`"version": STORAGE_VERSION`. If a stored file from a future schema version (say
version 2) is loaded by code that is still at version 1, the stored
`"version": 2` key _wins_ and overwrites the default — that part is fine. But
the inverse is also true: if a stored file has no `"version"` key (e.g. written
by a pre-versioned snapshot), the default version silently wins and the data is
treated as current-schema even if it is not. More critically, the
`DEFAULT_CONFIG` dict includes `"version": STORAGE_VERSION`, which means the
merged result always carries the _code's_ version — not what was actually
written to disk. When HA's `Store` handles schema migration it already manages
the version field internally. Embedding `"version"` inside the user-facing
config dict creates a second, desynchronised version field that will cause
confusion as soon as a migration is needed. The `version` field should be
removed from `DEFAULT_CONFIG` and from the merged runtime config; it belongs
solely to the `Store` constructor arguments.

**Fix:**

```python
# const.py — remove "version" from DEFAULT_CONFIG
DEFAULT_CONFIG: dict = {
    # "version" removed: this is managed by Store(version=STORAGE_VERSION),
    # not stored inside the config payload itself.
    "global_mode": DEFAULT_GLOBAL_MODE,
    "period_temperatures": { ... },
    "global_time_program": {"weekday_groups": []},
    "rooms": {},
    "persons": {},
}
```

### CR-02: `discover_rooms` and `discover_persons` include disabled entities

**File:** `custom_components/climate_manager/discovery.py:35-39`, `55-58`

**Issue:** Both discovery functions iterate over all entity registry entries and
filter only by domain prefix. They do not check `entry.disabled_by`. An entity
that a user has disabled in HA (via Settings → Entities) will still appear in
`rooms` and `persons`. Calling `hass.services.async_call` on a disabled climate
entity raises a `ServiceNotFound` or produces a silent no-op depending on HA
version, but more importantly, presenting disabled entities as managed
rooms/persons is semantically wrong — the user explicitly removed them from
active management. The fix is a one-line guard in each list comprehension.

**Fix:**

```python
# discovery.py — discover_rooms, line 35-39
climate_entity_ids = [
    entry.entity_id
    for entry in entity_reg.entities.get_entries_for_area_id(area.id)
    if entry.entity_id.split(".")[0] == "climate"
    and entry.disabled_by is None   # exclude disabled entities
]

# discovery.py — discover_persons, line 55-58
return [
    entry.entity_id
    for entry in entity_reg.entities.values()
    if entry.entity_id.split(".")[0] == "person"
    and entry.disabled_by is None   # exclude disabled entities
]
```

### CR-03: `test_setup_entry_runtime_config_is_default_on_fresh_install` asserts equality with `DEFAULT_CONFIG` which contains a `"version"` key that survives the merge — test will pass for wrong reasons and mask future divergence

**File:** `tests/test_init.py:54`

**Issue:** The test asserts
`entry.runtime_data.runtime_config == DEFAULT_CONFIG`. Because `async_load` on a
fresh install returns `copy.deepcopy(DEFAULT_CONFIG)`, this is trivially true
today. However, once CR-01 is fixed (removing `"version"` from `DEFAULT_CONFIG`)
or if the merge logic changes, this assertion will either break or continue to
pass while hiding a real mismatch. More pressingly, if CR-01 is left unfixed,
the `"version"` key in both sides of the comparison hides the fact that the
stored version field is redundant. The test should assert the _semantically
meaningful_ keys individually rather than doing a full-dict equality against the
mutable constant:

```python
# test_init.py — more robust form
data = entry.runtime_data.runtime_config
assert data["global_mode"] == DEFAULT_GLOBAL_MODE
assert data["period_temperatures"] == DEFAULT_PERIOD_TEMPERATURES
assert data["global_time_program"] == {"weekday_groups": []}
assert data["rooms"] == {}
assert data["persons"] == {}
# "version" key is intentionally NOT asserted here — it lives on the Store,
# not in the runtime config payload.
```

## Warnings

### WR-01: `conftest.py` autouse fixture does not `yield` — fixture return value is lost

**File:** `tests/conftest.py:8-14`

**Issue:** The `auto_enable_custom_integrations` fixture receives the
`enable_custom_integrations` fixture as a parameter (which is how pytest
activates it), but the function body is empty — it has no `yield` or `return`.
While this works because simply _requesting_ `enable_custom_integrations` in the
parameter list is enough to activate it, the pattern is fragile and confusing.
Any future developer reading this code will not understand why the body is empty
and may add a `return` or delete the fixture. The canonical pattern for a
passthrough autouse fixture is to yield the dependency:

```python
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield enable_custom_integrations
```

### WR-02: `pytest_plugins` is not declared — test collection order for `enable_custom_integrations` is non-deterministic

**File:** `tests/conftest.py:1`

**Issue:** `pytest-homeassistant-custom-component` requires
`pytest_plugins = ["pytest_homeassistant_custom_component"]` (or equivalent) to
be declared in `conftest.py` so that its fixtures are registered before test
collection. Without this declaration, the plugin is loaded via the installed
entry-point, which works in a clean venv but can fail silently in environments
where the plugin is not installed as an editable package or where plugin load
order is non-deterministic. The HA integration blueprint and the official docs
both show this declaration as mandatory.

```python
# tests/conftest.py — add at module level
pytest_plugins = ["pytest_homeassistant_custom_component"]
```

### WR-03: Makefile `deploy` target runs `ha core restart` over SSH without waiting — rsync and restart can race

**File:** `Makefile:9-10`

**Issue:** The `deploy` target rsyncs files and immediately triggers
`ha core restart` in a single chained SSH command. If the rsync does not
complete before the restart begins (e.g. on a slow network or when syncing many
files), HA may restart against a partially-transferred `custom_components`
directory. The two operations should be separate SSH calls, or at minimum, rsync
should be confirmed complete before the restart is issued. A `--checksum` or
`--delay-updates` flag on rsync would reduce the window further:

```make
deploy:
	rsync -av --delete --delay-updates $(SRC_DIR)/ $(HA_USER)@$(HA_HOST):$(HA_COMPONENT_DIR)/
	ssh $(HA_USER)@$(HA_HOST) "ha core restart"
```

### WR-04: Test accesses private attribute `store._store` to bypass the public API

**File:** `tests/test_storage.py:41`

**Issue:** `test_load_sparse_stored_data_merges_over_defaults` calls
`store._store.async_save(...)` directly, bypassing `ClimateManagerStore`'s
public `async_save` method. This couples the test to the internal implementation
detail of how the wrapper stores a reference to the underlying `Store` object.
If the attribute is renamed or the wrapper is refactored, the test will break
silently (no runtime error, just a different attribute lookup). The test should
either use `ClimateManagerStore.async_save()` to write the sparse data and then
reload, or document explicitly why the private access is intentional (e.g., to
simulate data written by an older code version):

```python
# Preferred: go through the public API
await store.async_save({"global_mode": "off"})
result = await store.async_load()
# But this writes a full config, not truly sparse.
# If sparse-written data is the intent, document and accept the private access.
```

### WR-05: `Store` constructed without `minor_version` — future minor schema changes cannot be handled without a major version bump

**File:** `custom_components/climate_manager/storage.py:32-36`

**Issue:** The `Store` helper in HA 2024.x+ supports a `minor_version`
constructor argument alongside `version`. Minor version allows backward-
compatible schema additions (e.g., adding a new optional key) to be handled with
`async_migrate_entry` without forcing a full `version` bump that would wipe
stored data for users on older versions. Since the schema will evolve
significantly across phases (adding per-room time programs, person schedules,
etc.), omitting `minor_version=1` now means all future schema evolutions require
a major version bump or no migration at all. This should be added proactively:

```python
self._store = Store(
    hass,
    version=STORAGE_VERSION,
    minor_version=1,
    key=STORAGE_KEY,
)
```

## Info

### IN-01: Domain filtering via `entity_id.split(".")[0]` instead of `entry.domain`

**File:** `custom_components/climate_manager/discovery.py:39`, `58`

**Issue:** The code uses `entry.entity_id.split(".")[0] == "climate"` as the
domain filter and explicitly comments this is to work around potential
`entry.domain` unreliability (Open Question 3 / A1). The comment in the
docstring says this is the "safe primary filter". However,
`RegistryEntry.domain` is a stable attribute in all HA versions the project
targets (2025.x), and the string-split approach is slightly less readable. If
the project team verified `entry.domain` works correctly (A1 confirmed),
consider switching to the cleaner form:

```python
if entry.domain == "climate" and entry.disabled_by is None
```

### IN-02: `manifest.json` has empty `documentation` and `issue_tracker` fields

**File:** `custom_components/climate_manager/manifest.json:9-10`

**Issue:** The `documentation` and `issue_tracker` fields are present but empty
strings. HACS and the HA frontend both display these fields to users. Empty
strings are rendered as blank links. These should either be populated with the
actual GitHub repository URLs or removed (HA allows them to be absent entirely
for custom integrations not targeting the core store).

### IN-03: `test_init.py` asserts `entry.state.value == "loaded"` using a string literal

**File:** `tests/test_init.py:24`

**Issue:** `entry.state` is a `ConfigEntryState` enum. Comparing `.value` to a
raw string `"loaded"` is fragile — if HA ever renames the enum value string
(unlikely but possible), the test silently passes until the rename propagates.
The canonical form uses the enum directly:

```python
from homeassistant.config_entries import ConfigEntryState
assert entry.state == ConfigEntryState.LOADED
```

---

_Reviewed: 2026-05-16T00:00:00Z_ _Reviewer: Claude (gsd-code-reviewer)_ _Depth:
standard_
