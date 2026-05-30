---
phase: quick-260526-jvg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/room-card.ts
  - custom_components/climate_manager/www/panel.js
autonomous: true
requirements:
  - QUICK-260526-jvg

must_haves:
  truths:
    - "In the Rooms tab, when a room is in Custom program mode, a 'Reset to global configuration' button is visible below the inline time-bar."
    - "Clicking the button switches the room's room_mode back to 'global', collapsing the inline time-bar and restoring the global program for that room."
    - "After click, the room card reflects the new mode (Global program selected in the mode dropdown) without a manual refresh."
    - "A 'Saved' toast appears on success; a retry toast appears on failure."
    - "The button is styled consistently with the existing 'Reset to default' button in the person card (outlined primary-color button)."
  artifacts:
    - path: "frontend/src/components/room-card.ts"
      provides: "_onResetToGlobal handler + render of the button in the Custom-mode branch + .reset-btn styles"
      contains: "Reset to global configuration"
    - path: "custom_components/climate_manager/www/panel.js"
      provides: "Rebuilt Vite bundle including the new button and handler"
      contains: "Reset to global configuration"
  key_links:
    - from: "frontend/src/components/room-card.ts"
      to: "ws.setRoomConfig"
      via: "_onResetToGlobal calling setRoomConfig(roomId, { room_mode: 'global' })"
      pattern: "setRoomConfig\\(this\\.roomId, \\{ room_mode: \"global\" \\}\\)"
    - from: "frontend/src/components/room-card.ts"
      to: "panel.reloadConfig + panel.showToast"
      via: "post-save UI sync mirroring person-card._onResetSchedule"
      pattern: "panel\\.reloadConfig\\(\\)"
---

<objective>
Append a "Reset to global configuration" button under the inline time-bar shown in a room card when the room is in Custom program mode. Clicking the button reverts that room to `room_mode: "global"` (NOT a reset of the custom time program to a default schedule). This mirrors the existing reset-button pattern used in person-card.ts but with different semantics: instead of resetting schedule content, it switches the room out of Custom mode entirely so the global program applies again.

Purpose: One-click way to abandon a per-room schedule override without using the mode dropdown.
Output: Updated `room-card.ts` source + rebuilt `panel.js` bundle, both committed.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@frontend/src/components/room-card.ts
@frontend/src/components/person-card.ts
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Add reset-to-global handler, button, and styles in room-card.ts</name>
  <files>frontend/src/components/room-card.ts</files>
  <behavior>
    - When the user clicks the new button, the room transitions out of Custom mode: `ws.setRoomConfig(this.roomId, { room_mode: "global" })` is called, followed by `panel.reloadConfig()` and a "Saved" toast.
    - On error: a "Save failed — retrying..." toast is shown (matches the existing handlers in the same file).
    - The button only renders when `resolvedMode === "custom"` (same gating as the time-bar).
    - The button label is exactly: `Reset to global configuration`.
    - The room's saved custom `time_program` MUST NOT be modified by this action — only `room_mode` changes. The existing seeding logic in `_onRoomModeChange` already handles re-seeding from the global program if the user switches back to Custom later with no stored program; that path is unaffected.
  </behavior>
  <action>
    Edit `frontend/src/components/room-card.ts`:

    1. Add a new private async method `_onResetToGlobal()` directly after `_onPeriodsChanged` (around line 403). Body mirrors `person-card.ts._onResetSchedule` (lines 325–333) with these differences:
       - Call `await this.ws.setRoomConfig(this.roomId, { room_mode: "global" })` (not `setPersonConfig`, and payload is the room_mode switch, not a schedule reset).
       - On success: `await this.panel.reloadConfig(); this.panel.showToast("Saved", false);` (use "Saved" — this is a mode switch, not a content reset; the wording "Reset to defaults" used in person-card does not apply here).
       - On failure: `this.panel.showToast("Save failed — retrying...", true);` — matches the other room-card handlers in the same file.

    2. In the render method (around lines 597–607), inside the `${resolvedMode === "custom" ? html\`...\` : ""}` branch, append a button AFTER the closing `</div>` of `.time-bar-section`, still inside the same html template literal:
       `<button class="reset-btn" @click=${() => void this._onResetToGlobal()}>Reset to global configuration</button>`
       The arrow-wrapping is intentional and mirrors person-card.ts line 463 so Lit does not bind the unbound method.

    3. Add the `.reset-btn` and `.reset-btn:hover` rules to the static `styles` block of `RoomCard`. Copy them verbatim from `person-card.ts` lines 269–283 (margin-top:12px, padding:8px 16px, font-size:14px, font-family:inherit, color:var(--primary-color, #03a9f4), background:none, border:1px solid var(--primary-color, #03a9f4), border-radius:4px, cursor:pointer; hover uses var(--secondary-background-color)). Place them at the end of the existing styles block, before the closing backtick.

    Do NOT alter `_onRoomModeChange`, the mode `<select>`, or any time-program data — the button is additive.
  </action>
  <verify>
    <automated>grep -n "_onResetToGlobal" frontend/src/components/room-card.ts | grep -v '^#' | wc -l | awk '{exit ($1 >= 2)?0:1}' && grep -q "Reset to global configuration" frontend/src/components/room-card.ts && grep -q "room_mode: \"global\"" frontend/src/components/room-card.ts && grep -q "\.reset-btn" frontend/src/components/room-card.ts</automated>
  </verify>
  <done>
    `room-card.ts` contains: (a) the `_onResetToGlobal` method, (b) a `<button class="reset-btn">Reset to global configuration</button>` rendered only inside the Custom-mode branch, (c) `.reset-btn` + `.reset-btn:hover` CSS rules. No other behavior in the file changed.
  </done>
</task>

<task type="auto" tdd="false">
  <name>Task 2: Rebuild Vite bundle so the deployed panel.js picks up the change</name>
  <files>custom_components/climate_manager/www/panel.js</files>
  <action>
    Run `npm run build` from `frontend/`. The Vite build outputs the bundled panel into `custom_components/climate_manager/www/panel.js` (this is the file HA loads via `async_register_panel`). Do not hand-edit `panel.js` — it is generated. If the build fails (TS errors), fix the source in `room-card.ts` and rebuild. After a successful build, verify the bundle now contains the new button copy and handler reference.

    Command: `cd frontend && npm run build`
  </action>
  <verify>
    <automated>cd frontend && npm run build && grep -q "Reset to global configuration" ../custom_components/climate_manager/www/panel.js && grep -q "_onResetToGlobal\|resetToGlobal" ../custom_components/climate_manager/www/panel.js</automated>
  </verify>
  <done>
    `frontend` build exits 0; `custom_components/climate_manager/www/panel.js` contains the literal string "Reset to global configuration" and a minified reference to the new handler. The bundle file size is in the same order of magnitude as before the change (sanity: no runaway bundle).
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 3: Human verify in Home Assistant UI</name>
  <what-built>
    A "Reset to global configuration" button now appears under the inline custom time-bar in any room card whose mode is set to "Custom program". Clicking it switches the room back to Global program mode (custom time program is no longer applied; the dropdown selects "Global program") and shows a "Saved" toast.
  </what-built>
  <how-to-verify>
    1. Restart Home Assistant (or reload the Climate Manager integration) so the rebuilt `panel.js` is served. Hard-refresh the browser (Ctrl+Shift+R) to bypass any cached bundle.
    2. Open the Climate Manager panel and go to the "Rooms" tab.
    3. Expand any room and set its mode to "Custom program". The inline time-bar should render. Just below it, the new "Reset to global configuration" button should be visible and styled like the person-card "Reset to default" button (outlined, primary color).
    4. Click the button. Expected: a "Saved" toast appears, the mode dropdown switches to "Global program", and the inline time-bar disappears (because the Custom branch no longer renders).
    5. Re-open the same room: it should still be in Global mode after a config reload (no flicker back to Custom).
    6. Switch the room back to "Custom program". Expected: the previous custom time-program is preserved (because Task 1 only touched `room_mode`, never the stored `time_program`). The button should reappear.
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues</resume-signal>
</task>

</tasks>

<verification>
- Source change isolated to `frontend/src/components/room-card.ts`.
- Built bundle `custom_components/climate_manager/www/panel.js` regenerated by Vite, contains the new copy.
- Button only renders in Custom mode; click reverts `room_mode` to `"global"` without touching `time_program`.
- Human verifier confirms behavior in a live HA instance.
</verification>

<success_criteria>
- Room card in Custom mode shows the new button below the time-bar.
- Clicking the button calls `setRoomConfig(roomId, { room_mode: "global" })`, reloads config, shows "Saved" toast.
- Stored custom `time_program` is preserved across the switch.
- Bundle rebuilt and committed alongside source.
</success_criteria>

<output>
Create `.planning/quick/260526-jvg-for-the-room-custom-program-in-rooms-tab/260526-jvg-SUMMARY.md` when done.
</output>
