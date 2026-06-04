// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — Zone Tab component (UI-04).
 *
 * Renders one zone's editor and is reused for both the Default Zone tab
 * and every custom zone tab. An `isDefault` boolean prop controls whether
 * the delete button is rendered (UI-05).
 *
 * Layout (top-to-bottom per D-04):
 *   1. Delete button / inline confirm row (custom zones only, D-05)
 *   2. Zone name (click-to-edit, D-06 / D-07)
 *   3. Mode picker (native <select>, HA 2026.x)
 *   4. Weekly time-bar
 *   5. Assigned Rooms section (chips + search-picker, D-08 / D-09 / D-10)
 *
 * HA 2026.x compatibility: uses native <input> and native <select> only.
 * No ha-textfield, ha-select, ha-tabs, paper-tab, or ha-dialog.
 *
 * All writes use write-then-reload pattern:
 *   await this.ws.X(); await this.panel.reloadConfig(); this.panel.showToast(…)
 */

import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

import type {
  ClimateConfig,
  ZoneConfig,
  DailyProgram,
  Period,
  RoomConfig,
  StatusPayload,
  Hass,
} from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import { programToDays, dayIndexToKey } from "./global-settings-tab.js";
import {
  chipStyles,
  sectionLabelStyles,
  selectStyles,
  scheduleHintStyles,
  floorGroupLabelStyles,
} from "../shared-styles.js";

import "./time-bar.js";
import "./search-picker.js";

export class ZoneTab extends LitElement {
  // -------------------------------------------------------------------------
  // Public properties
  // -------------------------------------------------------------------------

  /** Full panel config — enumerate rooms and resolve zone/room names. */
  @property({ attribute: false }) config!: ClimateConfig;

  /**
   * Zone ID: "default" for the Default Zone, UUID string for custom zones.
   * "default" routes renameZone to the default_zone sentinel (D-07).
   */
  @property({ attribute: false }) zoneId!: string;

  /**
   * Current zone's name, mode, and time_program.
   * Default Zone: passed from config.default_zone directly (Phase 14 D-14).
   */
  @property({ attribute: false }) zoneConfig!: ZoneConfig;

  /**
   * When true, the delete button is not rendered (UI-05).
   * Also hides chip remove buttons (rooms cannot leave Default Zone).
   */
  @property({ type: Boolean }) isDefault = false;

  /** WS client instance shared from root panel. */
  @property({ attribute: false }) ws!: WsClient;

  /** Reference to root panel for showToast() and reloadConfig(). */
  @property({ attribute: false }) panel!: ClimateManagerPanel;

  /** HA hass object — used for resolving area names. */
  @property({ attribute: false }) hass!: Hass;

  /** Live status — enumerates all TRV rooms, not just configured ones. */
  @property({ attribute: false }) status: StatusPayload | null = null;

  // -------------------------------------------------------------------------
  // Internal state
  // -------------------------------------------------------------------------

  @state() private _confirmingDelete = false;

  // -------------------------------------------------------------------------
  // Memoized days getter
  // Prevents time-bar drag-preview from clearing on status-only re-renders.
  // Keyed by zoneConfig.time_program identity (same as global-settings-tab.ts).
  // -------------------------------------------------------------------------

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

  // -------------------------------------------------------------------------
  // Static styles
  // -------------------------------------------------------------------------

  static styles = [
    chipStyles,
    sectionLabelStyles,
    selectStyles,
    scheduleHintStyles,
    floorGroupLabelStyles,
    css`
      :host {
        display: block;
      }

      /* Delete row (top of zone tab, custom zones only) */
      .delete-row {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 8px;
        justify-content: flex-end;
        margin-top: 24px;
      }

      .delete-btn {
        background: none;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        color: var(--secondary-text-color);
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-family: inherit;
      }

      .delete-btn:hover {
        background: var(--secondary-background-color);
      }

      .cancel-btn {
        background: none;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        color: var(--secondary-text-color);
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-family: inherit;
      }

      .cancel-btn:hover {
        background: var(--secondary-background-color);
      }

      .danger-btn {
        background: var(--error-color, #db4437);
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-family: inherit;
      }

      .danger-btn:hover {
        opacity: 0.9;
      }

      .select-wrapper {
        margin-bottom: 16px;
      }

      .section-divider {
        margin: 16px 0 8px;
      }

      .reset-row {
        display: flex;
        gap: 8px;
        margin-top: 8px;
        margin-bottom: 8px;
        justify-content: flex-end;
      }

      .reset-btn {
        background: none;
        border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
        color: var(--secondary-text-color);
        padding: 5px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 13px;
        font-family: inherit;
      }

      .reset-btn:hover {
        background: var(--secondary-background-color);
      }
    `,
  ];

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  /**
   * Pre-heat toggle — auto-save the zone preheat enable state.
   * Works for both Default Zone (zoneId="default") and custom zones
   * without branching: setZonePreheat accepts both forms.
   */
  private _onPreheatToggle = async (e: Event) => {
    const enabled = (e.target as HTMLInputElement).checked;
    try {
      await this.ws.setZonePreheat(this.zoneId, enabled);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed", true);
    }
  };

  /** Mode select change — auto-save the new zone mode. */
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

  private _onResetToDefault = async () => {
    try {
      if (this.isDefault) {
        await this.ws.resetZoneTimeProgram("default", "default");
      } else {
        await this.ws.resetZoneTimeProgram(this.zoneId, "default");
      }
      await this.panel.reloadConfig();
      this.panel.showToast("Reset to default", false);
    } catch {
      this.panel.showToast("Reset failed", true);
    }
  };

  private _onResetToGlobal = async () => {
    try {
      await this.ws.resetZoneTimeProgram(this.zoneId, "global");
      await this.panel.reloadConfig();
      this.panel.showToast(`Reset to ${this.config.default_zone.name}`, false);
    } catch {
      this.panel.showToast("Reset failed", true);
    }
  };

  /**
   * Time-bar periods-changed — update the zone time program for the day.
   * When isDefault, writes go to the global time program via ws.setTimeProgram
   * When isDefault, writes go to the Default Zone program via
   * ws.setZoneTimeProgram("default", ...) (Phase 14 D-09).
   */
  private _onPeriodsChanged = async (e: CustomEvent) => {
    const { dayIndex, periods } = e.detail as {
      dayIndex: number;
      periods: Period[];
    };
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
      this.panel.showToast("Save failed — retrying...", true);
    }
    e.stopPropagation();
  };

  /**
   * Add a room to this zone (D-09).
   * isDefault: zone_id: null — backend pops zone_id (D-06 sparse model).
   */
  private async _onAddRoom(roomId: string) {
    try {
      if (this.isDefault) {
        await this.ws.setRoomConfig(roomId, {
          zone_id: null as unknown as string | undefined,
        });
      } else {
        await this.ws.setRoomConfig(roomId, { zone_id: this.zoneId });
      }
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  /**
   * Remove a room from a custom zone (D-08).
   * Sends zone_id: null — backend pops zone_id (D-06 sparse model).
   * Absent zone_id = Default Zone member. Not rendered for Default Zone.
   */
  private async _onRemoveRoom(roomId: string) {
    const patch: Partial<RoomConfig> = {
      zone_id: null as unknown as string | undefined,
    };
    try {
      await this.ws.setRoomConfig(roomId, patch);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  /** search-picker @picked event — add the selected room to this zone. */
  private _onRoomPicked(e: CustomEvent) {
    e.stopPropagation();
    const roomId = (e.detail as { id: string }).id;
    if (!roomId) return;
    void this._onAddRoom(roomId);
  }

  /** First click on delete — show inline confirm row (D-05). */
  private _onDeleteClick() {
    this._confirmingDelete = true;
  }

  /** Cancel delete — hide confirm row. */
  private _onCancelDelete() {
    this._confirmingDelete = false;
  }

  /**
   * Confirm delete — delete zone and reload config.
   * On success, main.ts detects missing tab via _validateActiveTab()
   * and falls back to "global". This component does not navigate.
   */
  private async _onConfirmDelete() {
    try {
      await this.ws.deleteZone(this.zoneId);
      await this.panel.reloadConfig();
      this.panel.showToast("Zone deleted", false);
    } catch {
      this.panel.showToast("Delete failed", true);
    }
  }

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  /**
   * Resolve a room's display name from the HA areas registry.
   * Rooms are HA areas; areas[roomId].name is the canonical display name.
   */
  private _getRoomName(roomId: string): string {
    return (
      this.status?.rooms_status?.find((r) => r.area_id === roomId)?.name ??
      this.hass.areas[roomId]?.name ??
      roomId
    );
  }

  /** All TRV room IDs from status; falls back to config.rooms keys. */
  private _allRoomIds(): string[] {
    const fromStatus = this.status?.rooms_status?.filter(
      (r) => r.has_trv !== false,
    );
    if (fromStatus?.length) return fromStatus.map((r) => r.area_id);
    return Object.keys(this.config?.rooms ?? {});
  }

  /**
   * Returns IDs of rooms assigned to this zone.
   * For custom zones: rooms whose zone_id === this.zoneId.
   * Default Zone: rooms with undefined or orphaned zone_id (D-06 phase 4).
   * Universe is all TRV rooms so unconfigured rooms appear.
   */
  private _getAssignedRoomIds(): string[] {
    const zoneKeys = Object.keys(this.config?.zones ?? {});
    return this._allRoomIds().filter((roomId) => {
      const roomConfig: RoomConfig | undefined = this.config?.rooms?.[roomId];
      if (this.isDefault || this.zoneId === "default") {
        // Default Zone: no zone_id OR zone_id not in config.zones (orphan-safe)
        return !roomConfig?.zone_id || !zoneKeys.includes(roomConfig.zone_id);
      }
      return roomConfig?.zone_id === this.zoneId;
    });
  }

  /** Rooms grouped by floor (alpha-sorted), floors descending by level. */
  private _getSortedAssignedRoomGroups(): Array<{
    floorId: string | null;
    floorName: string;
    roomIds: string[];
  }> {
    const assignedIds = this._getAssignedRoomIds();
    const floorGroups = new Map<string | null, string[]>();
    for (const roomId of assignedIds) {
      const floorId = this.hass?.areas?.[roomId]?.floor_id ?? null;
      if (!floorGroups.has(floorId)) floorGroups.set(floorId, []);
      floorGroups.get(floorId)!.push(roomId);
    }
    for (const ids of floorGroups.values()) {
      ids.sort((a, b) =>
        this._getRoomName(a).localeCompare(this._getRoomName(b)),
      );
    }
    const sortedFloorIds = [...floorGroups.keys()]
      .filter((fid): fid is string => fid !== null)
      .sort(
        (a, b) =>
          (this.hass?.floors?.[b]?.level ?? 0) -
          (this.hass?.floors?.[a]?.level ?? 0),
      );
    const result: Array<{
      floorId: string | null;
      floorName: string;
      roomIds: string[];
    }> = sortedFloorIds.map((fid) => ({
      floorId: fid,
      floorName: this.hass?.floors?.[fid]?.name ?? fid,
      roomIds: floorGroups.get(fid)!,
    }));
    const floorless = floorGroups.get(null) ?? [];
    if (floorless.length)
      result.push({ floorId: null, floorName: "", roomIds: floorless });
    return result;
  }

  /**
   * Returns rooms NOT assigned to this zone, shaped for the search-picker.
   * Per D-10: includes rooms in other zones (valid reassignment targets).
   */
  private _getUnassignedRoomItems(): Array<{
    id: string;
    label: string;
    icon?: string;
  }> {
    const assignedIds = new Set(this._getAssignedRoomIds());
    return this._allRoomIds()
      .filter((roomId) => !assignedIds.has(roomId))
      .map((roomId) => ({
        id: roomId,
        label: this._getRoomName(roomId),
        icon: "mdi:home-outline",
      }));
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  private _renderModeDescription() {
    const mode = this.zoneConfig?.mode;
    if (mode === "off") {
      return html`<p class="schedule-hint">
        Zone is off. All assigned rooms are kept at frost protection temperature
        only.
      </p>`;
    }
    if (mode === "time_program_presences") {
      return html`
        <p class="schedule-hint">
          Rooms heat according to the schedule when an assigned person is
          present. While present, the room stays heated from the first
          Normal/Comfort period to the last — Reduced or Frost gaps in between
          are held at the preceding Normal/Comfort temperature. When everyone is
          absent, the room stays at Reduced temperature regardless of the
          schedule.
        </p>
        <p class="schedule-hint">
          <em>Example:</em> schedule Normal 06:00, Reduced 09:00, Normal 17:00,
          Frost 22:00 — if present, the room heats 06:00–22:00 and holds Normal
          temperature during the 09:00–17:00 gap. If absent, the room stays at
          Reduced all day.
        </p>
      `;
    }
    return html`<p class="schedule-hint">
      Rooms follow the weekly schedule. Each period sets the target temperature
      for all assigned rooms.
    </p>`;
  }

  private _getFloorIcon(fid: string): string {
    const floor = this.hass?.floors?.[fid];
    if (floor?.icon) return floor.icon;
    const level = floor?.level ?? 0;
    if (level === -1) return "mdi:home-floor-negative-1";
    if (level < 0) return "mdi:home-floor-b";
    if (level === 1) return "mdi:home-floor-1";
    if (level === 2) return "mdi:home-floor-2";
    if (level === 3) return "mdi:home-floor-3";
    if (level > 3) return "mdi:home-floor-3";
    return "mdi:home-floor-0";
  }

  render() {
    const roomGroups = this._getSortedAssignedRoomGroups();
    const unassignedRooms = this._getUnassignedRoomItems();

    const renderChip = (roomId: string) => html`
      <span class="chip" @click=${() => void this.panel.navigateToRoom(roomId)}>
        <ha-icon icon="mdi:home-outline"></ha-icon>
        ${this._getRoomName(roomId)}
        ${!this.isDefault
          ? html`<button
              class="chip-remove"
              @click=${(e: Event) => {
                e.stopPropagation();
                void this._onRemoveRoom(roomId);
              }}
            >
              ×
            </button>`
          : ""}
      </span>
    `;

    return html`
      <!-- 1. Mode picker -->
      <div
        class="section-label"
        title="Controls how rooms in this zone are heated"
      >
        Mode
      </div>
      <div class="select-wrapper">
        <select class="mode-select" @change=${this._onModeChange}>
          <option value="off" ?selected=${this.zoneConfig.mode === "off"}>
            Off
          </option>
          <option
            value="time_program"
            ?selected=${this.zoneConfig.mode === "time_program"}
          >
            Time program
          </option>
          <option
            value="time_program_presences"
            ?selected=${this.zoneConfig.mode === "time_program_presences"}
          >
            Time program &amp; presences
          </option>
        </select>
      </div>
      ${this._renderModeDescription()}

      <!-- 4. Time-bar -->
      <climate-manager-time-bar
        mode="schedule"
        .days=${this._days}
        @periods-changed=${this._onPeriodsChanged}
      ></climate-manager-time-bar>

      <!-- Reset row: Default Zone gets one button; custom zones get two -->
      <div class="reset-row">
        ${!this.isDefault
          ? html`<button class="reset-btn" @click=${this._onResetToGlobal}>
              Reset to ${this.config.default_zone.name}
            </button>`
          : ""}
        <button class="reset-btn" @click=${this._onResetToDefault}>
          Reset to default
        </button>
      </div>

      <!-- Pre-heat enable toggle (Phase 12 GAP-01) -->
      <div class="section-label">Pre-heat</div>
      <label style="display:flex;align-items:center;gap:8px;cursor:pointer;">
        <input
          type="checkbox"
          .checked=${this.zoneConfig?.preheat_enabled ?? false}
          @change=${this._onPreheatToggle}
        />
        Enable pre-heat for all rooms in this zone
      </label>
      <p class="schedule-hint">
        When enabled, the coordinator may start heating each room in this zone
        ahead of the first occupied period of the day.
      </p>

      <!-- 5. Assigned Rooms section (D-08 / D-09 / D-10) -->
      <div class="section-divider"></div>
      <div class="section-label" title="Rooms that follow this zone's schedule">
        Assigned rooms
      </div>
      ${roomGroups.map(
        (group) => html`
          ${group.floorId !== null
            ? html`<div class="floor-group-label">
                <ha-icon icon=${this._getFloorIcon(group.floorId)}></ha-icon
                >${group.floorName}
              </div>`
            : ""}
          <div class="chips">${group.roomIds.map(renderChip)}</div>
        `,
      )}
      ${unassignedRooms.length > 0
        ? html`
            <div class="chips">
              <search-picker
                .items=${unassignedRooms}
                triggerLabel="Add room"
                triggerIcon="mdi:plus"
                placeholder="Search rooms…"
                @picked=${this._onRoomPicked}
              ></search-picker>
            </div>
          `
        : ""}

      <!-- Delete row (custom zones only, D-05) -->
      ${!this.isDefault
        ? html`
            <div class="delete-row">
              ${this._confirmingDelete
                ? html`
                    <span>Delete zone?</span>
                    <button class="cancel-btn" @click=${this._onCancelDelete}>
                      Cancel
                    </button>
                    <button
                      class="danger-btn"
                      @click=${() => void this._onConfirmDelete()}
                    >
                      Confirm
                    </button>
                  `
                : html`
                    <button class="delete-btn" @click=${this._onDeleteClick}>
                      Delete zone
                    </button>
                  `}
            </div>
          `
        : ""}
    `;
  }
}

customElements.define("climate-manager-zone-tab", ZoneTab);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-zone-tab": ZoneTab;
  }
}
