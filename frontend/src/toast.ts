/**
 * Climate Manager Panel — Toast / snackbar notification element.
 *
 * Usage: call show("Saved", false) for success, show("Save failed — retrying...", true) for error.
 * Success auto-dismisses after 3 s; error stays until resolved.
 * Rendered bottom-center, pointer-events: none, role="status" (ARIA live region).
 */

import { LitElement, html, css } from "lit";
import { state } from "lit/decorators.js";

export class ClimateManagerToast extends LitElement {
  @state() private _visible = false;
  @state() private _message = "";
  @state() private _isError = false;

  private _dismissTimer: ReturnType<typeof setTimeout> | null = null;

  static styles = css`
    :host {
      position: fixed;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 9999;
      pointer-events: none;
      display: block;
    }

    .toast {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      border-radius: 4px;
      background: var(--card-background-color, #fff);
      box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.2));
      font-size: 14px;
      font-family: inherit;
      color: var(--primary-text-color, #212121);
      opacity: 0;
      transition: opacity 0.2s ease;
    }

    .toast.visible {
      opacity: 1;
    }

    .icon {
      --icon-size: 20px;
      width: var(--icon-size);
      height: var(--icon-size);
      flex-shrink: 0;
    }

    .icon.success {
      color: var(--primary-color, #03a9f4);
    }

    .icon.error {
      color: var(--error-color, #db4437);
    }
  `;

  /** Display the toast. Success auto-dismisses after 3s; error persists. */
  show(message: string, isError: boolean): void {
    if (this._dismissTimer !== null) {
      clearTimeout(this._dismissTimer);
      this._dismissTimer = null;
    }
    this._message = message;
    this._isError = isError;
    this._visible = true;

    if (!isError) {
      this._dismissTimer = setTimeout(() => {
        this._visible = false;
        this._dismissTimer = null;
      }, 3000);
    }
  }

  /** Programmatically dismiss the toast (e.g. after error recovery). */
  dismiss(): void {
    if (this._dismissTimer !== null) {
      clearTimeout(this._dismissTimer);
      this._dismissTimer = null;
    }
    this._visible = false;
  }

  render() {
    const iconName = this._isError ? "mdi:alert-circle" : "mdi:check-circle";
    const iconClass = this._isError ? "error" : "success";

    return html`
      <div
        class="toast ${this._visible ? "visible" : ""}"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <ha-icon
          class="icon ${iconClass}"
          icon="${iconName}"
        ></ha-icon>
        <span>${this._message}</span>
      </div>
    `;
  }
}

customElements.define("climate-manager-toast", ClimateManagerToast);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-toast": ClimateManagerToast;
  }
}
