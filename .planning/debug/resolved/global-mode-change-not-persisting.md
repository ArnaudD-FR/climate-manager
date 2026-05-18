---
slug: global-mode-change-not-persisting
status: verifying
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
hypothesis: >
  ha-select itself may not be working correctly with Lit's controlled binding or
  the initial value timing. New diagnostic: strip ALL backend interaction from
  _onModeChange (just update @state() _localMode + console.log). Use fully
  controlled ha-select (.value=${_localMode} binding). Show DEBUG row visually.
  If dropdown closes and DEBUG row updates → ha-select works, problem is backend
  interaction. If not → problem is ha-select/Lit lifecycle.
test: >
  1. Does "DEBUG selected:" row show current mode label after load?
  2. Click a different option — does dropdown close?
  3. Does "DEBUG selected:" row update to the new value?
  4. Check console for "[CM DEBUG] _onModeChange fired" messages.
expecting: pass
next_action: await user verification
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

- timestamp: 2026-05-18T00:00:03
  observation: >
    Second fix (@change + no !newMode guard) still did not work: dropdown stopped
    closing. New symptom confirms reloadConfig() is the remaining bug.
    Timeline: @change fires → setGlobalMode() resolves in ~5ms → reloadConfig()
    resolves in ~5ms → Lit re-render → ha-select.value setter called at ~T+10ms.
    Dropdown close animation is ~150-300ms so re-render happens mid-close.
    mwc-select receives .value setter mid-close → calls select() internally →
    prevents close or re-opens dropdown.
    Fix: introduce _modeValue (@state) updated immediately on user click BEFORE
    any await. Subsequent re-renders from reloadConfig() call .value with the same
    value already selected → mwc-select detects no change → skips select() → 
    dropdown closes normally. _modeSavePending flag prevents stale subscribe_status
    push from overwriting _modeValue during the save window.
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
  NOTE: fix 2 introduced new bug — dropdown not closing (see T+00:00:03).

fix_3: >
  Root cause: reloadConfig() resolves fast (~10ms) and triggers Lit re-render that
  calls ha-select.value setter while mwc-select close animation (~150-300ms) is
  still running. mwc-select mid-close + .value setter = menu stays open.
  1. Added @state() _modeValue = "" — local reactive state for ha-select binding.
  2. Added _modeSavePending = false flag to block stale config syncs during save.
  3. override willUpdate: syncs _modeValue from config.global_mode only when
     !_modeSavePending (prevents subscribe_status stale push from overwriting).
  4. _onModeChange: sets _modeValue = newMode IMMEDIATELY (before any await),
     sets _modeSavePending = true. Lit re-render from this update calls
     .value = newMode on ha-select — mwc-select already has this value selected →
     detects no change → no re-select → dropdown closes normally.
  5. reloadConfig() still called after save. But now _modeValue already equals the
     saved value, so subsequent re-render is idempotent on ha-select (.value is same).
  6. finally: _modeSavePending = false. On error: rolls back _modeValue to config value.
  7. Rebuilt panel.js (81.39 kB, built in 196ms).
verification: awaiting user confirmation
files_changed:
  - frontend/src/components/global-settings-tab.ts
  - custom_components/climate_manager/www/panel.js
```
