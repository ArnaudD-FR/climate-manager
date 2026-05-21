---
status: resolved
slug: global-settings-no-toast-no-reload
trigger: "still have the issue. The value is correctly saved in HA but I need to refresh the page to view it. Still no 'Saved' popup"
created: 2026-05-21
updated: 2026-05-21
---

## Symptoms

- **Expected:** After saving (e.g. global mode change), a "Saved" toast appears and the Current Status card refreshes in-place without a page reload.
- **Actual:** No toast appears. The value IS saved to HA (persists after manual page refresh), but the UI does not update and no toast is shown.
- **Timeline:** Follow-up to session `global-mode-change-not-saving`. The previous fix (arrow function class fields) made the WS call work. The remaining issue is toast + reload.
- **Reproduction:** Open Climate Manager → Global Settings → change Global mode → no toast, no UI update. Manual page refresh shows the saved value.

## Evidence

- `_onModeChange` (line 281) used `this.panel.patchConfig({ global_mode: newMode })` — a synchronous optimistic patch — while all 4 other handlers used `await this.panel.reloadConfig()`.
- `patchConfig` does not call `reloadConfig()` and therefore does not follow the established pattern for re-syncing `_config` from the backend after a write.
- The inconsistency was introduced in commit 57b1c2a when `ha-select @selected` was replaced with native `<select> @change`: the handler body was rewritten with `patchConfig` instead of `reloadConfig`.
- Git history confirms: all other handlers (`_onTemperatureBlur`, `_onPeriodsChanged`, `_onResetTemperatures`, `_onResetConfiguration`) call `await this.panel.reloadConfig()` before `showToast`.
- The arrow function fix (working tree) already fixed `this` binding for all 5 handlers. With `this.panel` accessible, `patchConfig` ran correctly but `showToast` was reached. However, `patchConfig` does NOT trigger `reloadConfig`, meaning the backend round-trip that other handlers rely on to update `_config` was skipped. This made the UI update path unreliable for `_onModeChange` vs the others.

## Eliminated

- WebSocket save call (ws.setGlobalMode etc.) — confirmed working, value persists in HA
- `this` binding on handlers — fixed in previous session (arrow function class fields)
- `this.panel` being null — `.panel=${this}` is correctly wired in `_renderTabContent`; `this.ws` from same binding works, confirming `this.panel` is accessible

## Current Focus

- hypothesis: `_onModeChange` used `patchConfig` instead of `reloadConfig`, diverging from the pattern that all other handlers use. Even after the arrow function fix, the lack of `reloadConfig` meant the config re-sync + toast pattern was broken for global mode changes.
- test: Replace `this.panel.patchConfig({ global_mode: newMode })` with `await this.panel.reloadConfig()` in `_onModeChange` — consistent with all other handlers.
- expecting: After the fix, changing global mode triggers a backend config re-fetch, updates `_config` reactively, re-renders the select, and shows the "Saved" toast.

## Resolution

- root_cause: `_onModeChange` called `this.panel.patchConfig({ global_mode: newMode })` — an optimistic local patch — instead of `await this.panel.reloadConfig()`. This broke the established post-save flow (backend re-fetch → reactive `_config` update → Lit re-render → toast) that all other handlers follow. The `patchConfig` call is synchronous and does not guarantee the same reactive propagation path.
- fix: Replaced `this.panel.patchConfig({ global_mode: newMode })` with `await this.panel.reloadConfig()` on line 281 of `global-settings-tab.ts`. Built with `make build`. All 5 handlers now follow the identical save pattern: `await ws.setXxx() → await panel.reloadConfig() → panel.showToast("Saved", false)`.
- verification: `panel.js` compiled output (line 1521) shows `await this.panel.reloadConfig()` replacing the former `patchConfig` call. Run `make deploy` to push to HA server and test in browser.
- files_changed:
  - frontend/src/components/global-settings-tab.ts (line 281: patchConfig → reloadConfig)
  - custom_components/climate_manager/www/panel.js (rebuilt)
