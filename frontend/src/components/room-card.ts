// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — Room Card component (UI-03).
 *
 * Expandable card per room. Header (always visible): room name + period
 * badge (D-32) + compact 3-item status line (°C / humidity / persons,
 * D-14d). Expanded: TRV entity IDs, associated persons chips, zone picker.
 *
 * Auto-save on field blur and select change. Toast feedback on
 * success/error (D-10).
 */

import { LitElement, html, css, nothing, type PropertyValues } from "lit";
import { property, state } from "lit/decorators.js";

import type { RoomConfig, RoomStatus, ClimateConfig, Hass } from "../types.js";
import { PERIOD_DISPLAY_NAMES, PERIOD_COLORS, getZoneColor } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import {
  chipStyles,
  sectionLabelStyles,
  selectStyles,
  expandIconStyles,
  scheduleHintStyles,
  groupDndStyles,
} from "../shared-styles.js";

import {
  createHistoryCard,
  historyPath,
  navigateTo,
  openMoreInfo,
  sharesClimateDevice,
  validEntityIds,
  type LovelaceCard,
} from "../ha-nav.js";
import { haEntityAdd, haItemChip, haNumber, haSelect } from "../ha-controls.js";

/** History graph durations offered in the card (hours). */
const HISTORY_HOURS: Array<[number, string]> = [
  [6, "6 h"],
  [24, "24 h"],
  [72, "3 days"],
  [168, "7 days"],
];
const HISTORY_HOURS_KEY = "climate-manager-history-hours";

/** Zone select value of the Default Zone (rooms without zone_id). */
const DEFAULT_ZONE_VALUE = "default";
const DEFAULT_HISTORY_HOURS = 24;
const ANTICIPATION_HINT =
  "Boost released when the target is this close at the current speed;" +
  " tuned on the overshoot";

/** Stored history duration (shared by all room cards), or the default. */
function loadHistoryHours(): number {
  try {
    const hours = Number(localStorage.getItem(HISTORY_HOURS_KEY));
    if (HISTORY_HOURS.some(([h]) => h === hours)) return hours;
  } catch {
    // storage unavailable (private window, blocked site data)
  }
  return DEFAULT_HISTORY_HOURS;
}

export class RoomCard extends LitElement {
  @property({ type: String }) roomId!: string;
  @property({ type: String }) roomName!: string;
  @property({ attribute: false }) config!: RoomConfig;
  /** Entry from status.rooms_status matching this room. */
  @property({ attribute: false }) roomStatus: RoomStatus | null = null;
  /** Full panel config — seeds custom program; provides persons list. */
  @property({ attribute: false }) panelConfig!: ClimateConfig;
  /** Full live status — used for present_persons and default zone mode. */
  @property({ attribute: false }) status:
    | import("../types.js").StatusPayload
    | null = null;
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;
  @property({ attribute: false }) hass!: Hass;
  /** Auto-expands card and scrolls it into view for one render cycle. */
  @property({ type: Boolean }) autoExpand = false;

  /** Expanded state. Defaults to collapsed. */
  @state() _expanded = false;
  @state() private _dragActive = false;
  @state() private _dragType: "matter" | "parent" | null = null;
  /** Native history-graph card, created lazily while expanded. */
  @state() private _historyCard: LovelaceCard | null = null;
  @state() private _historyHours = loadHistoryHours();
  /** Entities + duration the current history card was built for. */
  private _historyKey = "";

  connectedCallback() {
    super.connectedCallback();
    this._expanded = false;
  }

  updated(changedProperties: PropertyValues) {
    if (this._expanded) {
      void this._syncHistoryCard();
      if (changedProperties.has("hass") && this._historyCard) {
        this._historyCard.hass = this.hass;
      }
    }
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

      /* Period badge → room period sensor more-info (history) */
      .badge-link {
        display: inline-flex;
        cursor: pointer;
      }

      .badge-link:hover .program-badge {
        filter: brightness(1.15);
        text-decoration: underline;
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

      /* History section (native history-graph card) */
      .history-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 16px 0 8px;
      }

      .history-header .section-label {
        margin-bottom: 0;
      }

      .minutes {
        width: 140px;
      }

      .history-hours {
        min-width: 120px;
      }

      .history-open {
        --mdc-icon-button-size: 28px;
        --mdc-icon-size: 18px;
        color: var(--secondary-text-color);
      }

      .history-graph {
        --ha-card-box-shadow: none;
        --ha-card-border-width: 0;
        --ha-card-background: transparent;
        margin: 0 -16px;
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

      .select-wrapper {
        margin-bottom: 16px;
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
  // Zone assignment handler (ASSIGN-02)
  // -----------------------------------------------------------------------

  private _getZoneName(): string {
    const zoneId = this.config?.zone_id;
    if (!zoneId) {
      return this.panelConfig?.default_zone?.name ?? "Default Zone";
    }
    return (
      this.panelConfig?.zones?.[zoneId]?.name ??
      this.panelConfig?.default_zone?.name ??
      "Default Zone"
    );
  }

  private async _onZoneChange(newZoneId: string) {
    const patch: Partial<RoomConfig> =
      newZoneId !== DEFAULT_ZONE_VALUE
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
   * Returns empty when active_period is null/undefined.
   * Returns gray "Off" badge when globalMode is "off".
   * When pre-heat is active, shows amber "Pre-heating → XX.X°C" badge.
   * Otherwise returns a colored pill: "${name} · ${temp}°C".
   * When the room period sensor exists, the badge opens its more-info
   * dialog (state history) — the header click (expand) is not triggered.
   */
  private _renderPeriodBadge() {
    const badge = this._renderPeriodBadgeContent();
    const entityId = this.roomStatus?.period_entity_id;
    if (badge === nothing || !entityId) return badge;
    return html`
      <span
        class="badge-link"
        title="Show period history"
        @click=${(e: Event) => {
          e.stopPropagation();
          this._openEntityMoreInfo(entityId);
        }}
        >${badge}</span
      >
    `;
  }

  private _renderPeriodBadgeContent() {
    const zoneId = this.config?.zone_id;
    const zoneMode = zoneId
      ? this.status?.zones?.[zoneId]?.mode ??
        this.panelConfig?.zones?.[zoneId]?.mode
      : this.status?.zones?.["default"]?.mode ??
        this.panelConfig?.default_zone?.mode;

    if (zoneMode === "off") {
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
    if (period == null) return nothing;

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
    const _zoneId = this.config?.zone_id;
    const globalMode = _zoneId
      ? this.status?.zones?.[_zoneId]?.mode ??
        this.panelConfig?.zones?.[_zoneId]?.mode ??
        ""
      : this.status?.zones?.["default"]?.mode ??
        this.panelConfig?.default_zone?.mode ??
        "";
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
      <ha-chip-set class="chips">
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
            <ha-assist-chip
              .label=${name}
              @click=${() => this._openEntityMoreInfo(entityId)}
            >
              <ha-icon slot="icon" icon="mdi:thermometer"></ha-icon>
              <span slot="trailing-icon" class="chip-temp">${temp}</span>
            </ha-assist-chip>
          `;
        })}
      </ha-chip-set>
    `;
  }

  private _renderPersonsSection() {
    const assignedPersonIds = this._getAssignedPersonIds();
    const allPersonIds = this._getAllPersonIds();
    const unassignedPersonIds = allPersonIds.filter(
      (id) => !assignedPersonIds.includes(id),
    );

    return html`
      <div class="section-label" title="Persons whose presence heats this room">
        Associated persons
      </div>
      <ha-chip-set class="chips">
        ${assignedPersonIds.map((personId) =>
          haItemChip(
            this._getPersonName(personId),
            "mdi:account",
            () => void this.panel.navigateToPerson(personId),
            () => void this._onRemovePerson(personId),
          ),
        )}
      </ha-chip-set>
      ${unassignedPersonIds.length > 0
        ? html`<div class="chips">
            ${haEntityAdd(
              this.hass,
              unassignedPersonIds,
              "Add person",
              (id) => void this._onAddPerson(id),
            )}
          </div>`
        : ""}
    `;
  }

  private _openEntityMoreInfo(entityId: string) {
    openMoreInfo(this, entityId);
  }

  // -----------------------------------------------------------------------
  // History (native HA history-graph card)
  // -----------------------------------------------------------------------

  /**
   * Room period, temperature and humidity sensors, the learned pre-heat
   * parameters (heating rate, boost factor), then the TRVs that
   * actually receive setpoints (same rules as backend TRVGroup):
   * an entity with paired Matter valves is replaced by those valves
   * (pushed locally); a Matter valve paired to another entity is otherwise
   * skipped (not pushed on its own). The room temperature sensor is left
   * out when it sits on the same device as a plotted TRV: the TRV already
   * draws that temperature (current temperature).
   */
  private _historyEntityIds(): string[] {
    const s = this.roomStatus;
    const mappings = this.panelConfig?.matter_mappings ?? {};
    const paired = new Set(Object.values(mappings).flat());
    const trvs = (s?.entity_ids ?? []).flatMap((id) => {
      const mapped = mappings[id] ?? [];
      if (mapped.length) return mapped;
      return paired.has(id) ? [] : [id];
    });
    const temperature = sharesClimateDevice(
      s?.temperature_entity_id,
      trvs,
      this.hass?.entities,
    )
      ? null
      : s?.temperature_entity_id;
    return validEntityIds([
      s?.period_entity_id,
      temperature,
      s?.humidity_entity_id,
      s?.preheat_rate_entity_id,
      s?.preheat_anticipation_entity_id,
      ...trvs,
    ]);
  }

  /** (Re)build the history card when its entities or duration change. */
  private async _syncHistoryCard(): Promise<void> {
    const ids = this._historyEntityIds();
    const key = `${ids.join(",")}|${this._historyHours}`;
    if (key === this._historyKey) return;
    this._historyKey = key;
    let card: LovelaceCard | null = null;
    try {
      card = await createHistoryCard(ids, this._historyHours);
    } catch {
      card = null; // card helpers failed — keep the History link only
    }
    if (key !== this._historyKey) return; // superseded meanwhile
    if (card) card.hass = this.hass;
    this._historyCard = card;
  }

  /** Drop the card on collapse so its history subscription ends. */
  private _resetHistoryCard() {
    this._historyCard = null;
    this._historyKey = "";
  }

  private _onHistoryHoursChange(hours: number) {
    this._historyHours = hours;
    try {
      localStorage.setItem(HISTORY_HOURS_KEY, String(hours));
    } catch {
      // storage unavailable — keep the choice for this session only
    }
  }

  private _renderHistorySection() {
    const ids = this._historyEntityIds();
    if (!ids.length) return nothing;
    return html`
      <div class="history-header">
        <div
          class="section-label"
          title="Period, temperature, humidity, pre-heat and TRV history"
        >
          History
        </div>
        ${haSelect(
          this.hass,
          String(this._historyHours),
          HISTORY_HOURS.map(([hours, label]) => ({
            value: String(hours),
            label,
          })),
          (hours) => this._onHistoryHoursChange(Number(hours)),
          { cls: "history-hours" },
        )}
        <ha-icon-button
          class="history-open"
          title="Open in the HA history page"
          .label=${"Open in the HA history page"}
          @click=${() => {
            // Built on click: the range ends now, not at the last render.
            const path = historyPath(ids, this._historyHours);
            if (path) navigateTo(path);
          }}
          ><ha-icon icon="mdi:open-in-new"></ha-icon
        ></ha-icon-button>
      </div>
      ${this._historyCard
        ? html`<div class="history-graph">${this._historyCard}</div>`
        : nothing}
    `;
  }

  // -----------------------------------------------------------------------
  // Pre-heat handlers and render (Phase 12 D-11)
  // -----------------------------------------------------------------------

  private async _onPreheatMaxLeadChange(val: number) {
    if (!Number.isInteger(val) || val < 0 || val > 480) return;
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

  // Matter pairing DnD handlers

  private _entityName(id: string): string {
    return (
      (this.hass?.states[id]?.attributes?.["friendly_name"] as
        | string
        | undefined) ?? id
    );
  }

  private _startDrag(
    entityId: string,
    type: "matter" | "parent",
    fromParentId: string | null,
    e: DragEvent,
  ): void {
    if (!e.dataTransfer) return;
    e.dataTransfer.setData(
      "text/plain",
      JSON.stringify({ entityId, type, fromParentId }),
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
    fromParentId: string | null;
  } | null {
    const raw = e.dataTransfer?.getData("text/plain");
    if (!raw) return null;
    try {
      return JSON.parse(raw) as {
        entityId: string;
        type: string;
        fromParentId: string | null;
      };
    } catch {
      return null;
    }
  }

  private async _onDropOnParent(parentId: string, e: DragEvent): Promise<void> {
    e.preventDefault();
    (e.currentTarget as HTMLElement).classList.remove("drag-over");
    this._dragActive = false;
    this._dragType = null;
    const d = this._parseDragPayload(e);
    if (!d || d.type !== "matter") return;
    const { entityId: matterId, fromParentId } = d;
    if (fromParentId === parentId) return;
    try {
      if (fromParentId) {
        const src = this.panelConfig?.matter_mappings?.[fromParentId] ?? [];
        await this.ws.setMatterMapping(
          fromParentId,
          src.filter((id) => id !== matterId),
        );
      }
      const existing = this.panelConfig?.matter_mappings?.[parentId] ?? [];
      if (!existing.includes(matterId)) {
        await this.ws.setMatterMapping(parentId, [...existing, matterId]);
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
      if (d.type === "parent") {
        await this.ws.setMatterMapping(d.entityId, []);
        await this.panel.reloadConfig();
        this.panel.showToast("Saved", false);
        return;
      }
      if (!d.fromParentId) return;
      const src = this.panelConfig?.matter_mappings?.[d.fromParentId] ?? [];
      await this.ws.setMatterMapping(
        d.fromParentId,
        src.filter((id) => id !== d.entityId),
      );
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private _renderClimateSection() {
    const pairableEntities = this.panelConfig?.pairable_entities ?? [];
    const roomEntityIds = this.roomStatus?.entity_ids ?? [];
    const roomPairableIds = roomEntityIds.filter((id) =>
      pairableEntities.includes(id),
    );
    const matterEntities = this.panelConfig?.matter_entities ?? [];
    const canPair = roomPairableIds.length > 0 && matterEntities.length > 0;

    if (roomPairableIds.length === 0 && matterEntities.length === 0) {
      return this._renderTrvSection();
    }

    const mappings = this.panelConfig?.matter_mappings ?? {};
    const allMapped = new Set(Object.values(mappings).flat());
    const firstLevelOther = roomEntityIds.filter(
      (id) => !pairableEntities.includes(id) && !allMapped.has(id),
    );
    const firstLevel = [...firstLevelOther, ...roomPairableIds].sort((a, b) =>
      this._entityName(a).localeCompare(this._entityName(b)),
    );

    return html`
      ${canPair
        ? html`<p class="schedule-hint">
            Drag Matter entities onto a cloud TRV entity to pair them: they
            receive its setpoints locally and give sub-minute sensor alignment.
          </p>`
        : ""}
      <div class=${this._dragActive ? "climate-pair" : ""}>
        <div class="climate-tree">
          ${firstLevel.map((id) => {
            const isPairable = roomPairableIds.includes(id);
            const s = this.hass?.states[id];
            const name = this._entityName(id);
            const temp =
              s?.attributes?.["current_temperature"] != null
                ? `${s.attributes["current_temperature"]}°C`
                : "—";

            if (!isPairable) {
              const isMatter = matterEntities.includes(id);
              const draggable = canPair && isMatter;
              return html`
                <ha-assist-chip
                  class=${draggable ? "chip-draggable" : ""}
                  .label=${name}
                  .draggable=${draggable}
                  @dragstart=${draggable
                    ? (e: DragEvent) => this._startDrag(id, "matter", null, e)
                    : undefined}
                  @dragend=${draggable ? () => this._onDragEnd() : undefined}
                  @click=${() => this._openEntityMoreInfo(id)}
                >
                  <ha-icon slot="icon" icon="mdi:thermometer"></ha-icon>
                  <span slot="trailing-icon" class="chip-temp">${temp}</span>
                </ha-assist-chip>
              `;
            }

            // Pairable (cloud) entity
            const mapped = (mappings[id] ?? [])
              .slice()
              .sort((a, b) =>
                this._entityName(a).localeCompare(this._entityName(b)),
              );
            const isGroup = mapped.length > 0;

            if (isGroup) {
              return html`
                <div
                  class="pair-group"
                  @dragover=${this._onMatterDragOver}
                  @drop=${(e: DragEvent) => void this._onDropOnParent(id, e)}
                  @dragenter=${this._onMatterDragEnter}
                  @dragleave=${this._onMatterDragLeave}
                >
                  <ha-assist-chip
                    class=${canPair ? "chip-draggable" : ""}
                    .label=${name}
                    .draggable=${canPair}
                    @dragstart=${canPair
                      ? (e: DragEvent) => this._startDrag(id, "parent", null, e)
                      : undefined}
                    @dragend=${canPair ? () => this._onDragEnd() : undefined}
                    @click=${() => this._openEntityMoreInfo(id)}
                  >
                    <ha-icon slot="icon" icon="mdi:thermometer"></ha-icon>
                    <span slot="trailing-icon" class="chip-temp">${temp}</span>
                  </ha-assist-chip>
                  <div class="matter-children">
                    ${mapped.map((mid) => {
                      const ms = this.hass?.states[mid];
                      const mt =
                        ms?.attributes?.["current_temperature"] != null
                          ? `${ms.attributes["current_temperature"]}°C`
                          : "—";
                      return html`
                        <ha-assist-chip
                          class=${canPair ? "chip-draggable" : ""}
                          .label=${this._entityName(mid)}
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
                          <ha-icon slot="icon" icon="mdi:thermometer"></ha-icon>
                          <span slot="trailing-icon" class="chip-temp"
                            >${mt}</span
                          >
                        </ha-assist-chip>
                      `;
                    })}
                  </div>
                </div>
              `;
            }

            // Ungrouped pairable entity — plain chip, drop target for Matter
            return html`
              <ha-assist-chip
                .label=${name}
                @dragover=${canPair ? this._onMatterDragOver : undefined}
                @drop=${canPair
                  ? (e: DragEvent) => void this._onDropOnParent(id, e)
                  : undefined}
                @dragenter=${canPair ? this._onMatterDragEnter : undefined}
                @dragleave=${canPair ? this._onMatterDragLeave : undefined}
                @click=${() => this._openEntityMoreInfo(id)}
              >
                <ha-icon slot="icon" icon="mdi:thermometer"></ha-icon>
                <span slot="trailing-icon" class="chip-temp">${temp}</span>
              </ha-assist-chip>
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
    // Derive zone-level enable: Default Zone rooms check default_zone flag;
    // custom zone rooms check their zone's preheat_enabled (GAP-01).
    const zoneId = this.config?.zone_id;
    const enabled = zoneId
      ? this.panelConfig?.zones?.[zoneId]?.preheat_enabled ?? false
      : this.panelConfig?.default_zone?.preheat_enabled ?? false;

    const maxLead = this.config?.preheat_max_lead_minutes ?? 240;
    const boost = this.roomStatus?.preheat_boost ?? null;
    const preheatActive = this.roomStatus?.preheat_active ?? false;
    const preheatTarget = this.roomStatus?.preheat_target ?? null;
    const suppressed = this.roomStatus?.preheat_suppressed ?? false;

    if (!enabled && !preheatActive) return html``;

    return html`
      <div class="section-label">Pre-heat</div>
      ${enabled
        ? html`
            <div
              style="display:flex;align-items:center;gap:8px;margin-top:6px;"
            >
              Max lead time
              ${haNumber(
                this.hass,
                maxLead,
                { min: 0, max: 480, step: 5, unit: "min" },
                (val) => void this._onPreheatMaxLeadChange(val),
                { cls: "minutes" },
              )}
            </div>
          `
        : ""}
      ${preheatActive && preheatTarget != null
        ? html`
            <p class="schedule-hint">
              Pre-heating to
              ${preheatTarget}&nbsp;&deg;C${boost
                ? ` (TRV +${boost.toFixed(1)}\u00a0°C)`
                : ""}
            </p>
          `
        : ""}
      ${enabled && suppressed
        ? html`
            <p class="schedule-hint">
              Pre-heat disabled &mdash; presence cannot be scheduled
            </p>
          `
        : ""}
      ${enabled ? this._renderInertia() : ""}
    `;
  }

  /** Learned parameters: heating rate, anticipation, today's lead. */
  private _renderInertia() {
    const rate = this.roomStatus?.preheat_rate ?? null;
    const samples = this.roomStatus?.preheat_samples ?? 0;
    const anticipation = this.roomStatus?.preheat_anticipation ?? null;
    const lead = this.roomStatus?.preheat_lead ?? null;
    const runs = `${samples} ${samples === 1 ? "run" : "runs"}`;
    return html`
      <p class="schedule-hint">
        Heating rate:
        ${rate == null
          ? `learning (${Math.min(samples, 3)}/3 runs)`
          : `${rate.toFixed(1)} min/°C (${runs})`}
      </p>
      ${anticipation != null
        ? html`<p class="schedule-hint" title=${ANTICIPATION_HINT}>
            Anticipation: ${Math.round(anticipation)} min
          </p>`
        : ""}
      ${lead != null
        ? html`<p class="schedule-hint">Lead today: ${lead} min</p>`
        : ""}
    `;
  }

  render() {
    return html`
      <ha-card>
        <div
          class="card-header-row"
          @click=${() => {
            this._expanded = !this._expanded;
            if (!this._expanded) this._resetHistoryCard();
          }}
        >
          <div class="card-header-left">
            <div class="card-header-top">
              <span class="room-name">${this.roomName}</span>
              ${this._renderPeriodBadge()}
              <span
                class="zone-badge"
                style=${(() => {
                  const c = getZoneColor(
                    this.config?.zone_id,
                    Object.keys(this.panelConfig?.zones ?? {}),
                  );
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
                <!-- Zone picker (ASSIGN-02, D-12) -->
                <div
                  class="section-label"
                  title="Zone — rooms in a zone share a schedule"
                >
                  Zone
                </div>
                <div class="select-wrapper">
                  ${haSelect(
                    this.hass,
                    this.config?.zone_id ?? DEFAULT_ZONE_VALUE,
                    [
                      {
                        value: DEFAULT_ZONE_VALUE,
                        label:
                          this.panelConfig?.default_zone?.name ??
                          "Default Zone",
                      },
                      ...Object.entries(this.panelConfig?.zones ?? {}).map(
                        ([zoneId, zone]) => ({
                          value: zoneId,
                          label: zone.name,
                        }),
                      ),
                    ],
                    (zoneId) => void this._onZoneChange(zoneId),
                    { cls: "mode-select" },
                  )}
                </div>

                ${this._renderPersonsSection()}

                <div
                  class="section-label"
                  title="TRV climate entities controlled in this room"
                >
                  Climate entities
                </div>
                ${this._renderClimateSection()} ${this._renderPreheatSection()}
                ${this._renderHistorySection()}
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
