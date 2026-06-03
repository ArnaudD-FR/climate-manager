// SPDX-License-Identifier: MIT
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
  groupDndStyles,
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
  @state() private _dragActive = false;
  @state() private _dragType: "matter" | "tadox" | null = null;

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
    groupDndStyles,
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
   * When pre-heat is active, replaces the period badge with an amber
   * "Pre-heating → XX.X°C" badge so it is visible without expanding the card.
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

    const preheatActive = this.roomStatus?.preheat_active ?? false;
    const preheatTarget = this.roomStatus?.preheat_target ?? null;
    if (preheatActive && preheatTarget != null) {
      return html`
        <span class="program-badge" style="background: #e65100; color: white;"
          >Pre-heating &rarr; ${preheatTarget.toFixed(1)}&deg;C</span
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
      ? this.roomStatus?.present_person_count ?? 0
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
              <span class="chip-temp">${temp}</span>
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

  // -----------------------------------------------------------------------
  // Pre-heat handlers and render (Phase 12 D-11)
  // -----------------------------------------------------------------------

  private async _onPreheatMaxLeadChange(e: Event) {
    const value = (e.target as HTMLInputElement).value;
    const val = parseInt(value, 10);
    if (isNaN(val) || val < 0 || val > 480) return;
    try {
      await this.ws.setRoomConfig(this.roomId, {
        preheat_max_lead_minutes: val,
      });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  // Matter / Tado X DnD handlers

  private _entityName(id: string): string {
    return (
      (this.hass?.states[id]?.attributes?.["friendly_name"] as
        | string
        | undefined) ?? id
    );
  }

  private _startDrag(
    entityId: string,
    type: "matter" | "tadox",
    fromTadoId: string | null,
    e: DragEvent,
  ): void {
    if (!e.dataTransfer) return;
    e.dataTransfer.setData(
      "text/plain",
      JSON.stringify({ entityId, type, fromTadoId }),
    );
    e.dataTransfer.effectAllowed = "move";
    const el = e.currentTarget as HTMLElement;
    e.dataTransfer.setDragImage(el, el.offsetWidth / 2, el.offsetHeight / 2);
    this._dragActive = true;
    this._dragType = type;
  }

  private _onDragEnd(): void {
    this._dragActive = false;
    this._dragType = null;
  }

  private _onMatterDragOver(e: DragEvent): void {
    if (this._dragType !== "matter") return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
  }

  private _onAnyDragOver(e: DragEvent): void {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
  }

  private _onMatterDragEnter(e: DragEvent): void {
    if (this._dragType !== "matter") return;
    (e.currentTarget as HTMLElement).classList.add("drag-over");
  }

  private _onMatterDragLeave(e: DragEvent): void {
    if (this._dragType !== "matter") return;
    const el = e.currentTarget as HTMLElement;
    const rel = e.relatedTarget as Node | null;
    if (rel && el.contains(rel)) return;
    el.classList.remove("drag-over");
  }

  private _parseDragPayload(e: DragEvent): {
    entityId: string;
    type: string;
    fromTadoId: string | null;
  } | null {
    const raw = e.dataTransfer?.getData("text/plain");
    if (!raw) return null;
    try {
      return JSON.parse(raw) as {
        entityId: string;
        type: string;
        fromTadoId: string | null;
      };
    } catch {
      return null;
    }
  }

  private async _onDropOnTado(tadoId: string, e: DragEvent): Promise<void> {
    e.preventDefault();
    (e.currentTarget as HTMLElement).classList.remove("drag-over");
    this._dragActive = false;
    this._dragType = null;
    const d = this._parseDragPayload(e);
    if (!d || d.type !== "matter") return;
    const { entityId: matterId, fromTadoId } = d;
    if (fromTadoId === tadoId) return;
    try {
      if (fromTadoId) {
        const src = this.panelConfig?.matter_mappings?.[fromTadoId] ?? [];
        await this.ws.setMatterMapping(
          fromTadoId,
          src.filter((id) => id !== matterId),
        );
      }
      const existing = this.panelConfig?.matter_mappings?.[tadoId] ?? [];
      if (!existing.includes(matterId)) {
        await this.ws.setMatterMapping(tadoId, [...existing, matterId]);
      }
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onDropOnUnassign(e: DragEvent): Promise<void> {
    e.preventDefault();
    (e.currentTarget as HTMLElement).classList.remove("drag-over");
    this._dragActive = false;
    this._dragType = null;
    const d = this._parseDragPayload(e);
    if (!d) return;
    try {
      if (d.type === "tadox") {
        await this.ws.setMatterMapping(d.entityId, []);
        await this.panel.reloadConfig();
        this.panel.showToast("Saved", false);
        return;
      }
      if (!d.fromTadoId) return;
      const src = this.panelConfig?.matter_mappings?.[d.fromTadoId] ?? [];
      await this.ws.setMatterMapping(
        d.fromTadoId,
        src.filter((id) => id !== d.entityId),
      );
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private _renderClimateSection() {
    const tadoXEntities = this.panelConfig?.tado_x_entities ?? [];
    const roomEntityIds = this.roomStatus?.entity_ids ?? [];
    const roomTadoXIds = roomEntityIds.filter((id) =>
      tadoXEntities.includes(id),
    );
    const matterEntities = this.panelConfig?.matter_entities ?? [];
    const canPair = roomTadoXIds.length > 0 && matterEntities.length > 0;

    if (roomTadoXIds.length === 0 && matterEntities.length === 0) {
      return this._renderTrvSection();
    }

    const mappings = this.panelConfig?.matter_mappings ?? {};
    const allMapped = new Set(Object.values(mappings).flat());
    // First level: room entities that are not Tado X and not
    // already claimed as a group child (mapped Matter).
    const firstLevelOther = roomEntityIds.filter(
      (id) => !tadoXEntities.includes(id) && !allMapped.has(id),
    );
    const firstLevel = [...firstLevelOther, ...roomTadoXIds].sort((a, b) =>
      this._entityName(a).localeCompare(this._entityName(b)),
    );

    return html`
      ${canPair
        ? html`<p class="schedule-hint">
            Drag Matter entities onto a Tado X valve to pair them for sub-minute
            calibration.
          </p>`
        : ""}
      <div class=${this._dragActive ? "climate-pair" : ""}>
        <div class="climate-tree">
          ${firstLevel.map((id) => {
            const isTado = roomTadoXIds.includes(id);
            const s = this.hass?.states[id];
            const name = this._entityName(id);
            const temp =
              s?.attributes?.["current_temperature"] != null
                ? `${s.attributes["current_temperature"]}°C`
                : "—";

            if (!isTado) {
              // Regular or orphan-Matter entity — plain chip
              // (orphan Matter is draggable when canPair)
              const isMatter = matterEntities.includes(id);
              const draggable = canPair && isMatter;
              return html`
                <span
                  class=${`chip${draggable ? " chip-draggable" : ""}`}
                  .draggable=${draggable}
                  @dragstart=${draggable
                    ? (e: DragEvent) => this._startDrag(id, "matter", null, e)
                    : undefined}
                  @dragend=${draggable ? () => this._onDragEnd() : undefined}
                  @click=${() => this._openEntityMoreInfo(id)}
                >
                  <ha-icon icon="mdi:thermometer"></ha-icon>
                  ${name}
                  <span class="chip-temp">${temp}</span>
                </span>
              `;
            }

            // Tado X entity
            const mapped = (mappings[id] ?? [])
              .slice()
              .sort((a, b) =>
                this._entityName(a).localeCompare(this._entityName(b)),
              );
            const isGroup = mapped.length > 0;

            if (isGroup) {
              return html`
                <div
                  class="tado-group"
                  @dragover=${this._onMatterDragOver}
                  @drop=${(e: DragEvent) => void this._onDropOnTado(id, e)}
                  @dragenter=${this._onMatterDragEnter}
                  @dragleave=${this._onMatterDragLeave}
                >
                  <span
                    class=${`chip${canPair ? " chip-draggable" : ""}`}
                    .draggable=${canPair}
                    @dragstart=${canPair
                      ? (e: DragEvent) => this._startDrag(id, "tadox", null, e)
                      : undefined}
                    @dragend=${canPair ? () => this._onDragEnd() : undefined}
                    @click=${() => this._openEntityMoreInfo(id)}
                  >
                    <ha-icon icon="mdi:thermometer"></ha-icon>
                    ${name}
                    <span class="chip-temp">${temp}</span>
                  </span>
                  <div class="matter-children">
                    ${mapped.map((mid) => {
                      const ms = this.hass?.states[mid];
                      const mt =
                        ms?.attributes?.["current_temperature"] != null
                          ? `${ms.attributes["current_temperature"]}°C`
                          : "—";
                      return html`
                        <span
                          class=${`chip${canPair ? " chip-draggable" : ""}`}
                          .draggable=${canPair}
                          @dragstart=${canPair
                            ? (e: DragEvent) =>
                                this._startDrag(mid, "matter", id, e)
                            : undefined}
                          @dragend=${canPair
                            ? () => this._onDragEnd()
                            : undefined}
                          @click=${() => this._openEntityMoreInfo(mid)}
                        >
                          <ha-icon icon="mdi:thermometer"></ha-icon>
                          ${this._entityName(mid)}
                          <span class="chip-temp">${mt}</span>
                        </span>
                      `;
                    })}
                  </div>
                </div>
              `;
            }

            // Ungrouped Tado X — plain chip, drop target for Matter
            return html`
              <span
                class="chip"
                @dragover=${canPair ? this._onMatterDragOver : undefined}
                @drop=${canPair
                  ? (e: DragEvent) => void this._onDropOnTado(id, e)
                  : undefined}
                @dragenter=${canPair ? this._onMatterDragEnter : undefined}
                @dragleave=${canPair ? this._onMatterDragLeave : undefined}
                @click=${() => this._openEntityMoreInfo(id)}
              >
                <ha-icon icon="mdi:thermometer"></ha-icon>
                ${name}
                <span class="chip-temp">${temp}</span>
              </span>
            `;
          })}
        </div>
        ${this._dragActive
          ? html`
              <div
                class="unassign-drop-zone"
                @dragover=${this._onAnyDragOver}
                @drop=${(e: DragEvent) => void this._onDropOnUnassign(e)}
                @dragenter=${(e: DragEvent) =>
                  (e.currentTarget as HTMLElement).classList.add("drag-over")}
                @dragleave=${(e: DragEvent) => {
                  const el = e.currentTarget as HTMLElement;
                  const rel = e.relatedTarget as Node | null;
                  if (!rel || !el.contains(rel))
                    el.classList.remove("drag-over");
                }}
              >
                <ha-icon icon="mdi:link-variant-off"></ha-icon>
                <span>Remove</span>
              </div>
            `
          : ""}
      </div>
    `;
  }

  private _renderPreheatSection() {
    // Derive zone-level enable: Default Zone rooms check top-level flag;
    // custom zone rooms check their zone's preheat_enabled (GAP-01).
    const zoneId = this.config?.zone_id;
    const enabled = zoneId
      ? this.panelConfig?.zones?.[zoneId]?.preheat_enabled ?? false
      : this.panelConfig?.default_zone_preheat_enabled ?? false;

    const maxLead = this.config?.preheat_max_lead_minutes ?? 120;
    const preheatActive = this.roomStatus?.preheat_active ?? false;
    const preheatTarget = this.roomStatus?.preheat_target ?? null;
    const suppressed = this.roomStatus?.preheat_suppressed ?? false;

    if (!enabled && !preheatActive) return html``;

    return html`
      <div class="section-label">Pre-heat</div>
      ${enabled
        ? html`
            <label
              style="display:flex;align-items:center;gap:8px;margin-top:6px;"
            >
              Max lead time (min)
              <input
                type="number"
                min="0"
                max="480"
                step="5"
                .value=${String(maxLead)}
                @change=${this._onPreheatMaxLeadChange}
                style="width:70px;"
              />
            </label>
          `
        : ""}
      ${enabled && suppressed
        ? html`
            <p class="schedule-hint">
              Pre-heat disabled &mdash; presence cannot be scheduled
            </p>
          `
        : ""}
    `;
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
                ${this._renderClimateSection()} ${this._renderPreheatSection()}
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
