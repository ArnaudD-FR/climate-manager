/**
 * Climate Manager Panel — Room Card component (UI-03).
 *
 * Expandable card per room. Header (always visible): room name + period
 * badge (D-32) + mode badge + compact 3-item status line (°C / humidity /
 * persons, D-14d). Expanded: TRV entity IDs, associated persons chips,
 * 3-way mode selector (D-20),
 * inline time-bar (when Custom mode, D-20).
 *
 * Auto-save on field blur and select change (D-08). Time-bar saves on
 * interaction end (D-09). Toast feedback on success/error (D-10).
 */

import { LitElement, html, css, type PropertyValues } from "lit";
import { property, state } from "lit/decorators.js";

import type {
  RoomConfig,
  RoomStatus,
  DailyProgram,
  Period,
  ClimateConfig,
  Hass,
} from "../types.js";
import { PERIOD_DISPLAY_NAMES, PERIOD_COLORS, getZoneColor } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import { programToDays, dayIndexToKey } from "./global-settings-tab.js";
import {
  chipStyles,
  sectionLabelStyles,
  selectStyles,
  expandIconStyles,
  scheduleHintStyles,
} from "../shared-styles.js";

import "./time-bar.js";
import "./search-picker.js";

export class RoomCard extends LitElement {
  @property({ type: String }) roomId!: string;
  @property({ type: String }) roomName!: string;
  @property({ attribute: false }) config!: RoomConfig;
  /** Entry from status.rooms_status matching this room. */
  @property({ attribute: false }) roomStatus: RoomStatus | null = null;
  /** Full panel config — seeds custom program; provides persons list. */
  @property({ attribute: false }) panelConfig!: ClimateConfig;
  /** Full live status — used for present_persons and global_mode in header. */
  @property({ attribute: false }) status:
    | import("../types.js").StatusPayload
    | null = null;
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;
  @property({ attribute: false }) hass!: Hass;
  /** Auto-expands card and scrolls it into view for one render cycle. */
  @property({ type: Boolean }) autoExpand = false;

  /** Expanded state. Defaults to true when room_mode is "custom". */
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
    this._expanded = false;
  }

  updated(changedProperties: PropertyValues) {
    if (changedProperties.has("autoExpand") && this.autoExpand) {
      this._expanded = true;
      // setTimeout(0) defers past the microtask queue so Lit's next render
      // cycle (triggered by _expanded=true above) completes before we scroll.
      // updateComplete.then() is not safe here — it may resolve before the
      // expansion render when called from within updated().
      setTimeout(() => {
        const rect = this.getBoundingClientRect();
        this.scrollIntoView({
          behavior: "smooth",
          block: rect.height <= window.innerHeight ? "nearest" : "start",
        });
      }, 0);
    }
  }

  static styles = [
    chipStyles,
    sectionLabelStyles,
    selectStyles,
    expandIconStyles,
    scheduleHintStyles,
    css`
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

      .zone-badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 400;
        border: 1px solid;
        cursor: pointer;
      }

      .zone-badge:hover {
        opacity: 0.8;
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

      /* 3-way room mode selector (D-20) */
      .select-wrapper {
        margin-bottom: 16px;
      }

      /* Inline time bar */
      .time-bar-section {
        margin-top: 12px;
      }

      .reset-btn {
        margin-top: 12px;
        margin-bottom: 12px;
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
    `,
  ];

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
      (this.hass?.states[personId]?.attributes?.["friendly_name"] as
        | string
        | undefined) ??
      personId
        .replace(/^person\./, "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase())
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
    const currentIds = [
      ...(this.panelConfig?.persons?.[personId]?.room_ids ?? []),
    ];
    const newIds = currentIds.includes(this.roomId)
      ? currentIds
      : [...currentIds, this.roomId];
    try {
      await this.ws.setPersonConfig(personId, { room_ids: newIds });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onRemovePerson(personId: string) {
    const currentIds = [
      ...(this.panelConfig?.persons?.[personId]?.room_ids ?? []),
    ];
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
    const newMode = (e.target as HTMLSelectElement).value as
      | "global"
      | "frost_protection"
      | "custom";

    let payload: Partial<RoomConfig>;
    if (newMode === "custom" && !this.config?.time_program) {
      // First switch to Custom: seed from global program (deep copy)
      payload = {
        room_mode: "custom",
        time_program: JSON.parse(
          JSON.stringify(this.panelConfig.global_time_program),
        ) as DailyProgram,
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
    const { dayIndex, periods } = e.detail as {
      dayIndex: number;
      periods: Period[];
    };

    const currentProgram = this.config.time_program ?? {
      mon: [],
      tue: [],
      wed: [],
      thu: [],
      fri: [],
      sat: [],
      sun: [],
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
  // Zone assignment handler (ASSIGN-02)
  // -----------------------------------------------------------------------

  private _getZoneName(): string {
    const zoneId = this.config?.zone_id;
    if (!zoneId) {
      return this.panelConfig?.default_zone_name ?? "Default Zone";
    }
    return (
      this.panelConfig?.zones?.[zoneId]?.name ??
      this.panelConfig?.default_zone_name ??
      "Default Zone"
    );
  }

  private async _onZoneChange(e: Event) {
    const newZoneId = (e.target as HTMLSelectElement).value;
    const patch: Partial<RoomConfig> = newZoneId
      ? { zone_id: newZoneId }
      : { zone_id: null as unknown as string | undefined };
    try {
      await this.ws.setRoomConfig(this.roomId, patch);
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

    const globalMode =
      this.status?.global_mode ?? this.panelConfig?.global_mode ?? "";

    if (globalMode === "off") {
      return html`
        <span
          class="program-badge"
          style="background: var(--secondary-background-color); color: var(--secondary-text-color);"
          >Off</span
        >
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
        >${content}</span
      >
    `;
  }

  private _renderHeaderStatus() {
    const s = this.roomStatus;
    const tempVal =
      s?.temperature != null ? parseFloat(String(s.temperature)) : null;
    const temp =
      tempVal != null && !isNaN(tempVal) ? `${tempVal.toFixed(1)}°C` : "—";
    const humidity = s?.humidity != null ? `${s.humidity}%` : "—";
    const globalMode =
      this.status?.global_mode ?? this.panelConfig?.global_mode ?? "";
    const isPresenceMode = globalMode === "time_program_presences";
    const modeLabels: Record<string, string> = {
      off: "Off",
      time_program: "Time program",
      time_program_presences: "Time & presence",
    };
    const modeLabel = modeLabels[globalMode] ?? globalMode;
    const assignedIds = this._getAssignedPersonIds();
    const totalPersons = assignedIds.length;
    // D-23: present count from backend (rooms_status.present_person_count).
    const presentCount = isPresenceMode
      ? (this.roomStatus?.present_person_count ?? 0)
      : null;
    const personDisplay =
      presentCount != null
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
        <span
          class="status-item"
          title="${isPresenceMode
            ? `${presentCount} present / ${totalPersons} assigned`
            : `${totalPersons} assigned`}"
        >
          <ha-icon icon="mdi:account-group"></ha-icon>
          ${personDisplay}
        </span>
      </div>
    `;
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
      <div class="chips">
        ${entityIds.map((entityId) => {
          const state = this.hass?.states[entityId];
          const name =
            (state?.attributes?.["friendly_name"] as string | undefined) ??
            entityId;
          const temp =
            state?.attributes?.["current_temperature"] != null
              ? `${state.attributes["current_temperature"]}°C`
              : "—";
          return html`
            <span
              class="chip"
              @click=${() => this._openEntityMoreInfo(entityId)}
            >
              <ha-icon icon="mdi:thermometer"></ha-icon>
              ${name}
              <span
                style="color:var(--secondary-text-color);margin-left:4px;font-size:12px;"
                >${temp}</span
              >
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

    const pickerItems = unassignedPersonIds.map((id) => ({
      id,
      label: this._getPersonName(id),
      secondary: this._getPersonPresenceState(id),
      icon: "mdi:account",
    }));

    return html`
      <div class="section-label" title="Persons whose presence heats this room">
        Associated persons
      </div>
      <div class="chips">
        ${assignedPersonIds.map(
          (personId) => html`
            <span
              class="chip"
              @click=${() => void this.panel.navigateToPerson(personId)}
            >
              <ha-icon icon="mdi:account"></ha-icon>
              ${this._getPersonName(personId)}
              <button
                class="chip-remove"
                @click=${(e: Event) => {
                  e.stopPropagation();
                  void this._onRemovePerson(personId);
                }}
              >
                ×
              </button>
            </span>
          `,
        )}
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

  private _renderRoomModeDescription(resolvedMode: string) {
    let text: string;
    if (resolvedMode === "frost_protection") {
      text = "Heating is disabled. Room kept at frost protection temperature.";
    } else if (resolvedMode === "custom") {
      text = "Room uses its own custom schedule. Zone Off mode still applies.";
    } else {
      text = "This room follows the zone's heating schedule.";
    }
    return html`<p class="schedule-hint">${text}</p>`;
  }

  private _openEntityMoreInfo(entityId: string) {
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        bubbles: true,
        composed: true,
        detail: { entityId },
      }),
    );
  }

  render() {
    const resolvedMode = this.config?.room_mode ?? "global";

    const badgeClass =
      resolvedMode === "frost_protection"
        ? "frost"
        : resolvedMode === "custom"
          ? "custom"
          : "global";
    const badgeText =
      resolvedMode === "frost_protection"
        ? "Off"
        : resolvedMode === "custom"
          ? "Custom program"
          : "Zone program";

    return html`
      <ha-card>
        <div
          class="card-header-row"
          @click=${() => {
            this._expanded = !this._expanded;
          }}
        >
          <div class="card-header-left">
            <div class="card-header-top">
              <span class="room-name">${this.roomName}</span>
              ${this._renderPeriodBadge()}
              <span
                class="program-badge ${badgeClass}"
                style=${badgeClass === "frost"
                  ? `background: ${PERIOD_COLORS.frost_protection}; color: white;`
                  : ""}
                >${badgeText}</span
              >
              <span
                class="zone-badge"
                style=${(() => {
                  const c = getZoneColor(this.config?.zone_id);
                  return `background:${c.background};color:${c.color};border-color:${c.border}`;
                })()}
                @click=${(e: Event) => {
                  e.stopPropagation();
                  this.panel.navigateToZone(this.config?.zone_id);
                }}
                >${this._getZoneName()}</span
              >
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
                <div
                  class="section-label"
                  title="Zone: zone sched. Custom: room sched. Off: frost only."
                >
                  Mode
                </div>
                <div class="select-wrapper">
                  <select
                    class="mode-select"
                    .value=${resolvedMode}
                    @change=${this._onRoomModeChange}
                  >
                    <option
                      value="frost_protection"
                      ?selected=${resolvedMode === "frost_protection"}
                    >
                      Off
                    </option>
                    <option
                      value="global"
                      ?selected=${resolvedMode === "global"}
                    >
                      Zone program
                    </option>
                    <option
                      value="custom"
                      ?selected=${resolvedMode === "custom"}
                    >
                      Custom program
                    </option>
                  </select>
                </div>
                ${this._renderRoomModeDescription(resolvedMode)}

                <!-- Zone picker (ASSIGN-02, D-12) -->
                <div
                  class="section-label"
                  title="Zone — rooms in a zone share a schedule"
                >
                  Zone
                </div>
                <div class="select-wrapper">
                  <select class="mode-select" @change=${this._onZoneChange}>
                    <option value="" ?selected=${!this.config?.zone_id}>
                      ${this.panelConfig?.default_zone_name ?? "Default Zone"}
                    </option>
                    ${Object.entries(this.panelConfig?.zones ?? {}).map(
                      ([zoneId, zone]) => html`
                        <option
                          value=${zoneId}
                          ?selected=${this.config?.zone_id === zoneId}
                        >
                          ${zone.name}
                        </option>
                      `,
                    )}
                  </select>
                </div>

                <!-- Inline time-bar (only in Custom mode) -->
                ${resolvedMode === "custom"
                  ? html`
                      <div
                        class="section-label"
                        title="Custom schedule — overrides the zone program"
                      >
                        Schedule
                      </div>
                      <div class="time-bar-section">
                        <climate-manager-time-bar
                          mode="schedule"
                          .days=${this._days}
                          @periods-changed=${this._onPeriodsChanged}
                        ></climate-manager-time-bar>
                      </div>
                      <button
                        class="reset-btn"
                        @click=${() => void this._onResetToGlobal()}
                      >
                        Reset to global configuration
                      </button>
                    `
                  : ""}
                ${this._renderPersonsSection()}

                <div
                  class="section-label"
                  title="TRV climate entities controlled in this room"
                >
                  Climate entities
                </div>
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
