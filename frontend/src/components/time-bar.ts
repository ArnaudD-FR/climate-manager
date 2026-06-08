// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — shared 7-day time-bar component.
 *
 * Renders a stacked 7-row 24h bar editor used by both:
 *   - Time program schedules (mode = "schedule", 4 period modes)
 *   - Presence schedules       (mode = "presence", 2 states: present / absent)
 *
 * Each row shows:
 *   - 3-letter day label (Mon…Sun), right-aligned, 40px wide
 *   - Full-width 40px colored bar (segments from `days[i]`)
 *   - [Copy] and [Paste] icon buttons
 *
 * Above all 7 rows: a time axis (00:00 / 06:00 / 12:00 / 18:00 / 24:00).
 * Below all 7 rows: a shared time axis (same structure, same labels).
 *
 * Interactions (D-04…D-09):
 *   click empty bar   → mode popup "Split at HH:MM" → insert new segment
 *   click block       → popup: time range + Change mode + Split + Delete
 *   drag boundary     → tooltip shows HH:MM (snapped), save on pointerup
 *   Copy              → store day's periods in panel-local _clipboard
 *   Paste             → overwrite target day, emit periods-changed immediately
 *
 * Emits CustomEvent "periods-changed" { dayIndex, periods } on interaction end.
 * Never calls WebSocket — presentational + interaction only.
 */

import { LitElement, html, css, type PropertyValues } from "lit";
import { property, state } from "lit/decorators.js";

import {
  PERIOD_COLORS,
  PRESENCE_COLORS,
  PERIOD_DISPLAY_NAMES,
  type Period,
} from "../types.js";

// ---------------------------------------------------------------------------
// Internal drag state
// ---------------------------------------------------------------------------
interface DragState {
  dayIndex: number;
  segIndex: number;
  startX: number;
  initialBoundaryMinutes: number;
}

// ---------------------------------------------------------------------------
// Internal popup state
// ---------------------------------------------------------------------------
type PopupKind = "split" | "edit";

interface PopupState {
  kind: PopupKind;
  dayIndex: number;
  segIndex?: number; // for "edit" — which block was clicked
  snappedMinutes?: number; // for "split" — where to split
  x: number; // CSS left for popup position
  y: number; // CSS top for popup position
}

// ---------------------------------------------------------------------------
// Day names
// ---------------------------------------------------------------------------
const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// ---------------------------------------------------------------------------
// Period type cycles used by "Split period" action
// ---------------------------------------------------------------------------
const SCHEDULE_CYCLE = ["frost_protection", "reduced", "normal", "comfort"];
const PRESENCE_CYCLE = ["present", "absent"];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export class ClimateManagerTimeBar extends LitElement {
  /**
   * Seven-element array of period arrays.
   * Index 0 = Monday … Index 6 = Sunday.
   * Each element: Array<{ start: "HH:MM"; mode?: string; state?: string }>
   */
  @property({ type: Array }) days: Period[][] = Array.from(
    { length: 7 },
    () => [],
  );

  /** "schedule" (4 period modes) or "presence" (present / absent). */
  @property({ type: String }) mode: "schedule" | "presence" = "schedule";

  // ----- internal state ---------------------------------------------------
  @state() private _clipboard: Period[] | null = null;
  @state() private _drag: DragState | null = null;
  @state() private _dragTooltipMinutes: number | null = null;
  @state() private _dragTooltipX: number = 0;
  @state() private _dragTooltipY: number = 0;
  /**
   * Live preview of `days` during a drag operation.
   * Set on every pointermove with the dragged boundary applied.
   * Cleared on pointerup — the committed value comes from the
   * `periods-changed` event and parent re-render.
   * Never triggers `periods-changed` events.
   */
  @state() private _dragPreviewDays: Period[][] | null = null;
  @state() private _popup: PopupState | null = null;
  /** Set after drag; cleared by click handlers to suppress synthetic click. */
  private _justDragged = false;

  // -----------------------------------------------------------------------
  // Styles
  // -----------------------------------------------------------------------
  static styles = css`
    :host {
      display: block;
      user-select: none;
    }

    .week-grid {
      display: flex;
      flex-direction: column;
      gap: 4px;
      /* Prevent Android WebView from consuming touch events as scroll gestures
         before pointer events fire on child elements (drag handles). */
      touch-action: none;
    }

    .day-row {
      display: flex;
      align-items: center;
      height: 40px;
      /* overflow:visible so the 44px drag handle (positioned right:-22px on
         .segment) stays hittable beyond the segment boundary. overflow:hidden
         clips the handle, making the touch target unreachable on Android. */
      overflow: visible;
    }

    .day-label {
      width: 40px;
      flex-shrink: 0;
      text-align: right;
      font-size: 12px;
      font-weight: 400;
      color: var(--secondary-text-color, #757575);
      padding-right: 8px;
      line-height: 1;
    }

    .bar-wrap {
      flex: 1;
      min-width: 0;
      height: 40px;
      position: relative;
      cursor: pointer;
      overflow: visible;
    }

    .bar-row-inner {
      display: flex;
      width: 100%;
      height: 100%;
      position: relative;
    }

    .segment {
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-primary-color, white);
      overflow: hidden;
      position: relative;
      cursor: pointer;
      box-sizing: border-box;
    }

    .segment-label {
      pointer-events: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 100%;
      padding: 0 4px;
      box-sizing: border-box;
    }

    .drag-handle {
      position: absolute;
      right: -22px;
      top: 0;
      width: 44px;
      height: 100%;
      cursor: ew-resize;
      z-index: 2;
      touch-action: none;
    }

    .empty-hint {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      color: var(--secondary-text-color, #757575);
      background: var(--divider-color, #e0e0e0);
      border-radius: 2px;
    }

    .day-actions {
      display: flex;
      align-items: center;
      flex-shrink: 0;
      margin-left: 2px;
      gap: 0;
    }

    ha-icon-button.paste-disabled {
      opacity: 0.4;
    }

    /* ---- Shared time axis (above and below day rows) --------------------- */
    /* Mirrors the exact 3-column layout of .day-row so ticks align pixel-
       perfectly with the bar area regardless of button size. */
    .time-axis {
      display: flex;
      align-items: center;
      margin-top: 2px;
    }

    .time-axis-label-spacer {
      width: 40px;
      flex-shrink: 0;
      padding-right: 8px;
    }

    .time-axis-inner {
      position: relative;
      flex: 1;
      height: 1em;
    }

    /* Invisible clone of .day-actions — forces bar-wrap width to match.
       height:0 + overflow:hidden collapses to label height while the browser
       computes the natural button width for flex layout. */
    .time-axis-actions-ghost {
      display: flex;
      flex-shrink: 0;
      margin-left: 4px;
      gap: 0;
      visibility: hidden;
      pointer-events: none;
      --mdc-icon-button-size: 32px;
      height: 0;
      overflow: hidden;
    }

    .axis-tick {
      position: absolute;
      transform: translateX(-50%);
      font-size: 10px;
      color: var(--secondary-text-color, #757575);
      white-space: nowrap;
    }
    .axis-tick:first-child {
      transform: translateX(0);
    }
    .axis-tick:last-child {
      transform: translateX(-100%);
    }

    /* On narrow screens hide 3h-interval ticks (3, 9, 15, 21) */
    @media (max-width: 479px) {
      .axis-tick--3h {
        display: none;
      }
    }
    /* On very narrow screens also hide 6h-interval ticks (6, 18) */
    @media (max-width: 339px) {
      .axis-tick--6h {
        display: none;
      }
    }

    /* Drag tooltip */
    .drag-tooltip {
      position: fixed;
      background: var(--app-header-background-color, rgba(0, 0, 0, 0.75));
      color: var(--text-primary-color, white);
      font-size: 12px;
      border-radius: 3px;
      padding: 2px 6px;
      pointer-events: none;
      z-index: 9998;
      transform: translate(-50%, -130%);
    }

    /* Mode popup */
    .popup-overlay {
      position: fixed;
      inset: 0;
      z-index: 9990;
    }

    .popup {
      position: fixed;
      background: var(--card-background-color, #fff);
      border-radius: 4px;
      box-shadow: var(--ha-card-box-shadow, 0 4px 16px rgba(0, 0, 0, 0.25));
      padding: 12px;
      z-index: 9991;
      min-width: 160px;
    }

    .popup-title {
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 8px;
      color: var(--primary-text-color);
    }

    .mode-options {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .mode-option {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 8px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 13px;
      color: var(--primary-text-color);
      border: none;
      background: transparent;
      width: 100%;
      text-align: left;
    }

    .mode-option:hover {
      background: var(--secondary-background-color, #f5f5f5);
    }

    .mode-swatch {
      width: 14px;
      height: 14px;
      border-radius: 2px;
      flex-shrink: 0;
    }

    .popup-actions {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid var(--divider-color, #e0e0e0);
    }

    .popup-btn {
      padding: 6px 8px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 13px;
      border: none;
      background: transparent;
      width: 100%;
      text-align: left;
      color: var(--primary-text-color);
    }

    .popup-btn:hover {
      background: var(--secondary-background-color, #f5f5f5);
    }

    .popup-btn.danger {
      color: var(--error-color, #db4437);
    }
  `;

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  private _snapToMinutes(raw: number): number {
    return Math.round(raw / 15) * 15;
  }

  private _pixelToMinutes(x: number, barWidth: number): number {
    return (x / barWidth) * 1440;
  }

  /**
   * Extra upward offset (px) to apply to the drag tooltip Y position for touch
   * events. CSS transform already shifts ~23px above `top`; adding 28px on
   * touch gives ~51px total clearance — just above one row (40px) height.
   * Mouse/pen events get 0 — the CSS offset alone is sufficient.
   */
  private _touchTooltipOffset(e: PointerEvent): number {
    return e.pointerType === "touch" ? 28 : 0;
  }

  private _minutesToHHMM(minutes: number): string {
    const clamped = Math.max(0, Math.min(1440, minutes));
    const h = Math.floor(clamped / 60);
    const m = clamped % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  }

  private _colorForPeriod(period: Period): string {
    const key =
      this.mode === "presence"
        ? period.state ?? "absent"
        : period.mode ?? "frost_protection";
    if (this.mode === "presence") {
      return PRESENCE_COLORS[key] ?? PRESENCE_COLORS["absent"];
    }
    return PERIOD_COLORS[key] ?? PERIOD_COLORS["frost_protection"];
  }

  private _labelForPeriod(period: Period): string {
    const key =
      this.mode === "presence"
        ? period.state ?? "absent"
        : period.mode ?? "frost_protection";
    if (key === "calendar" && "calendar_config" in period) {
      const entityId = period.calendar_config?.entity_id;
      if (entityId) {
        const name = entityId.replace(/^calendar\./, "").replace(/_/g, " ");
        return `Calendar: ${name}`;
      }
    }
    return PERIOD_DISPLAY_NAMES[key] ?? key;
  }

  /**
   * Convert a periods array to renderable segments with computed widths.
   * Always starts at 00:00 — prepends a synthesised period if needed.
   */
  private _toSegments(
    periods: Period[],
  ): Array<{ period: Period; startMin: number; endMin: number }> {
    if (periods.length === 0) return [];

    const sorted = [...periods].sort((a, b) => a.start.localeCompare(b.start));

    // Ensure first segment starts at 00:00
    const first = sorted[0];
    const firstMin = this._timeToMinutes(first.start);
    const working =
      firstMin > 0
        ? [{ start: "00:00", mode: first.mode, state: first.state }, ...sorted]
        : sorted;

    const result: Array<{ period: Period; startMin: number; endMin: number }> =
      [];
    for (let i = 0; i < working.length; i++) {
      const startMin = this._timeToMinutes(working[i].start);
      const endMin =
        i + 1 < working.length
          ? this._timeToMinutes(working[i + 1].start)
          : 1440;
      result.push({ period: working[i], startMin, endMin });
    }
    return result;
  }

  private _timeToMinutes(hhmm: string): number {
    const [h, m] = hhmm.split(":").map(Number);
    return (h ?? 0) * 60 + (m ?? 0);
  }

  /** Emit periods-changed for a specific day. */
  private _emitChange(dayIndex: number, periods: Period[]) {
    this.dispatchEvent(
      new CustomEvent("periods-changed", {
        detail: { dayIndex, periods },
        bubbles: true,
        composed: true,
      }),
    );
  }

  /**
   * Returns true if every period in `preview` has identical start + mode/state
   * to the corresponding period in `days` for the same day index.
   *
   * Used by updated() to avoid clearing _dragPreviewDays when the incoming
   * `days` prop changes by reference but not by content — which happens when
   * _loadStatus() re-renders GlobalSettingsTab before _loadConfig() completes,
   * causing programToDays() to produce new array objects with the same values.
   */
  private _previewMatchesDays(preview: Period[][], days: Period[][]): boolean {
    if (preview.length !== days.length) return false;
    for (let d = 0; d < days.length; d++) {
      const pDay = preview[d] ?? [];
      const cDay = days[d] ?? [];
      if (pDay.length !== cDay.length) return false;
      for (let i = 0; i < pDay.length; i++) {
        const p = pDay[i];
        const c = cDay[i];
        if (p.start !== c.start || p.mode !== c.mode || p.state !== c.state) {
          return false;
        }
      }
    }
    return true;
  }

  // -----------------------------------------------------------------------
  // Popup helpers
  // -----------------------------------------------------------------------

  private _modeOptions(): Array<{ key: string; label: string; color: string }> {
    if (this.mode === "presence") {
      // Phase 11 (D-17): "calendar" is a selectable period state but NOT
      // part of PRESENCE_CYCLE (click/drag cycling). It is only reachable
      // via this popup's Change mode options (Landmine 6).
      return [
        { key: "present", label: "Present", color: PRESENCE_COLORS["present"] },
        { key: "absent", label: "Absent", color: PRESENCE_COLORS["absent"] },
        {
          key: "calendar",
          label: "Calendar",
          color: PRESENCE_COLORS["calendar"],
        },
      ];
    }
    return [
      {
        key: "frost_protection",
        label: "Frost protection",
        color: PERIOD_COLORS["frost_protection"],
      },
      { key: "reduced", label: "Reduced", color: PERIOD_COLORS["reduced"] },
      { key: "normal", label: "Normal", color: PERIOD_COLORS["normal"] },
      { key: "comfort", label: "Comfort", color: PERIOD_COLORS["comfort"] },
    ];
  }

  private _closePopup() {
    this._popup = null;
  }

  // -----------------------------------------------------------------------
  // Click on empty bar → split
  // -----------------------------------------------------------------------

  private _onBarClick(e: MouseEvent, dayIndex: number) {
    // Ignore if a drag is active or just ended
    if (this._drag) return;
    if (this._justDragged) {
      this._justDragged = false;
      e.stopPropagation();
      return;
    }

    const barEl = e.currentTarget as HTMLElement;
    const rect = barEl.getBoundingClientRect();
    const rawMinutes = this._pixelToMinutes(e.clientX - rect.left, rect.width);
    const snapped = this._snapToMinutes(rawMinutes);

    // Check if click is on an existing segment (handled by _onSegmentClick)
    // Fires on bar-wrap background — always a "new" area click.
    this._popup = {
      kind: "split",
      dayIndex,
      snappedMinutes: snapped,
      x: e.clientX,
      y: e.clientY,
    };
    e.stopPropagation();
  }

  private _onSplitModeSelect(modeKey: string) {
    if (!this._popup || this._popup.kind !== "split") return;
    const { dayIndex, snappedMinutes } = this._popup;

    const day = [...(this.days[dayIndex] ?? [])];
    const newPeriod: Period =
      this.mode === "presence"
        ? { start: this._minutesToHHMM(snappedMinutes ?? 0), state: modeKey }
        : { start: this._minutesToHHMM(snappedMinutes ?? 0), mode: modeKey };

    // Insert and remove zero-width duplicates
    day.push(newPeriod);
    const sorted = day.sort((a, b) => a.start.localeCompare(b.start));
    const deduped = sorted.filter(
      (p, i) => i === 0 || p.start !== sorted[i - 1].start,
    );

    this._closePopup();
    this._emitChange(dayIndex, deduped);
  }

  // -----------------------------------------------------------------------
  // Click on existing segment → edit/delete popup
  // -----------------------------------------------------------------------

  private _onSegmentClick(e: MouseEvent, dayIndex: number, segIndex: number) {
    // Only open popup for left-click (not drag end)
    if (this._drag) {
      e.stopPropagation();
      return;
    }
    if (this._justDragged) {
      this._justDragged = false;
      e.stopPropagation();
      return;
    }
    this._popup = {
      kind: "edit",
      dayIndex,
      segIndex,
      x: e.clientX,
      y: e.clientY,
    };
    e.stopPropagation();
  }

  private _onEditModeSelect(modeKey: string) {
    if (!this._popup || this._popup.kind !== "edit") return;
    const { dayIndex, segIndex } = this._popup;
    const segments = this._toSegments(this.days[dayIndex] ?? []);
    const seg = segments[segIndex ?? 0];
    if (!seg) return;

    // Rebuild the periods array, replacing this segment's mode/state
    const newPeriods = (this.days[dayIndex] ?? []).map((p) => {
      if (p.start === seg.period.start) {
        return this.mode === "presence"
          ? { ...p, state: modeKey }
          : { ...p, mode: modeKey };
      }
      return p;
    });

    this._closePopup();
    this._emitChange(dayIndex, newPeriods);
  }

  private _onDeleteSegment() {
    if (!this._popup || this._popup.kind !== "edit") return;
    const { dayIndex, segIndex } = this._popup;
    const segments = this._toSegments(this.days[dayIndex] ?? []);
    const seg = segments[segIndex ?? 0];
    if (!seg) return;

    // Delete: remove this period from the source periods array.
    // Left neighbor (or implicit 00:00 fill) expands to cover the gap (D-05).
    let newPeriods = (this.days[dayIndex] ?? []).filter(
      (p) => p.start !== seg.period.start,
    );

    // When the deleted period was the opening 00:00 entry, the schedule must
    // still begin at 00:00. Promote the new first period to "00:00" so it
    // explicitly covers from midnight instead of leaving a gap that
    // _toSegments would silently synthesise — which causes the first block to
    // appear to change state rather than disappear (D-05).
    if (
      seg.period.start === "00:00" &&
      newPeriods.length > 0 &&
      newPeriods[0].start !== "00:00"
    ) {
      newPeriods = [
        { ...newPeriods[0], start: "00:00" },
        ...newPeriods.slice(1),
      ];
    }

    this._closePopup();
    this._emitChange(dayIndex, newPeriods);
  }

  /**
   * Split the clicked period at its midpoint (snapped to 15 min).
   * The first half keeps the original type; the second half gets the next
   * type in the cycle:
   *   schedule: frost_protection→reduced→normal→comfort→frost_protection
   *   presence: present → absent → present
   *
   * If the period is too narrow to split (< 30 min, leaving no room for two
   * 15-min halves) the action is silently ignored.
   */
  private _onSplitPeriod() {
    if (!this._popup || this._popup.kind !== "edit") return;
    const { dayIndex, segIndex } = this._popup;
    const segments = this._toSegments(this.days[dayIndex] ?? []);
    const seg = segments[segIndex ?? 0];
    if (!seg) return;

    const duration = seg.endMin - seg.startMin;
    // Need at least 30 min to produce two 15-min halves
    if (duration < 30) return;

    // Compute midpoint snapped to 15 min, clamped so both halves are >= 15 min
    const rawMid = seg.startMin + duration / 2;
    const snappedMid = Math.max(
      seg.startMin + 15,
      Math.min(seg.endMin - 15, this._snapToMinutes(rawMid)),
    );

    // Determine the next type in the cycle
    const cycle = this.mode === "presence" ? PRESENCE_CYCLE : SCHEDULE_CYCLE;
    const currentType =
      this.mode === "presence"
        ? seg.period.state ?? "absent"
        : seg.period.mode ?? "frost_protection";
    const currentIdx = cycle.indexOf(currentType);
    // "calendar" is not in PRESENCE_CYCLE; use "absent" as the next half so
    // the split is explicit and safe — the user can then set the new half to
    // "calendar" and configure it (WR-02).
    const nextType =
      currentIdx === -1 ? "absent" : cycle[(currentIdx + 1) % cycle.length];

    // Build the two replacement periods
    const firstHalf: Period =
      this.mode === "presence"
        ? { start: seg.period.start, state: currentType }
        : { start: seg.period.start, mode: currentType };
    const secondHalf: Period =
      this.mode === "presence"
        ? { start: this._minutesToHHMM(snappedMid), state: nextType }
        : { start: this._minutesToHHMM(snappedMid), mode: nextType };

    // Replace the original period in the source array with the two halves.
    // The original period is identified by its start time.
    // For a synthesised 00:00 filler (absent from source), insert both halves.
    const sourcePeriods = this.days[dayIndex] ?? [];
    const existsInSource = sourcePeriods.some(
      (p) => p.start === seg.period.start,
    );

    let newPeriods: Period[];
    if (existsInSource) {
      newPeriods = sourcePeriods.flatMap((p) =>
        p.start === seg.period.start ? [firstHalf, secondHalf] : [p],
      );
    } else {
      // Synthesised 00:00 filler — just insert secondHalf; filler is implicit
      newPeriods = [secondHalf, ...sourcePeriods];
    }

    this._closePopup();
    this._emitChange(dayIndex, newPeriods);
  }

  // -----------------------------------------------------------------------
  // Drag boundary (D-06)
  // -----------------------------------------------------------------------

  private _onDragHandlePointerDown(
    e: PointerEvent,
    dayIndex: number,
    segIndex: number,
  ) {
    // Prevent the browser (Android WebView) from claiming the touch stream as a
    // scroll or tap gesture. Must be called before setPointerCapture so the
    // WebView gesture recognizer does not win the touch arbitration.
    e.preventDefault();
    e.stopPropagation();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    this._dragPreviewDays = null; // clear any stale preview from previous drag

    const segments = this._toSegments(this.days[dayIndex] ?? []);
    const seg = segments[segIndex];
    if (!seg) return;

    this._drag = {
      dayIndex,
      segIndex,
      startX: e.clientX,
      initialBoundaryMinutes: seg.endMin,
    };
    this._dragTooltipMinutes = seg.endMin;
    this._dragTooltipX = e.clientX;
    this._dragTooltipY = e.clientY - this._touchTooltipOffset(e);
  }

  private _onPointerMove(e: PointerEvent) {
    if (!this._drag) return;

    const { dayIndex, segIndex } = this._drag;

    const barEl = this.shadowRoot?.querySelector(
      `.day-row:nth-child(${dayIndex + 2}) .bar-wrap`,
    ) as HTMLElement | null;
    if (!barEl) return;

    const rect = barEl.getBoundingClientRect();
    const rawMinutes = this._pixelToMinutes(e.clientX - rect.left, rect.width);
    const snapped = this._snapToMinutes(rawMinutes);

    // Update tooltip time and position — do NOT emit (D-09)
    this._dragTooltipMinutes = snapped;
    this._dragTooltipX = e.clientX;
    this._dragTooltipY = e.clientY - this._touchTooltipOffset(e);

    // --- Live drag preview ---
    // Compute the clamped boundary (same logic as _onPointerUp) and write a
    // modified copy of `days` into _dragPreviewDays so Lit re-renders the
    // segment widths immediately. No event is emitted here.
    const segments = this._toSegments(this.days[dayIndex] ?? []);
    const leftSeg = segments[segIndex];
    const rightSeg = segments[segIndex + 1];

    if (leftSeg && rightSeg) {
      const minBoundary = leftSeg.startMin + 15;
      const maxBoundary = rightSeg.endMin - 15;
      const clamped = Math.max(minBoundary, Math.min(maxBoundary, snapped));

      const previewDay = (this.days[dayIndex] ?? []).map((p) => {
        if (p.start === rightSeg.period.start) {
          return { ...p, start: this._minutesToHHMM(clamped) };
        }
        return p;
      });

      // Build a full preview days array, replacing only the affected day
      const previewDays = this.days.map((day, i) =>
        i === dayIndex ? previewDay : day,
      );
      this._dragPreviewDays = previewDays;
    }
  }

  private _onPointerUp(e: PointerEvent) {
    if (!this._drag) return;

    const { dayIndex, segIndex } = this._drag;
    const barEl = this.shadowRoot?.querySelector(
      `.day-row:nth-child(${dayIndex + 2}) .bar-wrap`,
    ) as HTMLElement | null;

    if (barEl) {
      const rect = barEl.getBoundingClientRect();
      const rawMinutes = this._pixelToMinutes(
        e.clientX - rect.left,
        rect.width,
      );
      const snapped = this._snapToMinutes(rawMinutes);

      // Apply boundary change enforcing 15-min minimum segments
      const segments = this._toSegments(this.days[dayIndex] ?? []);
      const leftSeg = segments[segIndex];
      const rightSeg = segments[segIndex + 1];

      if (leftSeg && rightSeg) {
        const minBoundary = leftSeg.startMin + 15;
        const maxBoundary = rightSeg.endMin - 15;
        const clamped = Math.max(minBoundary, Math.min(maxBoundary, snapped));

        // Rebuild: move right segment's start to clamped value
        const newPeriods = (this.days[dayIndex] ?? []).map((p) => {
          if (p.start === rightSeg.period.start) {
            return { ...p, start: this._minutesToHHMM(clamped) };
          }
          return p;
        });

        // Keep preview at the final drag position to prevent flicker while
        // the parent round-trips through WS → reloadConfig → prop update.
        // Cleared in updated() when the `days` prop actually changes content.
        const finalPreviewDays = this.days.map((day, i) =>
          i === dayIndex ? newPeriods : day,
        );
        this._drag = null;
        this._dragTooltipMinutes = null;
        this._dragPreviewDays = finalPreviewDays;
        this._justDragged = true;
        this._emitChange(dayIndex, newPeriods);
        return;
      }
    }

    this._drag = null;
    this._dragTooltipMinutes = null;
    this._dragPreviewDays = null;
    this._justDragged = true;
  }

  private _onPointerCancel(_e: PointerEvent) {
    // Android cancels the pointer stream (e.g. scroll gesture wins) instead of
    // firing pointerup. Reset drag state so the component is not left stuck.
    if (!this._drag) return;
    this._drag = null;
    this._dragTooltipMinutes = null;
    this._dragPreviewDays = null;
    // Do NOT set _justDragged — drag cancelled, no synthetic click to suppress.
  }

  // -----------------------------------------------------------------------
  // Copy / Paste
  // -----------------------------------------------------------------------

  private _onCopy(dayIndex: number) {
    this._clipboard = JSON.parse(
      JSON.stringify(this.days[dayIndex] ?? []),
    ) as Period[];
  }

  private _onPaste(dayIndex: number) {
    if (!this._clipboard) return;
    const copy = JSON.parse(JSON.stringify(this._clipboard)) as Period[];
    // Emit immediately on paste (D-07 / D-09)
    this._emitChange(dayIndex, copy);
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  protected updated(changedProperties: PropertyValues): void {
    if (changedProperties.has("days") && this._dragPreviewDays) {
      // Only clear the preview when the incoming `days` prop has genuinely
      // different content from the preview. A reference-only change (same
      // content, new array objects) must NOT clear the preview — this is
      // exactly the intermediate re-render caused by _loadStatus() completing
      // before _loadConfig() after a WS save, which would otherwise flash the
      // bar back to the pre-drag position momentarily.
      if (!this._previewMatchesDays(this._dragPreviewDays, this.days)) {
        this._dragPreviewDays = null;
      }
    }

    // Clamp popup to viewport so bottom/right buttons are always reachable.
    // Runs after each render where popup is open; the guard ensures at most
    // one adjustment cycle (second render will be in-bounds → no change).
    if (this._popup) {
      const el = this.shadowRoot?.querySelector<HTMLElement>(".popup");
      if (el) {
        const rect = el.getBoundingClientRect();
        const margin = 8;
        let { x, y } = this._popup;
        if (rect.bottom > window.innerHeight - margin) {
          y -= rect.bottom - (window.innerHeight - margin);
        }
        if (rect.right > window.innerWidth - margin) {
          x -= rect.right - (window.innerWidth - margin);
        }
        y = Math.max(margin, y);
        x = Math.max(margin, x);
        if (x !== this._popup.x || y !== this._popup.y) {
          this._popup = { ...this._popup, x, y };
        }
      }
    }
  }

  render() {
    return html`
      <div
        class="week-grid"
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
        @pointercancel=${this._onPointerCancel}
      >
        <!-- Time axis above day rows — identical structure to bottom axis -->
        ${this._renderTimeAxis()}
        ${DAY_LABELS.map((label, dayIndex) =>
          this._renderDayRow(label, dayIndex),
        )}

        <!-- Shared time axis below day rows -->
        ${this._renderTimeAxis()}
      </div>

      <!-- Drag tooltip -->
      ${this._drag !== null && this._dragTooltipMinutes !== null
        ? html`<div
            class="drag-tooltip"
            style="left:${this._dragTooltipX}px;top:${this._dragTooltipY}px"
            aria-live="polite"
          >
            ${this._minutesToHHMM(this._dragTooltipMinutes)}
          </div>`
        : ""}

      <!-- Popup overlay + popup -->
      ${this._popup
        ? html`
            <div class="popup-overlay" @click=${this._closePopup}></div>
            <div
              class="popup"
              style="left:${this._popup.x}px;top:${this._popup.y}px"
            >
              ${this._renderPopup()}
            </div>
          `
        : ""}
    `;
  }

  /**
   * Renders the shared time axis row — used for both top (above day rows)
   * and bottom (below day rows).
   *
   * Mirrors the exact 3-column layout of a day row:
   *   [label spacer 40px+8px] [bar area flex:1] [invisible action buttons]
   * so ticks align pixel-perfectly with the bar regardless of button size.
   */
  private _renderTimeAxis() {
    const ticks = [0, 3, 6, 9, 12, 15, 18, 21, 24];
    return html`
      <div class="time-axis">
        <div class="time-axis-label-spacer"></div>
        <div class="time-axis-inner">
          ${ticks.map((h) => {
            const densityClass =
              h % 12 === 0
                ? ""
                : h % 6 === 0
                  ? "axis-tick--6h"
                  : "axis-tick--3h";
            return html`<span
              class="axis-tick ${densityClass}"
              style="left:${(h / 24) * 100}%"
              >${String(h).padStart(2, "0")}:00</span
            >`;
          })}
        </div>
        <div class="time-axis-actions-ghost" aria-hidden="true">
          <ha-icon-button
            ><ha-icon icon="mdi:content-copy"></ha-icon
          ></ha-icon-button>
          <ha-icon-button
            ><ha-icon icon="mdi:content-paste"></ha-icon
          ></ha-icon-button>
        </div>
      </div>
    `;
  }

  private _renderDayRow(label: string, dayIndex: number) {
    // Use live preview during drag, fall back to committed props otherwise
    const sourceDays = this._dragPreviewDays ?? this.days;
    const periods = sourceDays[dayIndex] ?? [];
    const segments = this._toSegments(periods);
    const isEmpty = segments.length === 0;

    return html`
      <div class="day-row">
        <div class="day-label">${label}</div>

        <div
          class="bar-wrap"
          @click=${(e: MouseEvent) => {
            // Only treat as bar click if not hitting a segment
            if (
              (e.target as HTMLElement).classList.contains("bar-wrap") ||
              (e.target as HTMLElement).classList.contains("bar-row-inner")
            ) {
              this._onBarClick(e, dayIndex);
            }
          }}
        >
          ${isEmpty
            ? html`<div class="empty-hint">
                Click the bar to add your first period.
              </div>`
            : html`<div class="bar-row-inner">
                ${segments.map((seg, segIdx) =>
                  this._renderSegment(seg, dayIndex, segIdx, segments.length),
                )}
              </div>`}
        </div>

        <div class="day-actions">
          <ha-icon-button
            style="--mdc-icon-button-size:32px"
            .label=${"Copy " + label + " schedule"}
            @click=${() => this._onCopy(dayIndex)}
          >
            <ha-icon icon="mdi:content-copy"></ha-icon>
          </ha-icon-button>
          <ha-icon-button
            style="--mdc-icon-button-size:32px"
            class=${this._clipboard === null ? "paste-disabled" : ""}
            .label=${"Paste to " + label}
            .disabled=${this._clipboard === null}
            @click=${() => this._onPaste(dayIndex)}
          >
            <ha-icon icon="mdi:content-paste"></ha-icon>
          </ha-icon-button>
        </div>
      </div>
    `;
  }

  private _renderSegment(
    seg: { period: Period; startMin: number; endMin: number },
    dayIndex: number,
    segIdx: number,
    totalSegments: number,
  ) {
    const color = this._colorForPeriod(seg.period);
    const label = this._labelForPeriod(seg.period);
    const widthPct = ((seg.endMin - seg.startMin) / 1440) * 100;
    const ariaLabel =
      this.mode === "presence"
        ? seg.period.state ?? "absent"
        : seg.period.mode?.replace(/_/g, " ") ?? "frost protection";

    return html`
      <div
        class="segment"
        style="width:${widthPct}%;background:${color}"
        aria-label="${ariaLabel}"
        @click=${(e: MouseEvent) => this._onSegmentClick(e, dayIndex, segIdx)}
      >
        ${widthPct >
        2.7 /* ~40px at typical width — hide label on very narrow blocks */
          ? html`<span class="segment-label">${label}</span>`
          : ""}

        <!-- Drag handle on right border (not on last segment) -->
        ${segIdx < totalSegments - 1
          ? html`<div
              class="drag-handle"
              @pointerdown=${(e: PointerEvent) =>
                this._onDragHandlePointerDown(e, dayIndex, segIdx)}
            ></div>`
          : ""}
      </div>
    `;
  }

  private _renderPopup() {
    if (!this._popup) return html``;

    if (this._popup.kind === "split") {
      const timeStr = this._minutesToHHMM(this._popup.snappedMinutes ?? 0);
      return html`
        <div class="popup-title">Split at ${timeStr}</div>
        <div class="mode-options">
          ${this._modeOptions().map(
            (opt) => html`
              <button
                class="mode-option"
                @click=${() => this._onSplitModeSelect(opt.key)}
              >
                <span
                  class="mode-swatch"
                  style="background:${opt.color}"
                ></span>
                ${opt.label}
              </button>
            `,
          )}
        </div>
      `;
    }

    if (this._popup.kind === "edit") {
      const segments = this._toSegments(this.days[this._popup.dayIndex] ?? []);
      const seg = segments[this._popup.segIndex ?? 0];
      if (!seg) return html``;

      const start = this._minutesToHHMM(seg.startMin);
      const end = this._minutesToHHMM(seg.endMin);
      const timeRange = `${start} – ${end}`;
      const modeLabel =
        this.mode === "presence"
          ? seg.period.state ?? "absent"
          : seg.period.mode?.replace(/_/g, " ") ?? "frost protection";
      const duration = seg.endMin - seg.startMin;
      const canSplit = duration >= 30;
      const canDelete = (this.days[this._popup.dayIndex]?.length ?? 0) > 1;

      return html`
        <div class="popup-title">${timeRange} · ${modeLabel}</div>

        <div class="mode-options">
          <div
            style="font-size:11px;color:var(--secondary-text-color);margin-bottom:4px"
          >
            Change mode
          </div>
          ${this._modeOptions().map(
            (opt) => html`
              <button
                class="mode-option"
                @click=${() => this._onEditModeSelect(opt.key)}
              >
                <span
                  class="mode-swatch"
                  style="background:${opt.color}"
                ></span>
                ${opt.label}
              </button>
            `,
          )}
        </div>

        <div class="popup-actions">
          <button
            class="popup-btn"
            ?disabled=${!canSplit}
            style=${!canSplit ? "opacity:0.4;cursor:default" : ""}
            @click=${this._onSplitPeriod}
          >
            Split period
          </button>
          <button
            class="popup-btn danger"
            ?disabled=${!canDelete}
            style=${!canDelete ? "opacity:0.4;cursor:default" : ""}
            @click=${this._onDeleteSegment}
          >
            Delete period
          </button>
        </div>
      `;
    }

    return html``;
  }
}

customElements.define("climate-manager-time-bar", ClimateManagerTimeBar);

declare global {
  interface HTMLElementTagNameMap {
    "climate-manager-time-bar": ClimateManagerTimeBar;
  }
}
