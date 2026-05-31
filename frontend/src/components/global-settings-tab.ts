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
 * HA 2026.x: uses native <input type="number"> for temperature fields
 * (ha-textfield renders nothing in HA 2026.x).
 */

import { LitElement, html, css, unsafeCSS } from "lit";
import { property, state } from "lit/decorators.js";

import {
  PERIOD_DISPLAY_NAMES,
  PRESENCE_COLORS,
  getZoneColor,
} from "../types.js";
import { chipStyles } from "../shared-styles.js";
import type {
  Hass,
  ClimateConfig,
  StatusPayload,
  DailyProgram,
  Period,
  TRVCalibrationEntry,
} from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";

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
      active = "mode" in p ? p.mode : null;
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

  @state() private _trvStatuses: TRVCalibrationEntry[] = [];
  @state() private _loadingStatuses = false;
  @state() private _tadoXLastFetched: string | null = null;
  @state() private _tadoXScanInterval: number | null = null;

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

      .temp-field {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .temp-label {
        display: block;
        font-size: 12px;
        color: var(--secondary-text-color);
      }

      .temp-input-row {
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .temp-input {
        width: 100%;
        padding: 8px 10px;
        font-size: 15px;
        font-family: inherit;
        color: var(--primary-text-color);
        background-color: var(
          --card-background-color,
          var(--secondary-background-color)
        );
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        outline: none;
        box-sizing: border-box;
      }

      .temp-input:focus {
        border-color: var(--primary-color);
        border-width: 2px;
      }

      .temp-suffix {
        font-size: 14px;
        color: var(--secondary-text-color);
        flex-shrink: 0;
      }

      /* Reset button */
      .reset-btn {
        margin-top: 16px;
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

      /* ---- Options card ---- */
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

      /* ---- TRV calibration status table ---- */
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

      .calib-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
      }

      .calib-badge.supported {
        background: rgba(34, 197, 94, 0.15);
        color: #15803d;
      }

      .calib-badge.unsupported {
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

      .refresh-btn {
        margin-top: 8px;
        background: none;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 12px;
        cursor: pointer;
        color: var(--primary-text-color);
      }

      .refresh-btn:hover {
        background: var(--secondary-background-color, #f5f5f5);
      }

      /* ---- Tado X info banner ---- */
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

  private _tempSaveTimer: ReturnType<typeof setTimeout> | null = null;

  private async _saveTemperatures(): Promise<void> {
    const root = this.shadowRoot;
    if (!root) return;
    const getValue = (id: string): number => {
      const field = root.querySelector<HTMLInputElement>(`#temp-${id}`);
      return field
        ? parseFloat(field.value)
        : this.config.period_temperatures[id] ?? 0;
    };
    const temperatures = {
      frost_protection: getValue("frost_protection"),
      reduced: getValue("reduced"),
      normal: getValue("normal"),
      comfort: getValue("comfort"),
    };
    try {
      await this.ws.setPeriodTemperatures(temperatures);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private _onTemperatureInput = () => {
    if (this._tempSaveTimer !== null) clearTimeout(this._tempSaveTimer);
    this._tempSaveTimer = setTimeout(() => {
      void this._saveTemperatures();
    }, 600);
  };

  private _onTemperatureBlur = () => {
    if (this._tempSaveTimer !== null) {
      clearTimeout(this._tempSaveTimer);
      this._tempSaveTimer = null;
    }
    void this._saveTemperatures();
  };

  private _onResetTemperatures = async () => {
    try {
      await this.ws.resetPeriodTemperatures();
      await this.panel.reloadConfig();
      this.panel.showToast("Reset to defaults", false);
    } catch {
      this.panel.showToast("Reset failed — retrying...", true);
    }
  };

  private _onCalibrationToggle = async (e: Event) => {
    const enabled = (e.target as HTMLInputElement).checked;
    try {
      await this.ws.setCalibrationConfig(enabled);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
      if (enabled) void this._loadCalibrationStatuses();
    } catch {
      this.panel.showToast("Save failed", true);
    }
  };

  private _loadCalibrationStatuses = async () => {
    this._loadingStatuses = true;
    try {
      const result = await this.ws.getCalibrationStatus();
      this._trvStatuses = result.trvs;
      this._tadoXScanInterval = result.tado_x_scan_interval;
      this._tadoXLastFetched = result.tado_x_last_fetched;
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
      name: this.config.default_zone_name,
      mode: this.status?.global_mode ?? this.config.global_mode,
      activePeriod: this.status?.active_period ?? null,
    });
    // Custom zones — client-side active period evaluation
    for (const [zoneId, zone] of Object.entries(this.config.zones)) {
      rows.push({
        id: zoneId,
        name: zone.name,
        mode: zone.mode,
        activePeriod:
          zone.mode !== MODE_OFF
            ? getActivePeriod(zone.time_program, now)
            : null,
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
        </div>
      </ha-card>
    `;
  }

  private _renderTemperaturesCard() {
    const temps = this.config.period_temperatures;

    const tempField = (id: string, label: string) => html`
      <div class="temp-field">
        <label class="temp-label" for="temp-${id}">${label}</label>
        <div class="temp-input-row">
          <input
            id="temp-${id}"
            class="temp-input"
            type="number"
            step="0.5"
            min="5"
            max="30"
            data-key="${id}"
            .value=${temps[id] != null ? String(temps[id]) : ""}
            @input=${this._onTemperatureInput}
            @blur=${this._onTemperatureBlur}
            @keydown=${(e: KeyboardEvent) => {
              if (e.key === "Enter") (e.target as HTMLElement).blur();
            }}
          />
          <span class="temp-suffix">°C</span>
        </div>
      </div>
    `;

    return html`
      <ha-card>
        <div class="card-header">Temperatures</div>
        <div class="card-content">
          <div class="temp-fields">
            ${tempField("frost_protection", "Frost protection")}
            ${tempField("reduced", "Reduced")} ${tempField("normal", "Normal")}
            ${tempField("comfort", "Comfort")}
          </div>
          <button class="reset-btn" @click=${this._onResetTemperatures}>
            Reset to default
          </button>
        </div>
      </ha-card>
    `;
  }

  private _openEntityMoreInfo(entityId: string | null) {
    if (!entityId) return;
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        bubbles: true,
        composed: true,
        detail: { entityId },
      }),
    );
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
            <span
              class="chip"
              @click=${() => this._openEntityMoreInfo(trv.entity_id)}
            >
              <ha-icon icon="mdi:thermometer"></ha-icon>
              ${trv.friendly_name}
            </span>
          </td>
          <td>
            <span
              class="calib-badge ${trv.supports_calibration
                ? "supported"
                : "unsupported"}"
            >
              ${trv.supports_calibration ? "Tado X" : "Not supported"}
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
            ${trv.last_applied_delta != null
              ? html`${trv.last_applied_delta > 0
                  ? "+"
                  : ""}${trv.last_applied_delta.toFixed(2)}
                °C`
              : "—"}
          </td>
          <td>
            ${trv.last_calibrated_at
              ? new Date(trv.last_calibrated_at).toLocaleString()
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
        <button
          class="refresh-btn"
          @click=${this._loadCalibrationStatuses}
          style="margin-top: 8px;"
        >
          Refresh
        </button>
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

    const hasTadoX = this._trvStatuses.some((t) => t.supports_calibration);
    const fetchedLabel = this._tadoXLastFetched
      ? new Date(this._tadoXLastFetched).toLocaleTimeString()
      : null;
    const scanLabel =
      this._tadoXScanInterval != null
        ? this._tadoXScanInterval >= 60
          ? `${Math.round(this._tadoXScanInterval / 60)} min`
          : `${this._tadoXScanInterval} s`
        : "~30 s";

    // Refresh button is placed ABOVE the table so it remains accessible
    // regardless of table length. During a subsequent refresh, the table
    // stays visible (no layout jump) and the button shows "Refreshing…".
    return html`
      <div class="calib-table-wrap">
        <button
          class="refresh-btn"
          style="margin-top: 8px; margin-bottom: 8px;"
          ?disabled=${this._loadingStatuses}
          @click=${this._loadCalibrationStatuses}
        >
          ${this._loadingStatuses ? "Refreshing…" : "Refresh"}
        </button>
        ${hasTadoX
          ? html`
              <div class="calib-info-banner">
                <ha-icon icon="mdi:information-outline"></ha-icon>
                <div>
                  Tado X data is fetched from the cloud every ${scanLabel} —
                  displayed temperatures may lag behind actual values.
                  ${fetchedLabel
                    ? html`<div class="calib-info-fetched">
                        Last fetched: ${fetchedLabel}
                      </div>`
                    : ""}
                </div>
              </div>
            `
          : ""}
        <table class="calib-table">
          <thead>
            <tr>
              <th>TRV</th>
              <th>Auto-calibration</th>
              <th>Current offset</th>
              <th>TRV temp</th>
              <th>Room temp</th>
              <th>Last applied delta</th>
              <th>Last adjusted</th>
            </tr>
          </thead>
          ${sortedFloorIds.map((fid) => {
            const floorName = this.hass?.floors?.[fid]?.name ?? fid;
            return html`
              <tbody>
                <tr>
                  <td colspan="7" class="calib-floor-header">
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
    const enabled = this.config.calibration_enabled ?? false;
    if (enabled && this._trvStatuses.length === 0 && !this._loadingStatuses) {
      void this._loadCalibrationStatuses();
    }
    return html`
      <ha-card>
        <div class="card-header">TRV Auto-Calibration</div>
        <div class="card-content">
          <div class="option-row">
            <span class="option-label">Enable auto-calibration</span>
            <ha-switch
              .checked=${enabled}
              @change=${this._onCalibrationToggle}
            ></ha-switch>
          </div>
          ${enabled ? this._renderTRVTable() : ""}
        </div>
      </ha-card>
    `;
  }

  render() {
    return html`
      ${this._renderStatusCard()} ${this._renderTemperaturesCard()}
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
