/**
 * Climate Manager Panel — Room Card component (UI-03).
 *
 * Expandable card per room. Header (always visible): room name + program
 * badge + compact status line (°C / humidity / active period, D-14c).
 * Expanded: TRV entity IDs, associated persons chips, override toggle,
 * inline time-bar (when override enabled).
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
  /** Full panel config — used to seed per-room override from global program and read persons. */
  @property({ attribute: false }) panelConfig!: ClimateConfig;
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;
  @property({ attribute: false }) hass!: Hass;

  /** Whether the card is expanded. Default: expanded when has custom time_program. */
  @state() _expanded = false;
  @state() _showPersonAdd = false;

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
      flex-direction: column;
      gap: 4px;
      min-width: 0;
    }

    .card-header-top {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .room-name {
      font-size: 16px;
      font-weight: 600;
      color: var(--primary-text-color);
    }

    /* Always-visible status line in the card header (D-14c) */
    .card-header-status {
      display: flex;
      gap: 12px;
      font-size: 13px;
      color: var(--secondary-text-color);
    }

    .card-header-status .status-item {
      display: flex;
      align-items: center;
      gap: 3px;
    }

    .card-header-status .status-item ha-icon {
      width: 15px;
      height: 15px;
      --mdc-icon-size: 15px;
      flex-shrink: 0;
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

    /* Person / room association chips */
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
  // Person association handlers
  // -----------------------------------------------------------------------

  private _getAssignedPersonIds(): string[] {
    const persons = this.panelConfig?.persons ?? {};
    return Object.entries(persons)
      .filter(([, cfg]) => cfg.room_ids?.includes(this.roomId))
      .map(([id]) => id);
  }

  private _getAllPersonIds(): string[] {
    const fromHass = Object.keys(this.hass?.states ?? {}).filter((id) =>
      id.startsWith("person."),
    );
    const fromConfig = Object.keys(this.panelConfig?.persons ?? {});
    return [...new Set([...fromHass, ...fromConfig])];
  }

  private _getPersonName(personId: string): string {
    return (
      (this.hass?.states[personId]?.attributes?.["friendly_name"] as string | undefined) ??
      personId.replace(/^person\./, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    );
  }

  private _onAddPersonSelect(e: Event) {
    const sel = e.target as HTMLSelectElement;
    const personId = sel.value;
    if (!personId) return;
    this._showPersonAdd = false;
    void this._onAddPerson(personId);
  }

  private async _onAddPerson(personId: string) {
    const currentIds = [...(this.panelConfig?.persons?.[personId]?.room_ids ?? [])];
    const newIds = currentIds.includes(this.roomId) ? currentIds : [...currentIds, this.roomId];
    try {
      await this.ws.setPersonConfig(personId, { room_ids: newIds });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onRemovePerson(personId: string) {
    const currentIds = [...(this.panelConfig?.persons?.[personId]?.room_ids ?? [])];
    const newIds = currentIds.filter((id) => id !== this.roomId);
    try {
      await this.ws.setPersonConfig(personId, { room_ids: newIds });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  // -----------------------------------------------------------------------
  // Schedule override handlers
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

  private _renderHeaderStatus() {
    const s = this.roomStatus;
    const temp = s?.temperature != null ? `${s.temperature}°C` : "—";
    const humidity = s?.humidity != null ? `${s.humidity}%` : "—";
    const period = s?.active_period ?? "—";
    return html`
      <div class="card-header-status">
        <span class="status-item">
          <ha-icon icon="mdi:thermometer"></ha-icon>
          ${temp}
        </span>
        <span class="status-item">
          <ha-icon icon="mdi:water-percent"></ha-icon>
          ${humidity}
        </span>
        <span class="status-item">
          <ha-icon icon="mdi:clock-outline"></ha-icon>
          ${period}
        </span>
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

  private _renderPersonsSection() {
    const assignedPersonIds = this._getAssignedPersonIds();
    const allPersonIds = this._getAllPersonIds();
    const unassignedPersonIds = allPersonIds.filter(
      (id) => !assignedPersonIds.includes(id),
    );

    return html`
      <div class="section-label">Associated persons</div>
      <div class="chips">
        ${assignedPersonIds.map((personId) => html`
          <span class="chip">
            <ha-icon icon="mdi:account"></ha-icon>
            ${this._getPersonName(personId)}
            <button
              class="chip-remove"
              @click=${() => void this._onRemovePerson(personId)}
            >×</button>
          </span>
        `)}
        ${unassignedPersonIds.length > 0
          ? this._showPersonAdd
            ? html`
              <select class="add-select" @change=${(e: Event) => this._onAddPersonSelect(e)}>
                <option value="">Select person…</option>
                ${unassignedPersonIds.map((id) => html`
                  <option value=${id}>${this._getPersonName(id)}</option>
                `)}
              </select>
            `
            : html`
              <button class="chip-add" @click=${() => { this._showPersonAdd = true; }}>
                <ha-icon icon="mdi:plus"></ha-icon>
                Add person
              </button>
            `
          : ""}
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
            <div class="card-header-top">
              <span class="room-name">${this.roomName}</span>
              <span class="program-badge ${badgeClass}">${badgeText}</span>
            </div>
            ${this._renderHeaderStatus()}
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${this._expanded
          ? html`
            <div class="card-content">
              ${this._renderTrvSection()}
              ${this._renderPersonsSection()}

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
