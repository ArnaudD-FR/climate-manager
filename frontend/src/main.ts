// SPDX-License-Identifier: MIT
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
import { getZoneColor } from "./types.js";
import type { ClimateManagerToast } from "./toast.js";

import "./toast.js";
import "./components/time-bar.js";
import "./components/global-settings-tab.js";
import "./components/rooms-tab.js";
import "./components/persons-tab.js";
import "./components/zone-tab.js";

export class ClimateManagerPanel extends LitElement {
  // HA-injected properties
  @property({ attribute: false }) hass!: Hass;
  @property({ type: Boolean }) narrow = false;
  @property({ attribute: false }) panel: unknown = null;

  // Internal state
  @state() private _config: ClimateConfig | null = null;
  @state() private _status: StatusPayload | null = null;
  @state() private _activeTab: string =
    localStorage.getItem("climate-manager-tab") ?? "global";
  @state() private _unsubStatus: Promise<() => void> | null = null;
  @state() private _wsError = false;
  @state() private _editingTabId: string | null = null;
  @state() private _tabNameInput = "";
  @state() private _expandRoomId: string | null = null;
  @state() private _expandPersonId: string | null = null;

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
      background: var(
        --app-header-background-color,
        var(--primary-background-color)
      );
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
    }

    .menu-btn {
      --mdc-icon-button-size: 40px;
      margin-right: 8px;
      margin-left: -8px;
      flex-shrink: 0;
      color: var(--app-header-text-color, var(--primary-text-color));
    }

    .loading {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 200px;
    }

    .error-banner {
      background: var(--error-color, #db4437);
      color: var(--text-primary-color, white);
      padding: 8px 16px;
      font-size: 14px;
      text-align: center;
    }

    .tab-bar {
      display: flex;
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
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

    .add-zone-btn {
      font-size: 18px;
      font-weight: 300;
      padding: 12px 14px;
    }

    .zone-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      vertical-align: middle;
      margin-right: 6px;
      flex-shrink: 0;
    }

    .tab-name-input {
      font-size: 14px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      border: none;
      border-bottom: 2px solid var(--primary-color);
      outline: none;
      background: transparent;
      color: var(--primary-color);
      padding: 0;
      width: 10ch;
      max-width: 20ch;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    // Create a single WS client instance used by all tab components
    this._ws = new WsClient(this.hass);
    this._loadConfig();
    this._loadStatus();
    this._subscribeStatus();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._unsubStatus) {
      this._unsubStatus
        .then((unsub) => unsub())
        .catch(() => {
          // Ignore errors during disconnect — connection may already be closed.
        });
      this._unsubStatus = null;
    }
  }

  private _validateActiveTab(): void {
    if (!this._config) return;
    // Static tabs always exist — return immediately.
    if (
      this._activeTab === "global" ||
      this._activeTab === "rooms" ||
      this._activeTab === "persons" ||
      this._activeTab === "zone_default"
    )
      return;
    // Custom zone tab: verify the UUID still exists in config.
    if (this._activeTab.startsWith("zone_")) {
      const zoneId = this._activeTab.slice(5); // strip "zone_"
      if (!this._config.zones[zoneId]) {
        this._activeTab = "global";
        localStorage.setItem("climate-manager-tab", "global");
      }
      return;
    }
    // Unknown/corrupted value — fall back to global.
    this._activeTab = "global";
    localStorage.setItem("climate-manager-tab", "global");
  }

  private async _loadConfig() {
    if (!this._ws) this._ws = new WsClient(this.hass);
    try {
      this._config = await this._ws.getConfig();
      this._validateActiveTab();
    } catch {
      // Config load failure is shown via the error banner on next render.
      this._wsError = true;
    }
  }

  private async _loadStatus() {
    if (!this._ws) this._ws = new WsClient(this.hass);
    try {
      this._status = await this._ws.getStatus();
    } catch {
      // Non-fatal: subscribe_status push will populate status on next tick.
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

  /** Navigate to a zone tab. Pass undefined/null for the Default Zone. */
  navigateToZone(zoneId: string | undefined | null): void {
    this._setTab(zoneId ? "zone_" + zoneId : "zone_default");
  }

  /** Navigate to the Rooms tab and auto-expand the given room card. */
  async navigateToRoom(roomId: string): Promise<void> {
    this._setTab("rooms");
    this._expandRoomId = roomId;
    await this.updateComplete;
    this._expandRoomId = null;
  }

  /** Navigate to the Persons tab and auto-expand the given person card. */
  async navigateToPerson(personId: string): Promise<void> {
    this._setTab("persons");
    this._expandPersonId = personId;
    await this.updateComplete;
    this._expandPersonId = null;
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
    await Promise.all([this._loadConfig(), this._loadStatus()]);
  }

  private async _onCreateZone(): Promise<void> {
    if (!this._config || !this._ws) return;
    // D-02: default name computed client-side as "Zone N".
    const newName = `Zone ${Object.keys(this._config.zones).length + 1}`;
    try {
      const result = await this._ws.createZone(newName);
      await this._loadConfig();
      this._setTab("zone_" + result.zone_id);
      // D-03: focus zone name field so user can rename immediately.
      await this.updateComplete;
      const zoneTab = this.shadowRoot?.querySelector(
        "climate-manager-zone-tab",
      );
      zoneTab?.shadowRoot?.querySelector<HTMLElement>(".zone-name")?.click();
      this.showToast("Zone created", false);
    } catch {
      this.showToast("Create zone failed", true);
    }
  }

  private async _onTabRename(zoneId: string, currentName: string, e: Event) {
    e.stopPropagation();
    this._editingTabId = zoneId;
    this._tabNameInput = currentName;
    await this.updateComplete;
    this.shadowRoot
      ?.querySelector<HTMLInputElement>(`input[data-zone="${zoneId}"]`)
      ?.select();
  }

  private _onTabNameInput(e: Event) {
    this._tabNameInput = (e.target as HTMLInputElement).value;
  }

  private async _onTabNameBlur(zoneId: string) {
    if (this._editingTabId !== zoneId) return;
    this._editingTabId = null;
    const name = this._tabNameInput.trim();
    if (!name || !this._ws) return;
    try {
      await this._ws.renameZone(zoneId, name);
      await this._loadConfig();
      this.showToast("Renamed", false);
    } catch {
      this.showToast("Rename failed", true);
    }
  }

  private _onTabNameKeydown(zoneId: string, e: KeyboardEvent) {
    if (e.key === "Enter") (e.target as HTMLElement).blur();
    else if (e.key === "Escape") {
      this._editingTabId = null;
    }
  }

  private _setTab(tab: string) {
    this._activeTab = tab;
    localStorage.setItem("climate-manager-tab", tab);
  }

  /** Open the HA sidebar — fired by the hamburger button on narrow viewports. */
  private _toggleMenu() {
    this.dispatchEvent(
      new Event("hass-toggle-menu", { bubbles: true, composed: true }),
    );
  }

  render() {
    if (!this._config) {
      return html`
        <div class="panel-header">
          ${this.narrow
            ? html`<ha-icon-button
                class="menu-btn"
                label="Menu"
                @click=${this._toggleMenu}
              >
                <ha-icon icon="mdi:menu"></ha-icon>
              </ha-icon-button>`
            : ""}
          Climate Manager
        </div>
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
      <div class="panel-header">
        ${this.narrow
          ? html`<ha-icon-button
              class="menu-btn"
              label="Menu"
              @click=${this._toggleMenu}
            >
              <ha-icon icon="mdi:menu"></ha-icon>
            </ha-icon-button>`
          : ""}
        Climate Manager
      </div>

      ${this._wsError
        ? html`<div class="error-banner">Connection lost. Reconnecting…</div>`
        : ""}

      <div class="tab-bar">
        <button
          class="tab-btn ${this._activeTab === "global" ? "active" : ""}"
          @click=${() => this._setTab("global")}
        >
          Overview
        </button>
        <button
          class="tab-btn ${this._activeTab === "rooms" ? "active" : ""}"
          @click=${() => this._setTab("rooms")}
        >
          Rooms
        </button>
        <button
          class="tab-btn ${this._activeTab === "persons" ? "active" : ""}"
          @click=${() => this._setTab("persons")}
        >
          Persons
        </button>
        <button
          class="tab-btn ${this._activeTab === "zone_default" ? "active" : ""}"
          @click=${() => this._setTab("zone_default")}
          @dblclick=${(e: Event) =>
            this._onTabRename("default", this._config!.default_zone_name, e)}
        >
          ${this._editingTabId === "default"
            ? html`<input
                data-zone="default"
                class="tab-name-input"
                .value=${this._tabNameInput}
                @input=${this._onTabNameInput}
                @blur=${() => this._onTabNameBlur("default")}
                @keydown=${(e: KeyboardEvent) =>
                  this._onTabNameKeydown("default", e)}
                @click=${(e: Event) => e.stopPropagation()}
              />`
            : html`<span
                  class="zone-dot"
                  style="background:${getZoneColor(undefined).color}"
                ></span
                >${this._config.default_zone_name}`}
        </button>
        ${Object.entries(this._config.zones).map(
          ([zoneId, zone]) => html`
            <button
              class="tab-btn ${this._activeTab === "zone_" + zoneId
                ? "active"
                : ""}"
              @click=${() => this._setTab("zone_" + zoneId)}
              @dblclick=${(e: Event) => this._onTabRename(zoneId, zone.name, e)}
            >
              ${this._editingTabId === zoneId
                ? html`<input
                    data-zone="${zoneId}"
                    class="tab-name-input"
                    .value=${this._tabNameInput}
                    @input=${this._onTabNameInput}
                    @blur=${() => this._onTabNameBlur(zoneId)}
                    @keydown=${(e: KeyboardEvent) =>
                      this._onTabNameKeydown(zoneId, e)}
                    @click=${(e: Event) => e.stopPropagation()}
                  />`
                : html`<span
                      class="zone-dot"
                      style="background:${getZoneColor(zoneId).color}"
                    ></span
                    >${zone.name}`}
            </button>
          `,
        )}
        <button
          class="tab-btn add-zone-btn"
          title="Add zone"
          @click=${() => void this._onCreateZone()}
        >
          +
        </button>
      </div>

      <div class="tab-content">${this._renderTabContent()}</div>

      <climate-manager-toast></climate-manager-toast>
    `;
  }

  private _renderTabContent() {
    // Zone tab cases — checked before switch so "zone_*" keys are intercepted.
    if (this._activeTab === "zone_default") {
      return html`<climate-manager-zone-tab
        .config=${this._config!}
        .zoneId=${"default"}
        .zoneConfig=${{
          name: this._config!.default_zone_name,
          mode: this._config!.global_mode,
          time_program: this._config!.global_time_program,
          preheat_enabled: this._config!.default_zone_preheat_enabled ?? false,
        }}
        .isDefault=${true}
        .status=${this._status}
        .ws=${this._ws!}
        .panel=${this}
        .hass=${this.hass}
      ></climate-manager-zone-tab>`;
    }
    if (this._activeTab.startsWith("zone_")) {
      const zoneId = this._activeTab.slice(5); // strip "zone_"
      const zoneConfig = this._config!.zones[zoneId];
      if (!zoneConfig) return html``; // _validateActiveTab covers this
      return html`<climate-manager-zone-tab
        .config=${this._config!}
        .zoneId=${zoneId}
        .zoneConfig=${zoneConfig}
        .isDefault=${false}
        .status=${this._status}
        .ws=${this._ws!}
        .panel=${this}
        .hass=${this.hass}
      ></climate-manager-zone-tab>`;
    }

    switch (this._activeTab) {
      case "global":
        return html`<climate-manager-global-settings-tab
          .config=${this._config!}
          .status=${this._status}
          .ws=${this._ws!}
          .panel=${this}
          .hass=${this.hass}
        ></climate-manager-global-settings-tab>`;
      case "rooms":
        return html`<climate-manager-rooms-tab
          .config=${this._config!}
          .status=${this._status}
          .ws=${this._ws!}
          .panel=${this}
          .hass=${this.hass}
          .expandRoomId=${this._expandRoomId}
        ></climate-manager-rooms-tab>`;
      case "persons":
        return html`<climate-manager-persons-tab
          .config=${this._config!}
          .status=${this._status}
          .ws=${this._ws!}
          .panel=${this}
          .hass=${this.hass}
          .expandPersonId=${this._expandPersonId}
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
