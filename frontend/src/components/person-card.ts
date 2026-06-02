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
  floorGroupLabelStyles,
} from "../shared-styles.js";

import "./time-bar.js";
import "./search-picker.js";

// Presence mode constants (D-21)
const PRESENCE_MODE_SCHEDULED = "scheduled";
const PRESENCE_MODE_HA = "ha";
const PRESENCE_MODE_FORCE_PRESENT = "force_present";
const PRESENCE_MODE_FORCE_ABSENT = "force_absent";
const PRESENCE_MODE_CALENDAR = "calendar";

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

// Presence-mode display helpers (Phase 10 / UI-01, UI-02).
// Pure functions — no Lit deps — imported for consistent labels and
// conditional option rendering (D-04) and stuck-mode hint (D-05).
import { haOptionLabel, presenceModeHint } from "./presence-mode.js";
export { getISOWeekNumber, getWeekParity };

export interface RoomChoice {
  id: string;
  name: string;
  /** Floor ID from hass.areas — used for grouping chips by floor. */
  floorId: string | null;
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
  // Whether the person has ≥1 device tracker in HA (D-04).
  // Forwarded from PersonsTab; gates the "HA home tracking" option.
  @property({ type: Boolean }) hasDeviceTrackers = false;

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
    floorGroupLabelStyles,
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

      .mode-badge.calendar {
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

      /* Calendar config block inline row (D-11, D-16) */
      .preheat-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
      }

      .preheat-row input[type="number"] {
        width: 72px;
        padding: 6px 8px;
        font-size: 14px;
        font-family: inherit;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
      }

      .preheat-row input[type="number"]:focus {
        outline: none;
        border-color: var(--primary-color, #03a9f4);
      }

      .preheat-row span {
        font-size: 14px;
        color: var(--secondary-text-color);
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

  // Calendar config save handlers (D-09 auto-save pattern, no Save button)

  private async _onCalendarEntityChange(e: Event) {
    const entityId = (e.target as HTMLSelectElement).value;
    const existing = this.config?.calendar_config ?? {};
    try {
      await this.ws.setPersonConfig(this.personId, {
        calendar_config: {
          ...existing,
          entity_id: entityId,
          event_means: existing.event_means ?? "absent",
        },
      });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onEventMeansChange(e: Event) {
    const means = (e.target as HTMLSelectElement).value as "absent" | "present";
    const existing = this.config?.calendar_config ?? {};
    // Cannot save event_means without a calendar entity selected — the
    // backend T-11-06 guard would silently discard the update (CR-02).
    if (!existing.entity_id) {
      this.panel.showToast(
        "Select a calendar entity first before changing event meaning.",
        true,
      );
      return;
    }
    try {
      await this.ws.setPersonConfig(this.personId, {
        calendar_config: { ...existing, event_means: means },
      });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onGapHandlingChange(e: Event) {
    const gap = (e.target as HTMLSelectElement).value as
      | "exact"
      | "day_span"
      | "threshold";
    const existing = this.config?.calendar_config ?? {};
    if (!existing.entity_id) return;
    const update = { ...existing, gap_handling: gap };
    if (gap !== "threshold") delete update.gap_threshold_minutes;
    try {
      await this.ws.setPersonConfig(this.personId, {
        calendar_config: update,
      });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onGapThresholdChange(e: Event) {
    const val = parseInt((e.target as HTMLInputElement).value, 10);
    if (isNaN(val) || val < 0 || val > 480) return;
    const existing = this.config?.calendar_config ?? {};
    if (!existing.entity_id) return;
    try {
      await this.ws.setPersonConfig(this.personId, {
        calendar_config: { ...existing, gap_threshold_minutes: val },
      });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  private async _onPreheatChange(e: Event) {
    const val = parseInt((e.target as HTMLInputElement).value, 10);
    if (!isNaN(val) && val >= 0 && val <= 480) {
      try {
        await this.ws.setPersonConfig(this.personId, {
          preheat_lead_minutes: val,
        });
        await this.panel.reloadConfig();
        this.panel.showToast("Saved", false);
      } catch {
        this.panel.showToast("Save failed — retrying...", true);
      }
    }
  }

  /**
   * Save handler for per-period calendar config changes (D-06).
   * Updates the period's own calendar_config within the schedule.
   */
  private async _onPeriodCalendarConfigChange(
    dayIndex: number,
    periodStart: string,
    newCalendarConfig: {
      entity_id: string;
      event_means: "absent" | "present";
    },
  ) {
    const scheduleType = this.config?.schedule_type ?? "single";
    const isEvenOdd = scheduleType === "even_odd";
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
    const dayKey = dayIndexToKey(dayIndex);
    const updatedDay = (base[dayKey] ?? []).map((p) =>
      p.start === periodStart && "state" in p
        ? { ...p, calendar_config: newCalendarConfig }
        : p,
    );
    const updated: DailyProgram = { ...base, [dayKey]: updatedDay };
    const field = isEvenOdd
      ? this._activeWeek === "even"
        ? "schedule_even"
        : "schedule_odd"
      : "schedule";
    try {
      await this.ws.setPersonConfig(this.personId, { [field]: updated });
      await this.panel.reloadConfig();
      this.panel.showToast("Saved", false);
    } catch {
      this.panel.showToast("Save failed — retrying...", true);
    }
  }

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  private _isCurrentlyPresent(): boolean {
    return this.status?.present_persons?.includes(this.personId) ?? false;
  }

  /**
   * Map floor ID to an MDI icon — same logic as zone-tab._getFloorIcon.
   * Uses panel.hass for floor metadata lookup.
   */
  private _getFloorIcon(fid: string): string {
    const floor = this.panel.hass?.floors?.[fid];
    if (floor?.icon) return floor.icon;
    const level = floor?.level ?? 0;
    if (level === -1) return "mdi:home-floor-negative-1";
    if (level < 0) return "mdi:home-floor-b";
    if (level === 1) return "mdi:home-floor-1";
    if (level === 2) return "mdi:home-floor-2";
    if (level === 3) return "mdi:home-floor-3";
    if (level > 3) return "mdi:home-floor-3";
    return "mdi:home-floor-0";
  }

  /**
   * Group assigned room choices by floor, floors sorted descending by level,
   * rooms alpha-sorted within each group. Floorless rooms go last.
   */
  private _getAssignedRoomGroups(
    currentRoomIds: string[],
  ): Array<{ floorId: string | null; floorName: string; rooms: RoomChoice[] }> {
    const assigned = this.roomChoices.filter((r) =>
      currentRoomIds.includes(r.id),
    );
    const floorGroups = new Map<
      string | null,
      { floorName: string; rooms: RoomChoice[] }
    >();
    for (const room of assigned) {
      if (!floorGroups.has(room.floorId)) {
        floorGroups.set(room.floorId, {
          floorName: room.secondary ?? "",
          rooms: [],
        });
      }
      floorGroups.get(room.floorId)!.rooms.push(room);
    }
    for (const entry of floorGroups.values()) {
      entry.rooms.sort((a, b) => a.name.localeCompare(b.name));
    }
    const sortedFloorIds = [...floorGroups.keys()]
      .filter((fid): fid is string => fid !== null)
      .sort(
        (a, b) =>
          (this.panel.hass?.floors?.[b]?.level ?? 0) -
          (this.panel.hass?.floors?.[a]?.level ?? 0),
      );
    const result: Array<{
      floorId: string | null;
      floorName: string;
      rooms: RoomChoice[];
    }> = sortedFloorIds.map((fid) => ({
      floorId: fid,
      floorName: floorGroups.get(fid)!.floorName,
      rooms: floorGroups.get(fid)!.rooms,
    }));
    const floorless = floorGroups.get(null);
    if (floorless?.rooms.length)
      result.push({ floorId: null, floorName: "", rooms: floorless.rooms });
    return result;
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
        return { cls: "ha", text: haOptionLabel(this.hasDeviceTrackers) };
      case PRESENCE_MODE_CALENDAR:
        return { cls: "calendar", text: "Calendar" };
      default:
        return { cls: "scheduled", text: "Scheduled" };
    }
  }

  render() {
    const { cls: badgeCls, text: badgeText } = this._getBadgeInfo();
    const currentMode = this.config?.mode ?? PRESENCE_MODE_SCHEDULED;
    const isScheduled = currentMode === PRESENCE_MODE_SCHEDULED;
    const isCalendar = currentMode === PRESENCE_MODE_CALENDAR;
    // Even/odd week rendering locals (D-01..D-15)
    const scheduleType = this.config?.schedule_type ?? "single";
    const isEvenOdd = scheduleType === "even_odd";
    const resetLabel = isEvenOdd
      ? this._activeWeek === "even"
        ? "Reset Even week to default"
        : "Reset Odd week to default"
      : "Reset to default";
    const currentRoomIds = this.config?.room_ids ?? [];
    const assignedGroups = this._getAssignedRoomGroups(currentRoomIds);
    const unassignedRooms = this.roomChoices.filter(
      (r) => !currentRoomIds.includes(r.id),
    );

    // D-15: calendar entity list from hass.states filtered to calendar.*
    const calendarEntityIds = Object.keys(this.panel.hass?.states ?? {})
      .filter((id) => id.startsWith("calendar."))
      .sort();

    const renderChip = (room: RoomChoice) => html`
      <span
        class="chip"
        @click=${() => void this.panel.navigateToRoom(room.id)}
      >
        <ha-icon icon="mdi:home-outline"></ha-icon>
        ${room.name}
        <button
          class="chip-remove"
          @click=${(e: Event) => {
            e.stopPropagation();
            void this._onRoomToggle(room.id, false);
          }}
        >
          ×
        </button>
      </span>
    `;

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
                <!-- 1. Presence mode selector -->
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
                      ${haOptionLabel(this.hasDeviceTrackers)}
                    </option>
                    <option
                      value=${PRESENCE_MODE_CALENDAR}
                      ?selected=${currentMode === PRESENCE_MODE_CALENDAR}
                    >
                      Calendar
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

                <!-- 2. Hint / stuck-mode paragraph -->
                <p class="schedule-hint">
                  ${isCalendar
                    ? "Presence determined by calendar events on the" +
                      " selected entity."
                    : presenceModeHint(currentMode, this.hasDeviceTrackers)}
                  ${currentMode === PRESENCE_MODE_HA && !this.hasDeviceTrackers
                    ? html`<ha-icon-button
                        title="Edit person in HA"
                        .label=${"Edit person in HA"}
                        @click=${() => {
                          const slug = this.personId.replace(/^person\./, "");
                          if (!/^[\w-]+$/.test(slug)) return;
                          history.pushState(
                            null,
                            "",
                            `/config/person/edit/${slug}`,
                          );
                          window.dispatchEvent(
                            new CustomEvent("location-changed", {
                              composed: true,
                            }),
                          );
                        }}
                      >
                        <ha-icon icon="mdi:account-edit"></ha-icon>
                      </ha-icon-button>`
                    : ""}
                </p>

                <!-- 3. Calendar config block (Calendar mode only) -->
                ${isCalendar
                  ? html`
                      <div
                        class="section-label"
                        title="Calendar entity for presence"
                      >
                        Calendar source
                      </div>
                      <div class="select-wrapper">
                        <select
                          class="mode-select"
                          @change=${this._onCalendarEntityChange}
                        >
                          ${calendarEntityIds.length === 0
                            ? html`<option value="" disabled selected>
                                No calendar entities found in Home Assistant.
                              </option>`
                            : html`
                                <option
                                  value=""
                                  disabled
                                  ?selected=${!this.config?.calendar_config
                                    ?.entity_id}
                                >
                                  — Select a calendar —
                                </option>
                                ${calendarEntityIds.map(
                                  (id) => html`
                                    <option
                                      value=${id}
                                      ?selected=${this.config?.calendar_config
                                        ?.entity_id === id}
                                    >
                                      ${(this.panel.hass?.states[id]?.attributes
                                        ?.friendly_name as
                                        | string
                                        | undefined) ?? id}
                                    </option>
                                  `,
                                )}
                              `}
                        </select>
                      </div>
                      <div class="section-label">Event means</div>
                      <div class="select-wrapper">
                        <select
                          class="mode-select"
                          @change=${this._onEventMeansChange}
                        >
                          <option
                            value="absent"
                            ?selected=${(this.config?.calendar_config
                              ?.event_means ?? "absent") === "absent"}
                          >
                            Absent during events
                          </option>
                          <option
                            value="present"
                            ?selected=${this.config?.calendar_config
                              ?.event_means === "present"}
                          >
                            Present during events
                          </option>
                        </select>
                      </div>
                      <div class="section-label">Gap handling</div>
                      <div class="select-wrapper">
                        <select
                          class="mode-select"
                          @change=${this._onGapHandlingChange}
                        >
                          <option
                            value="exact"
                            ?selected=${(this.config?.calendar_config
                              ?.gap_handling ?? "exact") === "exact"}
                          >
                            Return home between events
                          </option>
                          <option
                            value="day_span"
                            ?selected=${this.config?.calendar_config
                              ?.gap_handling === "day_span"}
                          >
                            Absent all day (first to last event)
                          </option>
                          <option
                            value="threshold"
                            ?selected=${this.config?.calendar_config
                              ?.gap_handling === "threshold"}
                          >
                            Return home in long gaps only
                          </option>
                        </select>
                      </div>
                      ${this.config?.calendar_config?.gap_handling ===
                      "threshold"
                        ? html`
                            <div class="section-label">
                              Minimum gap to return home
                            </div>
                            <div class="preheat-row">
                              <input
                                type="number"
                                min="0"
                                max="480"
                                step="5"
                                .value=${String(
                                  this.config?.calendar_config
                                    ?.gap_threshold_minutes ?? 30,
                                )}
                                @change=${this._onGapThresholdChange}
                              />
                              <span>min</span>
                            </div>
                          `
                        : ""}
                      <div class="section-label">Wake-up advance</div>
                      <div class="preheat-row">
                        <input
                          type="number"
                          min="0"
                          max="480"
                          step="5"
                          .value=${String(
                            this.config?.preheat_lead_minutes ?? 60,
                          )}
                          @change=${this._onPreheatChange}
                        />
                        <span>min</span>
                      </div>
                      <p class="schedule-hint">
                        Minutes to start heating before your first calendar
                        event of the day.
                      </p>
                    `
                  : ""}

                <!-- 4. Presence schedule section (Scheduled mode only) -->
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
                            <p class="schedule-hint">
                              Week ${getISOWeekNumber(new Date())} is currently
                              active (${getWeekParity(new Date())} week).
                            </p>
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
                      ${(() => {
                        // D-17: render inline calendar config for each
                        // period with state "calendar" in the active schedule.
                        const activeDays = isEvenOdd
                          ? this._activeWeek === "even"
                            ? this._daysEven
                            : this._daysOdd
                          : this._days;
                        const calPeriods: Array<{
                          dayIndex: number;
                          period: (typeof activeDays)[0][0];
                        }> = [];
                        activeDays.forEach((dayPeriods, dayIndex) => {
                          dayPeriods.forEach((p) => {
                            if ("state" in p && p.state === "calendar") {
                              calPeriods.push({ dayIndex, period: p });
                            }
                          });
                        });
                        const DAY_NAMES = [
                          "Mon",
                          "Tue",
                          "Wed",
                          "Thu",
                          "Fri",
                          "Sat",
                          "Sun",
                        ];
                        if (calPeriods.length === 0) return "";
                        return html`
                          ${calPeriods.map(({ dayIndex, period }) => {
                            const cfg =
                              "calendar_config" in period
                                ? period.calendar_config
                                : undefined;
                            const currentEntityId = cfg?.entity_id ?? "";
                            const currentMeans = cfg?.event_means ?? "absent";
                            const friendlyName = currentEntityId
                              ? (this.panel.hass?.states[currentEntityId]
                                  ?.attributes?.friendly_name as
                                  | string
                                  | undefined) ?? currentEntityId
                              : "";
                            return html`
                              <div class="section-label">
                                Calendar: ${friendlyName || "—"}
                                (${DAY_NAMES[dayIndex]} ${period.start})
                              </div>
                              <div class="select-wrapper">
                                <select
                                  class="mode-select"
                                  @change=${(e: Event) => {
                                    const newId = (
                                      e.target as HTMLSelectElement
                                    ).value;
                                    void this._onPeriodCalendarConfigChange(
                                      dayIndex,
                                      period.start,
                                      {
                                        entity_id: newId,
                                        event_means: currentMeans,
                                      },
                                    );
                                  }}
                                >
                                  <option
                                    value=""
                                    disabled
                                    ?selected=${!currentEntityId}
                                  >
                                    — Select a calendar —
                                  </option>
                                  ${calendarEntityIds.map(
                                    (id) => html`
                                      <option
                                        value=${id}
                                        ?selected=${currentEntityId === id}
                                      >
                                        ${(this.panel.hass?.states[id]
                                          ?.attributes?.friendly_name as
                                          | string
                                          | undefined) ?? id}
                                      </option>
                                    `,
                                  )}
                                </select>
                              </div>
                              <div class="select-wrapper">
                                <select
                                  class="mode-select"
                                  @change=${(e: Event) => {
                                    const newMeans = (
                                      e.target as HTMLSelectElement
                                    ).value as "absent" | "present";
                                    // Guard: no entity selected → save would
                                    // be silently discarded by T-11-06 (CR-02)
                                    if (!currentEntityId) {
                                      this.panel.showToast(
                                        "Select a calendar entity first" +
                                          " before changing event meaning.",
                                        true,
                                      );
                                      return;
                                    }
                                    void this._onPeriodCalendarConfigChange(
                                      dayIndex,
                                      period.start,
                                      {
                                        entity_id: currentEntityId,
                                        event_means: newMeans,
                                      },
                                    );
                                  }}
                                >
                                  <option
                                    value="absent"
                                    ?selected=${currentMeans === "absent"}
                                  >
                                    Absent during events
                                  </option>
                                  <option
                                    value="present"
                                    ?selected=${currentMeans === "present"}
                                  >
                                    Present during events
                                  </option>
                                </select>
                              </div>
                            `;
                          })}
                        `;
                      })()}
                      <button
                        class="reset-btn"
                        @click=${() => void this._onResetSchedule()}
                      >
                        ${resetLabel}
                      </button>
                    `
                  : ""}

                <!-- 5. Room associations grouped by floor (D-14: moved last) -->
                <div
                  class="section-label"
                  title="Rooms heated by this person's presence"
                >
                  Room associations
                </div>
                ${assignedGroups.map(
                  (group) => html`
                    ${group.floorId !== null
                      ? html`<div class="floor-group-label">
                          <ha-icon
                            icon=${this._getFloorIcon(group.floorId)}
                          ></ha-icon
                          >${group.floorName}
                        </div>`
                      : ""}
                    <div class="chips">${group.rooms.map(renderChip)}</div>
                  `,
                )}
                ${assignedGroups.length === 0
                  ? html`<div class="chips"></div>`
                  : ""}
                ${unassignedRooms.length > 0
                  ? html`
                      <div class="chips">
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
                      </div>
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
