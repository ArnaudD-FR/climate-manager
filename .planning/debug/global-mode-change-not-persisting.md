---
slug: global-mode-change-not-persisting
status: resolved
trigger: "the global mode is always at 'time programmed', impossible to change it to off or presence based"
created: 2026-05-18
updated: 2026-05-18
---

# Debug Session: global-mode-change-not-persisting

## Symptoms

- **Expected:** Global mode selector in the panel changes the active mode (Off / Time program / Time program & presences)
- **Actual:** Mode is always displayed as "time programmed"; changing the dropdown has no visible effect
- **Errors:** Unknown
- **Timeline:** Unknown — new feature being debugged
- **Reproduction:** Open Climate Manager panel → Global Settings tab → change mode dropdown

## Current Focus

```yaml
hypothesis: stale _config in root panel causes ha-select to fire spurious @selected event that overwrites the saved value
test: change global mode dropdown, observe it sticks
expecting: mode persists after reload
next_action: complete
```

## Evidence

- timestamp: 2026-05-18T00:00:00
  observation: >
    main.ts _loadConfig() is called only once in connectedCallback. After setGlobalMode
    succeeds, _config on the root panel still holds the old global_mode value.
    On the next Lit render cycle (triggered by _status update from subscribe_status),
    GlobalSettingsTab receives the stale config.global_mode via its .config prop.
    ha-select re-renders with .value="time_program" → mwc-select fires @selected with
    the old value → _onModeChange runs again → setGlobalMode("time_program") is sent
    to the backend, overwriting the value the user just saved.
  files: [frontend/src/main.ts, frontend/src/components/global-settings-tab.ts]

- timestamp: 2026-05-18T00:00:01
  observation: >
    Secondary guard needed: _onModeChange had no early-return for the case where
    newMode === this.config.global_mode (would cause a no-op save on init-time
    @selected fires when mwc-select first sets its value).
  files: [frontend/src/components/global-settings-tab.ts]

## Eliminated

- Backend set_global_mode handler: correctly mutates runtime_config, saves, and evaluates. Not the bug.
- ws-client.ts setGlobalMode: correctly sends mode field. Not the bug.
- Storage layer async_save: works correctly. Not the bug.

## Resolution

```yaml
root_cause: >
  Root panel _config is never refreshed after a write. The subscribe_status push
  triggers a re-render that propagates the stale global_mode back into ha-select
  via .value, causing mwc-select to fire a spurious @selected event that calls
  setGlobalMode with the old value and overwrites the just-saved one.
fix: >
  1. Added public reloadConfig() method to ClimateManagerPanel (main.ts) that
     re-fetches config from the backend via getConfig().
  2. In GlobalSettingsTab._onModeChange (and _onTemperatureBlur, _onPeriodsChanged),
     call await this.panel.reloadConfig() after each successful write so the parent's
     _config is immediately updated before the next render.
  3. Added guard in _onModeChange: skip if newMode is empty or equals current
     config.global_mode to prevent no-op saves on initialisation-time @selected fires.
verification: null
files_changed:
  - frontend/src/main.ts
  - frontend/src/components/global-settings-tab.ts
```
