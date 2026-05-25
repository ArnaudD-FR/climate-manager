---
phase: quick-260525-ldv
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/types.ts
  - frontend/src/components/time-bar.ts
autonomous: true
requirements:
  - QUICK-260525-LDV
must_haves:
  truths:
    - "Normal-mode segments in time-bar render as orange (warm shade), comfort-mode segments render as red"
    - "Popup mode swatches and segment colors stay consistent (single source of truth in PERIOD_COLORS)"
    - "Copy and paste icon buttons between day-row bars sit visually adjacent — no large gap"
    - "Time axis hour labels (00:00, 06:00, 12:00, 18:00, 24:00) are visually centered on their corresponding time positions along the bar, not left-aligned at each slot"
    - "Vite production build succeeds without errors after all three changes"
  artifacts:
    - path: "frontend/src/types.ts"
      provides: "PERIOD_COLORS map with normal=orange, comfort=red"
      contains: "PERIOD_COLORS"
    - path: "frontend/src/components/time-bar.ts"
      provides: "Tightened .day-actions spacing and centered .time-axis tick labels"
      contains: ".day-actions"
  key_links:
    - from: "frontend/src/components/time-bar.ts"
      to: "frontend/src/types.ts"
      via: "import { PERIOD_COLORS }"
      pattern: "PERIOD_COLORS"
---

<objective>
Three frontend UI polish tweaks to the 7-day time-bar editor:
1. Recolor schedule period modes: normal -> orange, comfort -> red.
2. Tighten horizontal spacing between the Copy/Paste icon buttons inside `.day-actions`.
3. Center-align the hour labels on the time axis (top and bottom) so each label visually sits over its tick position instead of being left-anchored within an equal-spaced slot.

Purpose: Improve scannability of the schedule editor — warmer modes should read warmer (semantic color cue), and the axis/buttons should look more compact and aligned.

Output: Updated `frontend/src/types.ts` and `frontend/src/components/time-bar.ts`. Production Vite build passes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/src/types.ts
@frontend/src/components/time-bar.ts

<interfaces>
<!-- Relevant code excerpts already in context. Key reference points: -->

From frontend/src/types.ts (lines 96-101) — PERIOD_COLORS to edit:
- `frost_protection: "#1565C0"` (dark blue — keep)
- `reduced: "#0277BD"` (medium blue — keep)
- `normal: "#2E7D32"` (green — CHANGE to orange)
- `comfort: "#E65100"` (dark orange — CHANGE to red)

From frontend/src/components/time-bar.ts:
- `.day-actions` rule (lines 201-206): currently `display: flex; align-items: center; flex-shrink: 0; margin-left: 4px;` — no gap defined; default ha-icon-button size (48px touch target) creates the visible spread.
- `.time-axis` (lines 213-219) and `.time-axis-inner` (lines 221-226): inner uses `display: flex; justify-content: space-between;` with 5 `.axis-tick` spans — flex space-between left-anchors the first tick, right-anchors the last, etc., producing visually left-anchored labels relative to their actual time positions.
- `_renderTimeAxis()` (lines 838-848): renders 5 ticks ["00:00", "06:00", "12:00", "18:00", "24:00"] in `.time-axis-inner > .axis-tick` spans.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Recolor PERIOD_COLORS — normal=orange, comfort=red</name>
  <files>frontend/src/types.ts</files>
  <action>
    Edit `PERIOD_COLORS` in `frontend/src/types.ts` (lines 96-101). Change two entries only:
    - `normal: "#2E7D32"` -> `normal: "#F57C00"` (Material Orange 700 — warm but distinct from comfort red, white text remains AA-readable)
    - `comfort: "#E65100"` -> `comfort: "#C62828"` (Material Red 800 — clearly red, white text remains AA-readable)
    Leave `frost_protection` and `reduced` untouched. Do not edit `PRESENCE_COLORS`, `PERIOD_LABELS`, or `PERIOD_DISPLAY_NAMES`. Note: these colors are referenced via the `PERIOD_COLORS` map only — `time-bar.ts` uses `_colorForPeriod` and `_modeOptions` which both read from this map, so the popup swatches and bar segments stay consistent automatically.
  </action>
  <verify>
    <automated>grep -E 'normal:|comfort:' frontend/src/types.ts | grep -v '^#' | grep -E '#F57C00|#C62828'</automated>
  </verify>
  <done>PERIOD_COLORS.normal === "#F57C00" and PERIOD_COLORS.comfort === "#C62828" in frontend/src/types.ts; other entries unchanged.</done>
</task>

<task type="auto">
  <name>Task 2: Tighten .day-actions spacing and center time-axis labels</name>
  <files>frontend/src/components/time-bar.ts</files>
  <action>
    Two CSS-only edits inside the `static styles = css\`...\`` block of `frontend/src/components/time-bar.ts`. Do NOT touch any rendering logic or TypeScript.

    Edit A — tighten Copy/Paste button spacing:
    Update the `.day-actions` rule (currently lines ~201-206). Keep `display: flex; align-items: center; flex-shrink: 0; margin-left: 4px;` and ADD:
      `gap: 0;`
      `--mdc-icon-button-size: 32px;`
    Rationale: the visible spread comes from the default 48px MDC icon-button touch target, not from a flex `gap`. Lowering the touch size to 32px collapses the buttons together while keeping them clickable. The explicit `gap: 0` is defensive (in case ha-icon-button's internal styles assume an inherited gap).

    Edit B — center the time-axis hour labels on their tick positions:
    Replace the `.time-axis-inner` rule (currently lines ~221-226):
        ```
        .time-axis-inner {
          flex: 1;
          display: flex;
          justify-content: space-between;
        }
        ```
    with a positioned variant that lets each tick sit centered on its time position:
        - Make `.time-axis-inner` `position: relative; flex: 1; height: 1em;` (no flex layout — children are absolutely positioned).
        - Update the `.axis-tick` rule so each tick is absolutely positioned with `transform: translateX(-50%)`, then set per-index `left` values via nth-child: 0%/25%/50%/75%/100% for the five ticks (00:00, 06:00, 12:00, 18:00, 24:00). The first tick (left:0) and last tick (left:100%) will get clipped at the edges — that is desired so the centers align with the bar's 00:00 and 24:00 endpoints (matching the bar geometry exactly, which is what "center-aligned on the time axis" means here).
        - Keep existing `.axis-tick` font-size/color rules; only add the positioning.
    Concretely add rules like:
      `.time-axis-inner > .axis-tick { position: absolute; transform: translateX(-50%); }`
      `.time-axis-inner > .axis-tick:nth-child(1) { left: 0%; }`
      `.time-axis-inner > .axis-tick:nth-child(2) { left: 25%; }`
      `.time-axis-inner > .axis-tick:nth-child(3) { left: 50%; }`
      `.time-axis-inner > .axis-tick:nth-child(4) { left: 75%; }`
      `.time-axis-inner > .axis-tick:nth-child(5) { left: 100%; }`

    Do NOT modify `_renderTimeAxis()` — same DOM structure, only CSS changes.
  </action>
  <verify>
    <automated>cd frontend && npm run build 2>&1 | tail -20</automated>
  </verify>
  <done>
    Vite build succeeds with no errors. `.day-actions` contains `gap: 0` and `--mdc-icon-button-size: 32px`. `.time-axis-inner` no longer uses `justify-content: space-between` and `.axis-tick` is absolutely positioned with nth-child left percentages for 5 ticks.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>
    Three UI polish changes applied to the time-bar editor:
    1. Normal mode now renders orange (#F57C00); comfort renders red (#C62828) — verified in popup swatches and in the bar segments themselves.
    2. Copy/paste icon buttons sit close together (32px touch targets, no extra gap).
    3. Hour labels (00:00 / 06:00 / 12:00 / 18:00 / 24:00) are centered on their time positions along the bar (first label left-edge of bar, last label right-edge of bar, middle three centered above their tick positions).
  </what-built>
  <how-to-verify>
    1. Reload the Climate Manager panel in Home Assistant (hard refresh to bust the panel JS cache).
    2. Open the Schedule (time program) tab and look at any day with normal/comfort segments — confirm normal blocks are orange, comfort blocks are red, frost/reduced are still blue.
    3. Click any segment to open the edit popup — confirm the mode swatches match the bar colors.
    4. Look at the row of Copy + Paste buttons to the right of each day's bar — confirm they sit visually adjacent with minimal gap (no longer feels "spaced out").
    5. Look at the top and bottom time axis rows — confirm each hour label (00:00, 06:00, 12:00, 18:00, 24:00) is visually centered above the corresponding point in the bar, with the bar's 00:00 edge under the center of "00:00" and the bar's 24:00 edge under the center of "24:00".
  </how-to-verify>
  <resume-signal>Type "approved" or describe what looks off.</resume-signal>
</task>

</tasks>

<verification>
- Vite build passes (`npm run build` inside `frontend/`).
- PERIOD_COLORS.normal and .comfort updated; other entries unchanged.
- `.day-actions` has tightened spacing; `.time-axis-inner` uses absolute positioning with centered ticks.
- No TypeScript or behavioral logic changed — pure CSS + color constants.
- Human checkpoint confirms visual outcome on a running HA instance.
</verification>

<success_criteria>
- All three changes visible in the running panel and approved at the human-verify checkpoint.
- `frontend && npm run build` completes without errors.
- No regressions in time-bar interactions (clicking, dragging, copy/paste still work — covered transitively by build + visual check; no logic was touched).
</success_criteria>

<output>
Create `.planning/quick/260525-ldv-time-bar-ui-polish-normal-orange-comfort/260525-ldv-SUMMARY.md` when done.
</output>
