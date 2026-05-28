# Phase 6: Zone & Room Assignment UI - Pattern Map

**Mapped:** 2026-05-28
**Files analyzed:** 6 (1 new, 5 modified)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/components/zone-tab.ts` | component | CRUD + request-response | `frontend/src/components/global-settings-tab.ts` | exact (mode picker + time-bar + write-then-reload) |
| `frontend/src/main.ts` | root component | event-driven + CRUD | self (extend existing) | self-modification |
| `frontend/src/components/room-card.ts` | component | CRUD + request-response | self (extend existing) | self-modification |
| `frontend/src/ws-client.ts` | service | request-response | self (extend existing) | self-modification |
| `frontend/src/components/person-card.ts` | component | display-only | self (extend existing) | self-modification |
| `frontend/src/components/persons-tab.ts` | component | display-only | self (extend existing) | self-modification |

---

## Pattern Assignments

### `frontend/src/components/zone-tab.ts` (new component, CRUD + request-response)

**Primary analog:** `frontend/src/components/global-settings-tab.ts`
**Secondary analog:** `frontend/src/components/room-card.ts` (chip pattern, persons section)

**Imports pattern** (copy from `global-settings-tab.ts` lines 19-27, adapt):
```typescript
import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

import type { ClimateConfig, ZoneConfig, DailyProgram, Period, Hass } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import { programToDays, dayIndexToKey } from "./global-settings-tab.js";

import "./time-bar.js";
import "./search-picker.js";
```

**Property declarations** (copy from `global-settings-tab.ts` lines 66-81, adapt):
```typescript
export class ZoneTab extends LitElement {
  @property({ attribute: false }) config!: ClimateConfig;
  @property({ attribute: false }) zoneId!: string;           // "default" | UUID
  @property({ attribute: false }) zoneConfig!: ZoneConfig;   // mode + time_program + name
  @property({ attribute: false }) isDefault = false;         // hides delete button
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;
  @property({ attribute: false }) hass!: Hass;
  @state() private _editingName = false;
  @state() private _confirmingDelete = false;
```

**Memoized days pattern** (copy verbatim from `global-settings-tab.ts` lines 86-95, adapt field name):
```typescript
// Memoize days array — same pattern as global-settings-tab and room-card.
// Prevents time-bar drag-preview from clearing on status-only re-renders.
private _lastProgram: DailyProgram | undefined = undefined;
private _cachedDays: Period[][] = [];
private get _days(): Period[][] {
  const program = this.zoneConfig?.time_program;
  if (program !== this._lastProgram) {
    this._lastProgram = program;
    this._cachedDays = programToDays(program);
  }
  return this._cachedDays;
}
```

**Mode select pattern** (copy from `global-settings-tab.ts` lines 267-276, adapt command):
```typescript
private _onModeChange = async (e: Event) => {
  const newMode = (e.target as HTMLSelectElement).value;
  if (!newMode || newMode === this.zoneConfig.mode) return;
  try {
    await this.ws.setZoneMode(this.zoneId, newMode);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed", true);
  }
};
```

**Time-bar periods-changed pattern** (copy from `global-settings-tab.ts` lines 316-333, adapt):
```typescript
private _onPeriodsChanged = async (e: CustomEvent) => {
  const { dayIndex, periods } = e.detail as { dayIndex: number; periods: Period[] };
  const program: DailyProgram = { ...this.zoneConfig.time_program };
  const key = dayIndexToKey(dayIndex);
  program[key] = periods;
  try {
    await this.ws.setZoneTimeProgram(this.zoneId, program);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
  e.stopPropagation();
};
```

**Chip pattern for assigned rooms** (copy from `room-card.ts` lines 176-241 CSS + lines 566-592 render, adapt to rooms):
```typescript
// CSS classes to copy verbatim: .chips, .chip, .chip ha-icon, .chip-remove,
// .chip-remove:hover, .chip-add, .chip-add:hover
// (room-card.ts lines 176-241)

// Render pattern:
html`
  <div class="chips">
    ${assignedRoomIds.map((roomId) => html`
      <span class="chip">
        <ha-icon icon="mdi:home-outline"></ha-icon>
        ${getRoomName(roomId)}
        <button class="chip-remove" @click=${() => void this._onRemoveRoom(roomId)}>×</button>
      </span>
    `)}
    ${unassignedRooms.length > 0
      ? html`<search-picker
          .items=${unassignedRooms}
          triggerLabel="Add room"
          triggerIcon="mdi:plus"
          placeholder="Search rooms…"
          @picked=${(e: CustomEvent) => this._onRoomPicked(e)}
        ></search-picker>`
      : ""}
  </div>
`
```

**search-picker @picked handler** (copy from `room-card.ts` lines 339-344):
```typescript
private _onRoomPicked(e: CustomEvent) {
  e.stopPropagation();
  const roomId = (e.detail as { id: string }).id;
  if (!roomId) return;
  void this._onAddRoom(roomId);
}
```

**Add room handler** (write-then-reload, copy from `room-card.ts` lines 346-356, adapt):
```typescript
private async _onAddRoom(roomId: string) {
  try {
    await this.ws.setRoomConfig(roomId, { zone_id: this.zoneId });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}

private async _onRemoveRoom(roomId: string) {
  // Absent zone_id = Default Zone member (sparse model, D-06/D-08 context)
  const patch: Partial<import("../types.js").RoomConfig> = {};
  // Send empty config object — backend removes zone_id key
  try {
    await this.ws.setRoomConfig(roomId, patch);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

**Click-to-edit name pattern** (new pattern, no exact analog — implement inline):
```typescript
// D-06: click-to-edit: styled text → click → <input> → blur/Enter saves → Escape cancels
@state() private _editingName = false;
@state() private _nameInputValue = "";

private _onNameClick() {
  this._nameInputValue = this.zoneConfig.name;
  this._editingName = true;
  this.updateComplete.then(() => {
    this.shadowRoot?.querySelector<HTMLInputElement>(".zone-name-input")?.focus();
  });
}

private async _onNameBlur() {
  if (!this._editingName) return;
  this._editingName = false;
  const newName = this._nameInputValue.trim();
  if (!newName || newName === this.zoneConfig.name) return;
  try {
    await this.ws.renameZone(this.zoneId, newName);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed", true);
  }
}

private _onNameKeydown(e: KeyboardEvent) {
  if (e.key === "Enter") (e.target as HTMLElement).blur();
  if (e.key === "Escape") { this._editingName = false; }
}
```

**Inline delete confirmation pattern** (D-05, no dialog):
```typescript
@state() private _confirmingDelete = false;

// Render: replaces delete button on first click
html`
  ${!this.isDefault
    ? this._confirmingDelete
      ? html`
          <span>Delete zone?</span>
          <button @click=${() => { this._confirmingDelete = false; }}>Cancel</button>
          <button class="danger-btn" @click=${() => void this._onConfirmDelete()}>Confirm</button>
        `
      : html`
          <button class="delete-btn" @click=${() => { this._confirmingDelete = true; }}>Delete zone</button>
        `
    : ""}
`

private async _onConfirmDelete() {
  try {
    await this.ws.deleteZone(this.zoneId);
    await this.panel.reloadConfig();
    // caller (main.ts) listens for a "zone-deleted" event or panel switches tab after reloadConfig
    this.panel.showToast("Zone deleted", false);
  } catch {
    this.panel.showToast("Delete failed", true);
  }
}
```

**Mode select render** (copy from `global-settings-tab.ts` lines 456-463, adapt):
```typescript
html`
  <div class="select-wrapper">
    <label class="select-label">Zone mode</label>
    <select class="mode-select" @change=${this._onModeChange}>
      <option value="off" ?selected=${this.zoneConfig.mode === "off"}>Off</option>
      <option value="time_program" ?selected=${this.zoneConfig.mode === "time_program"}>Time program</option>
      <option value="time_program_presences" ?selected=${this.zoneConfig.mode === "time_program_presences"}>Time program &amp; presences</option>
    </select>
  </div>
`
```

**Time-bar render** (copy from `global-settings-tab.ts` lines 466-474):
```typescript
html`
  <climate-manager-time-bar
    mode="schedule"
    .days=${this._days}
    @periods-changed=${this._onPeriodsChanged}
  ></climate-manager-time-bar>
`
```

**CSS to copy verbatim** (from `global-settings-tab.ts` lines 224-258):
- `.mode-select` + `.mode-select:focus` — native select styling
- `.reset-btn` + `.reset-btn:hover` — outline button styling
- `.section-divider` / `.section-label` — uppercase section headers

**CSS to copy verbatim** (from `room-card.ts` lines 166-241):
- `.chips`, `.chip`, `.chip ha-icon`, `.chip-remove`, `.chip-remove:hover`, `.chip-add`, `.chip-add:hover`

**customElements.define call:**
```typescript
customElements.define("climate-manager-zone-tab", ZoneTab);
```

---

### `frontend/src/main.ts` (root component, extend)

**Analog:** self — already contains the tab-bar and `_renderTabContent` patterns to extend.

**`_activeTab` initialization change** (lines 42-45 — replace union guard with broader check):
```typescript
// BEFORE (lines 42-45):
@state() private _activeTab: string = (() => {
  const t = localStorage.getItem("climate-manager-tab");
  return ["global", "rooms", "persons"].includes(t ?? "") ? t! : "global";
})();

// AFTER (zone IDs are dynamic — validate after config loads):
@state() private _activeTab: string = localStorage.getItem("climate-manager-tab") ?? "global";

// Add a post-load guard in _loadConfig() after this._config is set:
// If _activeTab starts with "zone_" and the UUID doesn't exist in config.zones,
// fall back to "global".
private _validateActiveTab() {
  if (!this._config) return;
  if (this._activeTab === "global" || this._activeTab === "rooms" || this._activeTab === "persons") return;
  if (this._activeTab === "zone_default") return;
  // Custom zone tab: check UUID still exists
  const zoneId = this._activeTab.replace(/^zone_/, "");
  if (!this._config.zones[zoneId]) {
    this._activeTab = "global";
    localStorage.setItem("climate-manager-tab", "global");
  }
}
```

**`_setTab` method** (line 212-215 — no change needed, already accepts string):
```typescript
private _setTab(tab: string) {
  this._activeTab = tab;
  localStorage.setItem("climate-manager-tab", tab);
}
```

**Import additions** (after line 31):
```typescript
import "./components/zone-tab.js";
```

**Tab-bar render extension** (lines 238-251, extend the `.tab-bar` section):
```typescript
// Tab order: Global Settings | Default Zone | [custom zones] | + | Rooms | Persons
html`
  <div class="tab-bar">
    <button class="tab-btn ${this._activeTab === "global" ? "active" : ""}"
      @click=${() => this._setTab("global")}>Overview</button>

    <!-- Default Zone tab -->
    <button class="tab-btn ${this._activeTab === "zone_default" ? "active" : ""}"
      @click=${() => this._setTab("zone_default")}>
      ${this._config.default_zone_name}
    </button>

    <!-- Dynamic custom zone tabs (keyed "zone_<uuid>") -->
    ${Object.entries(this._config.zones).map(([zoneId, zone]) => html`
      <button class="tab-btn ${this._activeTab === "zone_" + zoneId ? "active" : ""}"
        @click=${() => this._setTab("zone_" + zoneId)}>
        ${zone.name}
      </button>
    `)}

    <!-- + button: same .tab-btn class, + symbol only -->
    <button class="tab-btn" title="Add zone" @click=${() => void this._onCreateZone()}>+</button>

    <button class="tab-btn ${this._activeTab === "rooms" ? "active" : ""}"
      @click=${() => this._setTab("rooms")}>Rooms</button>
    <button class="tab-btn ${this._activeTab === "persons" ? "active" : ""}"
      @click=${() => this._setTab("persons")}>Persons</button>
  </div>
`
```

**`_onCreateZone` handler** (add to class):
```typescript
private async _onCreateZone() {
  if (!this._config || !this._ws) return;
  // D-02: default name computed client-side; backend also uses "Zone N" convention
  const newName = `Zone ${Object.keys(this._config.zones).length + 1}`;
  try {
    const newZone = await this._ws.createZone(newName);
    await this._loadConfig();
    // D-03: switch to new zone tab and focus name for rename
    this._setTab("zone_" + newZone.zone_id);
    this.panel.showToast("Zone created", false);  // note: use this.showToast in root
  } catch {
    this.showToast("Create zone failed", true);
  }
}
```

**`_renderTabContent` extension** (lines 261-289, add zone cases to switch):
```typescript
private _renderTabContent() {
  // Zone tab cases (default + custom)
  if (this._activeTab === "zone_default") {
    return html`<climate-manager-zone-tab
      .config=${this._config!}
      .zoneId=${"default"}
      .zoneConfig=${{
        name: this._config!.default_zone_name,
        mode: this._config!.global_mode,
        time_program: this._config!.global_time_program,
      }}
      .isDefault=${true}
      .ws=${this._ws!}
      .panel=${this}
      .hass=${this.hass}
    ></climate-manager-zone-tab>`;
  }
  if (this._activeTab.startsWith("zone_")) {
    const zoneId = this._activeTab.slice(5); // strip "zone_"
    const zoneConfig = this._config!.zones[zoneId];
    if (!zoneConfig) return html``;
    return html`<climate-manager-zone-tab
      .config=${this._config!}
      .zoneId=${zoneId}
      .zoneConfig=${zoneConfig}
      .isDefault=${false}
      .ws=${this._ws!}
      .panel=${this}
      .hass=${this.hass}
    ></climate-manager-zone-tab>`;
  }

  switch (this._activeTab) {
    case "global": /* existing */ ...
    case "rooms":  /* existing */ ...
    case "persons": /* existing */ ...
    default: return html``;
  }
}
```

---

### `frontend/src/components/room-card.ts` (modify)

**Analog:** self — add two features to existing render output.

**Zone badge CSS** (add to static styles after `.program-badge.global` block, lines 131-138):
```css
/* Zone badge — same pill shape as program-badge */
.zone-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 400;
  background: var(--secondary-background-color, #f5f5f5);
  color: var(--secondary-text-color, #757575);
  border: 1px solid var(--divider-color, #e0e0e0);
}
```

**Zone badge render** (add to `.card-header-top` div, lines 608-614, after existing badges):
```typescript
// Helper — determine display name for this room's zone
private _getZoneName(): string {
  const zoneId = this.config?.zone_id;
  if (!zoneId) return this.panelConfig.default_zone_name ?? "Default Zone";
  return this.panelConfig.zones?.[zoneId]?.name ?? this.panelConfig.default_zone_name ?? "Default Zone";
}

// In render() card-header-top:
html`
  <div class="card-header-top">
    <span class="room-name">${this.roomName}</span>
    ${this._renderPeriodBadge()}
    <span class="program-badge ${badgeClass}" ...>${badgeText}</span>
    <span class="zone-badge">${this._getZoneName()}</span>  <!-- NEW -->
  </div>
`
```

**Zone select render** (add in expanded card-content, after mode select wrapper, before persons section, around line 639):
```typescript
// D-12: zone picker below mode picker, above persons section
html`
  <!-- Zone assignment picker -->
  <div class="select-wrapper">
    <label class="select-label">Zone</label>
    <select class="mode-select" @change=${this._onZoneChange}>
      <option value="" ?selected=${!this.config?.zone_id}>
        ${this.panelConfig.default_zone_name ?? "Default Zone"}
      </option>
      ${Object.entries(this.panelConfig.zones ?? {}).map(([zoneId, zone]) => html`
        <option value=${zoneId} ?selected=${this.config?.zone_id === zoneId}>
          ${zone.name}
        </option>
      `)}
    </select>
  </div>
`
```

**Zone change handler** (add after `_onRoomModeChange`, copy write-then-reload pattern):
```typescript
private async _onZoneChange(e: Event) {
  const newZoneId = (e.target as HTMLSelectElement).value;
  // Absent zone_id = Default Zone (sparse model D-06); empty string means default
  const patch: Partial<RoomConfig> = newZoneId
    ? { zone_id: newZoneId }
    : { zone_id: undefined };
  try {
    await this.ws.setRoomConfig(this.roomId, patch);
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

---

### `frontend/src/ws-client.ts` (modify — add 6 zone methods)

**Analog:** self — all 6 new methods follow the exact pattern of existing methods.

**Pattern to copy** (existing `setGlobalMode`, lines 36-40, for single-arg commands):
```typescript
setZoneMode(zoneId: string, mode: string): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/set_zone_mode",
    zone_id: zoneId,
    mode,
  });
}
```

**Pattern to copy** (existing `setTimeProgram`, lines 54-58, for program commands):
```typescript
setZoneTimeProgram(zoneId: string, program: DailyProgram): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/set_zone_time_program",
    zone_id: zoneId,
    program,
  });
}
```

**Full set of 6 methods to add** (after existing `resetTimeProgram`, before `resetRoomToGlobalProgram`):
```typescript
/** Import required: add ZoneConfig to the import list at line 9-16 */
import type { ..., ZoneConfig } from "./types.js";

/** Create a new custom zone. Returns the new zone's id and full ZoneConfig. */
createZone(name: string): Promise<{ id: string } & ZoneConfig> {
  return this.hass.connection.sendMessagePromise<{ id: string } & ZoneConfig>({
    type: "climate_manager/create_zone",
    name,
  });
}

/** Delete a custom zone by UUID. */
deleteZone(zoneId: string): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/delete_zone",
    zone_id: zoneId,
  });
}

/** Rename a zone. Use zone_id="default" for the Default Zone (D-05 phase05 context). */
renameZone(zoneId: string, name: string): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/rename_zone",
    zone_id: zoneId,
    name,
  });
}

/** Set the heating mode for a zone. */
setZoneMode(zoneId: string, mode: string): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/set_zone_mode",
    zone_id: zoneId,
    mode,
  });
}

/** Replace the time program for a zone (all 7 day keys required). */
setZoneTimeProgram(zoneId: string, program: DailyProgram): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/set_zone_time_program",
    zone_id: zoneId,
    program,
  });
}

/** Reset a zone's time program to the global_time_program. */
resetZoneTimeProgram(zoneId: string, target: string): Promise<{ success: boolean }> {
  return this.hass.connection.sendMessagePromise<{ success: boolean }>({
    type: "climate_manager/reset_zone_time_program",
    zone_id: zoneId,
    target,
  });
}
```

---

### `frontend/src/components/person-card.ts` (modify — display label only)

**Target lines** (from actual file):

Line 29: `const PRESENCE_MODE_HA = "ha";` — value unchanged, only display strings change.

Line 373 (`_getBadgeInfo` method — "HA" badge text):
```typescript
// BEFORE (line 373):
case PRESENCE_MODE_HA: return { cls: "ha", text: "HA" };

// AFTER (D-13):
case PRESENCE_MODE_HA: return { cls: "ha", text: "HA home tracking" };
```

Line 411 (mode select option):
```typescript
// BEFORE (line 411):
<option value=${PRESENCE_MODE_HA} ?selected=${currentMode === PRESENCE_MODE_HA}>HA</option>

// AFTER (D-13):
<option value=${PRESENCE_MODE_HA} ?selected=${currentMode === PRESENCE_MODE_HA}>HA home tracking</option>
```

---

### `frontend/src/components/persons-tab.ts` (modify — display label only)

**Target line** (from actual file):

Line 373 does not exist in this file — the badge label is rendered by `person-card.ts`. Verify if `persons-tab.ts` renders any "HA" badge text directly. Based on the file read (74 lines render body), the "HA" badge is fully inside `person-card.ts`. No change needed in `persons-tab.ts` unless a standalone badge is confirmed.

> Note: Re-read `persons-tab.ts` lines 74-120 confirmed: it delegates all badge rendering to `<climate-manager-person-card>`. The CONTEXT.md reference to "line 373" of `persons-tab.ts` appears to be stale — the actual file is 129 lines total. The only change target is `person-card.ts`.

---

## Shared Patterns

### Write-then-reload (all mutating components)
**Source:** `frontend/src/components/global-settings-tab.ts` lines 267-276 (any save handler)
**Apply to:** all handlers in `zone-tab.ts`, `room-card.ts` zone change handler
```typescript
try {
  await this.ws.<method>(...);
  await this.panel.reloadConfig();
  this.panel.showToast("Saved", false);
} catch {
  this.panel.showToast("Save failed — retrying...", true);
}
```

### Memoized days array (all components with time-bar)
**Source:** `frontend/src/components/global-settings-tab.ts` lines 86-95
**Apply to:** `zone-tab.ts`
```typescript
private _lastProgram: DailyProgram | undefined = undefined;
private _cachedDays: Period[][] = [];
private get _days(): Period[][] {
  const program = this.zoneConfig?.time_program;
  if (program !== this._lastProgram) {
    this._lastProgram = program;
    this._cachedDays = programToDays(program);
  }
  return this._cachedDays;
}
```

### Native `<select>` dropdown (HA 2026.x)
**Source:** `frontend/src/components/room-card.ts` lines 254-271 (CSS) + lines 629-638 (render)
**Apply to:** zone mode picker in `zone-tab.ts`, zone assignment picker in `room-card.ts`
CSS classes: `.select-wrapper`, `.select-label`, `.mode-select`, `.mode-select:focus`

### CSS button tab bar (HA 2026.x)
**Source:** `frontend/src/main.ts` lines 90-121
**Apply to:** dynamic zone tabs in `main.ts` tab-bar
CSS classes: `.tab-bar`, `.tab-btn`, `.tab-btn.active`, `.tab-btn:hover:not(.active)`

### Chip association UI (chips + search-picker add)
**Source:** `frontend/src/components/room-card.ts` lines 176-241 (CSS) + lines 566-591 (render)
**Apply to:** assigned rooms section in `zone-tab.ts`
CSS classes: `.chips`, `.chip`, `.chip ha-icon`, `.chip-remove`, `.chip-remove:hover`

### search-picker usage
**Source:** `frontend/src/components/room-card.ts` lines 579-590
**Source:** `frontend/src/components/person-card.ts` lines 435-449
**Apply to:** room picker in `zone-tab.ts`
```typescript
<search-picker
  .items=${items}           // {id, label, secondary?, icon?}[]
  triggerLabel="Add room"
  triggerIcon="mdi:plus"
  placeholder="Search rooms…"
  @picked=${(e: CustomEvent) => handler(e)}
></search-picker>
// handler reads: (e.detail as { id: string }).id
```

---

## No Analog Found

All files have close analogs in the codebase. No items.

---

## Metadata

**Analog search scope:** `frontend/src/` and `frontend/src/components/`
**Files scanned:** 11 TypeScript source files (all files in scope)
**Pattern extraction date:** 2026-05-28
