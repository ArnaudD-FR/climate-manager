/**
 * Climate Manager Panel — Person Card component (UI-04).
 *
 * Expandable card per person. Collapsed: person name + presence mode badge + presence dot.
 * Expanded: presence mode selector (4-option select), room association
 * chips, presence schedule bar (only visible when mode === "scheduled").
 *
 * Auto-save on all changes (D-08). Presence time-bar saves on interaction
 * end (D-09). Toast feedback on success/error (D-10).
 * D-15 (updated): always collapsed by default.
 * D-21: four presence modes — scheduled, ha, force_present, force_absent.
 * D-22: default schedule seeded on first switch to scheduled mode.
 */

import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

import type { PersonConfig, DailyProgram, Period, StatusPayload } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import { programToDays, dayIndexToKey } from "./global-settings-tab.js";

import "./time-bar.js";
import "./search-picker.js";

// Presence mode constants (D-21)
const PRESENCE_MODE_SCHEDULED = "scheduled";
const PRESENCE_MODE_HA = "ha";
const PRESENCE_MODE_FORCE_PRESENT = "force_present";
const PRESENCE_MODE_FORCE_ABSENT = "force_absent";

// Default schedule seeded when switching to Scheduled mode with no existing schedule (D-22)
const DEFAULT_SCHEDULE: DailyProgram = {
  mon: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  tue: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  wed: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  thu: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  fri: [{ start: "00:00", state: "present" }, { start: "08:00", state: "absent" }, { start: "18:00", state: "present" }],
  sat: [{ start: "00:00", state: "present" }],
  sun: [{ start: "00:00", state: "present" }],
};

export interface RoomChoice {
  id: string;
  name: string;
  /** Optional floor name shown as secondary text in the add-room search-picker (D-19). */
  secondary?: string;
}

export class PersonCard extends LitElement {
  @property({ type: String }) personId!: string;
  @property({ type: String }) personName!: string;
  @property({ attribute: false }) config!: PersonConfig;
  @property({ attribute: false }) roomChoices: RoomChoice[] = [];
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;
  @property({ attribute: false }) status: StatusPayload | null = null;

  @state() _expanded = false;

  connectedCallback() {
    super.connectedCallback();
    // D-15 (updated): always collapsed by default
    this._expanded = false;
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

    .mode-badge.scheduled {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .mode-badge.force-present {
      border: 1px solid var(--primary-color, #03a9f4);
      color: var(--primary-color, #03a9f4);
    }

    .mode-badge.force-absent {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .mode-badge.ha {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .presence-dot {
      font-size: 12px;
      line-height: 1;
    }

    .presence-dot.present {
      color: var(--success-color, #4caf50);
    }

    .presence-dot.absent {
      color: var(--secondary-text-color, #9e9e9e);
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
      background: var(--secondary-background-color);
    }

    .chip-add ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
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
      // D-22: seed default schedule when switching to Scheduled with no existing schedule
      const hasSchedule =
        !!this.config?.schedule &&
        Object.values(this.config.schedule).some((day) => day.length > 0);

      if (newMode === PRESENCE_MODE_SCHEDULED && !hasSchedule) {
        await this.ws.setPersonConfig(this.personId, { mode: newMode, schedule: DEFAULT_SCHEDULE });
      } else {
        await this.ws.setPersonConfig(this.personId, { mode: newMode });
      }
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
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }

    e.stopPropagation();
  }

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  private _isCurrentlyPresent(): boolean {
    return this.status?.present_persons?.includes(this.personId) ?? false;
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  private _getBadgeInfo(): { cls: string; text: string } {
    const mode = this.config?.mode ?? PRESENCE_MODE_SCHEDULED;
    switch (mode) {
      case PRESENCE_MODE_FORCE_PRESENT: return { cls: "force-present", text: "Force Present" };
      case PRESENCE_MODE_FORCE_ABSENT: return { cls: "force-absent", text: "Force Absent" };
      case PRESENCE_MODE_HA: return { cls: "ha", text: "HA" };
      default: return { cls: "scheduled", text: "Scheduled" };
    }
  }

  render() {
    const { cls: badgeCls, text: badgeText } = this._getBadgeInfo();
    const currentMode = this.config?.mode ?? PRESENCE_MODE_SCHEDULED;
    const isScheduled = currentMode === PRESENCE_MODE_SCHEDULED;
    const currentRoomIds = this.config?.room_ids ?? [];
    const unassignedRooms = this.roomChoices.filter((r) => !currentRoomIds.includes(r.id));

    return html`
      <ha-card>
        <div class="card-header-row" @click=${() => { this._expanded = !this._expanded; }}>
          <div class="card-header-left">
            <span
              class="presence-dot ${this._isCurrentlyPresent() ? "present" : "absent"}"
              title="Currently ${this._isCurrentlyPresent() ? "present" : "absent"}"
            >●</span>
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
                  <option value=${PRESENCE_MODE_SCHEDULED} ?selected=${currentMode === PRESENCE_MODE_SCHEDULED}>Scheduled</option>
                  <option value=${PRESENCE_MODE_HA} ?selected=${currentMode === PRESENCE_MODE_HA}>HA</option>
                  <option value=${PRESENCE_MODE_FORCE_PRESENT} ?selected=${currentMode === PRESENCE_MODE_FORCE_PRESENT}>Force Present</option>
                  <option value=${PRESENCE_MODE_FORCE_ABSENT} ?selected=${currentMode === PRESENCE_MODE_FORCE_ABSENT}>Force Absent</option>
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
                  ? html`
                    <search-picker
                      .items=${unassignedRooms.map((r) => ({
                        id: r.id,
                        label: r.name,
                        secondary: r.secondary,
                        icon: "mdi:home-outline",
                      }))}
                      triggerLabel="Add room"
                      triggerIcon="mdi:plus"
                      placeholder="Search rooms…"
                      @picked=${(e: CustomEvent) => { const {id} = e.detail as {id: string}; void this._onRoomToggle(id, true); }}
                    ></search-picker>
                  `
                  : ""}
              </div>

              <!-- Presence schedule (only in Scheduled mode) -->
              ${isScheduled
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
