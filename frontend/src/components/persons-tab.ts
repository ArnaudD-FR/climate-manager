/**
 * Climate Manager Panel — Persons tab (UI-04).
 *
 * Ordered person list per D-15:
 *   1. Persons with any non-default setting — first, expanded by default
 *   2. Fully-default persons — after, collapsed by default
 *
 * Each person renders a <climate-manager-person-card>.
 * Empty state: "No persons found…" per Copywriting Contract.
 */

import { LitElement, html, css } from "lit";
import { property } from "lit/decorators.js";

import type { ClimateConfig, StatusPayload, RoomStatus } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import type { RoomChoice } from "./person-card.js";

import "./person-card.js";

export class PersonsTab extends LitElement {
  @property({ attribute: false }) config!: ClimateConfig;
  @property({ attribute: false }) status: StatusPayload | null = null;
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;

  static styles = css`
    :host {
      display: block;
    }

    .empty-state {
      text-align: center;
      padding: 48px 16px;
      color: var(--secondary-text-color);
      font-size: 14px;
      line-height: 1.5;
    }
  `;

  /** Build the room choices list from config.rooms + rooms_status. */
  private _getRoomChoices(): RoomChoice[] {
    const rooms = this.config?.rooms ?? {};
    const statusRooms = this.status?.rooms_status ?? [];

    const allRoomIds = new Set([
      ...Object.keys(rooms),
      ...statusRooms.map((r) => r.area_id),
    ]);

    return [...allRoomIds].map((roomId) => {
      const name =
        (statusRooms.find((r) => r.area_id === roomId) as (RoomStatus & { name?: string }) | undefined)?.name ??
        roomId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
      return { id: roomId, name };
    });
  }

  /** Determine if a person config has any non-default setting (D-15). */
  private _isNonDefault(personId: string): boolean {
    const c = this.config?.persons?.[personId];
    if (!c) return false;
    const hasNonDefaultMode = c.mode != null && c.mode !== "automatic";
    const hasRooms = (c.room_ids?.length ?? 0) > 0;
    const hasSchedule = c.schedule
      ? Object.values(c.schedule).some((dayPeriods) => dayPeriods.length > 0)
      : false;
    return hasNonDefaultMode || hasRooms || hasSchedule;
  }

  render() {
    const persons = this.config?.persons ?? {};
    const allPersonIds = Object.keys(persons);

    if (allPersonIds.length === 0) {
      return html`
        <div class="empty-state">
          No persons found. Add person entities in Home Assistant.
        </div>
      `;
    }

    // Sort: non-default persons first, then fully-default (D-15)
    const sortedIds = [...allPersonIds].sort((a, b) => {
      const aNonDefault = this._isNonDefault(a);
      const bNonDefault = this._isNonDefault(b);
      if (aNonDefault && !bNonDefault) return -1;
      if (!aNonDefault && bNonDefault) return 1;
      return a.localeCompare(b);
    });

    const roomChoices = this._getRoomChoices();

    return html`
      ${sortedIds.map((personId) => {
        const personConfig = persons[personId] ?? {};
        // Display name: derive from person entity id (person.john_doe → "John Doe")
        const personName = personId
          .replace(/^person\./, "")
          .replace(/_/g, " ")
          .replace(/\b\w/g, (c) => c.toUpperCase());

        return html`
          <climate-manager-person-card
            .personId=${personId}
            .personName=${personName}
            .config=${personConfig}
            .roomChoices=${roomChoices}
            .ws=${this.ws}
            .panel=${this.panel}
          ></climate-manager-person-card>
        `;
      })}
    `;
  }
}

customElements.define("climate-manager-persons-tab", PersonsTab);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-persons-tab": PersonsTab;
  }
}
