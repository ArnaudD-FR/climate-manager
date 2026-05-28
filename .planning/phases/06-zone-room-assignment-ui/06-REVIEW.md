---
phase: 06-zone-room-assignment-ui
reviewed: 2026-05-28T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - frontend/src/ws-client.ts
  - frontend/src/components/zone-tab.ts
  - frontend/src/main.ts
  - frontend/src/components/room-card.ts
  - frontend/src/components/person-card.ts
findings:
  critical: 3
  warning: 3
  info: 2
  total: 8
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-05-28
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 6 added zone management UI: new WebSocket methods in ws-client.ts, a 589-line zone-tab.ts LitElement, and zone-related updates in main.ts, room-card.ts, and person-card.ts. The WebSocket client method signatures and backend contracts are correctly aligned for the six new zone commands. The HA 2026.x compatibility guideline (native `<input>`/`<select>` over broken ha-textfield/ha-select) is correctly applied throughout zone-tab.ts.

Three correctness blockers are present, all in zone-tab.ts: (1) the Default Zone mode selector routes to the wrong WebSocket command and always fails; (2) the Default Zone time-bar routes to the wrong WebSocket command and always fails; (3) removing a room from a custom zone sends `zone_id: undefined` which JavaScript's JSON serializer silently drops, making the remove a no-op on the backend.

---

## Critical Issues

### CR-01: Default Zone mode change calls `setZoneMode` — always rejected by backend

**File:** `frontend/src/components/zone-tab.ts:357`

**Issue:** `_onModeChange` unconditionally calls `this.ws.setZoneMode(this.zoneId, newMode)`. When the Default Zone tab is active, `this.zoneId === "default"`. The backend `set_zone_mode` handler explicitly rejects `zone_id="default"` with `ERR_NOT_FOUND` (websocket.py line 632–640: "zone_id='default' is not supported here and routes to ERR_NOT_FOUND"). The Default Zone's mode is `global_mode` and must be mutated via `set_global_mode` / `ws.setGlobalMode()`. The result: every mode change on the Default Zone tab silently fails with a "Save failed" toast. The native `<select>` retains the visually-changed state (no `reloadConfig()` is called in the `catch` block), so the UI shows an unsaved value until the next page reload.

**Fix:** Branch on `this.isDefault` (or `this.zoneId === "default"`) in `_onModeChange`:

```typescript
private _onModeChange = async (e: Event) => {
  const newMode = (e.target as HTMLSelectElement).value;
  if (!newMode || newMode === this.zoneConfig.mode) return;
  try {
    if (this.isDefault) {
      await this.ws.setGlobalMode(newMode);
    } else {
      await this.ws.setZoneMode(this.zoneId, newMode);
    }
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    await this.panel.reloadConfig(); // restore select to actual backend value
    this.panel.showToast("Save failed", true);
  }
};
```

---

### CR-02: Default Zone time-bar calls `setZoneTimeProgram` — always rejected by backend

**File:** `frontend/src/components/zone-tab.ts:372`

**Issue:** `_onPeriodsChanged` calls `this.ws.setZoneTimeProgram(this.zoneId, program)` unconditionally. When `this.zoneId === "default"`, the backend `set_zone_time_program` handler rejects with `ERR_NOT_FOUND` (websocket.py line 742–748). The Default Zone's time program is `global_time_program` and must be saved via `set_time_program` / `ws.setTimeProgram()`. Every time-bar interaction on the Default Zone tab fails, and the user's schedule edits are lost.

**Fix:** Branch on `this.isDefault` in `_onPeriodsChanged`:

```typescript
private _onPeriodsChanged = async (e: CustomEvent) => {
  const { dayIndex, periods } = e.detail as { dayIndex: number; periods: Period[] };
  const program: DailyProgram = { ...this.zoneConfig.time_program };
  const key = dayIndexToKey(dayIndex);
  program[key] = periods;
  try {
    if (this.isDefault) {
      await this.ws.setTimeProgram(program);
    } else {
      await this.ws.setZoneTimeProgram(this.zoneId, program);
    }
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed", true);
  }
  e.stopPropagation();
};
```

---

### CR-03: `_onRemoveRoom` sends `zone_id: undefined` — JSON serializer drops it, backend no-op

**File:** `frontend/src/components/zone-tab.ts:403`

**Issue:** `_onRemoveRoom` builds `const patch: Partial<RoomConfig> = { zone_id: undefined }` and passes it to `ws.setRoomConfig(roomId, patch)`. The HA WebSocket client serializes the message to JSON before transmitting. `JSON.stringify({ zone_id: undefined })` produces `{}` — JavaScript's JSON serializer silently drops keys with `undefined` values. The backend `set_room_config` handler receives `config: {}` and calls `.update({})`, which is a no-op. The room's `zone_id` is never cleared, so the room remains in the zone after the "Saved" toast appears. The UI re-renders correctly from `reloadConfig()` data (showing the room still assigned), which contradicts the toast feedback.

The same issue exists in `room-card.ts:458`: `const patch: Partial<RoomConfig> = newZoneId ? { zone_id: newZoneId } : { zone_id: undefined }` — selecting the Default Zone from the room card's zone picker is also a no-op.

**Fix:** The backend expects the `zone_id` key to be absent (not null, not a string "default") for Default Zone membership (sparse model per D-06). The backend's `delete_zone` handler uses `room_cfg.pop("zone_id", None)` to achieve this. The frontend must use a different mechanism. The correct approach is to add a dedicated backend command or accept a sentinel string (e.g., `"default"`) that the backend explicitly interprets as "remove zone_id":

Option A — send `zone_id: null` and add a backend branch to `set_room_config` that calls `room_cfg.pop("zone_id", None)` when it sees `null` (keep the `validate_zone_assignment` explicit-null check gated on `isinstance(zone_id, str)` first).

Option B — add a `remove_room_from_zone` WS command that does the pop directly.

Option C (minimal frontend-only) — if the backend is changed to accept `zone_id: null` as "clear", the frontend sends `null` instead of `undefined`:

```typescript
private async _onRemoveRoom(roomId: string) {
  // zone_id: null is serialized to JSON (unlike undefined which is dropped)
  // Backend must explicitly handle null as "pop zone_id" (see set_room_config handler)
  const patch = { zone_id: null } as unknown as Partial<RoomConfig>;
  try {
    await this.ws.setRoomConfig(roomId, patch);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed", true);
  }
}
```

Note: this also applies to `room-card.ts:458` — the `zone_id: undefined` branch has the same serialization problem.

---

## Warnings

### WR-01: `_onAddRoom` for Default Zone sends `zone_id: "default"` — backend rejects it

**File:** `frontend/src/components/zone-tab.ts:388`

**Issue:** `_onAddRoom(roomId)` calls `ws.setRoomConfig(roomId, { zone_id: this.zoneId })`. When `this.zoneId === "default"`, the backend's `validate_zone_assignment` (storage.py line 53) checks `if zone_id not in zones` — "default" is never a key in `config.zones`, so it raises `ValueError("Room references unknown zone_id 'default'")`. The backend returns `ERR_INVALID_FORMAT`. The "Add room" chip on the Default Zone tab therefore always fails. The comment on line 384 acknowledges this: "NOTE: If backend rejects 'default' here, flag it rather than silently dropping." The note correctly identifies the risk but the fix was never implemented.

**Fix:** For the Default Zone, adding a room means clearing its `zone_id`. This is the same mechanism as `_onRemoveRoom` from a custom zone. Reuse the fix from CR-03:

```typescript
private async _onAddRoom(roomId: string) {
  // For Default Zone: clearing zone_id is the "add to Default Zone" operation
  const patch = this.isDefault
    ? { zone_id: null } as unknown as Partial<RoomConfig>  // clears zone_id (see CR-03)
    : { zone_id: this.zoneId };
  try {
    await this.ws.setRoomConfig(roomId, patch);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed", true);
  }
}
```

---

### WR-02: Mode select retains visually-changed state after save failure (no `reloadConfig` in catch)

**File:** `frontend/src/components/zone-tab.ts:360`

**Issue:** When `_onModeChange` throws (e.g., network error), the `catch` block only calls `this.panel.showToast("Save failed", true)`. The native `<select>` element has already changed its value visually (browsers update `<select>` immediately on user interaction). Without calling `reloadConfig()` in the `catch` block, the select stays at the new (unsaved) value. The Lit `?selected` binding only sets the attribute at render time — it does not reset the native select's live `value` property on subsequent renders unless the parent re-renders with the old `zoneConfig.mode`, which only happens on the next `reloadConfig()`. Users see a desync between displayed mode and actual backend mode until page reload.

The same issue exists for custom zone mode changes where the WS call fails for transient reasons.

**Fix:** Call `await this.panel.reloadConfig()` inside the `catch` block of `_onModeChange`:

```typescript
  } catch {
    await this.panel.reloadConfig(); // resets select to actual backend value
    this.panel.showToast("Save failed", true);
  }
```

---

### WR-03: `_unsubStatus` declared `@state()` — causes unnecessary re-renders on subscribe

**File:** `frontend/src/main.ts:44`

**Issue:** `@state() private _unsubStatus: Promise<() => void> | null = null` uses `@state()` on a `Promise` object. Lit's `@state()` triggers a re-render when the property reference changes. Setting `_unsubStatus` from `null` to the subscription Promise (line 206) will trigger a full re-render of the panel — including the tab-bar and all tab content — purely due to the subscription being established, not because any visible data changed. The Promise itself is not renderable state; it is implementation-internal lifecycle data.

**Fix:** Remove `@state()`. Store as a plain private field:

```typescript
private _unsubStatus: Promise<() => void> | null = null;
```

The disconnect logic in `disconnectedCallback` reads this field directly and does not need reactivity.

---

## Info

### IN-01: `resetZoneTimeProgram` WS method is declared but never called from any UI component

**File:** `frontend/src/ws-client.ts:132`

**Issue:** `resetZoneTimeProgram(zoneId, target)` is fully implemented in `ws-client.ts` but no component in the reviewed files calls it. The zone-tab.ts renders the time-bar and a mode picker but has no "Reset zone program" button. This is dead API surface — not a bug, but a signal that either the feature was planned and not implemented, or the method can be removed until needed.

**Fix:** Either add a "Reset to defaults" button in `zone-tab.ts` (analogous to the room-card reset button) or remove the method until the UI exists. If keeping it, add a `TODO` comment noting it is intentionally unused pending UI.

---

### IN-02: Auto-focus after zone creation may silently miss the name field

**File:** `frontend/src/main.ts:249-251`

**Issue:** After creating a zone, `_onCreateZone` does:
```typescript
await this.updateComplete;
const zoneTab = this.shadowRoot?.querySelector("climate-manager-zone-tab");
(zoneTab?.shadowRoot?.querySelector<HTMLElement>(".zone-name"))?.click();
```
`this.updateComplete` resolves when the root panel finishes its render pass, inserting the `<climate-manager-zone-tab>` element into the DOM. However, `zone-tab.ts` is itself a LitElement with its own asynchronous render cycle. Its `shadowRoot` may not contain `.zone-name` yet when the `querySelector` executes. The optional chaining means no error is thrown — the click simply does not happen and the auto-focus feature silently does not work on the first creation attempt.

**Fix:** Wait for the child element's update cycle before querying its shadow DOM:

```typescript
await this.updateComplete;
const zoneTab = this.shadowRoot?.querySelector("climate-manager-zone-tab") as LitElement | null;
if (zoneTab) {
  await zoneTab.updateComplete;
  (zoneTab.shadowRoot?.querySelector<HTMLElement>(".zone-name"))?.click();
}
```

---

_Reviewed: 2026-05-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
