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
import { property } from "lit/decorators.js";

import {
  PERIOD_DISPLAY_NAMES,
  PRESENCE_COLORS,
  getZoneColor,
} from "../types.js";
import type {
  Hass,
  ClimateConfig,
  StatusPayload,
  DailyProgram,
  Period,
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

  static styles = css`
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
  `;

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

  render() {
    return html`
      ${this._renderStatusCard()} ${this._renderTemperaturesCard()}
    `;
  }
}

customElements.define("climate-manager-global-settings-tab", GlobalSettingsTab);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-global-settings-tab": GlobalSettingsTab;
  }
}
