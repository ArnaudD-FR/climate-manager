/**
 * Climate Manager Panel — Rooms tab (UI-03).
 *
 * Ordered room list per D-14a/D-14b:
 *   1. Rooms grouped by floor, ordered by floor.level ascending
 *   2. Within each floor: alphabetical by room name
 *   3. Floorless rooms at the end, alphabetical, no section header
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

    .floor-header {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--secondary-text-color);
      padding: 16px 4px 8px;
    }

    .floor-header:first-child {
      padding-top: 0;
    }

    .floor-header ha-icon {
      --mdc-icon-size: 16px;
      width: 16px;
      height: 16px;
      flex-shrink: 0;
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

    // Display name helper: prefer status name, fall back to formatted area_id
    const getName = (id: string) =>
      this.status?.rooms_status?.find((r) => r.area_id === id)?.name ??
      id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

    // Group rooms by floor_id (null = floorless)
    const floorGroups = new Map<string | null, string[]>();
    for (const roomId of allRoomIds) {
      const floorId = this.hass?.areas?.[roomId]?.floor_id ?? null;
      if (!floorGroups.has(floorId)) {
        floorGroups.set(floorId, []);
      }
      floorGroups.get(floorId)!.push(roomId);
    }

    // Sort each group alphabetically by display name
    for (const ids of floorGroups.values()) {
      ids.sort((a, b) => getName(a).localeCompare(getName(b)));
    }

    // Sort non-null floor IDs by floor.level ascending
    const sortedFloorIds = [...floorGroups.keys()]
      .filter((fid): fid is string => fid !== null)
      .sort(
        (a, b) =>
          (this.hass?.floors?.[b]?.level ?? 0) -
          (this.hass?.floors?.[a]?.level ?? 0),
      );

    const floorlessIds = floorGroups.get(null) ?? [];

    // Room card renderer (shared for all groups)
    const renderRoomCard = (roomId: string) => {
      const roomConfig = rooms[roomId] ?? {};
      const roomStatus = this._getRoomStatus(roomId);
      const roomName = getName(roomId);
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
    };

    const getFloorIcon = (fid: string): string => {
      const floor = this.hass?.floors?.[fid];
      if (floor?.icon) return floor.icon;
      const level = floor?.level ?? 0;
      if (level === -1) return "mdi:home-floor-negative-1";
      if (level < 0) return "mdi:home-floor-b";
      if (level === 1) return "mdi:home-floor-1";
      if (level === 2) return "mdi:home-floor-2";
      if (level === 3) return "mdi:home-floor-3";
      if (level > 3) return "mdi:home-floor-3";
      return "mdi:home-floor-0";
    };

    return html`
      ${sortedFloorIds.map((fid) => {
        const floorName = this.hass?.floors?.[fid]?.name ?? fid;
        const ids = floorGroups.get(fid) ?? [];
        return html`
          <div class="floor-header">
            <ha-icon icon=${getFloorIcon(fid)}></ha-icon>
            ${floorName}
          </div>
          ${ids.map(renderRoomCard)}
        `;
      })}
      ${floorlessIds.map(renderRoomCard)}
    `;
  }
}

customElements.define("climate-manager-rooms-tab", RoomsTab);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-rooms-tab": RoomsTab;
  }
}
