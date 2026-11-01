// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — Global Settings tab (UI-02).
 *
 * Renders three ha-card sections per D-13 (updated 2026-05-21):
 *   1. "Current Status" — read-only, fed by subscribe_status push (D-18):
 *        current global mode, active period name + end time, present persons
 *   2. "Temperatures" — the 4 period temperature inputs (Frost protection,
 *        Reduced, Normal, Comfort). Auto-saves on blur.
 *   3. "Configuration" — editable, auto-saves on every change (D-08):
 *        global mode selector, global time program, reset button
 *
 * Auto-save on every change — no Save button (D-08).
 * Toast feedback on success/error (D-10).
 *
 * Fields are HA number selectors (ha-controls.ts).
 */

import { LitElement, html, css, unsafeCSS } from "lit";
import { property, state } from "lit/decorators.js";

import {
  PERIOD_DISPLAY_NAMES,
  PRESENCE_COLORS,
  getZoneColor,
} from "../types.js";
import { chipStyles } from "../shared-styles.js";
import { historyPath, navigateTo, openMoreInfo } from "../ha-nav.js";
import { boilerCandidates } from "../boiler-candidates.js";
import { haButton, haEntity, haNumber, haSelect } from "../ha-controls.js";
import type {
  Hass,
  ClimateConfig,
  StatusPayload,
  DailyProgram,
  Period,
  TRVAlignmentEntry,
  CloudPolling,
  BoilerConfig,
} from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";

import "./presence-periods-card.js";

// Day key order matching time-bar days[] indices (0=Mon..6=Sun)
const DAY_KEYS: Array<keyof DailyProgram> = [
  "mon",
  "tue",
  "wed",
  "thu",
  "fri",
  "sat",
  "sun",
];

// ---------------------------------------------------------------------------
// Pure helpers (also exported for reuse by room-card / person-card)
// ---------------------------------------------------------------------------

/** Convert a DailyProgram into a 7-element Period[][] array. */
export function programToDays(program: DailyProgram | undefined): Period[][] {
  return DAY_KEYS.map((key) => (program?.[key] ? [...program[key]] : []));
}

/** Convert a day index (0=Mon..6=Sun) back to a DailyProgram key. */
export function dayIndexToKey(index: number): keyof DailyProgram {
  return DAY_KEYS[index] ?? "mon";
}

/** Evaluate the active period name from a DailyProgram at the given time. */
export function getActivePeriod(
  program: DailyProgram | undefined,
  now: Date,
): string | null {
  if (!program) return null;
  const jsDay = now.getDay(); // 0=Sun..6=Sat
  const dayIdx = jsDay === 0 ? 6 : jsDay - 1; // remap to Mon=0..Sun=6
  const dayKey = DAY_KEYS[dayIdx];
  const periods = program[dayKey] ?? [];
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  let active: string | null = null;
  for (const p of periods) {
    const [h = 0, m = 0] = p.start.split(":").map(Number);
    if (h * 60 + m <= nowMinutes) {
      active = p.mode ?? null;
    }
  }
  return active;
}

// ---------------------------------------------------------------------------
// Mode constants (kept local — backend uses these string values)
// ---------------------------------------------------------------------------
const MODE_OFF = "off";
const MODE_TIME_PROGRAM = "time_program";
const MODE_TIME_PROGRAM_PRESENCES = "time_program_presences";

const MODE_LABELS: Record<string, string> = {
  [MODE_OFF]: "Off",
  [MODE_TIME_PROGRAM]: "Time program",
  [MODE_TIME_PROGRAM_PRESENCES]: "Time program & presences",
};

/** Optional boiler sensors recorded with each pre-heat sample. */
const BOILER_READING_SENSORS = [
  "outdoor_temperature_entity_id",
  "flow_temperature_entity_id",
] as const;

/** Boiler defaults (mirror const.py DEFAULT_BOILER_*). */
const BOILER_DEFAULTS = {
  on_hvac_mode: "heat",
  off_hvac_mode: "off",
  min_on_minutes: 10,
  min_off_minutes: 10,
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export class GlobalSettingsTab extends LitElement {
  /** Full merged runtime config — fed from root panel. */
  @property({ attribute: false }) config!: ClimateConfig;

  /** Live status payload pushed by subscribe_status — fed from root panel. */
  @property({ attribute: false }) status: StatusPayload | null = null;

  /** WS client instance shared from root panel. */
  @property({ attribute: false }) ws!: WsClient;

  /** Reference to root panel for showToast() and reloadConfig(). */
  @property({ attribute: false }) panel!: ClimateManagerPanel;

  /** HA hass object — used for resolving person entity friendly names. */
  @property({ attribute: false }) hass!: Hass;

  @state() private _trvStatuses: TRVAlignmentEntry[] = [];
  @state() private _loadingStatuses = false;
  @state() private _cloudPolling: CloudPolling[] = [];

  static styles = [
    chipStyles,
    css`
      :host {
        display: block;
        --present-color: ${unsafeCSS(PRESENCE_COLORS.present)};
      }

      ha-card {
        margin-bottom: 16px;
      }

      .card-header {
        padding: 16px 16px 0;
        font-size: 16px;
        font-weight: 600;
        line-height: 1.2;
        color: var(--primary-text-color);
      }

      .card-content {
        padding: 16px;
      }

      /* ---- Status card ---- */
      .status-row {
        display: flex;
        align-items: baseline;
        gap: 8px;
        margin-bottom: 8px;
        font-size: 14px;
        color: var(--primary-text-color);
      }

      .status-label {
        font-weight: 600;
        flex-shrink: 0;
      }

      .status-value {
        color: var(--secondary-text-color);
      }

      .person-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--present-color);
        margin-right: 4px;
        vertical-align: middle;
      }

      .person-dot.absent {
        background: var(--secondary-text-color, #9e9e9e);
      }

      /* ---- Zone status grid ---- */
      .zone-status-grid {
        margin-bottom: 12px;
      }

      .zone-status-header {
        display: grid;
        grid-template-columns: 1.2fr 1fr 1fr;
        gap: 8px;
        padding-bottom: 4px;
        border-bottom: 1px solid var(--divider-color);
        margin-bottom: 2px;
        font-size: 11px;
        font-weight: 600;
        color: var(--secondary-text-color);
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }

      .zone-status-row {
        display: grid;
        grid-template-columns: 1.2fr 1fr 1fr;
        gap: 8px;
        padding: 5px 0;
        border-bottom: 1px solid var(--divider-color);
        font-size: 13px;
        align-items: center;
      }

      .zone-status-grid .zone-status-row:last-child {
        border-bottom: none;
      }

      .zone-status-name {
        font-weight: 500;
      }

      .zone-status-name:hover {
        text-decoration: underline;
      }

      .zone-status-value {
        color: var(--secondary-text-color);
      }

      /* ---- Temperatures card ---- */
      .temp-fields {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 16px;
      }

      /* Reset row + button — matches zone-tab reset styling */
      .reset-row {
        display: flex;
        gap: 8px;
        margin-top: 8px;
        margin-bottom: 8px;
        justify-content: flex-end;
      }

      /* ---- Options card ---- */
      .boiler-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-right: 16px;
      }

      .hint {
        margin: 0 0 12px;
        font-size: 13px;
        color: var(--secondary-text-color);
      }

      .option-row ha-selector {
        flex: 0 1 60%;
        min-width: 0;
      }

      .option-row ha-selector.minutes {
        flex: 0 0 140px;
      }

      .option-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
        font-size: 14px;
        color: var(--primary-text-color);
      }

      .option-label {
        font-weight: 500;
        flex: 1;
        margin-right: 16px;
      }

      /* ---- Sensor alignment status table ---- */
      .calib-table-wrap {
        margin-top: 16px;
        overflow-x: auto;
      }

      .calib-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        color: var(--primary-text-color);
      }

      .calib-table th {
        text-align: left;
        font-weight: 600;
        padding: 6px 8px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        white-space: nowrap;
      }

      .calib-table td {
        padding: 6px 8px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        vertical-align: middle;
      }

      .calib-table tr:last-child td {
        border-bottom: none;
      }

      .align-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
      }

      .align-badge.supported {
        background: rgba(34, 197, 94, 0.15);
        color: #15803d;
      }

      .align-badge.unsupported {
        background: rgba(0, 0, 0, 0.06);
        color: var(--secondary-text-color);
      }

      .calib-loading {
        text-align: center;
        padding: 16px;
        color: var(--secondary-text-color);
        font-size: 13px;
      }

      .calib-empty {
        text-align: center;
        padding: 16px;
        color: var(--secondary-text-color);
        font-size: 13px;
      }

      .refresh-row {
        margin: 8px 0;
      }

      /* ---- Cloud polling info banner ---- */
      .calib-info-banner {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 8px 10px;
        margin-bottom: 10px;
        border-radius: 4px;
        background: rgba(3, 169, 244, 0.08);
        border: 1px solid rgba(3, 169, 244, 0.25);
        font-size: 12px;
        color: var(--secondary-text-color);
        line-height: 1.5;
      }

      .calib-info-banner ha-icon {
        --mdc-icon-size: 16px;
        width: 16px;
        height: 16px;
        flex-shrink: 0;
        color: #0288d1;
        margin-top: 1px;
      }

      .calib-info-fetched {
        margin-top: 2px;
        font-size: 11px;
        color: var(--secondary-text-color);
        opacity: 0.75;
      }

      /* ---- TRV floor section headers ---- */
      .calib-floor-header {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        color: var(--secondary-text-color);
        padding: 10px 8px 4px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }

      .calib-floor-header ha-icon {
        --mdc-icon-size: 14px;
        width: 14px;
        height: 14px;
        flex-shrink: 0;
      }
    `,
  ];

  // -----------------------------------------------------------------------
  // Save handlers — arrow function class fields so `this` is always the
  // component instance, even when passed as a bare event listener reference
  // in Lit @event=${} bindings (Lit calls addEventListener(name, fn) which
  // would otherwise set `this` to the DOM element).
  // -----------------------------------------------------------------------

  private async _saveTemperature(id: string, value: number): Promise<void> {
    const current = this.config.period_temperatures;
    const temperatures = {
      frost_protection: current.frost_protection,
      reduced: current.reduced,
      normal: current.normal,
      comfort: current.comfort,
      [id]: value,
    };
    try {
      await this.ws.setPeriodTemperatures(temperatures);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private _onResetTemperatures = async () => {
    try {
      await this.ws.resetPeriodTemperatures();
      await this.panel.reloadConfig();
      this.panel.showToast("Reset to defaults", false);
    } catch {
      this.panel.showToast("Reset failed — retrying...", true);
    }
  };

  private _onAlignmentToggle = async (e: Event) => {
    const enabled = (e.target as HTMLInputElement).checked;
    try {
      await this.ws.setAlignmentConfig(enabled);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
      if (enabled) void this._loadAlignmentStatuses();
    } catch {
      this.panel.showToast("Save failed", true);
    }
  };

  private _loadAlignmentStatuses = async () => {
    this._loadingStatuses = true;
    try {
      const result = await this.ws.getAlignmentStatus();
      this._trvStatuses = result.trvs;
      this._cloudPolling = result.cloud_polling;
    } catch {
      this._trvStatuses = [];
    } finally {
      this._loadingStatuses = false;
    }
  };

  // -----------------------------------------------------------------------
  // Render helpers
  // -----------------------------------------------------------------------

  private _getZoneRows(): Array<{
    id: string;
    name: string;
    mode: string;
    activePeriod: string | null;
  }> {
    const now = new Date();
    const rows: Array<{
      id: string;
      name: string;
      mode: string;
      activePeriod: string | null;
    }> = [];
    // Default Zone — use backend status for accuracy
    rows.push({
      id: "default",
      name: this.config.default_zone.name,
      mode:
        this.status?.zones?.["default"]?.mode ?? this.config.default_zone.mode,
      activePeriod: this.status?.zones?.["default"]?.active_period ?? null,
    });
    // Custom zones — prefer the backend status active period (it honors
    // presence gating and gap-fill, so it matches the room cards). Fall back
    // to client-side schedule evaluation only when status is unavailable.
    for (const [zoneId, zone] of Object.entries(this.config.zones)) {
      const statusPeriod = this.status?.zones?.[zoneId]?.active_period;
      rows.push({
        id: zoneId,
        name: zone.name,
        mode: this.status?.zones?.[zoneId]?.mode ?? zone.mode,
        activePeriod:
          zone.mode === MODE_OFF
            ? null
            : statusPeriod ?? getActivePeriod(zone.time_program, now),
      });
    }
    return rows;
  }

  private _renderStatusCard() {
    const status = this.status;
    const zoneRows = this._getZoneRows();

    // All persons with presence status
    const allPersonIds = Object.keys(this.config?.persons ?? {});
    const presentSet = new Set(status?.present_persons ?? []);
    const personsContent =
      allPersonIds.length === 0
        ? html`<span class="status-value">No persons configured</span>`
        : html`
            <span class="status-value">
              ${allPersonIds.map((personId, i) => {
                const name =
                  this.hass?.states[personId]?.attributes?.friendly_name ??
                  personId;
                const isPresent = presentSet.has(personId);
                return html`<span
                    class="person-dot ${isPresent ? "" : "absent"}"
                  ></span
                  >${name}${i < allPersonIds.length - 1 ? ", " : ""}`;
              })}
            </span>
          `;

    return html`
      <ha-card>
        <div class="card-header">Current Status</div>
        <div class="card-content">
          <div class="zone-status-grid">
            <div class="zone-status-header">
              <span>Zone</span>
              <span>Mode</span>
              <span>Active period</span>
            </div>
            ${zoneRows.map((row) => {
              const color = getZoneColor(
                row.id === "default" ? undefined : row.id,
                Object.keys(this.config?.zones ?? {}),
              );
              const modeLabel = MODE_LABELS[row.mode] ?? row.mode;
              const periodLabel = row.activePeriod
                ? PERIOD_DISPLAY_NAMES[row.activePeriod] ?? row.activePeriod
                : "—";
              return html`
                <div class="zone-status-row">
                  <span
                    class="zone-status-name"
                    style="color: ${color.color}; cursor: pointer;"
                    @click=${() =>
                      this.panel.navigateToZone(
                        row.id === "default" ? undefined : row.id,
                      )}
                    >${row.name}</span
                  >
                  <span class="zone-status-value">${modeLabel}</span>
                  <span class="zone-status-value">${periodLabel}</span>
                </div>
              `;
            })}
          </div>
          <div class="status-row">
            <span class="status-label">Persons:</span>
            ${personsContent}
          </div>
          ${this._renderBoilerStatus()}
        </div>
      </ha-card>
    `;
  }

  // -----------------------------------------------------------------------
  // Boiler
  // -----------------------------------------------------------------------

  private _areaName(areaId: string): string {
    return this.hass?.areas?.[areaId]?.name ?? areaId;
  }

  /** "On — demand: …" / "Off" / "Waiting (min on) until HH:MM". */
  private _boilerStatusText(): string | null {
    const boiler = this.status?.boiler;
    if (!boiler) return null;
    const state = boiler.on === null ? "Unknown" : boiler.on ? "On" : "Off";
    const parts = [state];
    if (boiler.demand_rooms.length) {
      const names = boiler.demand_rooms.map((id) => this._areaName(id));
      parts.push(`demand: ${names.join(", ")}`);
    }
    if (boiler.waiting_until) {
      const until = new Date(boiler.waiting_until).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });
      parts.push(`waiting (min ${boiler.on ? "on" : "off"}) until ${until}`);
    }
    return parts.join(" — ");
  }

  private _renderBoilerStatus() {
    const text = this._boilerStatusText();
    if (text === null) return "";
    return html`
      <div class="status-row">
        <span class="status-label">Boiler:</span>
        <span class="status-value">${text}</span>
      </div>
    `;
  }

  /** On/off hvac modes for a newly picked climate boiler. */
  private _defaultHvacModes(entityId: string) {
    const modes = (this.hass?.states[entityId]?.attributes?.hvac_modes ??
      []) as string[];
    const pick = (preferred: string, fallback?: string) =>
      modes.includes(preferred) ? preferred : fallback;
    return {
      on_hvac_mode: pick(
        BOILER_DEFAULTS.on_hvac_mode,
        modes.find((m) => m !== "off"),
      ),
      off_hvac_mode: pick(BOILER_DEFAULTS.off_hvac_mode),
    };
  }

  /** Save the boiler config merged with `patch`; no entity clears it. */
  private async _saveBoiler(patch: Partial<BoilerConfig>) {
    const current = this.config.boiler;
    const entityId = patch.entity_id ?? current?.entity_id;
    if (!entityId) return;
    const isClimate = entityId.startsWith("climate.");
    const sameEntity = entityId === current?.entity_id;
    const next: BoilerConfig = {
      entity_id: entityId,
      min_on_minutes: current?.min_on_minutes ?? BOILER_DEFAULTS.min_on_minutes,
      min_off_minutes:
        current?.min_off_minutes ?? BOILER_DEFAULTS.min_off_minutes,
      ...(isClimate
        ? sameEntity
          ? {
              on_hvac_mode: current?.on_hvac_mode,
              off_hvac_mode: current?.off_hvac_mode,
            }
          : this._defaultHvacModes(entityId)
        : {}),
      ...patch,
    };
    for (const key of BOILER_READING_SENSORS) {
      next[key] = key in patch ? patch[key] : current?.[key];
      if (!next[key]) delete next[key];
    }
    if (next.on_hvac_mode === undefined) delete next.on_hvac_mode;
    if (next.off_hvac_mode === undefined) delete next.off_hvac_mode;
    try {
      await this.ws.setBoilerConfig(next);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch (err) {
      const message = (err as { message?: string })?.message;
      this.panel.showToast(
        message ? `Save failed: ${message}` : "Save failed",
        true,
      );
    }
  }

  private _onBoilerEntityChange = async (value: string) => {
    if (value) {
      await this._saveBoiler({ entity_id: value });
      return;
    }
    try {
      await this.ws.setBoilerConfig({ entity_id: null });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed", true);
    }
  };

  private _saveBoilerMinutes(
    field: "min_on_minutes" | "min_off_minutes",
    value: number,
  ) {
    if (!Number.isInteger(value) || value < 0 || value > 60) {
      this.panel.showToast("Enter whole minutes between 0 and 60", true);
      return;
    }
    return this._saveBoiler({ [field]: value });
  }

  private _renderHvacModeSelect(
    label: string,
    field: "on_hvac_mode" | "off_hvac_mode",
    modes: string[],
    value: string,
  ) {
    return html`
      <div class="option-row">
        <span class="option-label">${label}</span>
        ${haSelect(
          this.hass,
          value,
          modes.map((mode) => ({ value: mode, label: mode })),
          (mode) => void this._saveBoiler({ [field]: mode }),
        )}
      </div>
    `;
  }

  /**
   * Optional temperature sensor recorded with each pre-heat sample; empty
   * means the boiler vendor's own reading ("Auto"), if any.
   */
  private _renderReadingSensorSelect(
    label: string,
    field: (typeof BOILER_READING_SENSORS)[number],
  ) {
    const value = this.config.boiler?.[field] ?? "";
    const vendor = this.status?.boiler?.vendor;
    return html`
      <div class="option-row">
        <span class="option-label">${label}</span>
        ${haEntity(
          this.hass,
          value,
          { domain: "sensor", device_class: "temperature" },
          (id) => void this._saveBoiler({ [field]: id }),
          { placeholder: vendor ? `Auto (${vendor})` : "None" },
        )}
      </div>
    `;
  }

  /** HA History page for the boiler entity and the demand sensor. */
  private _renderBoilerHistoryButton() {
    const entityId = this.config.boiler?.entity_id;
    const path = historyPath([entityId, this.status?.boiler?.demand_entity_id]);
    if (!entityId || !path) return "";
    return haButton("History", () => navigateTo(path), {
      icon: "mdi:open-in-new",
      title: "Open the HA history of the boiler and its demand",
    });
  }

  /** Boiler entity options, grouped (heating devices, switches, helpers). */
  private _renderBoilerCard() {
    const boiler = this.config.boiler;
    const entityId = boiler?.entity_id ?? "";
    const isClimate = entityId.startsWith("climate.");
    const hvacModes = (this.hass?.states[entityId]?.attributes?.hvac_modes ??
      []) as string[];
    const minOn = boiler?.min_on_minutes ?? BOILER_DEFAULTS.min_on_minutes;
    const minOff = boiler?.min_off_minutes ?? BOILER_DEFAULTS.min_off_minutes;
    return html`
      <ha-card>
        <div class="card-header boiler-header">
          Boiler ${this._renderBoilerHistoryButton()}
        </div>
        <div class="card-content">
          <p class="hint">
            Heats while at least one room is in Normal, Comfort or Pre-heat; off
            otherwise.
          </p>
          <div class="option-row">
            <span class="option-label">Boiler entity</span>
            ${haEntity(
              this.hass,
              entityId,
              {
                include_entities: boilerCandidates(
                  this.hass?.states ?? {},
                  this.hass?.entities,
                  entityId,
                  this.config.boiler_candidates,
                ).map((c) => c.id),
              },
              (id) => void this._onBoilerEntityChange(id),
              { placeholder: "None" },
            )}
          </div>
          ${isClimate
            ? html`
                ${this._renderHvacModeSelect(
                  "Mode when heating",
                  "on_hvac_mode",
                  hvacModes,
                  boiler?.on_hvac_mode ?? BOILER_DEFAULTS.on_hvac_mode,
                )}
                ${this._renderHvacModeSelect(
                  "Mode when stopped",
                  "off_hvac_mode",
                  hvacModes,
                  boiler?.off_hvac_mode ?? BOILER_DEFAULTS.off_hvac_mode,
                )}
              `
            : ""}
          ${entityId
            ? html`
                <div class="option-row">
                  <span class="option-label">Minimum on time</span>
                  ${haNumber(
                    this.hass,
                    minOn,
                    { min: 0, max: 60, step: 1, unit: "min" },
                    (val) =>
                      void this._saveBoilerMinutes("min_on_minutes", val),
                    { cls: "minutes" },
                  )}
                </div>
                <div class="option-row">
                  <span class="option-label">Minimum off time</span>
                  ${haNumber(
                    this.hass,
                    minOff,
                    { min: 0, max: 60, step: 1, unit: "min" },
                    (val) =>
                      void this._saveBoilerMinutes("min_off_minutes", val),
                    { cls: "minutes" },
                  )}
                </div>
                <p class="hint">
                  Recorded with each pre-heat run, for later analysis.
                </p>
                ${this._renderReadingSensorSelect(
                  "Outdoor temperature",
                  "outdoor_temperature_entity_id",
                )}
                ${this._renderReadingSensorSelect(
                  "Flow temperature",
                  "flow_temperature_entity_id",
                )}
              `
            : ""}
        </div>
      </ha-card>
    `;
  }

  private _renderTemperaturesCard() {
    const temps = this.config.period_temperatures;

    const tempField = (id: string, label: string) =>
      haNumber(
        this.hass,
        temps[id] ?? undefined,
        { min: 5, max: 30, step: 0.5, unit: "°C" },
        (value) => void this._saveTemperature(id, value),
        { label },
      );

    return html`
      <ha-card>
        <div class="card-header">Temperatures</div>
        <div class="card-content">
          <div class="temp-fields">
            ${tempField("frost_protection", "Frost protection")}
            ${tempField("reduced", "Reduced")} ${tempField("normal", "Normal")}
            ${tempField("comfort", "Comfort")}
          </div>
          <div class="reset-row">
            ${haButton("Reset to default", this._onResetTemperatures)}
          </div>
        </div>
      </ha-card>
    `;
  }

  private _openEntityMoreInfo(entityId: string | null) {
    openMoreInfo(this, entityId);
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

  private _renderTRVRows(trvs: typeof this._trvStatuses) {
    return trvs.map(
      (trv) => html`
        <tr>
          <td>
            <ha-assist-chip
              .label=${trv.friendly_name}
              @click=${() => this._openEntityMoreInfo(trv.entity_id)}
            >
              <ha-icon slot="icon" icon="mdi:thermometer"></ha-icon>
            </ha-assist-chip>
          </td>
          <td>
            <span
              class="align-badge ${trv.supports_alignment
                ? "supported"
                : "unsupported"}"
            >
              ${trv.supports_alignment
                ? trv.vendor ?? "Supported"
                : "Not supported"}
            </span>
          </td>
          <td>
            ${trv.current_offset != null
              ? html`${trv.current_offset > 0
                  ? "+"
                  : ""}${trv.current_offset.toFixed(1)}
                °C`
              : "—"}
          </td>
          <td>
            ${trv.trv_temperature != null
              ? html`${trv.trv_temperature.toFixed(1)} °C`
              : "—"}
          </td>
          <td>
            ${trv.room_temperature != null
              ? html`${trv.room_temperature.toFixed(1)} °C`
              : "—"}
          </td>
          <td>
            ${trv.last_aligned_at
              ? new Date(trv.last_aligned_at).toLocaleString()
              : "Never"}
          </td>
        </tr>
      `,
    );
  }

  private _renderTRVTable() {
    // Initial load: no data yet
    if (this._trvStatuses.length === 0) {
      if (this._loadingStatuses) {
        return html`<div class="calib-loading">Loading TRV status…</div>`;
      }
      return html`
        <div class="refresh-row">
          ${haButton("Refresh", this._loadAlignmentStatuses, {
            icon: "mdi:refresh",
          })}
        </div>
        <div class="calib-empty">No managed TRVs found.</div>
      `;
    }

    // Group by floor (mirrors rooms-tab floor grouping logic)
    const floorGroups = new Map<string | null, typeof this._trvStatuses>();
    for (const trv of this._trvStatuses) {
      const fid = this.hass?.areas?.[trv.area_id]?.floor_id ?? null;
      if (!floorGroups.has(fid)) floorGroups.set(fid, []);
      floorGroups.get(fid)!.push(trv);
    }

    // Sort each group by friendly_name
    for (const group of floorGroups.values()) {
      group.sort((a, b) => a.friendly_name.localeCompare(b.friendly_name));
    }

    // Sort floor IDs by level descending (top floor first)
    const sortedFloorIds = [...floorGroups.keys()]
      .filter((fid): fid is string => fid !== null)
      .sort(
        (a, b) =>
          (this.hass?.floors?.[b]?.level ?? 0) -
          (this.hass?.floors?.[a]?.level ?? 0),
      );

    const floorlessTrvs = floorGroups.get(null) ?? [];

    // One banner per cloud-polled vendor that has rows in the table.
    const vendors = new Set(this._trvStatuses.map((t) => t.vendor));
    const polled = this._cloudPolling.filter((p) => vendors.has(p.vendor));
    const scanLabel = (seconds: number) =>
      seconds >= 60 ? `${Math.round(seconds / 60)} min` : `${seconds} s`;

    // Refresh button is placed ABOVE the table so it remains accessible
    // regardless of table length. During a subsequent refresh, the table
    // stays visible (no layout jump) and the button shows "Refreshing…".
    return html`
      <div class="calib-table-wrap">
        <div class="refresh-row">
          ${haButton(
            this._loadingStatuses ? "Refreshing…" : "Refresh",
            this._loadAlignmentStatuses,
            { icon: "mdi:refresh", disabled: this._loadingStatuses },
          )}
        </div>
        ${polled.map(
          (p) => html`
            <div class="calib-info-banner">
              <ha-icon icon="mdi:information-outline"></ha-icon>
              <div>
                ${p.vendor} data is fetched from the cloud every
                ${scanLabel(p.interval)} — displayed temperatures may lag behind
                actual values.
              </div>
            </div>
          `,
        )}
        <table class="calib-table">
          <thead>
            <tr>
              <th>TRV</th>
              <th>Sensor alignment</th>
              <th>Current offset</th>
              <th>TRV temp</th>
              <th>Room temp</th>
              <th>Last adjusted</th>
            </tr>
          </thead>
          ${sortedFloorIds.map((fid) => {
            const floorName = this.hass?.floors?.[fid]?.name ?? fid;
            return html`
              <tbody>
                <tr>
                  <td colspan="6" class="calib-floor-header">
                    <ha-icon icon=${this._getFloorIcon(fid)}></ha-icon>
                    ${floorName}
                  </td>
                </tr>
                ${this._renderTRVRows(floorGroups.get(fid) ?? [])}
              </tbody>
            `;
          })}
          ${floorlessTrvs.length > 0
            ? html`<tbody>
                ${this._renderTRVRows(floorlessTrvs)}
              </tbody>`
            : ""}
        </table>
      </div>
    `;
  }

  private _renderOptionsCard() {
    const enabled = this.config.alignment_enabled ?? false;
    if (enabled && this._trvStatuses.length === 0 && !this._loadingStatuses) {
      void this._loadAlignmentStatuses();
    }
    return html`
      <ha-card>
        <div class="card-header">Sensor alignment</div>
        <div class="card-content">
          <div class="option-row">
            <span class="option-label">Enable sensor alignment</span>
            <ha-switch
              .checked=${enabled}
              @change=${this._onAlignmentToggle}
            ></ha-switch>
          </div>
          ${enabled ? this._renderTRVTable() : ""}
        </div>
      </ha-card>
    `;
  }

  render() {
    return html`
      ${this._renderStatusCard()}
      <climate-manager-presence-periods-card
        .config=${this.config}
        .hass=${this.hass}
        .ws=${this.ws}
        .panel=${this.panel}
      ></climate-manager-presence-periods-card>
      ${this._renderTemperaturesCard()} ${this._renderBoilerCard()}
      ${this._renderOptionsCard()}
    `;
  }
}

customElements.define("climate-manager-global-settings-tab", GlobalSettingsTab);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-global-settings-tab": GlobalSettingsTab;
  }
}
