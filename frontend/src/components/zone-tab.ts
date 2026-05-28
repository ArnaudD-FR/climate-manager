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
 *   await this.ws.X(); await this.panel.reloadConfig(); this.panel.showToast(...)
 */

import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

import type { ClimateConfig, ZoneConfig, DailyProgram, Period, RoomConfig, StatusPayload, Hass } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import { programToDays, dayIndexToKey } from "./global-settings-tab.js";

import "./time-bar.js";
import "./search-picker.js";

export class ZoneTab extends LitElement {
  // -------------------------------------------------------------------------
  // Public properties
  // -------------------------------------------------------------------------

  /** Full panel config — needed to enumerate rooms and resolve zone/room names. */
  @property({ attribute: false }) config!: ClimateConfig;

  /**
   * Zone ID: "default" for the Default Zone, UUID string for custom zones.
   * "default" routes renameZone to backend default_zone_name sentinel (D-07).
   */
  @property({ attribute: false }) zoneId!: string;

  /**
   * Current zone's name, mode, and time_program.
   * For the Default Zone, main.ts synthesizes this from global_mode + global_time_program.
   */
  @property({ attribute: false }) zoneConfig!: ZoneConfig;

  /**
   * When true, the delete button is not rendered (UI-05).
   * Also controls chip remove visibility (rooms cannot be removed from Default Zone).
   */
  @property({ type: Boolean }) isDefault = false;

  /** WS client instance shared from root panel. */
  @property({ attribute: false }) ws!: WsClient;

  /** Reference to root panel for showToast() and reloadConfig(). */
  @property({ attribute: false }) panel!: ClimateManagerPanel;

  /** HA hass object — used for resolving area names. */
  @property({ attribute: false }) hass!: Hass;

  /** Live status — used to enumerate all TRV rooms, not just configured ones. */
  @property({ attribute: false }) status: StatusPayload | null = null;

  // -------------------------------------------------------------------------
  // Internal state
  // -------------------------------------------------------------------------

  @state() private _confirmingDelete = false;

  // -------------------------------------------------------------------------
  // Memoized days getter
  // Prevents time-bar drag-preview from clearing on status-only re-renders.
  // Keyed by zoneConfig.time_program identity (same pattern as global-settings-tab.ts).
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

  static styles = css`
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
      border: 1px solid var(--divider-color, rgba(0,0,0,0.12));
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
      border: 1px solid var(--divider-color, rgba(0,0,0,0.12));
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

    /* Mode select — from global-settings-tab.ts */
    .select-wrapper {
      margin-bottom: 16px;
    }

    .select-label {
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-bottom: 4px;
    }

    .mode-select {
      width: 100%;
      padding: 10px 12px;
      font-size: 16px;
      font-family: inherit;
      color: var(--primary-text-color);
      background-color: var(--card-background-color, var(--secondary-background-color));
      border: 1px solid var(--divider-color);
      border-radius: 4px;
      outline: none;
      cursor: pointer;
    }

    .mode-select:focus {
      border-color: var(--primary-color);
      border-width: 2px;
    }

    /* Section labels — from global-settings-tab.ts */
    .section-divider {
      margin: 16px 0 8px;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
    }

    .section-label {
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
      margin-bottom: 8px;
    }

    /* Chip association UI — from room-card.ts */
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 16px;
      background: var(--secondary-background-color, #f5f5f5);
      border: 1px solid var(--divider-color, #e0e0e0);
      font-size: 13px;
      color: var(--primary-text-color);
    }

    .chip ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }

    .chip-remove {
      background: none;
      border: none;
      padding: 0 0 0 2px;
      margin: 0;
      cursor: pointer;
      color: var(--secondary-text-color);
      font-size: 18px;
      line-height: 1;
      display: flex;
      align-items: center;
    }

    .chip-remove:hover {
      color: var(--error-color, #f44336);
    }

    .chip-add {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      border-radius: 16px;
      background: none;
      border: 1px solid var(--primary-color, #03a9f4);
      font-size: 13px;
      color: var(--primary-color, #03a9f4);
      cursor: pointer;
      font-family: inherit;
    }

    .chip-add:hover {
      background: var(--secondary-background-color);
    }

    .chip-add ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }
  `;

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  /** Mode select change — auto-save the new zone mode. */
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
      this.panel.showToast("Save failed", true);
    }
  };

  /**
   * Time-bar periods-changed event — update the zone time program for the changed day.
   * When isDefault is true, writes go to the global time program via ws.setTimeProgram
   * (the Default Zone is backed by global_time_program per Phase 4 D-02).
   */
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
      this.panel.showToast("Save failed — retrying...", true);
    }
    e.stopPropagation();
  };

  /**
   * Add a room to this zone (D-09).
   * When isDefault is true, sends zone_id: null — Task 1's backend handler interprets
   * null as 'pop zone_id' per D-06 sparse model (gap WR-01 fix).
   */
  private async _onAddRoom(roomId: string) {
    try {
      if (this.isDefault) {
        await this.ws.setRoomConfig(roomId, { zone_id: null as unknown as string | undefined });
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
   * Sends setRoomConfig with zone_id: null — Task 1's backend handler interprets null
   * as 'pop zone_id' per D-06 sparse model (gap CR-03 fix from VERIFICATION 06-04).
   * Absent zone_id = Default Zone member (D-06 phase 4).
   * Not rendered for Default Zone (rooms can't be removed — no other zone to send them to).
   */
  private async _onRemoveRoom(roomId: string) {
    const patch: Partial<RoomConfig> = { zone_id: null as unknown as string | undefined };
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
   * After successful delete, parent main.ts detects missing tab via _validateActiveTab()
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

  /** All TRV room IDs from status; falls back to config.rooms keys when status unavailable. */
  private _allRoomIds(): string[] {
    const fromStatus = this.status?.rooms_status?.filter((r) => r.has_trv !== false);
    if (fromStatus?.length) return fromStatus.map((r) => r.area_id);
    return Object.keys(this.config?.rooms ?? {});
  }

  /**
   * Returns IDs of rooms assigned to this zone.
   * For custom zones: rooms whose zone_id === this.zoneId.
   * For Default Zone: rooms whose zone_id is undefined OR points to a non-existent zone (orphan-safe, D-06 phase 4).
   * Uses all TRV rooms as the universe (not just configured rooms) so unconfigured rooms appear.
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

  /**
   * Returns rooms NOT assigned to this zone, shaped for the search-picker.
   * Per D-10: includes rooms in other zones (valid reassignment targets).
   */
  private _getUnassignedRoomItems(): Array<{ id: string; label: string; icon?: string }> {
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

  render() {
    const assignedRoomIds = this._getAssignedRoomIds();
    const unassignedRooms = this._getUnassignedRoomItems();

    return html`
      <!-- 1. Mode picker -->
      <div class="section-label">Mode</div>
      <div class="select-wrapper">
        <select class="mode-select" @change=${this._onModeChange}>
          <option value="off" ?selected=${this.zoneConfig.mode === "off"}>Off</option>
          <option value="time_program" ?selected=${this.zoneConfig.mode === "time_program"}>Time program</option>
          <option value="time_program_presences" ?selected=${this.zoneConfig.mode === "time_program_presences"}>Time program &amp; presences</option>
        </select>
      </div>

      <!-- 4. Time-bar -->
      <climate-manager-time-bar
        mode="schedule"
        .days=${this._days}
        @periods-changed=${this._onPeriodsChanged}
      ></climate-manager-time-bar>

      <!-- 5. Assigned Rooms section (D-08 / D-09 / D-10) -->
      <div class="section-divider"></div>
      <div class="section-label">Assigned rooms</div>
      <div class="chips">
        ${assignedRoomIds.map((roomId) => html`
          <span class="chip">
            <ha-icon icon="mdi:home-outline"></ha-icon>
            ${this._getRoomName(roomId)}
            ${!this.isDefault
              ? html`<button class="chip-remove" @click=${() => void this._onRemoveRoom(roomId)}>×</button>`
              : ""}
          </span>
        `)}
        ${unassignedRooms.length > 0
          ? html`
            <search-picker
              .items=${unassignedRooms}
              triggerLabel="Add room"
              triggerIcon="mdi:plus"
              placeholder="Search rooms…"
              @picked=${this._onRoomPicked}
            ></search-picker>
          `
          : ""}
      </div>

      <!-- Delete row (custom zones only, D-05) -->
      ${!this.isDefault
        ? html`
          <div class="delete-row">
            ${this._confirmingDelete
              ? html`
                <span>Delete zone?</span>
                <button class="cancel-btn" @click=${this._onCancelDelete}>Cancel</button>
                <button class="danger-btn" @click=${() => void this._onConfirmDelete()}>Confirm</button>
              `
              : html`
                <button class="delete-btn" @click=${this._onDeleteClick}>Delete zone</button>
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
