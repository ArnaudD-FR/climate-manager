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
hypothesis: resolved
test: n/a
expecting: n/a
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
    Previous fix added reloadConfig() + guard `if (!newMode || newMode === this.config.global_mode)`.
    Fix was compiled into panel.js (confirmed by timestamp). But symptom persisted.
  files: [frontend/src/components/global-settings-tab.ts]

- timestamp: 2026-05-18T00:00:02
  observation: >
    Re-investigation of all source files. Backend confirmed correct (set_global_mode
    mutates runtime_config in-place, saves, evaluates). Storage confirmed correct.
    Coordinator does NOT reset global_mode. Mode string constants match exactly.

    The !newMode guard in the previous fix is the remaining bug.
    ha-select's @selected event may fire with e.target.value === "" (empty string)
    before mwc-select settles the new value onto ha-select's .value property.
    The !newMode check returns early on every legitimate user click, preventing
    setGlobalMode from ever being called.

    Switching @selected to @change fixes this: the @change event fires after
    selection is committed and ha-select.value is stable. The !newMode guard is
    also removed — only the dedup guard (newMode === this.config.global_mode)
    is retained to prevent redundant saves.
  files: [frontend/src/components/global-settings-tab.ts]

## Eliminated

- Backend set_global_mode handler: confirmed correct — mutates runtime_config["global_mode"],
  saves to store, re-evaluates. The mutation is in-memory and persisted.
- ws-client.ts setGlobalMode: confirmed correct — sends {type: "climate_manager/set_global_mode", mode}.
- Storage layer async_save/async_load: confirmed correct — sparse merge preserves global_mode.
- Coordinator: does NOT reset global_mode — reads runtime_config["global_mode"] by reference.
- Mode string constants: frontend "off", "time_program", "time_program_presences" match backend exactly.
- Build artifact: fix was compiled into panel.js correctly (timestamps confirmed).

## Resolution

```yaml
root_cause: >
  Two compounding bugs:
  1. stale _config re-render loop: subscribeStatus push triggered re-render with
     stale global_mode before reloadConfig() completed, causing @selected to fire
     with old value and overwrite the just-saved mode. (Original root cause — correct.)
  2. Overly aggressive !newMode guard added in the first fix: ha-select's @selected
     event fires with e.target.value === "" before mwc-select settles .value on the
     host element. The !newMode check catches this but also swallows every real user
     click, so setGlobalMode is never called.
fix: >
  1. Changed @selected to @change on ha-select in GlobalSettingsTab template.
     @change fires after selection is committed with stable .value — no spurious fires.
  2. Removed the !newMode guard. Retained only the dedup guard
     (newMode === this.config.global_mode) to prevent redundant saves.
  3. Kept reloadConfig() call after successful write (still needed to keep _config
     in sync before next render cycle, preventing the overwrite loop from bug 1).
  4. Rebuilt panel.js (81.03 kB, built in 259ms).
verification: null
files_changed:
  - frontend/src/components/global-settings-tab.ts
  - custom_components/climate_manager/www/panel.js
```
