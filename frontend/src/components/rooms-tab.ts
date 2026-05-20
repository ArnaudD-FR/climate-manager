/**
 * Climate Manager Panel — Rooms tab (UI-03).
 *
 * Ordered room list per D-14:
 *   1. Rooms with a time_program override — first, expanded by default
 *   2. Rooms using the global program — after, collapsed by default
 *
 * Each room renders a <climate-manager-room-card>.
 * Empty state: "No rooms discovered…" per Copywriting Contract.
 */

import { LitElement, html, css } from "lit";
import { property } from "lit/decorators.js";

import type { ClimateConfig, StatusPayload, RoomStatus, Hass } from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";

import "./room-card.js";

export class RoomsTab extends LitElement {
  @property({ attribute: false }) config!: ClimateConfig;
  @property({ attribute: false }) status: StatusPayload | null = null;
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;
  @property({ attribute: false }) hass!: Hass;

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

  private _getRoomStatus(roomId: string): RoomStatus | null {
    return (
      this.status?.rooms_status?.find((r) => r.area_id === roomId) ?? null
    );
  }

  render() {
    const rooms = this.config?.rooms ?? {};
    // Also include rooms discovered via rooms_status that aren't in config.rooms yet
    const statusRooms = this.status?.rooms_status ?? [];
    const allRoomIds = new Set([
      ...Object.keys(rooms),
      ...statusRooms.map((r) => r.area_id),
    ]);

    if (allRoomIds.size === 0) {
      return html`
        <div class="empty-state">
          No rooms discovered. Create areas in Home Assistant and assign climate entities.
        </div>
      `;
    }

    // Sort: rooms with time_program first, then the rest (D-14)
    const sortedIds = [...allRoomIds].sort((a, b) => {
      const aHasProgram = !!(rooms[a]?.time_program);
      const bHasProgram = !!(rooms[b]?.time_program);
      if (aHasProgram && !bHasProgram) return -1;
      if (!aHasProgram && bHasProgram) return 1;
      return a.localeCompare(b);
    });

    return html`
      ${sortedIds.map((roomId) => {
        const roomConfig = rooms[roomId] ?? {};
        const roomStatus = this._getRoomStatus(roomId);
        // Display name: area_id as fallback (backend may provide a name in status)
        const roomName = roomStatus?.name ?? roomId.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

        return html`
          <climate-manager-room-card
            .roomId=${roomId}
            .roomName=${roomName}
            .config=${roomConfig}
            .roomStatus=${roomStatus}
            .panelConfig=${this.config}
            .ws=${this.ws}
            .panel=${this.panel}
            .hass=${this.hass}
          ></climate-manager-room-card>
        `;
      })}
    `;
  }
}

customElements.define("climate-manager-rooms-tab", RoomsTab);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-rooms-tab": RoomsTab;
  }
}
