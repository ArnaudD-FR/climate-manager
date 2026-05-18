/**
 * Climate Manager Panel — root Lovelace custom element.
 *
 * Registered as "climate-manager-panel" (must match PANEL_COMPONENT_NAME in
 * custom_components/climate_manager/__init__.py — RESEARCH Pitfall 2).
 *
 * HA injects three properties onto this element:
 *   hass   — HomeAssistant object with .connection for WebSocket calls
 *   narrow — boolean, true on mobile viewports
 *   panel  — panel config dict passed at registration
 *
 * On connect: loads full config via climate_manager/get_config and subscribes
 * to coordinator push events via climate_manager/subscribe_status.
 * On disconnect: unsubscribes the status subscription.
 *
 * Renders a ha-tabs shell with three tabs: Global Settings / Rooms / Persons.
 * Tab bodies are placeholder stubs in this plan; filled in by the next plan.
 */

import { LitElement, html, css } from "lit";
import { property, state, query } from "lit/decorators.js";

import { WsClient } from "./ws-client.js";
import type { Hass, ClimateConfig, StatusPayload } from "./types.js";
import type { ClimateManagerToast } from "./toast.js";

import "./toast.js";
import "./components/time-bar.js";
import "./components/global-settings-tab.js";
import "./components/rooms-tab.js";
import "./components/persons-tab.js";

export class ClimateManagerPanel extends LitElement {
  // HA-injected properties
  @property({ attribute: false }) hass!: Hass;
  @property({ type: Boolean }) narrow = false;
  @property({ attribute: false }) panel: unknown = null;

  // Internal state
  @state() private _config: ClimateConfig | null = null;
  @state() private _status: StatusPayload | null = null;
  @state() private _activeTab = "global";
  @state() private _unsubStatus: Promise<() => void> | null = null;
  @state() private _wsError = false;

  @query("climate-manager-toast")
  private _toast?: ClimateManagerToast;

  // Shared WS client instance — created once after hass is set
  private _ws: WsClient | null = null;

  static styles = css`
    :host {
      display: block;
      background: var(--primary-background-color);
      min-height: 100%;
      font-family: var(--mdc-typography-body1-font-family, Roboto, sans-serif);
    }

    .panel-header {
      display: flex;
      align-items: center;
      padding: 0 16px;
      height: 56px;
      font-size: 20px;
      font-weight: 400;
      color: var(--app-header-text-color, var(--primary-text-color));
      background: var(--app-header-background-color, var(--primary-background-color));
      border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
    }

    .loading {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 200px;
    }

    .error-banner {
      background: var(--error-color, #db4437);
      color: #fff;
      padding: 8px 16px;
      font-size: 14px;
      text-align: center;
    }

    .tab-bar {
      display: flex;
      border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.12));
      background: var(--primary-background-color);
      padding: 0 8px;
      overflow-x: auto;
    }

    .tab-btn {
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      padding: 12px 16px;
      margin-bottom: -1px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      color: var(--secondary-text-color);
      text-transform: uppercase;
      letter-spacing: 0.07em;
      white-space: nowrap;
      outline: none;
      transition: color 0.15s;
    }

    .tab-btn.active {
      border-bottom-color: var(--primary-color);
      color: var(--primary-color);
    }

    .tab-btn:hover:not(.active) {
      color: var(--primary-text-color);
    }

    .tab-content {
      padding: 16px;
      max-width: 900px;
      margin: 0 auto;
    }

    .placeholder {
      color: var(--secondary-text-color);
      font-size: 14px;
      padding: 24px 0;
      text-align: center;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    // Create a single WS client instance used by all tab components
    this._ws = new WsClient(this.hass);
    this._loadConfig();
    this._subscribeStatus();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._unsubStatus) {
      this._unsubStatus.then((unsub) => unsub()).catch(() => {
        // Ignore errors during disconnect — connection may already be closed.
      });
      this._unsubStatus = null;
    }
  }

  private async _loadConfig() {
    if (!this._ws) this._ws = new WsClient(this.hass);
    try {
      this._config = await this._ws.getConfig();
    } catch {
      // Config load failure is shown via the error banner on next render.
      this._wsError = true;
    }
  }

  private _subscribeStatus() {
    if (!this._ws) this._ws = new WsClient(this.hass);
    this._unsubStatus = this._ws
      .subscribeStatus((status) => {
        this._status = status;
        this._wsError = false;
      })
      .catch(() => {
        this._wsError = true;
        return () => {};
      });
  }

  /** Show a toast notification. Called by tab components after a save. */
  showToast(message: string, isError: boolean): void {
    this._toast?.show(message, isError);
  }

  /** Patch a subset of _config in-place without a WS round-trip. */
  patchConfig(patch: Partial<ClimateConfig>): void {
    if (this._config) this._config = { ...this._config, ...patch };
  }

  /**
   * Re-fetch the full config from the backend and update _config.
   *
   * Tab components call this after every successful write so that the parent's
   * _config stays in sync with the backend. Without this, Lit re-renders the
   * tab with the stale .config prop (e.g. the old global_mode), causing
   * ha-select to fire a spurious @selected event that immediately overwrites
   * the value just saved on the backend.
   */
  async reloadConfig(): Promise<void> {
    await this._loadConfig();
  }

  private _setTab(tab: string) {
    this._activeTab = tab;
  }

  render() {
    if (!this._config) {
      return html`
        <div class="panel-header">Climate Manager</div>
        ${this._wsError
          ? html`<div class="error-banner">Connection lost. Reconnecting…</div>`
          : ""}
        <div class="loading">
          <ha-circular-progress active></ha-circular-progress>
        </div>
        <climate-manager-toast></climate-manager-toast>
      `;
    }

    return html`
      <div class="panel-header">Climate Manager</div>

      ${this._wsError
        ? html`<div class="error-banner">Connection lost. Reconnecting…</div>`
        : ""}

      <div class="tab-bar">
        <button
          class="tab-btn ${this._activeTab === "global" ? "active" : ""}"
          @click=${() => this._setTab("global")}
        >Global Settings</button>
        <button
          class="tab-btn ${this._activeTab === "rooms" ? "active" : ""}"
          @click=${() => this._setTab("rooms")}
        >Rooms</button>
        <button
          class="tab-btn ${this._activeTab === "persons" ? "active" : ""}"
          @click=${() => this._setTab("persons")}
        >Persons</button>
      </div>

      <div class="tab-content">
        ${this._renderTabContent()}
      </div>

      <climate-manager-toast></climate-manager-toast>
    `;
  }

  private _renderTabContent() {
    switch (this._activeTab) {
      case "global":
        return html`<climate-manager-global-settings-tab
          .config=${this._config!}
          .status=${this._status}
          .ws=${this._ws!}
          .panel=${this}
        ></climate-manager-global-settings-tab>`;
      case "rooms":
        return html`<climate-manager-rooms-tab
          .config=${this._config!}
          .status=${this._status}
          .ws=${this._ws!}
          .panel=${this}
        ></climate-manager-rooms-tab>`;
      case "persons":
        return html`<climate-manager-persons-tab
          .config=${this._config!}
          .status=${this._status}
          .ws=${this._ws!}
          .panel=${this}
        ></climate-manager-persons-tab>`;
      default:
        return html``;
    }
  }
}

customElements.define("climate-manager-panel", ClimateManagerPanel);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-panel": ClimateManagerPanel;
  }
}
