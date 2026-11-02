// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — root Lovelace custom element.
 *
 * Registered as "climate-manager-panel" (must match PANEL_COMPONENT_NAME in
 * custom_components/climate_manager/__init__.py — RESEARCH Pitfall 2).
 *
 * HA injects these properties onto this element:
 *   hass   — HomeAssistant object with .connection for WebSocket calls
 *   narrow — boolean, true on mobile viewports
 *   route  — {prefix, path}: the URL under /climate_manager
 *   panel  — panel config dict passed at registration
 *
 * On connect: loads full config via climate_manager/get_config and subscribes
 * to coordinator push events via climate_manager/subscribe_status.
 * On disconnect: unsubscribes the status subscription.
 *
 * Renders an ha-tab-group: Overview / Rooms / Persons, then one tab per
 * zone (double click to rename) and an add-zone button.
 *
 * The URL is the navigation state (panel-route.ts): the active tab and the
 * card to expand come from `route`, and every move goes through navigateTo,
 * so Back / Forward restore them and the sidebar link opens the Overview.
 */

import { LitElement, html, css } from "lit";
import type { PropertyValues } from "lit";
import { property, state } from "lit/decorators.js";
import { live } from "lit/directives/live.js";

import { WsClient } from "./ws-client.js";
import { loadHaElements } from "./ha-elements.js";
import { navigateTo } from "./ha-nav.js";
import { buildPath, parseRoute } from "./panel-route.js";
import type { PanelRoute, PanelView } from "./panel-route.js";
import type { Hass, ClimateConfig, StatusPayload } from "./types.js";
import { getZoneColor } from "./types.js";

import "./components/time-bar.js";
import "./components/global-settings-tab.js";
import "./components/rooms-tab.js";
import "./components/persons-tab.js";
import "./components/zone-tab.js";

export class ClimateManagerPanel extends LitElement {
  // HA-injected properties
  @property({ attribute: false }) hass!: Hass;
  @property({ type: Boolean }) narrow = false;
  @property({ attribute: false }) route: PanelRoute | null = null;
  @property({ attribute: false }) panel: unknown = null;

  // Internal state
  @state() private _config: ClimateConfig | null = null;
  @state() private _status: StatusPayload | null = null;
  @state() private _unsubStatus: Promise<() => void> | null = null;
  @state() private _wsError = false;
  @state() private _editingTabId: string | null = null;
  @state() private _tabNameInput = "";
  /** HA elements still undefined once loaded; null while loading. */
  @state() private _haMissing: string[] | null = null;

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

    ha-alert {
      display: block;
      margin: 8px 16px 0;
    }

    .missing {
      margin: 8px 16px 0;
      color: var(--error-color);
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

  /** URL prefix of the panel ("/climate_manager"). */
  private get _prefix(): string {
    return this.route?.prefix ?? "/climate_manager";
  }

  /** The view named by the URL. */
  private get _view(): PanelView {
    return parseRoute(this.route?.path);
  }

  private get _activeTab(): string {
    return this._view.tab;
  }

  private _navigate(view: PanelView, replace = false): void {
    navigateTo(buildPath(this._prefix, view), { replace });
  }

  /**
   * Rewrite a URL that names nothing (unknown path, deleted zone) into the
   * view actually shown, replacing the history entry so Back never lands on
   * it again.
   */
  private _fixRoute(): void {
    if (!this.route || !this._config) return;
    let view = this._view;
    if (
      view.tab.startsWith("zone_") &&
      view.tab !== "zone_default" &&
      !this._config.zones[view.tab.slice(5)]
    ) {
      view = { tab: "global", cardId: null };
    }
    const path = buildPath(this._prefix, view);
    if (path !== this._prefix + this.route.path) this._navigate(view, true);
  }

  updated(changedProperties: PropertyValues) {
    if (changedProperties.has("route") || changedProperties.has("_config")) {
      this._fixRoute();
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

  /**
   * Show a message in HA's own toast. Called by tab components after a
   * save; a new message replaces the previous one; errors stay longer and
   * can be dismissed.
   */
  showToast(message: string, isError: boolean): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", {
        detail: {
          id: "climate-manager",
          message,
          duration: isError ? 10000 : 4000,
          dismissable: isError,
        },
        bubbles: true,
        composed: true,
      }),
    );
  }

  /** Navigate to a zone tab. Pass undefined/null for the Default Zone. */
  navigateToZone(zoneId: string | undefined | null): void {
    this._setTab(zoneId ? "zone_" + zoneId : "zone_default");
  }

  /** Navigate to the Rooms tab with the given room card expanded. */
  navigateToRoom(roomId: string): void {
    this._navigate({ tab: "rooms", cardId: roomId });
  }

  /** Navigate to the Persons tab with the given person card expanded. */
  navigateToPerson(personId: string): void {
    this._navigate({ tab: "persons", cardId: personId });
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

  /** Open a tab (new history entry); no-op on the current one. */
  private _setTab(tab: string) {
    if (tab !== this._activeTab) this._navigate({ tab, cardId: null });
  }

  /** Open the HA sidebar — fired by the hamburger button on narrow viewports. */
  private _toggleMenu() {
    this.dispatchEvent(
      new Event("hass-toggle-menu", { bubbles: true, composed: true }),
    );
  }

  private _renderWsError() {
    return this._wsError
      ? html`<ha-alert alert-type="error"
          >Connection lost. Reconnecting…</ha-alert
        >`
      : "";
  }

  /** Banner listing the HA elements HA did not provide. */
  private _renderMissing() {
    if (!this._haMissing?.length) return "";
    const text =
      "Some Home Assistant elements could not be loaded; parts of the " +
      `panel will not render: ${this._haMissing.join(", ")}`;
    // ha-alert itself may be missing: plain text then.
    return customElements.get("ha-alert")
      ? html`<ha-alert alert-type="error">${text}</ha-alert>`
      : html`<p class="missing">${text}</p>`;
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
        ${this._renderWsError()}
        <div class="loading">
          <ha-circular-progress active></ha-circular-progress>
        </div>
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

      ${this._renderWsError()} ${this._renderMissing()}

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
      if (!zoneConfig) return html``; // _fixRoute covers this
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
          .expandRoomId=${this._view.cardId}
        ></climate-manager-rooms-tab>`;
      case "persons":
        return html`<climate-manager-persons-tab
          .config=${this._config!}
          .status=${this._status}
          .ws=${this._ws!}
          .panel=${this}
          .hass=${this.hass}
          .expandPersonId=${this._view.cardId}
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
