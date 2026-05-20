/**
 * Climate Manager Panel — Person Card component (UI-04).
 *
 * Expandable card per person. Collapsed: person name + presence mode badge.
 * Expanded: presence mode selector (3-option select), room association
 * chips, presence schedule bar (only visible when mode === "automatic").
 *
 * Auto-save on all changes (D-08). Presence time-bar saves on interaction
 * end (D-09). Toast feedback on success/error (D-10).
 */

import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

import type { PersonConfig, DailyProgram, Period } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import { programToDays, dayIndexToKey } from "./global-settings-tab.js";

import "./time-bar.js";

// Presence mode constants
const PRESENCE_MODE_AUTOMATIC = "automatic";
const PRESENCE_MODE_PRESENT = "present";
const PRESENCE_MODE_ABSENT = "absent";

export interface RoomChoice {
  id: string;
  name: string;
}

export class PersonCard extends LitElement {
  @property({ type: String }) personId!: string;
  @property({ type: String }) personName!: string;
  @property({ attribute: false }) config!: PersonConfig;
  @property({ attribute: false }) roomChoices: RoomChoice[] = [];
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;

  @state() _expanded = false;
  @state() _showRoomAdd = false;

  connectedCallback() {
    super.connectedCallback();
    // Default: expand if any non-default setting (D-15)
    this._expanded = this._isNonDefault();
  }

  private _isNonDefault(): boolean {
    const c = this.config;
    if (!c) return false;
    return (
      (c.mode != null && c.mode !== PRESENCE_MODE_AUTOMATIC) ||
      (c.room_ids != null && c.room_ids.length > 0) ||
      (c.schedule != null && this._hasSchedulePeriods(c.schedule))
    );
  }

  private _hasSchedulePeriods(schedule: DailyProgram): boolean {
    return Object.values(schedule).some((dayPeriods) => dayPeriods.length > 0);
  }

  static styles = css`
    :host {
      display: block;
    }

    ha-card {
      margin-bottom: 12px;
    }

    .card-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      cursor: pointer;
    }

    .card-header-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .person-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--primary-text-color);
    }

    .mode-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 400;
    }

    .mode-badge.automatic {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .mode-badge.present {
      border: 1px solid var(--primary-color, #03a9f4);
      color: var(--primary-color, #03a9f4);
    }

    .mode-badge.absent {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .expand-icon {
      color: var(--secondary-text-color);
      transition: transform 0.2s;
    }

    .expand-icon.expanded {
      transform: rotate(180deg);
    }

    .card-content {
      padding: 0 16px 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    .section-label {
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
      margin: 12px 0 8px;
    }

    .select-wrapper {
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

    /* Chip UI for room associations */
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
      background: rgba(3, 169, 244, 0.08);
    }

    .chip-add ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }

    .add-select {
      padding: 4px 10px;
      font-size: 13px;
      font-family: inherit;
      color: var(--primary-text-color);
      background-color: var(--card-background-color, var(--secondary-background-color));
      border: 1px solid var(--primary-color, #03a9f4);
      border-radius: 16px;
      cursor: pointer;
      outline: none;
    }

    /* Presence schedule */
    .schedule-section {
      margin-top: 12px;
    }
  `;

  // -----------------------------------------------------------------------
  // Save handlers
  // -----------------------------------------------------------------------

  private async _onModeChange(e: Event) {
    const newMode = (e.target as HTMLSelectElement).value;
    if (!newMode) return;
    try {
      await this.ws.setPersonConfig(this.personId, { mode: newMode });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onRoomToggle(roomId: string, add: boolean) {
    const currentIds = [...(this.config?.room_ids ?? [])];
    const newIds = add
      ? currentIds.includes(roomId) ? currentIds : [...currentIds, roomId]
      : currentIds.filter((id) => id !== roomId);
    try {
      await this.ws.setPersonConfig(this.personId, { room_ids: newIds });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private _onAddRoomSelect(e: Event) {
    const sel = e.target as HTMLSelectElement;
    const roomId = sel.value;
    if (!roomId) return;
    this._showRoomAdd = false;
    void this._onRoomToggle(roomId, true);
  }

  private async _onSchedulePeriodsChanged(e: CustomEvent) {
    const { dayIndex, periods } = e.detail as { dayIndex: number; periods: Period[] };

    const currentSchedule = this.config.schedule ?? {
      mon: [], tue: [], wed: [], thu: [], fri: [], sat: [], sun: [],
    };
    const schedule: DailyProgram = { ...currentSchedule };
    const key = dayIndexToKey(dayIndex);
    schedule[key] = periods;

    try {
      await this.ws.setPersonConfig(this.personId, { schedule });
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }

    e.stopPropagation();
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  private _getBadgeInfo(): { cls: string; text: string } {
    const mode = this.config?.mode ?? PRESENCE_MODE_AUTOMATIC;
    switch (mode) {
      case PRESENCE_MODE_PRESENT: return { cls: "present", text: "Present" };
      case PRESENCE_MODE_ABSENT: return { cls: "absent", text: "Absent" };
      default: return { cls: "automatic", text: "Automatic" };
    }
  }

  render() {
    const { cls: badgeCls, text: badgeText } = this._getBadgeInfo();
    const currentMode = this.config?.mode ?? PRESENCE_MODE_AUTOMATIC;
    const isAutomatic = currentMode === PRESENCE_MODE_AUTOMATIC;
    const currentRoomIds = this.config?.room_ids ?? [];
    const unassignedRooms = this.roomChoices.filter((r) => !currentRoomIds.includes(r.id));

    return html`
      <ha-card>
        <div class="card-header-row" @click=${() => { this._expanded = !this._expanded; }}>
          <div class="card-header-left">
            <span class="person-name">${this.personName}</span>
            <span class="mode-badge ${badgeCls}">${badgeText}</span>
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${this._expanded
          ? html`
            <div class="card-content">

              <!-- Presence mode selector -->
              <div class="section-label">Presence mode</div>
              <div class="select-wrapper">
                <select class="mode-select" @change=${this._onModeChange}>
                  <option value=${PRESENCE_MODE_AUTOMATIC} ?selected=${currentMode === PRESENCE_MODE_AUTOMATIC}>Automatic</option>
                  <option value=${PRESENCE_MODE_PRESENT} ?selected=${currentMode === PRESENCE_MODE_PRESENT}>Present</option>
                  <option value=${PRESENCE_MODE_ABSENT} ?selected=${currentMode === PRESENCE_MODE_ABSENT}>Absent</option>
                </select>
              </div>

              <!-- Room associations as chips -->
              <div class="section-label">Room associations</div>
              <div class="chips">
                ${currentRoomIds.map((roomId) => {
                  const room = this.roomChoices.find((r) => r.id === roomId);
                  if (!room) return "";
                  return html`
                    <span class="chip">
                      <ha-icon icon="mdi:home-outline"></ha-icon>
                      ${room.name}
                      <button
                        class="chip-remove"
                        @click=${() => void this._onRoomToggle(roomId, false)}
                      >×</button>
                    </span>
                  `;
                })}
                ${unassignedRooms.length > 0
                  ? this._showRoomAdd
                    ? html`
                      <select class="add-select" @change=${(e: Event) => this._onAddRoomSelect(e)}>
                        <option value="">Select room…</option>
                        ${unassignedRooms.map((r) => html`<option value=${r.id}>${r.name}</option>`)}
                      </select>
                    `
                    : html`
                      <button class="chip-add" @click=${() => { this._showRoomAdd = true; }}>
                        <ha-icon icon="mdi:plus"></ha-icon>
                        Add room
                      </button>
                    `
                  : ""}
              </div>

              <!-- Presence schedule (only in Automatic mode) -->
              ${isAutomatic
                ? html`
                  <div class="section-label">Presence schedule</div>
                  <div class="schedule-section">
                    <climate-manager-time-bar
                      mode="presence"
                      .days=${programToDays(this.config?.schedule)}
                      @periods-changed=${this._onSchedulePeriodsChanged}
                    ></climate-manager-time-bar>
                  </div>
                `
                : ""}
            </div>
          `
          : ""}
      </ha-card>
    `;
  }
}

customElements.define("climate-manager-person-card", PersonCard);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-person-card": PersonCard;
  }
}
