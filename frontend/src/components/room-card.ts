/**
 * Climate Manager Panel — Room Card component (UI-03).
 *
 * Expandable card per room. Header (always visible): room name + period badge (D-32)
 * + mode badge + compact 3-item status line (°C / humidity / persons, D-14d).
 * Expanded: TRV entity IDs, associated persons chips, 3-way mode selector (D-20),
 * inline time-bar (when Custom mode, D-20).
 *
 * Auto-save on field blur and select change (D-08). Time-bar saves on
 * interaction end (D-09). Toast feedback on success/error (D-10).
 */

import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

import type { RoomConfig, RoomStatus, DailyProgram, Period, ClimateConfig, Hass } from "../types.js";
import { PERIOD_DISPLAY_NAMES, PERIOD_COLORS } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import { programToDays, dayIndexToKey } from "./global-settings-tab.js";

import "./time-bar.js";
import "./search-picker.js";

export class RoomCard extends LitElement {
  @property({ type: String }) roomId!: string;
  @property({ type: String }) roomName!: string;
  @property({ attribute: false }) config!: RoomConfig;
  /** Entry from status.rooms_status matching this room. */
  @property({ attribute: false }) roomStatus: RoomStatus | null = null;
  /** Full panel config — used to seed per-room override from global program and read persons. */
  @property({ attribute: false }) panelConfig!: ClimateConfig;
  /** Full live status — used for present_persons and global_mode in header. */
  @property({ attribute: false }) status: import("../types.js").StatusPayload | null = null;
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;
  @property({ attribute: false }) hass!: Hass;

  /** Whether the card is expanded. Default: expanded when room_mode is "custom". */
  @state() _expanded = false;

  // Memoize days array — same pattern as global-settings-tab and person-card to
  // prevent time-bar drag-preview from clearing on status-only re-renders.
  // programToDays() creates new array references on every call. Without this,
  // any re-render that happens while the WS round-trip is in flight (e.g. a
  // subscribe_status push) passes a new `days` reference to the time-bar,
  // causing its updated() hook to clear _dragPreviewDays and flash.
  private _lastTimeProgram: DailyProgram | null | undefined = undefined;
  private _cachedDays: Period[][] = [];
  private get _days(): Period[][] {
    const program = this.config?.time_program;
    if (program !== this._lastTimeProgram) {
      this._lastTimeProgram = program;
      this._cachedDays = programToDays(program ?? undefined);
    }
    return this._cachedDays;
  }

  connectedCallback() {
    super.connectedCallback();
    this._expanded = (this.config?.room_mode === "custom");
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

    /* Always-visible 3-item status line in the card header (D-14d, D-32) */
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
      padding: 12px 16px 16px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    /* No TRV badge */
    .no-trv-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      border-radius: 4px;
      background: var(--secondary-background-color);
      color: var(--warning-color, #e65100);
      font-size: 12px;
      margin-bottom: 12px;
    }

    /* TRV section */
    .trv-section {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 8px;
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
      background: var(--secondary-background-color);
    }

    .chip-add ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* 3-way room mode selector (D-20) */
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

    .reset-btn {
      margin-top: 12px;
      margin-bottom: 20px;
      padding: 8px 16px;
      font-size: 14px;
      font-family: inherit;
      color: var(--primary-color, #03a9f4);
      background: none;
      border: 1px solid var(--primary-color, #03a9f4);
      border-radius: 4px;
      cursor: pointer;
    }

    .reset-btn:hover {
      background: var(--secondary-background-color);
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

  private _getPersonPresenceState(personId: string): string {
    const state = this.hass?.states[personId]?.state;
    if (state === "home") return "Home";
    if (state === "not_home") return "Away";
    if (state) return state.charAt(0).toUpperCase() + state.slice(1);
    return "—";
  }

  private _onPersonPicked(e: CustomEvent) {
    e.stopPropagation();
    const personId = (e.detail as { id: string }).id;
    if (!personId) return;
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
  // Room mode handler (D-20)
  // -----------------------------------------------------------------------

  private async _onRoomModeChange(e: Event) {
    const newMode = (e.target as HTMLSelectElement).value as "global" | "frost_protection" | "custom";

    let payload: Partial<RoomConfig>;
    if (newMode === "custom" && !this.config?.time_program) {
      // First switch to Custom: seed from global program (deep copy to avoid shared refs)
      payload = {
        room_mode: "custom",
        time_program: JSON.parse(JSON.stringify(this.panelConfig.global_time_program)) as DailyProgram,
      };
    } else {
      payload = { room_mode: newMode };
    }

    try {
      await this.ws.setRoomConfig(this.roomId, payload);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  // -----------------------------------------------------------------------
  // Schedule override handlers
  // -----------------------------------------------------------------------

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
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }

    e.stopPropagation();
  }

  private async _onResetToGlobal() {
    try {
      await this.ws.resetRoomToGlobalProgram(this.roomId);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------

  /** D-32: render period badge for row 1 of the card header.
   *
   * Returns empty when:
   *   - resolvedMode is "frost_protection" (mode badge already conveys state)
   *   - active_period is null/undefined (no active period to display)
   *
   * Returns gray "Off" badge when globalMode is "off".
   * Otherwise returns a colored pill: "${name} · ${temp}°C".
   */
  private _renderPeriodBadge() {
    const resolvedMode = this.config?.room_mode ?? "global";
    if (resolvedMode === "frost_protection") return html``;

    const globalMode = this.status?.global_mode ?? this.panelConfig?.global_mode ?? "";

    if (globalMode === "off") {
      return html`
        <span
          class="program-badge"
          style="background: var(--secondary-background-color); color: var(--secondary-text-color);"
        >Off</span>
      `;
    }

    const period = this.roomStatus?.active_period ?? null;
    if (period == null) return html``;

    const label = PERIOD_DISPLAY_NAMES[period] ?? period;
    const temp = this.panelConfig?.period_temperatures?.[period];
    const content = temp != null ? `${label} · ${temp}°C` : label;

    return html`
      <span
        class="program-badge"
        style="background: ${PERIOD_COLORS[period]}; color: white;"
      >${content}</span>
    `;
  }

  private _renderHeaderStatus() {
    const s = this.roomStatus;
    const temp = s?.temperature != null ? `${s.temperature}°C` : "—";
    const humidity = s?.humidity != null ? `${s.humidity}%` : "—";
    const globalMode = this.status?.global_mode ?? this.panelConfig?.global_mode ?? "";
    const isPresenceMode = globalMode === "time_program_presences";
    const modeLabels: Record<string, string> = {
      "off": "Off",
      "time_program": "Time program",
      "time_program_presences": "Time & presence",
    };
    const modeLabel = modeLabels[globalMode] ?? globalMode;
    const assignedIds = this._getAssignedPersonIds();
    const totalPersons = assignedIds.length;
    // D-23: present count comes from backend (rooms_status.present_person_count) — no TS-side intersection.
    const presentCount = isPresenceMode
      ? (this.roomStatus?.present_person_count ?? 0)
      : null;
    const personDisplay = presentCount != null
      ? `${presentCount}/${totalPersons}`
      : `${totalPersons}`;
    return html`
      <div class="card-header-status">
        <span class="status-item" title="Mode: ${modeLabel}">
          <ha-icon icon="mdi:thermometer"></ha-icon>
          ${temp}
        </span>
        <span class="status-item">
          <ha-icon icon="mdi:water-percent"></ha-icon>
          ${humidity}
        </span>
        <span class="status-item" title="${isPresenceMode ? `${presentCount} present / ${totalPersons} assigned` : `${totalPersons} assigned`}">
          <ha-icon icon="mdi:account-group"></ha-icon>
          ${personDisplay}
        </span>
      </div>
    `;
  }

  // Cache hui-thermostat-card instances so they are not recreated on every render.
  // On each render we only need to push the updated hass object to each card.
  private _trvCards = new Map<string, HTMLElement>();

  private _getTrvCard(entityId: string): HTMLElement {
    let card = this._trvCards.get(entityId);
    if (!card) {
      card = document.createElement("hui-thermostat-card") as HTMLElement;
      (card as unknown as { setConfig(c: object): void }).setConfig({
        type: "thermostat",
        entity: entityId,
      });
      this._trvCards.set(entityId, card);
    }
    (card as unknown as { hass: unknown }).hass = this.hass;
    return card;
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
        ${entityIds.map((id) => this._getTrvCard(id))}
      </div>
    `;
  }

  private _renderPersonsSection() {
    const assignedPersonIds = this._getAssignedPersonIds();
    const allPersonIds = this._getAllPersonIds();
    const unassignedPersonIds = allPersonIds.filter(
      (id) => !assignedPersonIds.includes(id),
    );

    const pickerItems = unassignedPersonIds.map((id) => ({
      id,
      label: this._getPersonName(id),
      secondary: this._getPersonPresenceState(id),
      icon: "mdi:account",
    }));

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
          ? html`
            <search-picker
              .items=${pickerItems}
              triggerLabel="Add person"
              triggerIcon="mdi:plus"
              placeholder="Search persons…"
              @picked=${(e: CustomEvent) => this._onPersonPicked(e)}
            ></search-picker>
          `
          : ""}
      </div>
    `;
  }

  render() {
    const resolvedMode = this.config?.room_mode ?? "global";

    const badgeClass = resolvedMode === "frost_protection" ? "frost"
      : resolvedMode === "custom" ? "custom"
      : "global";
    const badgeText = resolvedMode === "frost_protection" ? "Frost protection"
      : resolvedMode === "custom" ? "Custom program"
      : "Global program";

    return html`
      <ha-card>
        <div class="card-header-row" @click=${() => { this._expanded = !this._expanded; }}>
          <div class="card-header-left">
            <div class="card-header-top">
              <span class="room-name">${this.roomName}</span>
              ${this._renderPeriodBadge()}
              <span
                class="program-badge ${badgeClass}"
                style=${badgeClass === "frost" ? `background: ${PERIOD_COLORS.frost_protection}; color: white;` : ""}
              >${badgeText}</span>
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
              <!-- 3-way room mode selector (D-20) -->
              <div class="section-label">Mode</div>
              <div class="select-wrapper">
                <select
                  class="mode-select"
                  .value=${resolvedMode}
                  @change=${this._onRoomModeChange}
                >
                  <option value="global" ?selected=${resolvedMode === "global"}>Global program</option>
                  <option value="frost_protection" ?selected=${resolvedMode === "frost_protection"}>Frost protection</option>
                  <option value="custom" ?selected=${resolvedMode === "custom"}>Custom program</option>
                </select>
              </div>

              <!-- Inline time-bar (only in Custom mode) -->
              ${resolvedMode === "custom"
                ? html`
                  <div class="section-label">Schedule</div>
                  <div class="time-bar-section">
                    <climate-manager-time-bar
                      mode="schedule"
                      .days=${this._days}
                      @periods-changed=${this._onPeriodsChanged}
                    ></climate-manager-time-bar>
                  </div>
                  <button class="reset-btn" @click=${() => void this._onResetToGlobal()}>Reset to global configuration</button>
                `
                : ""}

              ${this._renderPersonsSection()}

              <div class="section-label">Climate entities</div>
              ${this._renderTrvSection()}
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
