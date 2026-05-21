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

import { LitElement, html, css } from "lit";
import { property } from "lit/decorators.js";

import type { Hass, ClimateConfig, StatusPayload, DailyProgram, Period } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";

import "./time-bar.js";

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

// Default temperature values (used by Reset to default)
const DEFAULT_TEMPERATURES = {
  frost_protection: 7,
  reduced: 18,
  normal: 20,
  comfort: 22,
};

// Default global mode (mirrors backend DEFAULT_GLOBAL_MODE in const.py)
const DEFAULT_GLOBAL_MODE = "time_program";

// Default 7-day time program (mirrors backend _DEFAULT_DAY_PERIODS in const.py)
// Each day gets its own independent array — deep-cloned to prevent mutation of shared refs.
const DEFAULT_TIME_PROGRAM: DailyProgram = (() => {
  const mkDay = (): Period[] => [
    { start: "00:00", mode: "reduced" },
    { start: "06:00", mode: "normal" },
    { start: "22:00", mode: "reduced" },
  ];
  return {
    mon: mkDay(),
    tue: mkDay(),
    wed: mkDay(),
    thu: mkDay(),
    fri: mkDay(),
    sat: mkDay(),
    sun: mkDay(),
  };
})();

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

  // Memoize the days array by program identity — programToDays() creates new
  // array references on every call. Without this, any status-only re-render
  // (which happens before config arrives after a WS save) passes a new days
  // reference to the time-bar, causing it to clear _dragPreviewDays and flash.
  private _lastProgram: DailyProgram | undefined = undefined;
  private _cachedDays: Period[][] = [];
  private get _days(): Period[][] {
    const program = this.config?.global_time_program;
    if (program !== this._lastProgram) {
      this._lastProgram = program;
      this._cachedDays = programToDays(program);
    }
    return this._cachedDays;
  }

  static styles = css`
    :host {
      display: block;
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
      background: #388E3C;
      margin-right: 4px;
      vertical-align: middle;
    }

    /* ---- Config card ---- */
    .section-divider {
      margin: 16px 0 8px;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
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

    /* ---- Config card ---- */
    .time-program-section {
      margin-top: 16px;
    }

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
      background: rgba(3, 169, 244, 0.08);
    }
  `;

  // -----------------------------------------------------------------------
  // Save handlers — arrow function class fields so `this` is always the
  // component instance, even when passed as a bare event listener reference
  // in Lit @event=${} bindings (Lit calls addEventListener(name, fn) which
  // would otherwise set `this` to the DOM element).
  // -----------------------------------------------------------------------

  private _onModeChange = async (e: Event) => {
    const newMode = (e.target as HTMLSelectElement).value;
    if (!newMode || newMode === this.config.global_mode) return;
    try {
      await this.ws.setGlobalMode(newMode);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed", true);
    }
  };

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

  private _onPeriodsChanged = async (e: CustomEvent) => {
    const { dayIndex, periods } = e.detail as { dayIndex: number; periods: Period[] };

    // Rebuild the full DailyProgram, replacing the changed day
    const program: DailyProgram = { ...this.config.global_time_program };
    const key = dayIndexToKey(dayIndex);
    program[key] = periods;

    try {
      await this.ws.setTimeProgram(program);
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }

    e.stopPropagation();
  };

  private _onResetTemperatures = async () => {
    try {
      await this.ws.setPeriodTemperatures(DEFAULT_TEMPERATURES);
      await this.panel.reloadConfig();
      this.panel.showToast("Reset to defaults", false);
    } catch {
      this.panel.showToast("Reset failed — retrying...", true);
    }
  };

  private _onResetConfiguration = async () => {
    try {
      await this.ws.setGlobalMode(DEFAULT_GLOBAL_MODE);
      await this.ws.setTimeProgram(DEFAULT_TIME_PROGRAM);
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
      activePeriodText = status.active_period;
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

    const tempField = (id: string, label: string, defaultVal: number) => html`
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
            .value=${String(temps[id] ?? defaultVal)}
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
            ${tempField("frost_protection", "Frost protection", 7)}
            ${tempField("reduced", "Reduced", 18)}
            ${tempField("normal", "Normal", 20)}
            ${tempField("comfort", "Comfort", 22)}
          </div>
          <button class="reset-btn" @click=${this._onResetTemperatures}>Reset to default</button>
        </div>
      </ha-card>
    `;
  }

  private _renderConfigCard() {
    return html`
      <ha-card>
        <div class="card-header">Configuration</div>
        <div class="card-content">

          <div class="select-wrapper">
            <label class="select-label">Global mode</label>
            <select class="mode-select" @change=${this._onModeChange}>
              <option value=${MODE_OFF} ?selected=${this.config.global_mode === MODE_OFF}>Off</option>
              <option value=${MODE_TIME_PROGRAM} ?selected=${this.config.global_mode === MODE_TIME_PROGRAM}>Time program</option>
              <option value=${MODE_TIME_PROGRAM_PRESENCES} ?selected=${this.config.global_mode === MODE_TIME_PROGRAM_PRESENCES}>Time program &amp; presences</option>
            </select>
          </div>

          <!-- Global time program editor -->
          <div class="section-divider">Global time program</div>
          <div class="time-program-section">
            <climate-manager-time-bar
              mode="schedule"
              .days=${this._days}
              @periods-changed=${this._onPeriodsChanged}
            ></climate-manager-time-bar>
          </div>

          <button class="reset-btn" @click=${this._onResetConfiguration}>Reset to default</button>
        </div>
      </ha-card>
    `;
  }

  render() {
    return html`
      ${this._renderStatusCard()}
      ${this._renderTemperaturesCard()}
      ${this._renderConfigCard()}
    `;
  }
}

customElements.define("climate-manager-global-settings-tab", GlobalSettingsTab);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-global-settings-tab": GlobalSettingsTab;
  }
}
