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
 * Above all 7 rows: a time axis showing hour markers (00:00 / 06:00 / 12:00 / 18:00 / 24:00).
 * Below all 7 rows: a shared time axis (same structure, same labels).
 *
 * Interactions (D-04…D-09):
 *   click empty bar   → mode popup "Split at HH:MM" → insert new segment
 *   click block       → popup: time range + Change mode + Split period + Delete (merges into left)
 *   drag boundary     → tooltip shows HH:MM (snapped), save fires on pointerup only
 *   Copy              → store day's periods in panel-local _clipboard
 *   Paste             → overwrite target day, emit periods-changed immediately
 *
 * Emits CustomEvent "periods-changed" { dayIndex, periods } on interaction END only.
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
  /** Set true by _onPointerUp; cleared by _onBarClick/_onSegmentClick to swallow the synthetic post-drag click. */
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
    }

    .day-row {
      display: flex;
      align-items: center;
      height: 44px;
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
      right: -3px;
      top: 0;
      width: 6px;
      height: 100%;
      cursor: ew-resize;
      z-index: 2;
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
      margin-left: 4px;
    }

    ha-icon-button.paste-disabled {
      opacity: 0.4;
    }

    /* ---- Shared time axis (above and below day rows) ---------------------- */
    .time-axis {
      display: flex;
      align-items: center;
      margin-top: 2px;
      padding-left: 48px; /* 40px label + 8px padding */
      padding-right: 80px; /* approximate button width */
    }

    .time-axis-inner {
      flex: 1;
      display: flex;
      justify-content: space-between;
    }

    .axis-tick {
      font-size: 11px;
      color: var(--secondary-text-color, #757575);
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
      box-shadow: var(--ha-card-box-shadow, 0 4px 16px rgba(0,0,0,0.25));
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

  private _minutesToHHMM(minutes: number): string {
    const clamped = Math.max(0, Math.min(1440, minutes));
    const h = Math.floor(clamped / 60);
    const m = clamped % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
  }

  private _colorForPeriod(period: Period): string {
    const key = this.mode === "presence"
      ? (period.state ?? "absent")
      : (period.mode ?? "frost_protection");
    if (this.mode === "presence") {
      return PRESENCE_COLORS[key] ?? PRESENCE_COLORS["absent"];
    }
    return PERIOD_COLORS[key] ?? PERIOD_COLORS["frost_protection"];
  }

  private _labelForPeriod(period: Period): string {
    const key = this.mode === "presence"
      ? (period.state ?? "absent")
      : (period.mode ?? "frost_protection");
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

    const sorted = [...periods].sort((a, b) =>
      a.start.localeCompare(b.start),
    );

    // Ensure first segment starts at 00:00
    const first = sorted[0];
    const firstMin = this._timeToMinutes(first.start);
    const working = firstMin > 0
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

  // -----------------------------------------------------------------------
  // Popup helpers
  // -----------------------------------------------------------------------

  private _modeOptions(): Array<{ key: string; label: string; color: string }> {
    if (this.mode === "presence") {
      return [
        { key: "present", label: "Present", color: PRESENCE_COLORS["present"] },
        { key: "absent", label: "Absent", color: PRESENCE_COLORS["absent"] },
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

    const barEl = (e.currentTarget as HTMLElement);
    const rect = barEl.getBoundingClientRect();
    const rawMinutes = this._pixelToMinutes(e.clientX - rect.left, rect.width);
    const snapped = this._snapToMinutes(rawMinutes);

    // Check if click is on an existing segment (handled by _onSegmentClick)
    // This handler fires on the bar wrap background, so it's a "new" area click.
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
    // The left neighbor (or implicit 00:00 fill) expands to cover the gap (D-05).
    const newPeriods = (this.days[dayIndex] ?? []).filter(
      (p) => p.start !== seg.period.start,
    );

    this._closePopup();
    this._emitChange(dayIndex, newPeriods);
  }

  /**
   * Split the clicked period at its midpoint (snapped to 15 min).
   * The first half keeps the original type; the second half gets the next
   * type in the cycle:
   *   schedule: frost_protection → reduced → normal → comfort → frost_protection
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
    const currentType = this.mode === "presence"
      ? (seg.period.state ?? "absent")
      : (seg.period.mode ?? "frost_protection");
    const currentIdx = cycle.indexOf(currentType);
    const nextType = cycle[(currentIdx + 1) % cycle.length];

    // Build the two replacement periods
    const firstHalf: Period = this.mode === "presence"
      ? { start: seg.period.start, state: currentType }
      : { start: seg.period.start, mode: currentType };
    const secondHalf: Period = this.mode === "presence"
      ? { start: this._minutesToHHMM(snappedMid), state: nextType }
      : { start: this._minutesToHHMM(snappedMid), mode: nextType };

    // Replace the original period in the source array with the two halves.
    // The original period is identified by its start time.
    // For a synthesised 00:00 filler (not present in source), we insert both halves.
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
    this._dragTooltipY = e.clientY;
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
    this._dragTooltipY = e.clientY;

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
        const clamped = Math.max(
          minBoundary,
          Math.min(maxBoundary, snapped),
        );

        // Rebuild: move right segment's start to clamped value
        const newPeriods = (this.days[dayIndex] ?? []).map((p) => {
          if (p.start === rightSeg.period.start) {
            return { ...p, start: this._minutesToHHMM(clamped) };
          }
          return p;
        });

        // Keep preview at the final drag position to prevent flicker while
        // the parent round-trips through WS → reloadConfig → prop update.
        // Cleared in updated() when the `days` prop actually changes.
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
      this._dragPreviewDays = null;
    }
  }

  render() {
    return html`
      <div
        class="week-grid"
        @pointermove=${this._onPointerMove}
        @pointerup=${this._onPointerUp}
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
            <div
              class="popup-overlay"
              @click=${this._closePopup}
            ></div>
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
   * and bottom (below day rows). Identical structure and CSS class so both
   * rulers are pixel-perfect matches of each other.
   *
   * Layout: 48px left pad (40px label + 8px gap) + flex bar area +
   * 80px right pad (button column) — mirrors the day row geometry exactly.
   */
  private _renderTimeAxis() {
    return html`
      <div class="time-axis">
        <div class="time-axis-inner">
          ${["00:00", "06:00", "12:00", "18:00", "24:00"].map(
            (t) => html`<span class="axis-tick">${t}</span>`,
          )}
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
            if ((e.target as HTMLElement).classList.contains("bar-wrap") ||
                (e.target as HTMLElement).classList.contains("bar-row-inner")) {
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
            .label=${"Copy " + label + " schedule"}
            @click=${() => this._onCopy(dayIndex)}
          >
            <ha-icon icon="mdi:content-copy"></ha-icon>
          </ha-icon-button>
          <ha-icon-button
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
        ? (seg.period.state ?? "absent")
        : (seg.period.mode?.replace(/_/g, " ") ?? "frost protection");

    return html`
      <div
        class="segment"
        style="width:${widthPct}%;background:${color}"
        aria-label="${ariaLabel}"
        @click=${(e: MouseEvent) => this._onSegmentClick(e, dayIndex, segIdx)}
      >
        ${widthPct > 2.7 /* ~40px at typical width — hide label on very narrow blocks */
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
      const segments = this._toSegments(
        this.days[this._popup.dayIndex] ?? [],
      );
      const seg = segments[this._popup.segIndex ?? 0];
      if (!seg) return html``;

      const timeRange = `${this._minutesToHHMM(seg.startMin)} – ${this._minutesToHHMM(seg.endMin)}`;
      const modeLabel =
        this.mode === "presence"
          ? (seg.period.state ?? "absent")
          : (seg.period.mode?.replace(/_/g, " ") ?? "frost protection");
      const duration = seg.endMin - seg.startMin;
      const canSplit = duration >= 30;

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
