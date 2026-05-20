/**
 * Climate Manager Panel — Room Card component (UI-03).
 *
 * Expandable card per room. Collapsed: room name + program badge.
 * Expanded: live status row, TRV entity IDs (read-only), optional sensor
 * fields (editable), override toggle, inline time-bar (when override enabled).
 *
 * Auto-save on field blur and toggle change (D-08). Time-bar saves on
 * interaction end (D-09). Toast feedback on success/error (D-10).
 */

import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

import type { RoomConfig, RoomStatus, DailyProgram, Period, ClimateConfig, Hass } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import { programToDays, dayIndexToKey } from "./global-settings-tab.js";

import "./time-bar.js";

export class RoomCard extends LitElement {
  @property({ type: String }) roomId!: string;
  @property({ type: String }) roomName!: string;
  @property({ attribute: false }) config!: RoomConfig;
  /** Entry from status.rooms_status matching this room. */
  @property({ attribute: false }) roomStatus: RoomStatus | null = null;
  /** Full panel config — used to seed per-room override from global program. */
  @property({ attribute: false }) panelConfig!: ClimateConfig;
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;
  @property({ attribute: false }) hass!: Hass;

  /** Whether the card is expanded. Default: expanded when has custom time_program. */
  @state() _expanded = false;

  connectedCallback() {
    super.connectedCallback();
    // Default: expand if this room has a custom time program override (D-14)
    this._expanded = !!this.config?.time_program;
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

    .room-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--primary-text-color);
    }

    .program-badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 400;
    }

    .program-badge.custom {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
    }

    .program-badge.global {
      background: var(--secondary-background-color, #f5f5f5);
      color: var(--secondary-text-color, #757575);
    }

    .card-content {
      padding: 0 16px 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    /* Live status row */
    .status-row {
      display: flex;
      gap: 16px;
      padding: 12px 0 8px;
      font-size: 14px;
      color: var(--secondary-text-color);
      flex-wrap: wrap;
    }

    .status-item {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .status-item ha-icon {
      width: 18px;
      height: 18px;
      --mdc-icon-size: 18px;
      color: var(--secondary-text-color);
    }

    /* No TRV badge */
    .no-trv-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      border-radius: 4px;
      background: rgba(255, 152, 0, 0.12);
      color: #e65100;
      font-size: 12px;
      margin-bottom: 12px;
    }

    /* TRV entity chips */
    .trv-section {
      margin-bottom: 12px;
    }

    .section-label {
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
      margin-bottom: 8px;
    }

    .trv-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      margin: 0 4px 6px 0;
      border-radius: 16px;
      background: var(--secondary-background-color, #f5f5f5);
      border: 1px solid var(--divider-color, #e0e0e0);
      font-size: 13px;
      color: var(--primary-text-color);
      cursor: pointer;
      transition: background 0.15s;
    }

    .trv-chip:hover {
      background: var(--primary-color);
      color: var(--text-primary-color, #fff);
      border-color: var(--primary-color);
    }

    .trv-chip ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* Override toggle row */
    .override-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 0;
      margin-bottom: 8px;
    }

    .override-label {
      font-size: 14px;
      color: var(--primary-text-color);
    }

    /* Inline time bar */
    .time-bar-section {
      margin-top: 12px;
    }

    .expand-icon {
      color: var(--secondary-text-color);
      transition: transform 0.2s;
    }

    .expand-icon.expanded {
      transform: rotate(180deg);
    }
  `;

  // -----------------------------------------------------------------------
  // Save handlers
  // -----------------------------------------------------------------------

  private async _onOverrideToggle(e: Event) {
    const checkbox = e.target as HTMLElement & { checked: boolean };
    let timeProgram: DailyProgram | null;

    if (checkbox.checked) {
      // Enabling override — seed from global program (or empty program if none)
      const globalProgram = this.panelConfig?.global_time_program;
      timeProgram = globalProgram
        ? { ...globalProgram }
        : { mon: [], tue: [], wed: [], thu: [], fri: [], sat: [], sun: [] };
    } else {
      // Disabling override — clear the per-room program
      timeProgram = null;
    }

    try {
      await this.ws.setRoomConfig(this.roomId, { time_program: timeProgram });
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onPeriodsChanged(e: CustomEvent) {
    const { dayIndex, periods } = e.detail as { dayIndex: number; periods: Period[] };

    const currentProgram = this.config.time_program ?? {
      mon: [], tue: [], wed: [], thu: [], fri: [], sat: [], sun: [],
    };
    const program: DailyProgram = { ...currentProgram };
    const key = dayIndexToKey(dayIndex);
    program[key] = periods;

    try {
      await this.ws.setRoomConfig(this.roomId, { time_program: program });
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }

    e.stopPropagation();
  }

  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------

  private _renderStatusRow() {
    const s = this.roomStatus;
    return html`
      <div class="status-row">
        ${s?.temperature != null
          ? html`<span class="status-item">
              <ha-icon icon="mdi:thermometer"></ha-icon>
              ${s.temperature}°C
            </span>`
          : ""}
        ${s?.humidity != null
          ? html`<span class="status-item">
              <ha-icon icon="mdi:water-percent"></ha-icon>
              ${s.humidity}%
            </span>`
          : ""}
        ${s?.active_period
          ? html`<span class="status-item">
              <ha-icon icon="mdi:clock-outline"></ha-icon>
              ${s.active_period}
            </span>`
          : ""}
      </div>
    `;
  }

  private _openMoreInfo(entityId: string) {
    this.dispatchEvent(new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId },
    }));
  }

  private _renderTrvSection() {
    const entityIds = this.roomStatus?.entity_ids ?? [];

    if (entityIds.length === 0) {
      return html`
        <div class="no-trv-badge">
          <ha-icon icon="mdi:alert"></ha-icon>
          No climate entities
        </div>
      `;
    }

    return html`
      <div class="trv-section">
        <div class="section-label">Climate entities</div>
        ${entityIds.map((id) => {
          const name = this.hass?.states[id]?.attributes?.["friendly_name"] ?? id;
          return html`
            <span class="trv-chip" @click=${() => this._openMoreInfo(id)}>
              <ha-icon icon="mdi:radiator"></ha-icon>
              ${name}
            </span>
          `;
        })}
      </div>
    `;
  }

  render() {
    const hasCustomProgram = !!this.config?.time_program;
    const badgeClass = hasCustomProgram ? "custom" : "global";
    const badgeText = hasCustomProgram ? "Custom program" : "Global program";

    return html`
      <ha-card>
        <div class="card-header-row" @click=${() => { this._expanded = !this._expanded; }}>
          <div class="card-header-left">
            <span class="room-name">${this.roomName}</span>
            <span class="program-badge ${badgeClass}">${badgeText}</span>
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${this._expanded
          ? html`
            <div class="card-content">
              ${this._renderStatusRow()}
              ${this._renderTrvSection()}

              <!-- Override toggle -->
              <div class="override-row">
                <span class="override-label">Override global time program</span>
                <ha-switch
                  .checked=${hasCustomProgram}
                  @change=${this._onOverrideToggle}
                ></ha-switch>
              </div>

              <!-- Inline time-bar (only when override enabled) -->
              ${hasCustomProgram
                ? html`
                  <div class="time-bar-section">
                    <climate-manager-time-bar
                      mode="schedule"
                      .days=${programToDays(this.config.time_program)}
                      @periods-changed=${this._onPeriodsChanged}
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

customElements.define("climate-manager-room-card", RoomCard);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-room-card": RoomCard;
  }
}
