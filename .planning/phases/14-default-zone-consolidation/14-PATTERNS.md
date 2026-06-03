# Phase 14: Default Zone Consolidation - Pattern Map

**Mapped:** 2026-06-03
**Files analyzed:** 11 (9 modified, 2 test files)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `custom_components/climate_manager/const.py` | config | transform | itself (schema reshape) | self |
| `custom_components/climate_manager/storage.py` | utility | transform | itself (existing migrations lines 129-169) | self |
| `custom_components/climate_manager/coordinator.py` | service | event-driven | itself (existing `_resolve_zone_config`, `_build_status_payload`) | self |
| `custom_components/climate_manager/websocket.py` | middleware | request-response | itself (existing `set_zone_preheat`, `rename_zone` sentinel pattern) | self |
| `frontend/src/types.ts` | config | transform | itself (`ZoneConfig` interface already at line 90) | self |
| `frontend/src/main.ts` | component | request-response | itself (custom zone tab path lines 521-534) | self |
| `frontend/src/ws-client.ts` | utility | request-response | itself (existing `setZoneMode`, `resetZoneTimeProgram` methods) | self |
| `frontend/src/components/global-settings-tab.ts` | component | request-response | itself (custom zone rows lines 551-561) | self |
| `frontend/src/components/room-card.ts` | component | request-response | itself (existing zone name fallback pattern line 413-422) | self |
| `frontend/src/components/zone-tab.ts` | component | request-response | itself (`zoneConfig.time_program` read at line 284) | self |
| `tests/test_storage.py` | test | — | existing migration tests (lines 120-172) | exact |
| `tests/test_coordinator.py` | test | — | `_make_runtime_config` helper (lines 86-105) | exact |

## Pattern Assignments

### `custom_components/climate_manager/const.py` (config, transform)

**Analog:** Itself — existing `DEFAULT_CONFIG` at line 220; custom zone shape in
comments lines 193-218.

**Current `DEFAULT_CONFIG` keys to replace** (lines 220-238):
```python
# REMOVE these 4 flat keys:
"global_mode": DEFAULT_GLOBAL_MODE,
"global_time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
"default_zone_name": "Home",
# (default_zone_preheat_enabled is absent from DEFAULT_CONFIG already — sparse)

# ADD this single key (D-01):
"default_zone": {
    "name": "Home",
    "mode": DEFAULT_GLOBAL_MODE,
    "time_program": copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
    "preheat_enabled": False,
},
```

**Import pattern** (lines 1-10): no new imports needed — `copy` and
`DEFAULT_GLOBAL_MODE`, `_DEFAULT_DAILY_PROGRAM` already in scope.

**Comment block to update** (lines 215-217): the `# Default Zone is NOT stored
here` paragraph must be revised to say Default Zone is stored under
`default_zone:` key.

---

### `custom_components/climate_manager/storage.py` (utility, transform)

**Analog:** Itself — existing migration blocks at lines 129-170.

**Existing migration pattern to copy** (lines 129-170):
```python
# Pattern: post-merge guard → detect old format → mutate result in-place
# Example from GAP-01 (lines 157-169):
for room_cfg in result.get("rooms", {}).values():
    was_enabled = room_cfg.get("preheat_enabled") is True
    room_cfg.pop("preheat_enabled", None)
    if was_enabled:
        zone_id = room_cfg.get("zone_id")
        if zone_id and zone_id in result.get("zones", {}):
            result["zones"][zone_id]["preheat_enabled"] = True
        else:
            result["default_zone_preheat_enabled"] = True
```

**Insertion point:** After the GAP-01 block (after line 169), before
`return result`. Replace the existing day-fill block (lines 121-127) with the
unified compat shim below.

**Phase 14 compat shim — full pattern** (D-02/D-03, from RESEARCH.md):
```python
# Phase 14 compat shim: promote old flat keys to default_zone sub-dict.
# Guard: old format has global_mode present AND default_zone absent.
# Explicit guard avoids false-positive on new-format configs.
if "global_mode" in result and "default_zone" not in result:
    # Day-fill pass on legacy time_program before absorbing it.
    tp = result.get("global_time_program", {})
    for day, periods in tp.items():
        if not periods:
            tp[day] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM[day])
    result["default_zone"] = {
        "name": result.pop("default_zone_name", "Home"),
        "mode": result.pop("global_mode"),
        "time_program": result.pop(
            "global_time_program",
            copy.deepcopy(_DEFAULT_DAILY_PROGRAM),
        ),
        "preheat_enabled": result.pop(
            "default_zone_preheat_enabled", False
        ),
    }
else:
    # New format: day-fill pass on default_zone["time_program"].
    tp = result.get("default_zone", {}).get("time_program", {})
    for day, periods in tp.items():
        if not periods:
            tp[day] = copy.deepcopy(_DEFAULT_DAILY_PROGRAM[day])
```

**Note:** The existing day-fill block at lines 121-127 (which fills
`global_time_program`) is removed and replaced by the shim above. The shim
covers both the legacy path (fills before absorbing) and the new-format path
(fills directly).

**Const import:** add `_DEFAULT_DAILY_PROGRAM` is already imported (line 24).

---

### `custom_components/climate_manager/coordinator.py` (service, event-driven)

**Analog:** Itself — three sections require changes.

#### Section A: `async_evaluate` — `_last_active_period` block (lines 216-222)

**Current pattern** (lines 216-222):
```python
# Pitfall 7: _last_active_period reflects Default Zone for backward-compat.
global_mode = config["global_mode"]
self._last_active_period = (
    evaluate_schedule(config["global_time_program"], now)
    if global_mode != MODE_OFF
    else None
)
```

**After D-05/Pitfall 6** — reads from `default_zone`:
```python
# D-05: _last_active_period still useful as room fallback; now reads
# from config["default_zone"] (global_mode key no longer exists).
dz = config["default_zone"]
self._last_active_period = (
    evaluate_schedule(dz["time_program"], now)
    if dz["mode"] != MODE_OFF
    else None
)
```

**Also add `_last_zone_periods` population** after the `_last_active_period`
assignment (D-05):
```python
# D-05: per-zone active period dict for _build_status_payload.
# Key "default" mirrors the zone_id="default" sentinel convention.
self._last_zone_periods = {
    "default": (
        evaluate_schedule(dz["time_program"], now)
        if dz["mode"] != MODE_OFF
        else None
    ),
    **{
        zone_id: (
            evaluate_schedule(zone["time_program"], now)
            if zone["mode"] != MODE_OFF
            else None
        )
        for zone_id, zone in config.get("zones", {}).items()
    },
}
```

**Instance variable initialisation** — add to `__init__` near
`_last_active_period` and `_last_room_periods`:
```python
self._last_zone_periods: dict[str, str | None] = {}
```

#### Section B: `_resolve_zone_config` (lines 1315-1335)

**Current pattern** (lines 1315-1335):
```python
def _resolve_zone_config(
    self, area_id: str, config: dict
) -> tuple[str, dict]:
    zone_id = config.get("rooms", {}).get(area_id, {}).get("zone_id")
    if zone_id is None:
        return (config["global_mode"], config["global_time_program"])
    zone = config.get("zones", {}).get(zone_id)
    if zone is None:
        _LOGGER.warning(
            "Room %s has unknown zone_id %r — using Default Zone",
            area_id,
            zone_id,
        )
        return (config["global_mode"], config["global_time_program"])
    return (zone["mode"], zone["time_program"])
```

**After D-04** — both Default Zone return paths read from `config["default_zone"]`:
```python
def _resolve_zone_config(
    self, area_id: str, config: dict
) -> tuple[str, dict]:
    zone_id = config.get("rooms", {}).get(area_id, {}).get("zone_id")
    if zone_id is None:
        dz = config["default_zone"]
        return (dz["mode"], dz["time_program"])
    zone = config.get("zones", {}).get(zone_id)
    if zone is None:
        _LOGGER.warning(
            "Room %s has unknown zone_id %r — using Default Zone",
            area_id,
            zone_id,
        )
        dz = config["default_zone"]
        return (dz["mode"], dz["time_program"])
    return (zone["mode"], zone["time_program"])
```

**Critical:** Both `return` paths for the Default Zone must be updated. Missing
the second (dangling zone_id) causes `KeyError` on deleted zones (Pitfall in
RESEARCH.md).

#### Section C: `_build_status_payload` return dict (lines 1584-1589)

**Current pattern** (lines 1584-1589):
```python
return {
    "global_mode": self._data.runtime_config["global_mode"],
    "active_period": self._last_active_period,
    "present_persons": self._last_present_persons,
    "rooms_status": rooms_status,
}
```

**After D-06** — replaces `global_mode` + `active_period` with `zones` dict:
```python
config = self._data.runtime_config
return {
    "zones": {
        "default": {
            "mode": config["default_zone"]["mode"],
            "active_period": self._last_zone_periods.get("default"),
        },
        **{
            zone_id: {
                "mode": zone["mode"],
                "active_period": self._last_zone_periods.get(zone_id),
            }
            for zone_id, zone in config.get("zones", {}).items()
        },
    },
    "present_persons": self._last_present_persons,
    "rooms_status": rooms_status,
}
```

**`rooms_status` room entry fallback** (line 1514): the existing
`self._last_room_periods.get(area_id, self._last_active_period)` fallback is
unchanged — `_last_active_period` is retained as an instance variable for this
purpose.

---

### `custom_components/climate_manager/websocket.py` (middleware, request-response)

**Analog:** Itself — `set_zone_preheat` sentinel pattern (lines 896-964) and
`set_zone_mode` (lines 850-893) are the primary templates.

#### Section A: `async_register_commands` (lines 86-137)

Remove two registrations:
```python
# REMOVE:
websocket_api.async_register_command(hass, _make_ws_set_global_mode(entry))
# ...
websocket_api.async_register_command(
    hass, _make_ws_reset_time_program(entry)
)
websocket_api.async_register_command(
    hass, _make_ws_reset_room_to_global_program(entry)
)
# ADD in place of _make_ws_reset_room_to_global_program:
websocket_api.async_register_command(
    hass, _make_ws_reset_room_to_default_zone_program(entry)
)
```

#### Section B: `set_global_mode` factory (lines 329-355)

**Remove entirely.** Copy `set_zone_mode`'s success/error pattern when extending
`set_zone_mode` for `zone_id="default"`.

#### Section C: `set_zone_mode` extension (lines 850-893)

**Current** (line 870-879): rejects `zone_id="default"` via `ERR_NOT_FOUND` when
not in `zones` dict.

**After D-08** — add `zone_id="default"` sentinel branch first (T-05-01 pattern,
same as `set_zone_preheat`). Copy the rollback/save/evaluate pattern from
`set_zone_preheat` lines 928-940:
```python
runtime_config = entry.runtime_data.runtime_config
if msg["zone_id"] == "default":
    old_val = runtime_config["default_zone"].get("mode")
    runtime_config["default_zone"]["mode"] = msg["mode"]
    try:
        await entry.runtime_data.store.async_save(runtime_config)
    except Exception as exc:  # noqa: BLE001
        runtime_config["default_zone"]["mode"] = old_val
        connection.send_error(
            msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
        )
        return
else:
    # existing custom zone path — unchanged
    if msg["zone_id"] not in runtime_config.get("zones", {}):
        ...
```

#### Section D: `set_zone_preheat` update (lines 928-940)

**Current** (line 929-930):
```python
old_val = runtime_config.get("default_zone_preheat_enabled")
runtime_config["default_zone_preheat_enabled"] = enabled
```

**After D-11** — write to `default_zone` sub-key:
```python
old_val = runtime_config["default_zone"].get("preheat_enabled")
runtime_config["default_zone"]["preheat_enabled"] = enabled
```

Rollback on line 934 changes accordingly:
```python
runtime_config["default_zone"]["preheat_enabled"] = old_val
```

#### Section E: `rename_zone` update (existing sentinel at line ~815)

**Current** (`zone_id="default"` branch writes `runtime_config["default_zone_name"]`):
```python
# D-11: change to:
runtime_config["default_zone"]["name"] = msg["name"]
```
Rollback similarly targets `runtime_config["default_zone"]["name"]`.

#### Section F: `reset_time_program` factory (lines 662-694)

**Remove entirely** (D-09). The `reset_zone_time_program` with
`zone_id="default"`, `target="default"` replaces it.

#### Section G: `reset_zone_time_program` extension (lines 1086-1141)

**Current** (lines 1110-1116): rejects `zone_id` not in `zones` via
`ERR_NOT_FOUND`. `zone_id="default"` would fall through and get rejected.

**After D-09** — add `zone_id="default"` sentinel branch before the zones dict
check. Copy deepcopy pattern from `target == "default"` branch (lines 1119-1123):
```python
runtime_config = entry.runtime_data.runtime_config
if msg["zone_id"] == "default":
    zones_backup = copy.deepcopy(
        runtime_config.get("default_zone", {})
    )
    if msg["target"] == "default":
        runtime_config["default_zone"]["time_program"] = (
            copy.deepcopy(_DEFAULT_DAILY_PROGRAM)
        )
    else:
        # target == "global" means reset to the Default Zone's own default
        # (after Phase 14 there is no separate "global_time_program").
        # Convention: "global" target for default zone also resets to
        # _DEFAULT_DAILY_PROGRAM (no "other" zone to copy from).
        runtime_config["default_zone"]["time_program"] = (
            copy.deepcopy(_DEFAULT_DAILY_PROGRAM)
        )
    try:
        await entry.runtime_data.store.async_save(runtime_config)
    except Exception as exc:  # noqa: BLE001
        runtime_config["default_zone"] = zones_backup
        connection.send_error(
            msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
        )
        return
else:
    # existing custom zone path unchanged...
```

Note: per D-09, `target="default"` is the canonical reset for Default Zone.
The `vol.In(["default", "global"])` schema allows `"global"` for backward
compat — backend treats both as `_DEFAULT_DAILY_PROGRAM` for Default Zone.

#### Section H: `reset_room_to_global_program` rename (lines 697-729)

**After D-10** — rename factory function and command type string:
```python
# RENAME function to:
def _make_ws_reset_room_to_default_zone_program(entry):

# RENAME command type string (line 700-702):
vol.Required("type"): f"{DOMAIN}/reset_room_to_default_zone_program",

# CHANGE key read (line 721):
# Before:
global_time_program = runtime_config.get("global_time_program", {})
# After:
global_time_program = runtime_config["default_zone"]["time_program"]
```

#### Section I: `create_zone` (line 764)

**Current** seeds new zone time_program from `global_time_program` (line 764):
```python
"time_program": copy.deepcopy(
    runtime_config["global_time_program"]
),
```

**After Phase 14** (Pitfall 1 in RESEARCH.md):
```python
"time_program": copy.deepcopy(
    runtime_config["default_zone"]["time_program"]
),
```

---

### `frontend/src/types.ts` (config, transform)

**Analog:** Itself — `ZoneConfig` interface (lines 90-102) is the shape that
`default_zone` will use.

**`ClimateConfig` interface changes** (lines 104-149):

Remove (D-12):
```typescript
// REMOVE:
global_mode: string;
global_time_program: DailyProgram;
/** D-03: Default Zone display name. Always present in get_config payloads. */
default_zone_name: string;
default_zone_preheat_enabled?: boolean;
```

Add in their place:
```typescript
// ADD (D-12):
/** Phase 14 (D-01): Default Zone stored as first-class ZoneConfig. */
default_zone: ZoneConfig;
```

**`StatusPayload` interface changes** (lines 177-182):

Remove (D-13):
```typescript
// REMOVE:
global_mode: string;
active_period: string | null;
```

Add in their place:
```typescript
// ADD (D-13):
zones: Record<string, { mode: string; active_period: string | null }>;
```

**`ZoneConfig` interface** (lines 90-102): already has `name`, `mode`,
`time_program`, `preheat_enabled`. No changes needed — already the correct shape.

---

### `frontend/src/main.ts` (component, request-response)

**Analog:** Itself — custom zone tab path (lines 521-534) shows the direct
`zoneConfig` passthrough pattern that the Default Zone path will now match.

**Current Default Zone synthesis block** (lines 504-519):
```typescript
// BEFORE (lines 508-513) — constructs ZoneConfig from 4 flat keys:
.zoneConfig=${{
  name: this._config!.default_zone_name,
  mode: this._config!.global_mode,
  time_program: this._config!.global_time_program,
  preheat_enabled: this._config!.default_zone_preheat_enabled ?? false,
}}
```

**After D-14** — pass `config.default_zone` directly:
```typescript
// AFTER — identical to the custom zone path at lines 522-524:
.zoneConfig=${this._config!.default_zone}
```

No other changes in `main.ts` — `_subscribeStatus` (lines 250-261) already
assigns the full `StatusPayload` and `patchConfig` pattern is unchanged.

---

### `frontend/src/ws-client.ts` (utility, request-response)

**Analog:** Itself — `setZoneMode` (lines 122-128) and `resetZoneTimeProgram`
(lines 162-171) already accept `"default"` as `zoneId`.

**Changes (D-08/D-09/D-10/D-16):**

Remove `setGlobalMode()` (lines 38-44):
```typescript
// REMOVE entirely:
setGlobalMode(mode: string): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/set_global_mode",
    mode,
  });
}
```

Remove `resetTimeProgram()` (lines 72-76) — keep only as internal note; the
method was for the global program which no longer has a standalone command:
```typescript
// REMOVE entirely (D-09):
resetTimeProgram(): Promise<{ success: boolean }> { ... }
```

Rename `resetRoomToGlobalProgram` → `resetRoomToDefaultZoneProgram` (lines
173-179):
```typescript
// RENAME method and update command type string:
resetRoomToDefaultZoneProgram(roomId: string): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/reset_room_to_default_zone_program",
    room_id: roomId,
  });
}
```

`setZoneMode("default", mode)` already works — no code change needed in method
body. Only callers change (global-settings-tab, zone-tab).

`resetZoneTimeProgram("default", "default")` already works — no code change
needed in method body. Only callers change.

---

### `frontend/src/components/global-settings-tab.ts` (component, request-response)

**Analog:** Itself — custom zone rows (lines 551-561) already read from
`zone.name` and `zone.mode` directly. Default Zone rows at lines 544-549 are
the analog to update.

**Current Default Zone row construction** (lines 544-549):
```typescript
rows.push({
  id: "default",
  name: this.config.default_zone_name,
  mode: this.status?.global_mode ?? this.config.global_mode,
  activePeriod: this.status?.active_period ?? null,
});
```

**After D-15** — use `default_zone` sub-key and `zones["default"]` from status:
```typescript
rows.push({
  id: "default",
  name: this.config.default_zone.name,
  mode:
    this.status?.zones?.["default"]?.mode
    ?? this.config.default_zone.mode,
  activePeriod: this.status?.zones?.["default"]?.active_period ?? null,
});
```

**Optional chaining rule** (Pitfall 5 in RESEARCH.md): always use
`status?.zones?.["default"]?.mode` — the middle `?.` on `zones` is mandatory
since `zones` is absent during initial load.

---

### `frontend/src/components/room-card.ts` (component, request-response)

**Analog:** Itself — `_getZoneName()` (lines 413-422) already falls back
through `panelConfig?.zones?.[zoneId]?.name`. Same optional-chaining pattern
applies throughout.

**`_getZoneName()`** (line 416):
```typescript
// BEFORE:
return this.panelConfig?.default_zone_name ?? "Default Zone";
// AFTER (D-15):
return this.panelConfig?.default_zone?.name ?? "Default Zone";
```

**`_renderPeriodBadge()`** (line 459):
```typescript
// BEFORE:
const globalMode =
  this.status?.global_mode ?? this.panelConfig?.global_mode ?? "";
// AFTER (D-15):
const globalMode =
  this.status?.zones?.["default"]?.mode
  ?? this.panelConfig?.default_zone?.mode
  ?? "";
```

**`_renderHeaderStatus()`** (line 505):
```typescript
// BEFORE:
const globalMode =
  this.status?.global_mode ?? this.panelConfig?.global_mode ?? "";
// AFTER (D-15):
const globalMode =
  this.status?.zones?.["default"]?.mode
  ?? this.panelConfig?.default_zone?.mode
  ?? "";
```

**Pattern:** Every occurrence of `panelConfig?.global_mode` →
`panelConfig?.default_zone?.mode`; `status?.global_mode` →
`status?.zones?.["default"]?.mode`.

---

### `frontend/src/components/zone-tab.ts` (component, request-response)

**Analog:** Itself — the component already receives `zoneConfig` as a prop and
reads `this.zoneConfig.time_program` (line 284). The only flat-key reads are
`config.default_zone_name` and `config.global_time_program`.

**`_onResetToGlobal`** (line 268):
```typescript
// BEFORE:
this.panel.showToast(`Reset to ${this.config.default_zone_name}`, false);
// AFTER (D-15):
this.panel.showToast(
  `Reset to ${this.config.default_zone.name}`,
  false,
);
```

**Reset button label** (line 585):
```typescript
// BEFORE:
Reset to ${this.config.default_zone_name}
// AFTER (D-15):
Reset to ${this.config.default_zone.name}
```

**`_onPeriodsChanged`** (line 284): reads `this.zoneConfig.time_program` — no
change needed; `zoneConfig` is the prop passed from `main.ts`.

---

### `tests/test_storage.py` (test)

**Analog:** Existing migration tests (lines 120-172) — each test writes raw
storage via `store._store.async_save({...})` and asserts on `async_load()` result.

**Tests to update:**

`test_load_fresh_install_returns_default_config` (line 17): still passes — asserts
`result == DEFAULT_CONFIG` which will be the new shape after const.py changes.

`test_load_fresh_install_returns_copy_not_same_object` (lines 25-40):
```python
# BEFORE (line 31-32): mutates global_mode
result["global_mode"] = "off"
assert DEFAULT_CONFIG["global_mode"] == "time_program"
# AFTER: mutate default_zone.mode instead
result["default_zone"]["mode"] = "off"
assert DEFAULT_CONFIG["default_zone"]["mode"] == "time_program"
```

`test_load_sparse_stored_data_merges_over_defaults` (lines 43-62):
```python
# BEFORE (line 48): stores old format
await store._store.async_save({"global_mode": "off"})
# result["global_mode"] == "off"
# AFTER: compat shim triggers; assert new location
await store._store.async_save({"global_mode": "off"})
result = await store.async_load()
# Compat shim promotes global_mode → default_zone["mode"]
assert result["default_zone"]["mode"] == "off"
assert "global_mode" not in result
```

`test_load_fresh_install_includes_zones_and_default_zone_name` (line 153):
```python
# BEFORE:
assert "default_zone_name" in result
assert result["default_zone_name"] == "Home"
# AFTER (D-01):
assert "default_zone" in result
assert result["default_zone"]["name"] == "Home"
assert result["default_zone"]["mode"] == "time_program"
```

`test_load_v10_data_without_zones_gets_defaults` (line 163):
```python
# BEFORE (line 172): asserts flat key
assert result["global_mode"] == "off"
# AFTER: compat shim absorbs global_mode
assert result["default_zone"]["mode"] == "off"
assert "global_mode" not in result
```

**New compat shim tests to add** (Wave 0 per RESEARCH.md):
```python
async def test_load_legacy_flat_keys_builds_default_zone(hass):
    """Phase 14 compat shim: old format with global_mode is promoted."""
    store = ClimateManagerStore(hass)
    await store._store.async_save({
        "global_mode": "off",
        "global_time_program": {d: [] for d in DAYS},
        "default_zone_name": "Maison",
        "default_zone_preheat_enabled": True,
    })
    result = await store.async_load()
    assert result["default_zone"]["mode"] == "off"
    assert result["default_zone"]["name"] == "Maison"
    assert result["default_zone"]["preheat_enabled"] is True
    assert "global_mode" not in result
    assert "global_time_program" not in result
    assert "default_zone_name" not in result

async def test_load_new_format_reads_default_zone_directly(hass):
    """Phase 14: new format with default_zone key loads without shim."""
    store = ClimateManagerStore(hass)
    await store._store.async_save({
        "default_zone": {
            "name": "Home",
            "mode": "time_program",
            "time_program": {d: [] for d in DAYS},
            "preheat_enabled": False,
        }
    })
    result = await store.async_load()
    assert result["default_zone"]["mode"] == "time_program"
    assert "global_mode" not in result
```

---

### `tests/test_coordinator.py` (test)

**Analog:** `_make_runtime_config` helper (lines 86-105) — used as fixture
throughout. All 40+ usages downstream read `config["global_mode"]` or
`config["global_time_program"]`.

**`_make_runtime_config` new signature** (lines 86-105):
```python
def _make_runtime_config(
    default_zone_mode: str = MODE_TIME_PROGRAM,  # renamed from global_mode
    daily_program: dict | None = None,
    rooms_config: dict | None = None,
    persons_config: dict | None = None,
    zones_config: dict | None = None,
) -> dict:
    """Build a runtime_config dict suitable for coordinator tests."""
    return {
        "version": 2,
        "default_zone": {
            "name": "Home",
            "mode": default_zone_mode,
            "time_program": daily_program
            if daily_program is not None
            else ALL_DAYS_NORMAL_PROGRAM,
            "preheat_enabled": False,
        },
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "rooms": rooms_config or {},
        "persons": persons_config or {},
        "zones": zones_config or {},
    }
```

**Call-site updates:** All existing `_make_runtime_config(global_mode=X)` calls
become `_make_runtime_config(default_zone_mode=X)`.

**Status payload assertions** — any test asserting `result["global_mode"]`
or `event.data["global_mode"]` must change to
`result["zones"]["default"]["mode"]`.

---

## Shared Patterns

### `zone_id="default"` Sentinel — T-05-01 pattern

**Source:** `custom_components/climate_manager/websocket.py` lines 928-940
(`set_zone_preheat` Default Zone branch)

**Apply to:** `set_zone_mode` extension (D-08), `reset_zone_time_program`
extension (D-09), `set_zone_preheat` update (D-11), `rename_zone` update (D-11)

```python
# T-05-01: sentinel-first — check "default" BEFORE zones dict lookup.
# Default Zone never appears in zones{} (sparse model, D-06).
if msg["zone_id"] == "default":
    old_val = runtime_config["default_zone"].get("<key>")
    runtime_config["default_zone"]["<key>"] = msg["<value>"]
    try:
        await entry.runtime_data.store.async_save(runtime_config)
    except Exception as exc:  # noqa: BLE001
        runtime_config["default_zone"]["<key>"] = old_val
        connection.send_error(
            msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc)
        )
        return
else:
    if msg["zone_id"] not in runtime_config.get("zones", {}):
        connection.send_error(
            msg["id"],
            websocket_api.ERR_NOT_FOUND,
            f"Zone {msg['zone_id']!r} not found",
        )
        return
    # ... zones[zone_id] mutation ...
connection.send_result(msg["id"], {"success": True})
hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
```

### Write-Then-Evaluate Pattern

**Source:** `custom_components/climate_manager/websocket.py` lines 880-891
(`set_zone_mode` custom zone branch)

**Apply to:** Every mutating WS handler in Phase 14 changes.

```python
# Write-then-evaluate: persist → ack → background re-evaluate.
# Never await async_evaluate() — it's fire-and-forget.
await entry.runtime_data.store.async_save(runtime_config)
connection.send_result(msg["id"], {"success": True})
hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
```

### `copy.deepcopy` for Time Programs

**Source:** `custom_components/climate_manager/websocket.py` lines 1119-1123
(`reset_zone_time_program` target="default" branch)

**Apply to:** All time_program assignments in storage shim and websocket handlers.

```python
# Always deepcopy when seeding or resetting time programs.
# Prevents runtime_config from sharing references with module constants.
runtime_config["default_zone"]["time_program"] = (
    copy.deepcopy(_DEFAULT_DAILY_PROGRAM)
)
```

### Frontend Optional-Chaining Fallback

**Source:** `frontend/src/components/global-settings-tab.ts` line 547
(existing `?? this.config.global_mode` fallback)

**Apply to:** All components reading `default_zone` mode/active_period from
status.

```typescript
// status?.zones is absent during initial load before first push.
// Three levels of optional chaining are MANDATORY (Pitfall 5).
const defaultZoneMode =
  this.status?.zones?.["default"]?.mode
  ?? this.config?.default_zone?.mode
  ?? "";
```

## No Analog Found

All files to be modified have existing analogs within themselves. No file
requires patterns from RESEARCH.md code examples exclusively — all patterns
are grounded in existing codebase code.

## Critical Anti-Patterns

The following are pitfalls documented in RESEARCH.md with specific line numbers
to verify before closing each task:

| Anti-Pattern | Grep to run after change | Expected result |
|---|---|---|
| `global_time_program` still referenced | `grep -n "global_time_program" websocket.py` | 0 matches |
| `global_mode` still referenced | `grep -n '"global_mode"' websocket.py coordinator.py` | 0 matches |
| `default_zone_name` still referenced | `grep -rn "default_zone_name" frontend/src/` | 0 matches |
| `status?.global_mode` still referenced | `grep -rn "global_mode" frontend/src/` | 0 matches |
| `status?.active_period` (top-level) still referenced | `grep -rn "active_period" frontend/src/` | only `active_period` inside `zones["default"]` and `rooms_status` |
| `resetRoomToGlobalProgram` still called | `grep -rn "resetRoomToGlobal" frontend/src/` | 0 matches |
| `setGlobalMode` still called | `grep -rn "setGlobalMode" frontend/src/` | 0 matches |

## Metadata

**Analog search scope:** `custom_components/climate_manager/`, `frontend/src/`,
`tests/`
**Files scanned:** 11 source files (full reads), 3 targeted section reads in
coordinator.py and websocket.py
**Pattern extraction date:** 2026-06-03
