---
status: resolved
slug: global-mode-change-not-saving
trigger: "the global settings does not save as expected, for example setting the global mode does not make the saved popup appearing. See last screenshot where I selected it to off but the current status is not updated"
created: 2026-05-21
updated: 2026-05-21
---

## Symptoms

- **Expected:** Selecting a different option in the "Global mode" dropdown in the Configuration card shows a "Saved" toast and the Current Status card updates to reflect the new mode.
- **Actual:** No toast appears; Current Status still shows "Mode: Time program" even though the select element displays "Off".
- **Error messages:** None reported (no browser console errors mentioned).
- **Timeline:** Observed after latest deploy — the Configuration card was recently refactored (plan 03-05, D-13).
- **Reproduction:** Open Climate Manager panel → Global Settings tab → Configuration card → change "Global mode" select to "Off" → nothing happens.

## Evidence

- timestamp: 2026-05-21
  file: frontend/src/components/global-settings-tab.ts
  observation: >
    All 5 event handler methods (_onModeChange, _onTemperatureBlur, _onResetTemperatures,
    _onPeriodsChanged, _onResetConfiguration) are declared as regular private methods
    (not arrow function class fields). They are bound in templates as @change=${this._onModeChange}
    (method reference). In Lit 3, @event=${fn} calls addEventListener(name, fn) which causes
    the browser to invoke fn with this=<DOM element>, not this=<component instance>.
    As a result, this.config / this.ws / this.panel / this.shadowRoot all resolve to
    undefined or wrong targets, causing silent failures (TypeError before try/catch in
    _onModeChange; early return via if (!root) return in _onTemperatureBlur).

## Eliminated

- WebSocket client (ws-client.ts): setGlobalMode is correctly implemented; never reached
- Backend websocket.py: set_global_mode handler is correctly implemented; never reached
- HA 2026.x ha-select: correctly avoided — native <select> is used
- patchConfig / @state() propagation in main.ts: correct; not the source of the bug

## Current Focus

- hypothesis: All 5 event handlers use unbound method references in Lit @event=${} bindings, causing `this` to be the DOM element instead of the component instance
- test: Confirmed by reading all @event=${} bindings in _renderTemperaturesCard and _renderConfigCard
- expecting: Converting handlers to arrow function class fields will fix all 5 broken handlers
- next_action: Apply fix

## Resolution

- root_cause: All event handler methods in GlobalSettingsTab are declared as regular methods but bound in Lit templates as bare method references (e.g. @change=${this._onModeChange}). In Lit 3, @event=${fn} registers fn via addEventListener, so the browser calls fn with this=<DOM element>. All handlers then fail because this.config, this.ws, this.panel are undefined on a DOM element. _onModeChange throws before the try/catch (on this.config.global_mode), producing an unhandled rejected promise. _onTemperatureBlur silently returns early (this.shadowRoot is null on an input element). The other three handlers would also fail once called.
- fix: Convert all 5 handler methods from regular methods to arrow function class fields so this is lexically captured as the component instance at class initialisation time.
- verification: After fix, changing Global mode select fires _onModeChange with correct this, ws.setGlobalMode is called, toast appears, Current Status updates via patchConfig.
- files_changed: [frontend/src/components/global-settings-tab.ts]
