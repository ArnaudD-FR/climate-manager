---
phase: 06-zone-room-assignment-ui
reviewed: 2026-05-28T17:14:21Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - custom_components/climate_manager/websocket.py
  - tests/test_storage.py
  - tests/test_websocket.py
  - frontend/src/components/zone-tab.ts
  - frontend/src/components/room-card.ts
  - frontend/src/main.ts
findings:
  critical: 2
  warning: 4
  info: 3
  total: 9
status: issues_found
---

# Phase 06: Code Review Report (gap-closure re-review)

**Reviewed:** 2026-05-28T17:14:21Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This is the gap-closure re-review covering plan 06-04 changes. The three original
BLOCKER findings (CR-01 Default Zone mode wrong WS command; CR-02 Default Zone time-bar
wrong WS command; CR-03 remove-room sends `undefined` silently dropped by JSON) have
been correctly fixed: `_onModeChange` and `_onPeriodsChanged` now branch on `isDefault`,
and `_onRemoveRoom` / `_onAddRoom` in `zone-tab.ts` and `_onZoneChange` in `room-card.ts`
all use `null as unknown as string | undefined` to carry the sentinel through the WS layer.
The backend `ws_set_room_config` handler now pops `zone_id` when it receives `null`, and
`validate_zone_assignment` in storage.py rejects `zone_id: null` if it somehow survives
to disk.

Two new correctness issues survive the gap closure:

1. **ws_set_room_config only catches ValueError** — a storage write failure from any
   other exception (e.g., `OSError`) leaves `runtime_config` mutated but not rolled back.
2. **ZoneTab reuses `_confirmingDelete` / `_editingName` state across zone switches** —
   a user who partially initiates a delete on Zone A then navigates to Zone B will see
   Zone B's confirm row already open; pressing Confirm deletes Zone B silently.

Four warnings and three info items round out the review.

---

## Critical Issues

### CR-01: `ws_set_room_config` only catches `ValueError` — OSError / other write failures leave `runtime_config` mutated with no rollback

**File:** `custom_components/climate_manager/websocket.py:373-379`

**Issue:** The handler mutates `runtime_config` before the try block (lines 364-371:
null-zone_id pop + `.update(incoming_config)`). A `rooms_backup` deepcopy is taken at
line 360, but it is only restored in the `except ValueError` branch. If `store.async_save`
raises anything other than `ValueError` (for example an `OSError` from an HA Store
file-write failure, or any future exception from `validate_zone_assignment` subclasses),
the mutations survive in memory. The in-memory `runtime_config` is then inconsistent
with what was persisted on disk, and `send_error` is not called (the exception propagates
unhandled to the HA WebSocket framework, which sends a generic error to the client).

All other write handlers in `websocket.py` that take backups use `except Exception`
(e.g., `ws_create_zone` line 547, `ws_rename_zone` line 593, `ws_set_zone_mode` line 653,
`ws_set_zone_time_program` line 766, `ws_reset_zone_time_program` line 820). The
`ws_set_room_config` handler is the only one that narrows to `ValueError` exclusively,
making it inconsistent and fragile.

**Fix:** Separate the `ValueError` case (maps to `ERR_INVALID_FORMAT`) from all other
exceptions (maps to `ERR_UNKNOWN_ERROR`), and restore the backup in both:

```python
try:
    await entry.runtime_data.store.async_save(entry.runtime_data.runtime_config)
except ValueError as exc:
    entry.runtime_data.runtime_config["rooms"] = rooms_backup
    connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, str(exc))
    return
except Exception as exc:  # noqa: BLE001
    entry.runtime_data.runtime_config["rooms"] = rooms_backup
    connection.send_error(msg["id"], websocket_api.ERR_UNKNOWN_ERROR, str(exc))
    return
```

### CR-02: `ZoneTab` does not reset `_confirmingDelete` / `_editingName` when `zoneId` changes — stale confirm row visible on newly-navigated zone

**File:** `frontend/src/components/zone-tab.ts:72-74`

**Issue:** `_confirmingDelete` and `_editingName` are `@state()` fields on the `ZoneTab`
LitElement. Lit reuses the same element instance when the parent (`main.ts`) changes
the `zoneId` / `zoneConfig` props (because the custom element tag is the same in the
template; Lit diffs the template and updates props in-place rather than destroying and
recreating the element).

Scenario: User opens Zone A's tab, clicks "Delete zone" (sets `_confirmingDelete = true`,
showing the confirm row). User then clicks the Zone B tab. `main.ts` re-renders with
`zoneId = "zone-b-uuid"` and `zoneConfig = {...zone B's config...}`. `ZoneTab.updated()`
is not overridden, so `_confirmingDelete` stays `true`. Zone B's tab renders with the
"Delete zone? / Cancel / Confirm" row already visible. A user who expected to be looking
at a fresh zone view presses "Confirm" — `ws.deleteZone(this.zoneId)` is called with
Zone B's ID. Zone B is silently deleted.

`_editingName` has the same problem: a stale open edit field from Zone A appears on
Zone B, pre-populated with Zone A's name. Saving it renames Zone B to Zone A's name.

**Fix:** Override `updated()` to reset transient UI state on `zoneId` changes:

```typescript
private _lastZoneId: string | undefined;

override updated(changed: Map<string, unknown>): void {
  super.updated(changed);
  if (changed.has("zoneId") && this.zoneId !== this._lastZoneId) {
    this._lastZoneId = this.zoneId;
    this._confirmingDelete = false;
    this._editingName = false;
    this._nameInputValue = "";
  }
}
```

---

## Warnings

### WR-01: `msg["config"]` mutated in-place by null-zone_id pop — `msg` should be read-only

**File:** `custom_components/climate_manager/websocket.py:363-365`

**Issue:** `incoming_config = msg["config"]` (line 363) assigns a **reference** to the
message dict's `config` sub-dict. The subsequent `incoming_config.pop("zone_id")` at
line 365 mutates `msg["config"]` in place. HA's WebSocket framework does not document
whether message dicts are reused or shared across handlers; treating `msg` as immutable
is a safe convention the rest of the codebase follows (all other handlers read `msg[key]`
without modifying it).

**Fix:** Take a shallow copy before modifying:

```python
incoming_config = dict(msg["config"])  # copy so msg stays read-only
```

### WR-02: `null as unknown as string | undefined` type lie is replicated in three places — should be modelled in the type system

**File:** `frontend/src/components/zone-tab.ts:401, 420`
**File:** `frontend/src/components/room-card.ts:458`

**Issue:** The pattern `null as unknown as string | undefined` appears three times to
force `null` through a field typed `string | undefined`. This double-cast bypasses
TypeScript's type checker. The root cause is that `RoomConfig.zone_id` (types.ts:36)
is typed `string | undefined` — correct for the on-disk sparse model — but the
**wire-protocol patch** is a distinct type that intentionally allows `zone_id: null` as
a "clear this key" sentinel. TypeScript cannot catch future regressions at these three
call sites.

**Fix:** Add an explicit wire-protocol patch type and update `WsClient.setRoomConfig`:

```typescript
// In types.ts
export type RoomConfigPatch = Omit<RoomConfig, "zone_id"> & {
  zone_id?: string | null;  // null = signal to backend to pop the key
};
```

Update `WsClient.setRoomConfig` parameter from `Partial<RoomConfig>` to
`Partial<RoomConfigPatch>`. All three `null as unknown as ...` casts can then be replaced
with a plain `null`.

### WR-03: `test_set_room_config_null_zone_id_preserves_other_keys` tests an incorrect initial state — does not actually exercise the pop

**File:** `tests/test_websocket.py:745-771`

**Issue:** The test is designed to verify that `{zone_id: null, room_mode: "custom"}`
pops `zone_id` AND applies `room_mode`. However the initial room state at line 753 is
`{}` — the room has no `zone_id` to pop. The pop at websocket.py:366 calls
`.pop("zone_id", None)` on an empty dict, which is a no-op. The test therefore does
not distinguish between:
- A working implementation (pops existing key, then applies remaining keys), and
- A broken implementation that skips the pop entirely (same observable outcome on an
  empty dict).

The test title says "preserves other keys" but it does not seed a room with an existing
`zone_id`, so it is testing a degenerate case.

**Fix:** Seed the room with a valid zone assigned before sending the mixed patch:

```python
zone_id = "some-uuid"
entry.runtime_data.runtime_config.setdefault("zones", {})[zone_id] = {
    "name": "Test Zone", "mode": "time_program",
    "time_program": {d: [] for d in ["mon","tue","wed","thu","fri","sat","sun"]},
}
entry.runtime_data.runtime_config.setdefault("rooms", {})["living_room"] = {
    "zone_id": zone_id  # existing assignment — pop must remove this
}
# ... then send {zone_id: null, room_mode: "custom"} and assert:
# "zone_id" not in room, room.get("room_mode") == "custom"
```

### WR-04: `ws_reset_zone_time_program` and `ws_create_zone` access `runtime_config["global_time_program"]` without a guard — raises `KeyError` on sparse configs

**File:** `custom_components/climate_manager/websocket.py:541, 815`

**Issue:** Two handlers access `runtime_config["global_time_program"]` via bracket
subscript (KeyError on missing key) rather than `.get()`:

- `ws_create_zone` line 541: `copy.deepcopy(runtime_config["global_time_program"])`
- `ws_reset_zone_time_program` line 815: `runtime_config["global_time_program"]`

The storage layer's `async_load()` always populates `global_time_program` via merge
with `DEFAULT_CONFIG`, so in normal operation the key is present. However if
`runtime_config` is constructed directly (in tests, or via a future code path that
bypasses `async_load`), the bracket access raises `KeyError` and the exception propagates
unhandled (the try/except in both handlers only wraps the `store.async_save` call, not
the key access). The inconsistency is visible: line 498 in the same file uses
`.get("global_time_program", {})` with a safe fallback.

**Fix:** Use `.get()` with a deepcopy of the default as fallback:

```python
# ws_create_zone (line 541):
source = runtime_config.get("global_time_program") or copy.deepcopy(_DEFAULT_DAILY_PROGRAM)
new_zone["time_program"] = copy.deepcopy(source)

# ws_reset_zone_time_program (line 815):
source = runtime_config.get("global_time_program") or copy.deepcopy(_DEFAULT_DAILY_PROGRAM)
runtime_config["zones"][msg["zone_id"]]["time_program"] = copy.deepcopy(source)
```

---

## Info

### IN-01: `_getAssignedRoomIds` uses a redundant dual condition (`isDefault || zoneId === "default"`)

**File:** `frontend/src/components/zone-tab.ts:485`

**Issue:** The filter reads `if (this.isDefault || this.zoneId === "default")`. In every
call path from `main.ts`, `isDefault` is always `true` when `zoneId === "default"` and
vice versa — they are set together. The `|| this.zoneId === "default"` branch is dead
code. If they ever diverge (e.g., a caller sets `isDefault=false, zoneId="default"`),
the dual condition masks the misconfiguration silently. All other `isDefault` guards in
the same file (delete row, chip-remove, mode-change) rely on `isDefault` alone.

**Fix:** Remove the redundant branch:

```typescript
if (this.isDefault) {
  return !roomConfig.zone_id || !zoneKeys.includes(roomConfig.zone_id);
}
```

### IN-02: `_onCreateZone` auto-focus may silently fail if `ZoneTab` has not finished its render cycle

**File:** `frontend/src/main.ts:249-251`

**Issue:** After creating a zone:

```typescript
await this.updateComplete;
const zoneTab = this.shadowRoot?.querySelector("climate-manager-zone-tab");
(zoneTab?.shadowRoot?.querySelector<HTMLElement>(".zone-name"))?.click();
```

`this.updateComplete` resolves after the root panel's render, which inserts
`<climate-manager-zone-tab>` into the DOM. But `zone-tab.ts` is a LitElement with its
own async render cycle. Its `shadowRoot` may not yet contain `.zone-name` when the
`querySelector` runs — optional chaining silences the failure and auto-focus does not
happen.

**Fix:** Wait for the child element's own update cycle:

```typescript
await this.updateComplete;
const zoneTab = this.shadowRoot?.querySelector("climate-manager-zone-tab") as LitElement | null;
if (zoneTab) {
  await zoneTab.updateComplete;
  (zoneTab.shadowRoot?.querySelector<HTMLElement>(".zone-name"))?.click();
}
```

### IN-03: Default Zone name numbering collides after zone deletion

**File:** `frontend/src/main.ts:243`

**Issue:** New zones are named `` `Zone ${Object.keys(this._config.zones).length + 1}` ``.
After creating Zone 1, Zone 2, then deleting Zone 1, the next zone is named "Zone 2"
(length=1, +1=2), colliding with the existing "Zone 2" tab label. Zone names are not
unique identifiers (UUIDs are), but duplicate tab labels confuse users.

**Fix:** Find the max trailing integer across existing names:

```typescript
const existingNums = Object.values(this._config.zones)
  .map((z) => Number(z.name.match(/^Zone (\d+)$/)?.[1] ?? "0"))
  .filter((n) => n > 0);
const next = existingNums.length ? Math.max(...existingNums) + 1 : 1;
const newName = `Zone ${next}`;
```

---

_Reviewed: 2026-05-28T17:14:21Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
