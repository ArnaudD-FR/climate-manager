# Phase 15: Remove Room-Level Mode Override - Pattern Map

**Mapped:** 2026-06-04
**Files analyzed:** 10 (7 modified, 3 test files cleaned)
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `custom_components/climate_manager/const.py` | config | — | self (deletion only) | exact |
| `custom_components/climate_manager/storage.py` | utility | batch | `storage.py` GAP-01 shim + Phase 14 shim (lines 148–198) | exact |
| `custom_components/climate_manager/coordinator.py` | service | event-driven | `coordinator.py` zone MODE_OFF branch (lines 392–402) | exact |
| `custom_components/climate_manager/websocket.py` | middleware | request-response | `websocket.py` GAP-01 silent-drop at line 374 | exact |
| `frontend/src/types.ts` | model | — | self (field deletion) | exact |
| `frontend/src/components/room-card.ts` | component | request-response | `room-card.ts` zone-badge and period-badge blocks | exact |
| `frontend/src/ws-client.ts` | utility | request-response | `ws-client.ts` `resetZoneTimeProgram()` method (lines 143–156) | exact |
| `tests/test_storage.py` | test | batch | `test_storage.py` Phase 14 shim test (lines 304–345) | exact |
| `tests/test_coordinator.py` | test | event-driven | self (deletion + import cleanup) | exact |
| `tests/test_websocket.py` | test | request-response | `test_websocket.py` `test_ws_reset_room_to_global_program_is_removed` (lines 512–530) | exact |

---

## Pattern Assignments

### `custom_components/climate_manager/const.py` (config, deletion)

**Analog:** self — lines 49–52

**Pattern — block to delete entirely** (lines 49–52):
```python
# ---------------------------------------------------------------------------
# Per-room mode constants (D-20)
# ---------------------------------------------------------------------------

ROOM_MODE_GLOBAL = "global"
ROOM_MODE_FROST = "frost_protection"
ROOM_MODE_CUSTOM = "custom"
```

Delete the section header comment and all three constants. No replacement.
The comment on line 37 referencing `(D-20)` in the presence section header is
unrelated and stays.

---

### `custom_components/climate_manager/storage.py` (utility, batch)

**Analog — GAP-01 shim** (`storage.py` lines 148–161):
```python
# GAP-01 (Phase 12): migrate preheat_enabled from per-room to
# per-zone scope.  Unconditionally pop the deprecated room key so it
# never silently re-gates behaviour after upgrade (T-12-13).
for room_cfg in result.get("rooms", {}).values():
    was_enabled = room_cfg.get("preheat_enabled") is True
    room_cfg.pop("preheat_enabled", None)
    if was_enabled:
        zone_id = room_cfg.get("zone_id")
        if zone_id and zone_id in result.get("zones", {}):
            result["zones"][zone_id]["preheat_enabled"] = True
        else:
            result["default_zone"]["preheat_enabled"] = True
```

**Phase 15 shim to insert** — after the Phase 14 `else:` day-fill block
(after line 198), before `return result`:
```python
# Phase 15 compat shim (D-01/D-03): strip room_mode and time_program
# from all room records on every load.  Silent — no log emitted (D-02).
# pop() is safe regardless of storage format: absent key → no-op.
# Scope: result.get("rooms", {}) — NOT result.values() (Pitfall 2).
for room_cfg in result.get("rooms", {}).values():
    room_cfg.pop("room_mode", None)
    room_cfg.pop("time_program", None)
```

**Key constraint:** `result.get("rooms", {}).values()` — never
`result.values()`. The latter would strip `time_program` from
`default_zone` and zone entries (Pitfall 2 in RESEARCH.md).

---

### `custom_components/climate_manager/coordinator.py` (service, event-driven)

**Analog — zone MODE_OFF block to keep** (lines 392–402):
```python
zone_mode, zone_time_program = self._resolve_zone_config(
    area_id, config
)

if zone_mode == MODE_OFF:
    # EVAL-01: zone off → frost protection for all rooms in the
    # zone, including those with a custom schedule (SCHED-05 only
    # overrides the schedule selection, not the zone power state).
    desired_temps[area_id] = period_temperatures[
        PERIOD_FROST_PROTECTION
    ]
    room_periods[area_id] = PERIOD_FROST_PROTECTION
    frost_locked_rooms.add(area_id)
    mode_off_rooms.add(area_id)
    continue
```

**Pattern — blocks to delete in `_compute_desired_temps`:**

1. Lines 373–384 — delete `room_mode` preamble and `ROOM_MODE_FROST` branch:
```python
room_config = config.get("rooms", {}).get(area_id, {})
room_mode = room_config.get("room_mode", "global")  # DELETE

if room_mode == ROOM_MODE_FROST:            # DELETE entire block
    desired_temps[area_id] = period_temperatures[
        PERIOD_FROST_PROTECTION
    ]
    room_periods[area_id] = PERIOD_FROST_PROTECTION
    frost_locked_rooms.add(area_id)
    mode_off_rooms.add(area_id)
    continue
```

2. Lines 360–366 — delete docstring bullet points referencing `room_mode`
   priorities (EVAL-05 / SCHED-05):
```
1. frost_protection room_mode — wins unconditionally (EVAL-05 / D-20)
...
3. Custom room schedule (room_mode=custom) — wins over zone schedule
   when the zone is active (SCHED-05 / EVAL-05)
```

3. Lines 404–422 — delete `ROOM_MODE_CUSTOM` block:
```python
if room_mode == ROOM_MODE_CUSTOM:           # DELETE entire block
    room_program = (
        room_config.get("time_program")
        or config["default_zone"]["time_program"]
    )
    period_mode = evaluate_schedule(room_program, now)
    temp = period_temperatures.get(period_mode)
    if temp is None:
        _LOGGER.warning(...)
        continue
    desired_temps[area_id] = temp
    room_periods[area_id] = period_mode
    continue
```

4. Lines 516–519 — delete `ROOM_MODE_CUSTOM` guard in
   `_apply_presence_overrides`:
```python
room_config = config.get("rooms", {}).get(area_id, {})
if room_config.get("room_mode", "global") == ROOM_MODE_CUSTOM:
    # Custom room schedule wins; preserved v1.0 behavior
    continue
```

5. Lines 783–789 — delete in `_async_preheat_room` step 2:
```python
room_cfg_step2 = config.get("rooms", {}).get(area_id, {})
if room_cfg_step2.get("room_mode") == ROOM_MODE_CUSTOM:  # DELETE branch
    tp_step2 = room_cfg_step2.get("time_program") or config.get(
        "default_zone", {}
    ).get("time_program", {})
else:
    _, tp_step2 = self._resolve_zone_config(area_id, config)
```
Replace with:
```python
_, tp_step2 = self._resolve_zone_config(area_id, config)
```

6. Lines 868–874 — delete in `_async_preheat_room` step 4:
```python
room_cfg = config.get("rooms", {}).get(area_id, {})
if room_cfg.get("room_mode") == ROOM_MODE_CUSTOM:  # DELETE branch
    time_program = room_cfg.get("time_program") or config.get(
        "default_zone", {}
    ).get("time_program", {})
else:
    _, time_program = self._resolve_zone_config(area_id, config)
```
Replace with:
```python
_, time_program = self._resolve_zone_config(area_id, config)
```

**After all deletions:** every room reaches `_resolve_zone_config`
unconditionally. The `room_config = config.get("rooms", {}).get(area_id, {})`
line at ~373 is no longer needed in `_compute_desired_temps` — delete it too.

**Import to remove** from `coordinator.py` top-level imports block:
```python
from .const import (
    ...
    ROOM_MODE_CUSTOM,   # DELETE
    ROOM_MODE_FROST,    # DELETE
    ROOM_MODE_GLOBAL,   # DELETE (if imported)
    ...
)
```

---

### `custom_components/climate_manager/websocket.py` (middleware, request-response)

**Analog — GAP-01 silent-drop pattern** (line 374):
```python
# GAP-01: preheat_enabled is no longer a valid room key; silently drop
# it so legacy callers don't persist the deprecated room-level flag.
incoming_config.pop("preheat_enabled", None)
```

**Phase 15 addition in `ws_set_room_config`** — insert immediately after
line 374:
```python
# Phase 15 (D-07): room_mode is no longer a valid room key; silently
# drop it so legacy callers or residual frontend sends don't
# persist the field.
incoming_config.pop("room_mode", None)
```

**Registration line to delete** (line 121):
```python
websocket_api.async_register_command(
    hass, _make_ws_reset_room_to_default_zone_program(entry)
)
```

**Factory function to delete entirely** (lines 550–591):
```python
def _make_ws_reset_room_to_default_zone_program(
    entry: ClimateManagerConfigEntry,
):
    ...
    return ws_reset_room_to_default_zone_program
```

**Module docstring update** — remove `reset_room_to_default_zone_program`
from the command list in the module-level docstring (lines 14–15); add
"Removed in Phase 15" note matching the Phase 14 pattern at lines 35–37:
```python
Removed in Phase 15 (D-06):
- reset_room_to_default_zone_program: rooms no longer have independent
  schedules; all rooms follow their zone exclusively
```

---

### `frontend/src/types.ts` (model, deletion)

**Analog — surviving `RoomConfig` fields** (lines 53–71):
```typescript
/** Per-room configuration stored in ClimateConfig.rooms. */
export interface RoomConfig {
  /**
   * Absent = Default Zone member (D-06); UUID string for custom zone
   * (D-07). Sparse model — never written as null.
   */
  zone_id?: string;
  /**
   * Phase 12 (D-01): maximum lead time the coordinator may use.
   * Sparse — absent means default 120 minutes.
   */
  preheat_max_lead_minutes?: number;
}
```

**Lines to delete** (lines 55–60):
```typescript
  /**
   * Room heating mode (D-20). Absent key implies "global".
   * Legal values: "global" | "frost_protection" | "custom"
   */
  room_mode?: "global" | "frost_protection" | "custom";
  time_program?: DailyProgram | null;
```

Both fields — the JSDoc comment block for `room_mode` and the `time_program`
field — are deleted. `time_program` is only meaningful alongside `room_mode`
(D-13 covers `room_mode`; the research touch point map at line 513 adds
`time_program` deletion).

---

### `frontend/src/components/room-card.ts` (component, request-response)

**Analog — zone-badge block that survives** (lines 1061–1072):
```typescript
<span
  class="zone-badge"
  style=${(() => {
    const c = getZoneColor(this.config?.zone_id);
    return `background:${c.background};color:${c.color};border-color:${c.border}`;
  })()}
  @click=${(e: Event) => {
    e.stopPropagation();
    this.panel.navigateToZone(this.config?.zone_id);
  }}
  >${this._getZoneName()}</span
>
```

**Analog — period badge that survives** (`_renderPeriodBadge()` starting
line 454).

**Deletions in `render()` method:**

1. Lines 1027–1040 — delete computed values:
```typescript
const resolvedMode = this.config?.room_mode ?? "global";

const badgeClass =
  resolvedMode === "frost_protection"
    ? "frost"
    : resolvedMode === "custom"
      ? "custom"
      : "global";
const badgeText =
  resolvedMode === "frost_protection"
    ? "Off"
    : resolvedMode === "custom"
      ? "Custom program"
      : "Zone program";
```

2. Lines 1054–1059 — delete mode badge element:
```typescript
<span
  class="program-badge ${badgeClass}"
  style=${badgeClass === "frost"
    ? `background: ${PERIOD_COLORS.frost_protection}; color: white;`
    : ""}
  >${badgeText}</span
>
```

3. Lines 1085–1118 — delete Mode section (section-label + select-wrapper +
   description call):
```typescript
<!-- 3-way room mode selector (D-20) -->
<div
  class="section-label"
  title="Zone: zone sched. Custom: room sched. Off: frost only."
>
  Mode
</div>
<div class="select-wrapper">
  <select
    class="mode-select"
    .value=${resolvedMode}
    @change=${this._onRoomModeChange}
  >
    <option value="frost_protection" ...>Off</option>
    <option value="global" ...>Zone program</option>
    <option value="custom" ...>Custom program</option>
  </select>
</div>
${this._renderRoomModeDescription(resolvedMode)}
```

4. Lines 1145–1168 — delete inline time-bar conditional block:
```typescript
<!-- Inline time-bar (only in Custom mode) -->
${resolvedMode === "custom"
  ? html`
      <div class="section-label" ...>Schedule</div>
      <div class="time-bar-section">
        <climate-manager-time-bar ...></climate-manager-time-bar>
      </div>
      <button class="reset-btn" @click=${() => void this._onResetToGlobal()}>
        Reset to global configuration
      </button>
    `
  : ""}
```

**Deletions — methods:**

5. Lines 337–363 — delete `_onRoomModeChange()` method entirely.

6. Lines 399–407 — delete `_onResetToGlobal()` method entirely.

7. Lines 642–652 — delete `_renderRoomModeDescription()` method entirely.

**Deletion — JSDoc comment** (line 60):
```typescript
/** Expanded state. Defaults to true when room_mode is "custom". */
```
Replace with:
```typescript
/** Expanded state. Defaults to collapsed. */
```
The `_expanded = false` default at line 61 is unchanged — it is already
the correct collapsed default. The `autoExpand` property (line 88–91) is
unrelated to `room_mode` and stays.

**Deletion in `_renderPeriodBadge()`** (lines 455–456):
```typescript
const resolvedMode = this.config?.room_mode ?? "global";
if (resolvedMode === "frost_protection") return html``;
```
Delete both lines. The method body continues directly at the `globalMode`
check (line 458).

---

### `frontend/src/ws-client.ts` (utility, request-response)

**Analog — `resetZoneTimeProgram()` method that stays** (lines 143–156):
```typescript
resetZoneTimeProgram(
  zoneId: string,
  target: "default" | "global",
): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/reset_zone_time_program",
    zone_id: zoneId,
    target,
  });
}
```

**Method to delete entirely** (lines 158–166):
```typescript
/**
 * Reset room time_program to the Default Zone program (D-10 rename).
 */
resetRoomToDefaultZoneProgram(roomId: string): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/reset_room_to_default_zone_program",
    room_id: roomId,
  });
}
```

---

### `tests/test_storage.py` (test, batch)

**Analog — Phase 14 shim test** (lines 304–324):
```python
async def test_load_legacy_flat_keys_builds_default_zone(hass):
    """Phase 14 compat shim: old format with global_mode is promoted to default_zone."""
    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "global_mode": "off",
            "global_time_program": {d: [] for d in _ALL_DAYS},
            "default_zone_name": "Maison",
            "default_zone_preheat_enabled": True,
        }
    )
    result = await store.async_load()
    assert result["default_zone"]["mode"] == "off"
    assert result["default_zone"]["name"] == "Maison"
    assert result["default_zone"]["preheat_enabled"] is True
    assert "global_mode" not in result
    assert "global_time_program" not in result
    assert "default_zone_name" not in result
    # Day-fill: empty day lists are filled with defaults before absorption
    for day in _ALL_DAYS:
        assert result["default_zone"]["time_program"][day] != []
```

**New test to add** — insert after the Phase 14 shim tests section:
```python
# Phase 15 compat shim tests (D-01, D-02, D-03)
# ---------------------------------------------------------------------------


async def test_load_strips_room_mode_from_room_records(hass):
    """Phase 15 compat shim: room_mode and time_program are stripped from rooms.

    Stores data with room records containing room_mode and time_program keys.
    After async_load(), both keys must be absent from all room records.
    Zone time programs must be unaffected (Pitfall 2 guard).
    """
    store = ClimateManagerStore(hass)
    sentinel_zone_program = {
        d: [{"start": "06:00", "mode": "normal"}] for d in _ALL_DAYS
    }
    await store._store.async_save(
        {
            "rooms": {
                "room-a": {
                    "room_mode": "custom",
                    "time_program": sentinel_zone_program,
                    "zone_id": "uuid-1",
                },
                "room-b": {
                    "room_mode": "frost_protection",
                },
                "room-c": {
                    "zone_id": "uuid-1",
                    # no room_mode — should load unchanged
                },
            },
            "zones": {
                "uuid-1": {
                    "name": "Test zone",
                    "mode": "time_program",
                    "time_program": sentinel_zone_program,
                    "preheat_enabled": False,
                }
            },
        }
    )
    result = await store.async_load()

    # room_mode and time_program absent from all room records
    for room_id, room_cfg in result["rooms"].items():
        assert "room_mode" not in room_cfg, (
            f"room_mode still present in {room_id}"
        )
        assert "time_program" not in room_cfg, (
            f"time_program still present in {room_id}"
        )
    # zone time_program is untouched (Pitfall 2)
    assert result["zones"]["uuid-1"]["time_program"] == sentinel_zone_program
    # zone_id on room-a and room-c survives (only room_mode/time_program stripped)
    assert result["rooms"]["room-a"]["zone_id"] == "uuid-1"
    assert result["rooms"]["room-c"]["zone_id"] == "uuid-1"
```

**Existing tests to clean** — lines 214, 233, 270: remove `room_mode` key
from fixture dicts. Tests should still pass because the coordinator no longer
reads the field. Example:
```python
# Before:
"rooms": {"living_room": {"zone_id": "uuid-1", "room_mode": "global"}},
# After:
"rooms": {"living_room": {"zone_id": "uuid-1"}},
```

---

### `tests/test_coordinator.py` (test, event-driven)

**Pattern — import block to clean** (lines 39–41):
```python
from custom_components.climate_manager.const import (
    ...
    ROOM_MODE_GLOBAL,   # DELETE
    ROOM_MODE_FROST,    # DELETE
    ROOM_MODE_CUSTOM,   # DELETE
    ...
)
```

**Test functions to delete entirely:**
- `test_room_mode_frost_protection_pushes_frost_temp` (~line 440)
- `test_room_mode_custom_uses_room_time_program` (~line 480)
- `test_room_mode_global_explicit_key_uses_global_program` (~line 524)
- `test_room_mode_absent_key_uses_global_program` (~line 563)
- `test_room_mode_frost_wins_over_stale_time_program` (~line 606)
- `test_room_mode_frost_wins_over_presence` (~line 649)
- `test_zone_off_overrides_room_mode_custom_default_zone` (~line 708)
- `test_zone_off_overrides_room_mode_custom_custom_zone` (~line 759)
- `test_room_mode_custom_wins_over_active_zone_schedule` (~line 1627)

**Comment to update** (line 45):
```python
# Module-level fixture: all days Comfort (for custom room_mode tests)
```
Remove or update the comment. Keep `ALL_DAYS_COMFORT_PROGRAM` if any
surviving tests reference it.

---

### `tests/test_preheat.py` (test, event-driven)

**Import to remove** (line 34):
```python
from custom_components.climate_manager.const import (
    ...
    ROOM_MODE_FROST,    # DELETE
    ...
)
```

**Fixture to clean** (line 531):
```python
# Before:
"room_mode": ROOM_MODE_FROST,  # frost-locked
# After: remove line entirely
# (frost-locked rooms in preheat are gated by self._frost_locked_rooms,
#  not room_mode — the field is irrelevant to preheat behavior)
```

---

### `tests/test_websocket.py` (test, request-response)

**Analog — existing removed-command test** (lines 512–530):
```python
async def test_ws_reset_room_to_global_program_is_removed(hass, hass_ws_client):
    """D-10: reset_room_to_global_program command is no longer registered.

    Phase 14 (D-10): the command type string changed to
    reset_room_to_default_zone_program. Sending the old name must return an
    error.
    """
    await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/reset_room_to_global_program",
            "room_id": "room-a",
        }
    )
    msg = await client.receive_json()

    assert msg.get("success") is False
```

**Test to delete entirely:**
- `test_ws_reset_room_to_default_zone_program_copies_into_room`
  (lines 533–590)

**Test to rewrite** — `test_ws_reset_room_to_global_program_is_removed`
becomes a Phase 15 equivalent that also asserts the new command name errors:
```python
async def test_ws_reset_room_to_default_zone_program_is_removed(
    hass, hass_ws_client
):
    """Phase 15 (D-06): reset_room_to_default_zone_program command is no
    longer registered.

    Sending the Phase 14 command name must return an error (both old and
    new names are now gone).
    """
    await _setup_entry(hass)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/reset_room_to_default_zone_program",
            "room_id": "room-a",
        }
    )
    msg = await client.receive_json()

    assert msg.get("success") is False
```

**Fixture lines to clean:**
- Line 1147: remove `"room_mode": "global"` from fixture dict.
- Line 1164: update assertion — remove `room_mode` field check; assert only
  remaining fields.
- Lines 1170–1197: remove `"room_mode": "custom"` from test payload (line
  1186) and remove `room_mode` assertion (line 1197).

---

## Shared Patterns

### Silent Drop Pattern
**Source:** `custom_components/climate_manager/websocket.py` line 374
**Apply to:** `ws_set_room_config` handler (D-07)
```python
incoming_config.pop("preheat_enabled", None)
# follows this with:
incoming_config.pop("room_mode", None)
```

### Pop-Based Compat Shim Pattern
**Source:** `custom_components/climate_manager/storage.py` lines 148–161
**Apply to:** Phase 15 shim in `async_load()`
```python
for room_cfg in result.get("rooms", {}).values():
    room_cfg.pop("<deprecated_key>", None)
```
Always use `result.get("rooms", {}).values()` — never `result.values()`.

### WS Command Deletion Pattern
**Source:** `websocket.py` lines 105–106 (Phase 14 removal comment)
**Apply to:** `async_register_commands()` and module docstring
```python
# D-08: set_global_mode removed; set_zone_mode handles zone_id="default"
```
Mirror this commenting style when removing the registration line.

### Removed-Command Test Pattern
**Source:** `tests/test_websocket.py` lines 512–530
**Apply to:** new `test_ws_reset_room_to_default_zone_program_is_removed`
```python
await client.send_json_auto_id({"type": f"{DOMAIN}/<removed_cmd>", ...})
msg = await client.receive_json()
assert msg.get("success") is False
```

---

## No Analog Found

All modified files have close analogs within the codebase. No files require
patterns from RESEARCH.md exclusively.

---

## Metadata

**Analog search scope:** `custom_components/climate_manager/`,
`frontend/src/`, `tests/`
**Files scanned:** 10 source files + test suite
**Pattern extraction date:** 2026-06-04
