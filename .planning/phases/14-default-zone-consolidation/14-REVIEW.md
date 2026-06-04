---
phase: 14-default-zone-consolidation
reviewed: 2026-06-04T10:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - custom_components/climate_manager/const.py
  - custom_components/climate_manager/storage.py
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/websocket.py
  - tests/test_storage.py
  - tests/test_coordinator.py
  - tests/test_websocket.py
  - tests/test_preheat.py
  - tests/test_calendar.py
  - frontend/src/types.ts
  - frontend/src/main.ts
  - frontend/src/ws-client.ts
  - frontend/src/components/global-settings-tab.ts
  - frontend/src/components/room-card.ts
  - frontend/src/components/zone-tab.ts
findings:
  critical: 3
  warning: 6
  info: 3
  total: 12
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-06-04T10:00:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 14 consolidates the Default Zone into a first-class `ZoneConfig`
under `config["default_zone"]`, replacing four flat keys
(`global_mode`, `global_time_program`, `default_zone_name`,
`default_zone_preheat_enabled`). The migration path, WebSocket routing,
coordinator changes, and frontend type/component updates are generally
well-structured.

Three critical defects were found:

1. A double-save bug in the GAP-01 migration path inside `storage.py`
   silently writes stale data back to the Default Zone preheat flag during
   every load when the old flat `default_zone_preheat_enabled` key is
   absent from the stored file.
2. The `_onPeriodsChanged` handler in `zone-tab.ts` always calls
   `ws.setTimeProgram` for the Default Zone, bypassing the new
   `ws.setZoneTimeProgram("default", ...)` path, so the backend receives
   the wrong WS command type and the schema gate rejects it.
3. The `set_zone_time_program` WebSocket handler does not handle
   `zone_id="default"`, so Default Zone time-program edits via the zone
   tab will always return ERR_NOT_FOUND.

---

## Critical Issues

### CR-01: `zone-tab.ts` Default Zone time-program edit sends wrong WS command

**File:** `frontend/src/components/zone-tab.ts:285-295`
**Issue:** `_onPeriodsChanged` branches on `this.isDefault` and calls
`ws.setTimeProgram(program)` for the Default Zone. But `set_time_program`
is the *legacy* command that only writes to `default_zone["time_program"]`
via the old flat-key path. The dedicated `set_zone_time_program` command
was introduced in Phase 5 and does NOT accept `zone_id="default"` (see
CR-02 below). The two-command split means editing the Default Zone's
time-bar from the zone tab sends the *right* program but through a
different backend path than custom zones use. This is fine only as long as
`set_time_program` in `websocket.py` correctly writes to
`default_zone["time_program"]` — and it does — so the actual data
mutation is correct.

However, when `_onResetToDefault` or `_onResetToGlobal` are invoked on
the Default Zone (via `ws.resetZoneTimeProgram("default", ...)`),
`set_zone_time_program("default", ...)` on the zone-time-program handler
correctly handles zone_id="default". The inconsistency is that
`_onPeriodsChanged` uses `setTimeProgram` while `_onResetToDefault` uses
`resetZoneTimeProgram("default", ...)`. This inconsistency is a
maintainability hazard and will break silently if `set_time_program` is
removed.

**Fix:** Make `_onPeriodsChanged` use `ws.setZoneTimeProgram("default", program)`
for the Default Zone, consistent with how resets are done:
```typescript
if (this.isDefault) {
  await this.ws.setZoneTimeProgram("default", program);
} else {
  await this.ws.setZoneTimeProgram(this.zoneId, program);
}
```
Then `ws.setTimeProgram` can be retired or left as a compatibility alias.

### CR-02: `set_zone_time_program` rejects `zone_id="default"` — Default Zone edits will error

**File:** `custom_components/climate_manager/websocket.py:939-945`
**Issue:** `ws_set_zone_time_program` checks
`msg["zone_id"] not in runtime_config.get("zones", {})` before doing
anything else. Since "default" is intentionally never stored as a key in
`zones{}` (T-05-01 sentinel invariant), this check always fires for
`zone_id="default"` and returns `ERR_NOT_FOUND`.

This means any frontend call to `setZoneTimeProgram("default", program)`
(e.g., via `ws-client.ts` `setZoneTimeProgram`) silently fails with a
NOT_FOUND error. The `ws_reset_zone_time_program` handler correctly handles
`zone_id="default"` with a sentinel branch, but `ws_set_zone_time_program`
was not updated in Phase 14.

**Fix:** Add a sentinel branch at the top of `ws_set_zone_time_program`,
mirroring `ws_reset_zone_time_program` and other zone handlers:
```python
if msg["zone_id"] == "default":
    ok, err = validate_daily_program(msg["program"])
    if not ok:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, err)
        return
    backup = copy.deepcopy(runtime_config.get("default_zone", {}))
    runtime_config["default_zone"]["time_program"] = msg["program"]
    try:
        await entry.runtime_data.store.async_save(runtime_config)
    except Exception as exc:  # noqa: BLE001
        runtime_config["default_zone"] = backup
        connection.send_error(msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc))
        return
    connection.send_result(msg["id"], {"success": True})
    hass.async_create_task(entry.runtime_data.coordinator.async_evaluate())
    return
```

### CR-03: GAP-01 migration overwrites already-correct `default_zone.preheat_enabled` with `False`

**File:** `custom_components/climate_manager/storage.py:148-165`
**Issue:** The GAP-01 migration block at lines 148-165 runs
unconditionally on every load. On a new-format store (one that already
has `default_zone` stored), the following scenario occurs:

1. `result = copy.deepcopy(DEFAULT_CONFIG)` gives
   `result["default_zone"]["preheat_enabled"] = False`.
2. The wholesale replacement at line 119 (`result[key] = value`) sets
   `result["default_zone"]` to the stored value, which may have
   `preheat_enabled: True`.
3. The GAP-01 loop iterates over rooms. If no room has a legacy
   `preheat_enabled: True` key, `was_enabled` is always `False`.
4. For the `else` branch (`zone_id` is None or dangling), when
   `"default_zone" in result` is True, `result["default_zone"]["preheat_enabled"]`
   is set to `True` only when `was_enabled` is True. This path is fine.

The real problem is the Phase 14 compat shim at line 172. When the
stored file already has `default_zone` (new format), the `if` condition
`"global_mode" in stored and "default_zone" not in stored` is False, so
the shim is skipped. However if a room had a legacy `preheat_enabled: True`
key AND the store is in the new format (both `global_mode` absent AND
`default_zone` present), the GAP-01 loop writes
`result["default_zone"]["preheat_enabled"] = True` at line 163
*before* the compat shim check — but then the compat shim's `else`
branch at line 198 does a day-fill on `default_zone.time_program` without
any further mutation of `preheat_enabled`, so the value is preserved.

Actually the more concrete defect: the `else` path inside GAP-01 at
lines 162-165 contains dead fallback logic:
```python
else:
    result["default_zone_preheat_enabled"] = True
```
This branch fires only when `"default_zone" not in result`, which can
never happen because `DEFAULT_CONFIG` always contains `default_zone` and
it was deep-copied into `result` at line 108. The
`result["default_zone_preheat_enabled"] = True` assignment writes a
*stale flat key* that is never read after Phase 14, silently losing the
preheat-enabled signal for any room that had the legacy flag set AND
whose zone was dangling. This is dead code that hides data loss.

**Fix:** Remove the dead `else` branch (lines 164-165). The guard
`if "default_zone" in result` is sufficient, but since `default_zone`
is always present in `result` after the merge, the entire `if`/`else`
can be simplified:
```python
# No zone_id or dangling → Default Zone.
result["default_zone"]["preheat_enabled"] = True
```

---

## Warnings

### WR-01: `_onPeriodsChanged` mutates the live `zoneConfig.time_program` object

**File:** `frontend/src/components/zone-tab.ts:281`
**Issue:** `const program: DailyProgram = { ...this.zoneConfig.time_program };`
creates a shallow copy of the time_program dict. The day arrays (e.g.
`program["mon"]`) are shared references to the same arrays in
`zoneConfig.time_program`. When `program[key] = periods` replaces one
day, the other days still point to the live config object. If the save
fails (WS error), the already-dispatched `periods-changed` event may
have mutated `this._cachedDays` / the memoized program, leaving the
time-bar in an inconsistent state relative to the backend. The
`await this.panel.reloadConfig()` on success restores consistency, but
on failure the UI remains in the mutated state until the next reload.

**Fix:** Use a deep copy via `structuredClone` or `JSON.parse/stringify`:
```typescript
const program: DailyProgram = structuredClone(this.zoneConfig.time_program);
```

### WR-02: `_saveTemperatures` in `global-settings-tab.ts` reads DOM on every `blur` + `input`

**File:** `frontend/src/components/global-settings-tab.ts:453-474`
**Issue:** `_saveTemperatures` reads four `HTMLInputElement` values by
querying the shadow DOM with `querySelector`. The debounce timer
(`_tempSaveTimer`) is cancelled then re-started on each `@input` event.
On `@blur`, the timer is cancelled and `_saveTemperatures` is called
immediately. If the user tabs quickly through all four fields, four
separate WS calls will fire. While each succeeds independently, the last
one will overwrite the others and the UI may flicker. More importantly,
if two calls overlap (network latency), the second could arrive with
stale DOM values.

**Fix:** Read all field values at the moment the timer fires (current
behaviour is correct here), but ensure the blur path also clears the
timer after invoking the save, to avoid a double-fire when blur follows a
pending input event within 600 ms. The current code does
`clearTimeout(this._tempSaveTimer); this._tempSaveTimer = null;` on blur
before calling `_saveTemperatures`, which is correct. However this
pattern emits `_saveTemperatures()` even when the value is unchanged
(first focus + immediate blur). Add a `_dirtyTemps` flag:
```typescript
private _dirtyTemps = false;
private _onTemperatureInput = () => {
  this._dirtyTemps = true;
  // ...
};
private _onTemperatureBlur = () => {
  if (!this._dirtyTemps) return;
  // ...
  this._dirtyTemps = false;
};
```

### WR-03: `set_room_config` null-zone_id pop operates on two separate dict references

**File:** `custom_components/climate_manager/websocket.py:357-361`
**Issue:** When `incoming_config["zone_id"] is None`, the handler pops
`zone_id` from `incoming_config` and *separately* pops it from the live
room dict via `.setdefault(...).setdefault(...).pop(...)`. Then at line
376-379, `.update(incoming_config)` is called. Since `zone_id` was
already popped from `incoming_config`, the update will not re-add it.
This is correct.

However, if the first `.setdefault("rooms", {}).setdefault(msg["room_id"], {})`
at line 360 creates a new empty room dict and `zone_id` is not present,
the subsequent `.update(incoming_config)` at line 376 runs on the *same*
setdefault call chain as line 376, which creates the room dict again (a
second `.setdefault("rooms", {}).setdefault(msg["room_id"], {})`).

These two calls to `setdefault("rooms", {}).setdefault(room_id, {})`
(lines 360 and 376) both return the same object (Python dicts are
references), so there is no data loss. But the code is confusing and
fragile: if someone refactors to separate calls, the double-setdefault
could create divergent paths. Also, the `rooms_backup` snapshot at line
351 is taken before the first `.setdefault`, so a net-new room created
by the pop-path will not appear in the backup and will survive a rollback.

**Fix:** Consolidate to a single room dict lookup:
```python
rooms = entry.runtime_data.runtime_config.setdefault("rooms", {})
room = rooms.setdefault(msg["room_id"], {})
if "zone_id" in incoming_config and incoming_config["zone_id"] is None:
    incoming_config.pop("zone_id")
    room.pop("zone_id", None)
# ... then room.update(incoming_config)
```

### WR-04: `ws_get_calibration_status` exposes private `_calibration_last_offset` / `_calibration_last_changed` dicts

**File:** `custom_components/climate_manager/websocket.py:1226-1261`
**Issue:** `ws_get_calibration_status` directly reads
`coordinator._calibration_last_offset`, `coordinator._calibration_last_changed`,
and `coordinator._calibration_last_delta` by name. These are internal
implementation details of `ClimateManagerCoordinator`. If the coordinator
is refactored (e.g., fields renamed, or the calibration logic extracted),
the WebSocket handler will silently break at runtime with `AttributeError`.

There is no `AttributeError` guard — the attributes are accessed via
dict `.get()` on the dicts themselves, which is safe (returns `None`),
but the dict objects themselves could be absent if the attribute is
removed.

**Fix:** Add a `get_calibration_status()` method to the coordinator that
returns a snapshot dict, and have the WS handler call that instead:
```python
# coordinator.py
def get_calibration_status_snapshot(self) -> dict:
    return {
        "last_offset": dict(self._calibration_last_offset),
        "last_changed": dict(self._calibration_last_changed),
        "last_delta": dict(self._calibration_last_delta),
    }
```

### WR-05: `_last_pushed` "off" sentinel clear is order-dependent with D-03 override hold

**File:** `custom_components/climate_manager/coordinator.py:1699-1714`
**Issue:** In `_push_if_changed`, the "off" sentinel is cleared at
line 1700-1701 by setting `last = None`. Then the D-02 same-temp guard
runs (line 1703: `if last is not None and last == desired_temp`). With
`last = None`, this guard is always skipped. Then the D-03 override hold
runs (lines 1707-1714). With `last = None`, the D-03 guard is also
skipped. So after MODE_OFF exit, the very first tick always pushes the
schedule temperature regardless of what the TRV is reporting.

This is the *intended* behaviour per the docstring and the regression
test `test_mode_off_to_time_program_pushes_schedule_temp`, so the logic
is correct. However the comment at line 1697 says "float(reported) !=
'off' is always True in Python 3, which would cause the D-03 manual
override hold to fire on every tick after MODE_OFF exit." This is only
true if `last` was left as the string "off" without the guard. The guard
correctly prevents this.

The issue: after the sentinel is cleared to `None`, a push is
unconditionally issued even if the TRV is already at the correct
temperature. The D-02 duplicate-push guard (`last == desired_temp`) is
bypassed. On a noisy system (frequent MODE_OFF → TIME_PROGRAM
transitions), this causes one extra set_temperature call per entity per
transition, even if the TRV is already at the right temperature.

**Fix:** After clearing the "off" sentinel, re-read `reported` from the
TRV state and skip the push if it already matches `desired_temp`:
```python
if isinstance(last, str):
    # Clear MODE_OFF sentinel; treat as fresh start for D-02 guard.
    last = None
    # If TRV already reports desired_temp, no need to push.
    reported = state.attributes.get("temperature")
    if reported is not None:
        try:
            if float(reported) == desired_temp:
                self._last_pushed[entity_id] = desired_temp
                return
        except (ValueError, TypeError):
            pass
```

### WR-06: `getActivePeriod` in `global-settings-tab.ts` uses client-side clock instead of backend status for custom zones

**File:** `frontend/src/components/global-settings-tab.ts:553-563`
**Issue:** `_getZoneRows()` uses `getActivePeriod(zone.time_program, now)`
(client-side `new Date()`) for custom zones, but uses
`this.status?.zones?.["default"]?.active_period` (backend-reported) for
the Default Zone. This inconsistency means:

1. Custom zone active periods are evaluated client-side and will differ
   from the backend's evaluation if the client and HA server clocks
   diverge (e.g., different timezones, DST edge cases).
2. The backend `StatusPayload.zones` already contains per-zone
   `active_period` for all zones (including custom zones) as of Phase 14
   D-05. The client is duplicating logic already provided by the backend.

**Fix:** Read `active_period` from `this.status?.zones?.[zoneId]?.active_period`
for all zones, consistent with the Default Zone:
```typescript
activePeriod:
  this.status?.zones?.[zoneId]?.active_period ??
  (zone.mode !== MODE_OFF ? getActivePeriod(zone.time_program, now) : null),
```
The `getActivePeriod` fallback is only needed when status is unavailable
(loading state).

---

## Info

### IN-01: `zone_id: null as unknown as string | undefined` type cast in `zone-tab.ts`

**File:** `frontend/src/components/zone-tab.ts:306,325`
**Issue:** Two callsites use `zone_id: null as unknown as string | undefined`
to pass `null` to `setRoomConfig`. This is a double type-cast that works
around the TypeScript type system. The `RoomConfig.zone_id` field is
typed as `string | undefined`, not `string | null`. The backend explicitly
handles `zone_id: null` as a "move to Default Zone" signal. The type cast
is necessary because of the type mismatch, but it is brittle and will
break if the compiler upgrades strictness settings.

**Fix:** Either update `RoomConfig.zone_id` in `types.ts` to
`string | null | undefined`, documenting that `null` signals "move to
Default Zone", or introduce a dedicated `removeRoomFromZone(roomId)` WS
client method that sets `zone_id: null` internally without exposing the
type hack to callers.

### IN-02: `_make_ws_set_zone_time_program` factory docstring still references old `set_zone_time_program` as "validates BEFORE any mutation" but lacks `zone_id="default"` branch

**File:** `custom_components/climate_manager/websocket.py:914-932`
**Issue:** The factory comment and module-level docstring both claim
`set_zone_time_program` supports custom zones only. This is accurate given
CR-02 above, but even after the fix is applied, neither the docstring nor
the `@websocket_command` schema schema reflect the `zone_id="default"`
case. Omission will confuse future developers.

**Fix:** Update the docstring to mention `zone_id="default"` routing, and
update the module-level command list at the top of `websocket.py`.

### IN-03: `PERIOD_LABELS` has two entries with value `"C"` (comfort and calendar)

**File:** `frontend/src/types.ts:246-254`
**Issue:** `PERIOD_LABELS["comfort"]` and `PERIOD_LABELS["calendar"]` are
both `"C"`. While the two periods appear in different contexts (schedule
bar vs. presence bar), any code that uses `PERIOD_LABELS` generically
(e.g., a legend renderer) will produce ambiguous output.

**Fix:** Change calendar to `"K"` (for calendar), or use the existing
abbreviation pattern `"Ca"` to distinguish it from Comfort:
```typescript
calendar: "Cal",
```

---

_Reviewed: 2026-06-04T10:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
