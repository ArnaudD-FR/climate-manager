// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — Search Picker component (D-19).
 *
 * A shared Lit component that provides a floating search popup for selecting
 * items from a filtered list. Replaces the native <select> add-person and
 * add-room pickers in room-card.ts and person-card.ts.
 *
 * Public API:
 *   - items: Array<{id, label, secondary?, icon?}> — pre-filtered items
 *   - placeholder: string — input placeholder text (default: "Search…")
 *   - triggerLabel: string — text on the trigger button (default: "Add")
 *   - triggerIcon: string — mdi icon for trigger button (default: "mdi:plus")
 *   - Fires CustomEvent("picked", { detail: { id } }) on selection
 *
 * HA 2026.x constraints: uses only native HTML elements.
 *   Uses native <input type="text">, native <ul>/<li>, native <button>.
 *   No custom HA form elements (all broken or removed in HA 2026.x).
 */

import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

export interface SearchPickerItem {
  id: string;
  label: string;
  secondary?: string;
  icon?: string;
}

export class SearchPicker extends LitElement {
  /** Pre-filtered selectable items (consumer excludes already-assigned). */
  @property({ type: Array }) items: SearchPickerItem[] = [];

  /** Placeholder text for the search input. */
  @property({ type: String }) placeholder = "Search…";

  /** Text shown on the trigger button when popup is closed. */
  @property({ type: String }) triggerLabel = "Add";

  /** MDI icon for the trigger button. */
  @property({ type: String }) triggerIcon = "mdi:plus";

  /** Whether the popup is open. */
  @state() private _open = false;

  /** Current search query. */
  @state() private _query = "";

  /** Bound document click handler (stored for cleanup). */
  private _docClickHandler: ((e: MouseEvent) => void) | null = null;

  static styles = css`
    :host {
      display: inline-block;
      position: relative;
    }

    /* Trigger button — matches .chip-add style in room-card.ts */
    .trigger-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      border-radius: 16px;
      background: none;
      border: 1px solid var(--primary-color, #03a9f4);
      font-size: 13px;
      color: var(--primary-color, #03a9f4);
      cursor: pointer;
      font-family: inherit;
      outline-color: var(--primary-color);
    }

    .trigger-btn:hover {
      background: var(--secondary-background-color);
    }

    .trigger-btn ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
    }

    /* Popup container — positioned below trigger */
    .popup {
      position: absolute;
      top: 100%;
      left: 0;
      z-index: 999;
      min-width: 240px;
      max-width: 320px;
      margin-top: 4px;
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 8px;
      box-shadow: var(--ha-card-box-shadow, 0 4px 16px rgba(0, 0, 0, 0.15));
      overflow: hidden;
    }

    /* Search input row */
    .search-row {
      display: flex;
      align-items: center;
      padding: 8px 12px;
      border-bottom: 1px solid var(--divider-color, #e0e0e0);
    }

    .search-input {
      flex: 1;
      border: none;
      outline: none;
      font-size: 14px;
      font-family: inherit;
      color: var(--primary-text-color);
      background: transparent;
    }

    .search-input::placeholder {
      color: var(--secondary-text-color);
    }

    /* Item list */
    .item-list {
      list-style: none;
      margin: 0;
      padding: 4px 0;
      max-height: 240px;
      overflow-y: auto;
    }

    .item-row {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      cursor: pointer;
      transition: background 0.1s;
    }

    .item-row:hover {
      background: var(--secondary-background-color, #f5f5f5);
    }

    .item-icon {
      --mdc-icon-size: 18px;
      width: 18px;
      height: 18px;
      flex-shrink: 0;
      color: var(--secondary-text-color);
    }

    .item-text {
      display: flex;
      flex-direction: column;
      gap: 1px;
      min-width: 0;
    }

    .item-label {
      font-size: 14px;
      font-weight: 600;
      color: var(--primary-text-color);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .item-secondary {
      font-size: 12px;
      color: var(--secondary-text-color);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Empty state */
    .empty-message {
      padding: 12px;
      font-size: 13px;
      color: var(--secondary-text-color);
      text-align: center;
    }
  `;

  // -------------------------------------------------------------------------
  // Popup lifecycle
  // -------------------------------------------------------------------------

  private _openPopup() {
    this._open = true;
    this._query = "";

    // Focus the input after render
    this.updateComplete.then(() => {
      const input =
        this.shadowRoot?.querySelector<HTMLInputElement>(".search-input");
      input?.focus();
    });

    // Register document-level click handler to close on outside click
    this._docClickHandler = (e: MouseEvent) => {
      if (!e.composedPath().includes(this)) {
        this._closePopup();
      }
    };
    document.addEventListener("click", this._docClickHandler);
  }

  private _closePopup() {
    this._open = false;
    this._query = "";
    if (this._docClickHandler) {
      document.removeEventListener("click", this._docClickHandler);
      this._docClickHandler = null;
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    // Clean up document listener if component is removed while popup is open
    if (this._docClickHandler) {
      document.removeEventListener("click", this._docClickHandler);
      this._docClickHandler = null;
    }
  }

  // -------------------------------------------------------------------------
  // Event handlers
  // -------------------------------------------------------------------------

  private _onTriggerClick(e: MouseEvent) {
    e.stopPropagation(); // prevent document click from immediately closing
    if (this._open) {
      this._closePopup();
    } else {
      this._openPopup();
    }
  }

  private _onSearchInput(e: Event) {
    this._query = (e.target as HTMLInputElement).value;
  }

  private _onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.stopPropagation();
      this._closePopup();
    }
  }

  private _onItemClick(item: SearchPickerItem) {
    this.dispatchEvent(
      new CustomEvent("picked", {
        detail: { id: item.id },
        bubbles: true,
        composed: true,
      }),
    );
    this._closePopup();
  }

  // -------------------------------------------------------------------------
  // Filtering
  // -------------------------------------------------------------------------

  private _filteredItems(): SearchPickerItem[] {
    if (!this._query) return this.items;
    const q = this._query.toLowerCase();
    return this.items.filter((item) => {
      const labelMatch = item.label.toLowerCase().includes(q);
      const secondaryMatch = item.secondary?.toLowerCase().includes(q) ?? false;
      return labelMatch || secondaryMatch;
    });
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  render() {
    const filtered = this._filteredItems();

    return html`
      <button
        class="trigger-btn"
        @click=${this._onTriggerClick}
        aria-expanded=${this._open}
        aria-haspopup="listbox"
      >
        <ha-icon icon=${this.triggerIcon}></ha-icon>
        ${this.triggerLabel}
      </button>

      ${this._open
        ? html`
            <div class="popup" @click=${(e: MouseEvent) => e.stopPropagation()}>
              <div class="search-row">
                <input
                  class="search-input"
                  type="text"
                  .value=${this._query}
                  placeholder=${this.placeholder}
                  @input=${this._onSearchInput}
                  @keydown=${this._onKeydown}
                  autocomplete="off"
                  spellcheck="false"
                />
              </div>
              ${filtered.length > 0
                ? html`
                    <ul class="item-list" role="listbox">
                      ${filtered.map(
                        (item) => html`
                          <li
                            class="item-row"
                            role="option"
                            @click=${() => this._onItemClick(item)}
                          >
                            ${item.icon
                              ? html`<ha-icon
                                  class="item-icon"
                                  icon=${item.icon}
                                ></ha-icon>`
                              : ""}
                            <div class="item-text">
                              <span class="item-label">${item.label}</span>
                              ${item.secondary
                                ? html`<span class="item-secondary"
                                    >${item.secondary}</span
                                  >`
                                : ""}
                            </div>
                          </li>
                        `,
                      )}
                    </ul>
                  `
                : html`<div class="empty-message">No results</div>`}
            </div>
          `
        : ""}
    `;
  }
}

customElements.define("search-picker", SearchPicker);

declare global {
  interface HTMLElementTagNameMap {
    "search-picker": SearchPicker;
  }
}
