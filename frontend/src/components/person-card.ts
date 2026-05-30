// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — Person Card component (UI-04).
 *
 * Expandable card per person. Collapsed: name + presence mode badge + dot.
 * Expanded: presence mode selector (4-option select), room association
 * chips, presence schedule bar (only visible when mode === "scheduled").
 *
 * Auto-save on all changes (D-08). Presence time-bar saves on interaction
 * end (D-09). Toast feedback on success/error (D-10).
 * D-15 (updated): always collapsed by default.
 * D-21: four presence modes — scheduled, ha, force_present, force_absent.
 * D-22: default schedule seeded on first switch to scheduled mode.
 */

import { LitElement, html, css, type PropertyValues } from "lit";
import { property, state } from "lit/decorators.js";

import type {
  PersonConfig,
  DailyProgram,
  Period,
  StatusPayload,
} from "../types.js";
import type { WsClient } from "../ws-client.js";
import type { ClimateManagerPanel } from "../main.js";
import { programToDays, dayIndexToKey } from "./global-settings-tab.js";
import {
  chipStyles,
  sectionLabelStyles,
  selectStyles,
  expandIconStyles,
  scheduleHintStyles,
} from "../shared-styles.js";

import "./time-bar.js";
import "./search-picker.js";

// Presence mode constants (D-21)
const PRESENCE_MODE_SCHEDULED = "scheduled";
const PRESENCE_MODE_HA = "ha";
const PRESENCE_MODE_FORCE_PRESENT = "force_present";
const PRESENCE_MODE_FORCE_ABSENT = "force_absent";

// Default schedule seeded on first switch to Scheduled mode (D-22)
const DEFAULT_SCHEDULE: DailyProgram = {
  mon: [
    { start: "00:00", state: "present" },
    { start: "08:00", state: "absent" },
    { start: "18:00", state: "present" },
  ],
  tue: [
    { start: "00:00", state: "present" },
    { start: "08:00", state: "absent" },
    { start: "18:00", state: "present" },
  ],
  wed: [
    { start: "00:00", state: "present" },
    { start: "08:00", state: "absent" },
    { start: "18:00", state: "present" },
  ],
  thu: [
    { start: "00:00", state: "present" },
    { start: "08:00", state: "absent" },
    { start: "18:00", state: "present" },
  ],
  fri: [
    { start: "00:00", state: "present" },
    { start: "08:00", state: "absent" },
    { start: "18:00", state: "present" },
  ],
  sat: [{ start: "00:00", state: "present" }],
  sun: [{ start: "00:00", state: "present" }],
};

// ISO week-parity helpers — implemented in week-parity.ts to allow
// node --experimental-strip-types tests without Lit decorator transforms.
// Re-exported here so callers can import from person-card.ts directly.
import { getISOWeekNumber, getWeekParity } from "./week-parity.js";
export { getISOWeekNumber, getWeekParity };

export interface RoomChoice {
  id: string;
  name: string;
  /** Optional floor name shown as secondary text in the room search-picker. */
  secondary?: string;
}

export class PersonCard extends LitElement {
  @property({ type: String }) personId!: string;
  @property({ type: String }) personName!: string;
  @property({ attribute: false }) config!: PersonConfig;
  @property({ attribute: false }) roomChoices: RoomChoice[] = [];
  @property({ attribute: false }) ws!: WsClient;
  @property({ attribute: false }) panel!: ClimateManagerPanel;
  @property({ attribute: false }) status: StatusPayload | null = null;

  @state() _expanded = false;
  // Active week for even/odd schedule mode (D-10: not persisted).
  // Recalculated from ISO week parity each time the card expands (D-09).
  @state() private _activeWeek: "even" | "odd" = "even";
  @property({ type: Boolean }) autoExpand = false;

  // Memoize days array — same pattern as global-settings-tab to prevent
  // time-bar drag-preview from clearing on status-only re-renders.
  private _lastSchedule: DailyProgram | undefined = undefined;
  private _cachedDays: Period[][] = [];
  private get _days(): Period[][] {
    const schedule = this.config?.schedule;
    if (schedule !== this._lastSchedule) {
      this._lastSchedule = schedule;
      this._cachedDays = programToDays(schedule);
    }
    return this._cachedDays;
  }

  // Memoized even-week days (D-13)
  private _lastScheduleEven: DailyProgram | undefined = undefined;
  private _cachedDaysEven: Period[][] = [];
  private get _daysEven(): Period[][] {
    const schedule = this.config?.schedule_even;
    if (schedule !== this._lastScheduleEven) {
      this._lastScheduleEven = schedule;
      this._cachedDaysEven = programToDays(schedule);
    }
    return this._cachedDaysEven;
  }

  // Memoized odd-week days (D-13)
  private _lastScheduleOdd: DailyProgram | undefined = undefined;
  private _cachedDaysOdd: Period[][] = [];
  private get _daysOdd(): Period[][] {
    const schedule = this.config?.schedule_odd;
    if (schedule !== this._lastScheduleOdd) {
      this._lastScheduleOdd = schedule;
      this._cachedDaysOdd = programToDays(schedule);
    }
    return this._cachedDaysOdd;
  }

  connectedCallback() {
    super.connectedCallback();
    // D-15 (updated): always collapsed by default
    this._expanded = false;
  }

  updated(changedProperties: PropertyValues) {
    // D-09, D-10: recalculate active week from ISO parity on expand.
    if (changedProperties.has("_expanded") && this._expanded) {
      this._activeWeek = getWeekParity(new Date());
    }
    if (changedProperties.has("autoExpand") && this.autoExpand) {
      this._expanded = true;
      setTimeout(() => {
        const rect = this.getBoundingClientRect();
        this.scrollIntoView({
          behavior: "smooth",
          block: rect.height <= window.innerHeight ? "nearest" : "start",
        });
      }, 0);
    }
  }

  static styles = [
    chipStyles,
    sectionLabelStyles,
    selectStyles,
    expandIconStyles,
    scheduleHintStyles,
    css`
      :host {
        display: block;
      }

      ha-card {
        margin-bottom: 12px;
      }

      .card-header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        cursor: pointer;
      }

      .card-header-left {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .person-name {
        font-size: 16px;
        font-weight: 600;
        color: var(--primary-text-color);
      }

      .mode-badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 400;
      }

      .mode-badge.scheduled {
        background: var(--secondary-background-color, #f5f5f5);
        color: var(--secondary-text-color, #757575);
      }

      .mode-badge.force-present {
        border: 1px solid var(--primary-color, #03a9f4);
        color: var(--primary-color, #03a9f4);
      }

      .mode-badge.force-absent {
        background: var(--secondary-background-color, #f5f5f5);
        color: var(--secondary-text-color, #757575);
      }

      .mode-badge.ha {
        background: var(--secondary-background-color, #f5f5f5);
        color: var(--secondary-text-color, #757575);
      }

      .presence-dot {
        font-size: 12px;
        line-height: 1;
      }

      .presence-dot.present {
        color: var(--success-color, #4caf50);
      }

      .presence-dot.absent {
        color: var(--secondary-text-color, #9e9e9e);
      }

      .card-content {
        padding: 0 16px 16px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }

      .section-label {
        margin-top: 12px;
      }

      .select-wrapper {
        margin-bottom: 4px;
      }

      /* Presence schedule */
      .schedule-section {
        margin-top: 12px;
      }

      .reset-btn {
        margin-top: 12px;
        padding: 8px 16px;
        font-size: 14px;
        font-family: inherit;
        color: var(--primary-color, #03a9f4);
        background: none;
        border: 1px solid var(--primary-color, #03a9f4);
        border-radius: 4px;
        cursor: pointer;
      }

      .reset-btn:hover {
        background: var(--secondary-background-color);
      }

      /* Even/Odd week switcher (D-06, D-07) */
      .week-switcher {
        display: flex;
        gap: 4px;
        margin-bottom: 8px;
      }

      .week-switcher .tab-btn {
        background: none;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 8px 16px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        color: var(--secondary-text-color);
        text-transform: uppercase;
        letter-spacing: 0.07em;
        font-family: inherit;
        outline: none;
      }

      .week-switcher .tab-btn.active {
        border-bottom-color: var(--primary-color);
        color: var(--primary-color);
      }
    `,
  ];

  // -----------------------------------------------------------------------
  // Save handlers
  // -----------------------------------------------------------------------

  private async _onModeChange(e: Event) {
    const newMode = (e.target as HTMLSelectElement).value;
    if (!newMode) return;
    try {
      // D-22: seed default schedule when switching to Scheduled (no existing)
      const hasSchedule =
        !!this.config?.schedule &&
        Object.values(this.config.schedule).some((day) => day.length > 0);

      if (newMode === PRESENCE_MODE_SCHEDULED && !hasSchedule) {
        await this.ws.setPersonConfig(this.personId, {
          mode: newMode,
          schedule: DEFAULT_SCHEDULE,
        });
      } else {
        await this.ws.setPersonConfig(this.personId, { mode: newMode });
      }
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onRoomToggle(roomId: string, add: boolean) {
    const currentIds = [...(this.config?.room_ids ?? [])];
    const newIds = add
      ? currentIds.includes(roomId)
        ? currentIds
        : [...currentIds, roomId]
      : currentIds.filter((id) => id !== roomId);
    try {
      await this.ws.setPersonConfig(this.personId, { room_ids: newIds });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onScheduleTypeChange(e: Event) {
    const newType = (e.target as HTMLSelectElement).value as
      | "single"
      | "even_odd";
    try {
      await this.ws.setPersonConfig(this.personId, {
        schedule_type: newType,
      });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onResetSchedule() {
    // D-14, D-15: reset only the active week in even/odd mode.
    const isEvenOdd = (this.config.schedule_type ?? "single") === "even_odd";
    const field = isEvenOdd
      ? this._activeWeek === "even"
        ? "schedule_even"
        : "schedule_odd"
      : "schedule";
    try {
      await this.ws.setPersonConfig(this.personId, {
        [field]: DEFAULT_SCHEDULE,
      });
      await this.panel.reloadConfig();
      this.panel.showToast("Reset done", false);
    } catch {
      this.panel.showToast("Reset failed — retrying...", true);
    }
  }

  private async _onSchedulePeriodsChanged(e: CustomEvent) {
    const { dayIndex, periods } = e.detail as {
      dayIndex: number;
      periods: Period[];
    };
    // D-11, D-12: write to the active week's schedule field only.
    const isEvenOdd = (this.config.schedule_type ?? "single") === "even_odd";
    const activeSchedule = isEvenOdd
      ? this._activeWeek === "even"
        ? this.config.schedule_even
        : this.config.schedule_odd
      : this.config.schedule;
    const base: DailyProgram = activeSchedule ?? {
      mon: [],
      tue: [],
      wed: [],
      thu: [],
      fri: [],
      sat: [],
      sun: [],
    };
    const updated: DailyProgram = { ...base };
    updated[dayIndexToKey(dayIndex)] = periods;
    const field = isEvenOdd
      ? this._activeWeek === "even"
        ? "schedule_even"
        : "schedule_odd"
      : "schedule";
    try {
      await this.ws.setPersonConfig(this.personId, {
        [field]: updated,
      });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
    e.stopPropagation();
  }

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  private _isCurrentlyPresent(): boolean {
    return this.status?.present_persons?.includes(this.personId) ?? false;
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  private _getBadgeInfo(): { cls: string; text: string } {
    const mode = this.config?.mode ?? PRESENCE_MODE_SCHEDULED;
    switch (mode) {
      case PRESENCE_MODE_FORCE_PRESENT:
        return { cls: "force-present", text: "Force Present" };
      case PRESENCE_MODE_FORCE_ABSENT:
        return { cls: "force-absent", text: "Force Absent" };
      case PRESENCE_MODE_HA:
        return { cls: "ha", text: "HA home tracking" };
      default:
        return { cls: "scheduled", text: "Scheduled" };
    }
  }

  render() {
    const { cls: badgeCls, text: badgeText } = this._getBadgeInfo();
    const currentMode = this.config?.mode ?? PRESENCE_MODE_SCHEDULED;
    const isScheduled = currentMode === PRESENCE_MODE_SCHEDULED;
    // Even/odd week rendering locals (D-01..D-15)
    const scheduleType = this.config?.schedule_type ?? "single";
    const isEvenOdd = scheduleType === "even_odd";
    const resetLabel = isEvenOdd
      ? this._activeWeek === "even"
        ? "Reset Even week to default"
        : "Reset Odd week to default"
      : "Reset to default";
    const currentRoomIds = this.config?.room_ids ?? [];
    const unassignedRooms = this.roomChoices.filter(
      (r) => !currentRoomIds.includes(r.id),
    );

    return html`
      <ha-card>
        <div
          class="card-header-row"
          @click=${() => {
            this._expanded = !this._expanded;
          }}
        >
          <div class="card-header-left">
            <span
              class="presence-dot ${this._isCurrentlyPresent()
                ? "present"
                : "absent"}"
              title="Currently ${this._isCurrentlyPresent()
                ? "present"
                : "absent"}"
              >●</span
            >
            <span class="person-name">${this.personName}</span>
            <span class="mode-badge ${badgeCls}">${badgeText}</span>
          </div>
          <ha-icon
            class="expand-icon ${this._expanded ? "expanded" : ""}"
            icon="mdi:chevron-down"
          ></ha-icon>
        </div>

        ${this._expanded
          ? html`
              <div class="card-content">
                <!-- Presence mode selector -->
                <div
                  class="section-label"
                  title="How this person's presence is determined"
                >
                  Presence mode
                </div>
                <div class="select-wrapper">
                  <select class="mode-select" @change=${this._onModeChange}>
                    <option
                      value=${PRESENCE_MODE_SCHEDULED}
                      ?selected=${currentMode === PRESENCE_MODE_SCHEDULED}
                    >
                      Scheduled
                    </option>
                    <option
                      value=${PRESENCE_MODE_HA}
                      ?selected=${currentMode === PRESENCE_MODE_HA}
                    >
                      HA home tracking
                    </option>
                    <option
                      value=${PRESENCE_MODE_FORCE_PRESENT}
                      ?selected=${currentMode === PRESENCE_MODE_FORCE_PRESENT}
                    >
                      Force Present
                    </option>
                    <option
                      value=${PRESENCE_MODE_FORCE_ABSENT}
                      ?selected=${currentMode === PRESENCE_MODE_FORCE_ABSENT}
                    >
                      Force Absent
                    </option>
                  </select>
                </div>
                <p class="schedule-hint">
                  ${currentMode === PRESENCE_MODE_FORCE_PRESENT
                    ? "Always considered present, regardless of schedule."
                    : currentMode === PRESENCE_MODE_FORCE_ABSENT
                      ? "Always absent. Rooms are not heated for presence."
                      : currentMode === PRESENCE_MODE_HA
                        ? "Presence mirrors Home Assistant home/away tracking."
                        : "Presence follows a weekly schedule."}
                </p>

                <!-- Room associations as chips -->
                <div
                  class="section-label"
                  title="Rooms heated by this person's presence"
                >
                  Room associations
                </div>
                <div class="chips">
                  ${currentRoomIds.map((roomId) => {
                    const room = this.roomChoices.find((r) => r.id === roomId);
                    if (!room) return "";
                    return html`
                      <span
                        class="chip"
                        @click=${() => void this.panel.navigateToRoom(roomId)}
                      >
                        <ha-icon icon="mdi:home-outline"></ha-icon>
                        ${room.name}
                        <button
                          class="chip-remove"
                          @click=${(e: Event) => {
                            e.stopPropagation();
                            void this._onRoomToggle(roomId, false);
                          }}
                        >
                          ×
                        </button>
                      </span>
                    `;
                  })}
                  ${unassignedRooms.length > 0
                    ? html`
                        <search-picker
                          .items=${unassignedRooms.map((r) => ({
                            id: r.id,
                            label: r.name,
                            secondary: r.secondary,
                            icon: "mdi:home-outline",
                          }))}
                          triggerLabel="Add room"
                          triggerIcon="mdi:plus"
                          placeholder="Search rooms…"
                          @picked=${(e: CustomEvent) => {
                            const { id } = e.detail as { id: string };
                            void this._onRoomToggle(id, true);
                          }}
                        ></search-picker>
                      `
                    : ""}
                </div>

                <!-- Presence schedule (only in Scheduled mode) -->
                ${isScheduled
                  ? html`
                      <div
                        class="section-label"
                        title="When this person is considered present"
                      >
                        Presence schedule
                      </div>
                      <div class="section-label">Schedule type</div>
                      <div class="select-wrapper">
                        <select
                          class="mode-select"
                          @change=${this._onScheduleTypeChange}
                        >
                          <option
                            value="single"
                            ?selected=${scheduleType === "single"}
                          >
                            Single week
                          </option>
                          <option
                            value="even_odd"
                            ?selected=${scheduleType === "even_odd"}
                          >
                            Even / Odd weeks
                          </option>
                        </select>
                      </div>
                      ${isEvenOdd
                        ? html`
                            <div class="week-switcher">
                              <button
                                class="tab-btn ${this._activeWeek === "even"
                                  ? "active"
                                  : ""}"
                                @click=${() => {
                                  this._activeWeek = "even";
                                }}
                              >
                                Even
                              </button>
                              <button
                                class="tab-btn ${this._activeWeek === "odd"
                                  ? "active"
                                  : ""}"
                                @click=${() => {
                                  this._activeWeek = "odd";
                                }}
                              >
                                Odd
                              </button>
                            </div>
                            <p class="schedule-hint">
                              Week ${getISOWeekNumber(new Date())} is currently
                              active (${getWeekParity(new Date())} week).
                            </p>
                          `
                        : ""}
                      <div class="schedule-section">
                        <climate-manager-time-bar
                          mode="presence"
                          .days=${isEvenOdd
                            ? this._activeWeek === "even"
                              ? this._daysEven
                              : this._daysOdd
                            : this._days}
                          @periods-changed=${this._onSchedulePeriodsChanged}
                        ></climate-manager-time-bar>
                      </div>
                      <button
                        class="reset-btn"
                        @click=${() => void this._onResetSchedule()}
                      >
                        ${resetLabel}
                      </button>
                    `
                  : ""}
              </div>
            `
          : ""}
      </ha-card>
    `;
  }
}

customElements.define("climate-manager-person-card", PersonCard);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-person-card": PersonCard;
  }
}
