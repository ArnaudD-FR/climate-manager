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

import { PERIOD_DISPLAY_NAMES, PRESENCE_COLORS } from "../types.js";
import type { Hass, ClimateConfig, StatusPayload, DailyProgram, Period } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";

// Day key order matching time-bar days[] indices (0=Mon..6=Sun)
const DAY_KEYS: Array<keyof DailyProgram> = [
  "mon", "tue", "wed", "thu", "fri", "sat", "sun",
];

// ---------------------------------------------------------------------------
// Pure helpers (also exported for reuse by room-card / person-card)
// ---------------------------------------------------------------------------

/** Convert a DailyProgram (keyed by day name) into a 7-element Period[][] array. */
export function programToDays(program: DailyProgram | undefined): Period[][] {
  return DAY_KEYS.map((key) => (program?.[key] ? [...program[key]] : []));
}

/** Convert a day index (0=Mon..6=Sun) back to a DailyProgram key. */
export function dayIndexToKey(index: number): keyof DailyProgram {
  return DAY_KEYS[index] ?? "mon";
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
      background-color: var(--card-background-color, var(--secondary-background-color));
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
      return field ? parseFloat(field.value) : (this.config.period_temperatures[id] ?? 0);
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
    this._tempSaveTimer = setTimeout(() => { void this._saveTemperatures(); }, 600);
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

  private _renderStatusCard() {
    const status = this.status;

    // Global mode label
    const modeLabel = MODE_LABELS[status?.global_mode ?? this.config.global_mode] ?? status?.global_mode ?? this.config.global_mode;

    // Active period
    let activePeriodText = "No active period";
    if (status?.active_period) {
      activePeriodText = PERIOD_DISPLAY_NAMES[status.active_period] ?? status.active_period;
    }

    // Present persons
    let personsContent = html`<span class="status-value">No one home</span>`;
    if (status?.present_persons?.length) {
      personsContent = html`
        <span class="status-value">
          ${status.present_persons.map(
            (personId, i) => {
              const name = this.hass?.states[personId]?.attributes?.friendly_name ?? personId;
              return html`<span class="person-dot"></span>${name}${i < (status?.present_persons?.length ?? 1) - 1 ? ", " : ""}`;
            },
          )}
        </span>
      `;
    }

    return html`
      <ha-card>
        <div class="card-header">Current Status</div>
        <div class="card-content">
          <div class="status-row">
            <span class="status-label">Mode:</span>
            <span class="status-value">${modeLabel}</span>
          </div>
          <div class="status-row">
            <span class="status-label">Active period:</span>
            <span class="status-value">${activePeriodText}</span>
          </div>
          <div class="status-row">
            <span class="status-label">Present persons:</span>
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
            @keydown=${(e: KeyboardEvent) => { if (e.key === "Enter") (e.target as HTMLElement).blur(); }}
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
            ${tempField("reduced", "Reduced")}
            ${tempField("normal", "Normal")}
            ${tempField("comfort", "Comfort")}
          </div>
          <button class="reset-btn" @click=${this._onResetTemperatures}>Reset to default</button>
        </div>
      </ha-card>
    `;
  }

  render() {
    return html`
      ${this._renderStatusCard()}
      ${this._renderTemperaturesCard()}
    `;
  }
}

customElements.define("climate-manager-global-settings-tab", GlobalSettingsTab);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-global-settings-tab": GlobalSettingsTab;
  }
}
