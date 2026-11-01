// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — Presence & absence periods card (Global tab).
 *
 * Dated periods override each person's presence mode, from the start to
 * the return; rooms are pre-heated for the return. Persons can be picked
 * one by one only when a zone is in Time program & presences; otherwise a
 * period covers everyone, Time program zones included. Ended periods are
 * pruned by the backend.
 *
 * Controls are HA's own: ha-date-input / ha-time-input (they follow the
 * user profile's date format and 12/24-hour clock), a select ha-selector
 * and ha-button.
 */

import { LitElement, html, css } from "lit";
import { property, state } from "lit/decorators.js";

import { chipStyles } from "../shared-styles.js";
import {
  covers,
  currentAndUpcoming,
  formatPeriodDate,
  hasPresenceZone,
  isLocalDateTime,
  joinLocal,
  selectionToPersonIds,
  splitLocal,
  toLocalInput,
  useAmPm,
} from "../presence-periods.js";
import type {
  ClimateConfig,
  Hass,
  PresencePeriod,
  PresencePeriodKind,
} from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";

/** Selector of the period type. */
const KIND_SELECTOR = {
  select: {
    mode: "dropdown",
    options: [
      { value: "absent", label: "Absence" },
      { value: "present", label: "Presence" },
    ],
  },
};

interface ButtonOptions {
  primary?: boolean;
  disabled?: boolean;
}

interface PeriodDraft {
  periodId?: string;
  kind: PresencePeriodKind;
  start: string;
  end: string;
  /** Selected persons (all of them for everyone). */
  selected: string[];
}

export class PresencePeriodsCard extends LitElement {
  @property({ attribute: false }) config!: ClimateConfig;
  @property({ attribute: false }) hass!: Hass;
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;

  @state() private _draft: PeriodDraft | null = null;
  @state() private _saving = false;
  /** An ha-button. */
  private _button(
    label: string,
    onClick: () => void,
    { primary = false, disabled = false }: ButtonOptions = {},
  ) {
    return html`<ha-button
      size="s"
      appearance=${primary ? "accent" : "plain"}
      ?disabled=${disabled}
      @click=${onClick}
      >${label}</ha-button
    >`;
  }

  static styles = [
    chipStyles,
    css`
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

      .hint {
        margin: 0 0 12px;
        font-size: 13px;
        color: var(--secondary-text-color);
      }

      .hint.warning {
        color: var(--warning-color, #f57c00);
      }

      .period-row {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color);
        font-size: 14px;
      }

      .period-row:last-of-type {
        border-bottom: none;
      }

      .kind {
        font-size: 12px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 10px;
        color: #fff;
        background: var(--secondary-text-color, #9e9e9e);
      }

      .kind.present {
        background: var(--success-color, #43a047);
      }

      .kind.active {
        outline: 2px solid var(--primary-color);
      }

      .dates {
        color: var(--primary-text-color);
      }

      .who {
        flex: 1;
        color: var(--secondary-text-color);
        font-size: 13px;
      }

      .editor {
        margin-top: 12px;
        padding: 12px;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
      }

      .field {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 10px;
        font-size: 14px;
      }

      .when {
        display: flex;
        align-items: flex-start;
        gap: 4px;
        flex-wrap: wrap;
        justify-content: flex-end;
      }

      ha-date-input,
      .kind-select {
        min-width: 150px;
      }

      .persons-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-size: 14px;
      }

      .persons-head span {
        flex: 1;
      }

      .chips {
        margin-bottom: 12px;
      }

      .chip.selected {
        background: var(--primary-color);
        border-color: var(--primary-color);
        color: var(--text-primary-color, #fff);
      }

      .actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
      }
    `,
  ];

  /** Every known person: HA person.* entities and configured ones. */
  private _personIds(): string[] {
    const fromHass = Object.keys(this.hass?.states ?? {}).filter((id) =>
      id.startsWith("person."),
    );
    const ids = [
      ...new Set([...fromHass, ...Object.keys(this.config?.persons ?? {})]),
    ];
    return ids.sort((a, b) =>
      this._personName(a).localeCompare(this._personName(b)),
    );
  }

  private _personName(personId: string): string {
    const name = this.hass?.states[personId]?.attributes?.friendly_name;
    if (typeof name === "string" && name) return name;
    return personId
      .replace(/^person\./, "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  private _who(period: PresencePeriod): string {
    if (!period.person_ids) return "Everyone";
    return period.person_ids.map((id) => this._personName(id)).join(", ");
  }

  private _onAdd() {
    const now = new Date();
    this._draft = {
      kind: "absent",
      start: toLocalInput(now),
      end: "",
      selected: this._personIds(),
    };
  }

  private _onEdit(period: PresencePeriod) {
    const all = this._personIds();
    this._draft = {
      periodId: period.id,
      kind: period.kind,
      start: period.start,
      end: period.end,
      selected: all.filter((id) => covers(period, id)),
    };
  }

  private async _onDelete(period: PresencePeriod) {
    try {
      await this.ws.deletePresencePeriod(period.id);
      await this.panel.reloadConfig();
      this.panel.showToast("Period deleted", false);
    } catch (err) {
      this.panel.showToast(`Delete failed: ${this._message(err)}`, true);
    }
  }

  private _message(err: unknown): string {
    if (err && typeof err === "object" && "message" in err) {
      return String((err as { message: unknown }).message);
    }
    return String(err);
  }

  private _update(patch: Partial<PeriodDraft>) {
    if (this._draft) this._draft = { ...this._draft, ...patch };
  }

  private _toggle(personId: string) {
    if (!this._draft) return;
    const selected = this._draft.selected.includes(personId)
      ? this._draft.selected.filter((id) => id !== personId)
      : [...this._draft.selected, personId];
    this._update({ selected });
  }

  private async _onSave() {
    const draft = this._draft;
    if (!draft) return;
    if (!isLocalDateTime(draft.start) || !isLocalDateTime(draft.end)) {
      this.panel.showToast("Enter a start and a return", true);
      return;
    }
    if (draft.end <= draft.start) {
      this.panel.showToast("The return must follow the start", true);
      return;
    }
    const pickPersons = hasPresenceZone(this.config);
    if (pickPersons && draft.selected.length === 0) {
      this.panel.showToast("Select at least one person", true);
      return;
    }
    this._saving = true;
    try {
      await this.ws.setPresencePeriod({
        periodId: draft.periodId,
        kind: draft.kind,
        start: draft.start,
        end: draft.end,
        personIds: pickPersons
          ? selectionToPersonIds(draft.selected, this._personIds())
          : undefined,
      });
      this._draft = null;
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch (err) {
      this.panel.showToast(`Save failed: ${this._message(err)}`, true);
    } finally {
      this._saving = false;
    }
  }

  private _renderPersons(draft: PeriodDraft) {
    const all = this._personIds();
    return html`
      <div class="persons-head">
        <span>Persons</span>
        ${this._button("All", () => this._update({ selected: all }))}
        ${this._button("None", () => this._update({ selected: [] }))}
      </div>
      <div class="chips">
        ${all.map(
          (id) => html`
            <span
              class="chip ${draft.selected.includes(id) ? "selected" : ""}"
              role="checkbox"
              aria-checked=${draft.selected.includes(id)}
              @click=${() => this._toggle(id)}
              >${this._personName(id)}</span
            >
          `,
        )}
      </div>
    `;
  }

  private _renderKind(kind: PresencePeriodKind) {
    const onKind = (value: unknown) => {
      if (value === "absent" || value === "present") {
        this._update({ kind: value });
      }
    };
    return html`<ha-selector
      class="kind-select"
      .hass=${this.hass}
      .selector=${KIND_SELECTOR}
      .value=${kind}
      .required=${true}
      @value-changed=${(e: Event) => onKind((e as CustomEvent).detail?.value)}
    ></ha-selector>`;
  }

  /** A date and a time, joined as a local "YYYY-MM-DDTHH:MM". */
  private _renderWhen(
    label: string,
    value: string,
    onChange: (value: string) => void,
  ) {
    const { date, time } = splitLocal(value);
    const changed = (e: Event) => (e as CustomEvent).detail?.value ?? "";
    return html`
      <div class="field">
        <span>${label}</span>
        <div class="when">
          <ha-date-input
            .locale=${this.hass.locale}
            .value=${date || undefined}
            accessible-label=${`${label} date`}
            @value-changed=${(e: Event) =>
              onChange(joinLocal(changed(e), time))}
          ></ha-date-input>
          <ha-time-input
            .locale=${this.hass.locale}
            .value=${time || undefined}
            accessible-label=${`${label} time`}
            @value-changed=${(e: Event) =>
              onChange(joinLocal(date, changed(e)))}
          ></ha-time-input>
        </div>
      </div>
    `;
  }

  private _renderEditor(draft: PeriodDraft) {
    const pickPersons = hasPresenceZone(this.config);
    return html`
      <div class="editor">
        <div class="field">
          <span>Type</span>
          ${this._renderKind(draft.kind)}
        </div>
        ${this._renderWhen("Start", draft.start, (start) =>
          this._update({ start }),
        )}
        ${this._renderWhen("Return", draft.end, (end) => this._update({ end }))}
        ${pickPersons
          ? this._renderPersons(draft)
          : html`<p class="hint">Everyone</p>`}
        <div class="actions">
          ${this._button("Cancel", () => (this._draft = null))}
          ${this._button("Save", () => void this._onSave(), {
            primary: true,
            disabled: this._saving,
          })}
        </div>
      </div>
    `;
  }

  private _renderPeriod(period: PresencePeriod, now: string, amPm: boolean) {
    const active = period.start <= now;
    const restrictedNoEffect =
      !!period.person_ids && !hasPresenceZone(this.config);
    return html`
      <div class="period-row">
        <span class="kind ${period.kind} ${active ? "active" : ""}">
          ${period.kind === "absent" ? "Away" : "Home"}
        </span>
        <span class="dates">
          ${formatPeriodDate(period.start, amPm)} →
          ${formatPeriodDate(period.end, amPm)}
        </span>
        <span class="who">
          ${this._who(period)}
          ${restrictedNoEffect
            ? html` — no effect without a Time program & presences zone`
            : ""}
        </span>
        <ha-icon-button
          title="Edit"
          .label=${"Edit"}
          @click=${() => this._onEdit(period)}
          ><ha-icon icon="mdi:pencil"></ha-icon
        ></ha-icon-button>
        <ha-icon-button
          title="Delete"
          .label=${"Delete"}
          @click=${() => this._onDelete(period)}
          ><ha-icon icon="mdi:delete"></ha-icon
        ></ha-icon-button>
      </div>
    `;
  }

  render() {
    const now = toLocalInput(new Date());
    const periods = currentAndUpcoming(this.config?.presence_periods, now);
    const amPm = useAmPm(this.hass?.locale);
    return html`
      <ha-card>
        <div class="card-header">Presence &amp; absence periods</div>
        <div class="card-content">
          <p class="hint">
            A period overrides the presence mode from its start to the return;
            rooms with pre-heat are warm on return.
            ${hasPresenceZone(this.config)
              ? ""
              : html`No zone uses Time program &amp; presences: a period applies
                to everyone, Time program zones included (Reduced while away).`}
          </p>
          ${periods.map((p) => this._renderPeriod(p, now, amPm))}
          ${this._draft
            ? this._renderEditor(this._draft)
            : this._button("Add period", () => this._onAdd(), {
                primary: true,
              })}
        </div>
      </ha-card>
    `;
  }
}

customElements.define(
  "climate-manager-presence-periods-card",
  PresencePeriodsCard,
);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-presence-periods-card": PresencePeriodsCard;
  }
}
