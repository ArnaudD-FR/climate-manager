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
 * Renders an ha-tab-group: Overview / Rooms / Persons, then one tab per
 * zone (double click to rename) and an add-zone button.
 */

import { LitElement, html, css } from "lit";
import { property, state, query } from "lit/decorators.js";
import { live } from "lit/directives/live.js";

import { WsClient } from "./ws-client.js";
import { loadHaElements } from "./ha-elements.js";
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
  /** HA elements still undefined once loaded; null while loading. */
  @state() private _haMissing: string[] | null = null;

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
      align-items: center;
      border-bottom: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
      background: var(--primary-background-color);
      padding: 0 8px;
    }

    ha-tab-group {
      flex: 1;
      min-width: 0;
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
      flex-shrink: 0;
      color: var(--secondary-text-color);
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
      width: 16ch;
    }
  `;

  connectedCallback() {
    super.connectedCallback();
    // Create a single WS client instance used by all tab components
    this._ws = new WsClient(this.hass);
    void loadHaElements(this.hass, this).then((tags) => {
      if (tags.length) {
        console.error("Climate Manager: HA elements not loaded:", tags);
      }
      this._haMissing = tags;
      // A late element upgrades in place: drop it from the banner.
      for (const tag of tags) {
        void customElements.whenDefined(tag).then(() => {
          this._haMissing = (this._haMissing ?? []).filter((t) => t !== tag);
        });
      }
    });
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
    await this._loadConfig();
  }

  private async _onCreateZone(): Promise<void> {
    if (!this._config || !this._ws) return;
    // D-02: default name computed client-side as "Zone N".
    const newName = `Zone ${Object.keys(this._config.zones).length + 1}`;
    try {
      const result = await this._ws.createZone(newName);
      await this._loadConfig();
      this._setTab("zone_" + result.zone_id);
      // D-03: edit the new tab's name so the user can rename it at once.
      await this._onTabRename(result.zone_id, newName);
      this.showToast("Zone created", false);
    } catch {
      this.showToast("Create zone failed", true);
    }
  }

  private async _onTabRename(zoneId: string, currentName: string, e?: Event) {
    e?.stopPropagation();
    this._editingTabId = zoneId;
    this._tabNameInput = currentName;
    await this.updateComplete;
    const input = this.shadowRoot?.querySelector<
      HTMLElement & { select?: () => void }
    >(`ha-input[data-zone="${zoneId}"]`);
    input?.focus();
    input?.select?.();
  }

  private _onTabNameInput(e: Event) {
    this._tabNameInput = (e.target as HTMLInputElement).value ?? "";
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

  /** Banner listing the HA elements HA did not provide. */
  private _renderMissing() {
    if (!this._haMissing?.length) return "";
    const text =
      "Some Home Assistant elements could not be loaded; parts of the " +
      `panel will not render: ${this._haMissing.join(", ")}`;
    return customElements.get("ha-alert")
      ? html`<ha-alert alert-type="error">${text}</ha-alert>`
      : html`<div class="error-banner">${text}</div>`;
  }

  render() {
    if (!this._config || this._haMissing === null) {
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
      ${this._renderMissing()}

      <div class="tab-bar">
        <ha-tab-group
          @wa-tab-show=${(e: CustomEvent) => {
            const name = e.detail?.name;
            if (typeof name === "string") this._setTab(name);
          }}
        >
          ${this._renderTab("global", "Overview")}
          ${this._renderTab("rooms", "Rooms")}
          ${this._renderTab("persons", "Persons")}
          ${this._renderZoneTab("default", this._config.default_zone.name)}
          ${Object.entries(this._config.zones).map(([zoneId, zone]) =>
            this._renderZoneTab(zoneId, zone.name),
          )}
        </ha-tab-group>
        <ha-icon-button
          class="add-zone-btn"
          title="Add zone"
          .label=${"Add zone"}
          @click=${() => void this._onCreateZone()}
          ><ha-icon icon="mdi:plus"></ha-icon
        ></ha-icon-button>
      </div>

      <div class="tab-content">${this._renderTabContent()}</div>

      <climate-manager-toast></climate-manager-toast>
    `;
  }

  private _renderTab(id: string, label: unknown) {
    return html`<ha-tab-group-tab
      slot="nav"
      panel=${id}
      .active=${live(this._activeTab === id)}
      >${label}</ha-tab-group-tab
    >`;
  }

  /**
   * A zone tab: coloured dot and name; a double click renames it in an
   * ha-input (keys and clicks stay out of the tab group).
   */
  private _renderZoneTab(zoneId: string, name: string) {
    const tabId = zoneId === "default" ? "zone_default" : "zone_" + zoneId;
    const color = getZoneColor(
      zoneId === "default" ? undefined : zoneId,
      Object.keys(this._config?.zones ?? {}),
    ).color;
    const stop = (e: Event) => e.stopPropagation();
    const label =
      this._editingTabId === zoneId
        ? html`<ha-input
            data-zone=${zoneId}
            class="tab-name-input"
            .value=${this._tabNameInput}
            @input=${this._onTabNameInput}
            @blur=${() => this._onTabNameBlur(zoneId)}
            @keydown=${(e: KeyboardEvent) => {
              stop(e);
              this._onTabNameKeydown(zoneId, e);
            }}
            @click=${stop}
            @dblclick=${stop}
          ></ha-input>`
        : html`<span class="zone-dot" style="background:${color}"></span
            >${name}`;
    return html`<ha-tab-group-tab
      slot="nav"
      panel=${tabId}
      .active=${live(this._activeTab === tabId)}
      @dblclick=${(e: Event) => this._onTabRename(zoneId, name, e)}
      >${label}</ha-tab-group-tab
    >`;
  }

  private _renderTabContent() {
    // Zone tab cases — checked before switch so "zone_*" keys are intercepted.
    if (this._activeTab === "zone_default") {
      return html`<climate-manager-zone-tab
        .config=${this._config!}
        .zoneId=${"default"}
        .zoneConfig=${this._config!.default_zone}
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
