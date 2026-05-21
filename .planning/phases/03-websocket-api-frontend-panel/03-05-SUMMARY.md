---
phase: 03-websocket-api-frontend-panel
plan: 05
subsystem: frontend
tags: [phase-03, frontend, ui, search-picker, temperatures-card, d-13, d-19]
dependency_graph:
  requires: []
  provides:
    - SearchPicker component (search-picker.ts) — shared add-picker for plans 06 and 07
    - Restructured Global Settings tab with three cards
  affects:
    - frontend/src/components/global-settings-tab.ts
    - frontend/src/components/search-picker.ts
    - custom_components/climate_manager/www/panel.js
tech_stack:
  added: []
  patterns:
    - Native <input type="number"> with label+suffix instead of ha-textfield (HA 2026.x compatible)
    - Floating popup picker with document-level click-outside listener
    - Lit @state() for popup open/close, _query filter
key_files:
  created:
    - frontend/src/components/search-picker.ts
  modified:
    - frontend/src/components/global-settings-tab.ts
    - custom_components/climate_manager/www/panel.js
    - frontend/src/components/room-card.ts
decisions:
  - "SearchPicker uses native HTML elements exclusively (input, ul, li, button) — HA 2026.x broken components (ha-textfield, ha-select) avoided"
  - "Temperatures card card-header text is exactly 'Temperatures' per D-13 spec"
  - "Reset to default button added to Configuration card (resets to frost_protection:7, reduced:18, normal:20, comfort:22)"
  - "search-picker trigger button matches .chip-add pill style from room-card.ts for visual consistency"
  - "document-level click listener registered only when popup is open, cleaned up in disconnectedCallback"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-21"
  tasks_completed: 2
  files_changed: 4
---

# Phase 3 Plan 05: UI Building Blocks (search-picker + Temperatures card) Summary

**One-liner:** Shared search-picker Lit component with native input+floating list popup, plus Global Settings tab restructured into three ha-cards (Current Status / Temperatures / Configuration) with ha-textfield replaced by native inputs.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create shared search-picker.ts Lit component | ca844b2 | frontend/src/components/search-picker.ts, frontend/src/components/room-card.ts |
| 2 | Restructure Global Settings tab into three cards | 57b1c2a | frontend/src/components/global-settings-tab.ts, custom_components/climate_manager/www/panel.js |

## What Was Built

### Task 1: SearchPicker component (`frontend/src/components/search-picker.ts`)

A generic Lit component that provides a floating search popup for selecting items from a filtered list. Exported as `SearchPicker` class and registered as `<search-picker>` custom element.

**Public API:**
- `@property items: Array<{id, label, secondary?, icon?}>` — pre-filtered list; consumer excludes already-assigned items
- `@property placeholder: string` — input placeholder text (default: "Search…")
- `@property triggerLabel: string` — trigger button text (default: "Add")
- `@property triggerIcon: string` — MDI icon for trigger (default: "mdi:plus")
- Fires `CustomEvent("picked", {detail: {id}, bubbles: true, composed: true})` on selection

**Behavior:**
- Trigger button matches `.chip-add` pill style (rounded, border, primary-color)
- Popup appears below trigger (CSS `position: absolute; top: 100%; left: 0`)
- Search filters case-insensitively on `label` OR `secondary` (substring)
- Closes on Escape key, selection, or click outside (document-level listener)
- No HA 2026.x broken components (no ha-textfield, ha-select, ha-tabs, ha-list-item)

### Task 2: Global Settings tab restructure (`frontend/src/components/global-settings-tab.ts`)

Refactored to render THREE ha-cards in order: Current Status → Temperatures → Configuration.

**Temperatures card (new):**
- Card header text: exactly `"Temperatures"`
- Contains all 4 period temperature inputs with native `<input type="number">` + label + `°C` suffix
- IDs: `temp-frost_protection`, `temp-reduced`, `temp-normal`, `temp-comfort`
- Saves via existing `_onTemperatureBlur` → `ws.setPeriodTemperatures`
- Displayed in 2-column grid layout

**Configuration card (trimmed):**
- Retains: global mode `<select>`, global time-bar editor, "Reset to default" button
- Removed: temperature inputs, "Default temperatures" section divider
- Reset button calls new `_onResetToDefault()` → `ws.setPeriodTemperatures({frost_protection:7, reduced:18, normal:20, comfort:22})`

**ha-textfield replacement:**
- All 4 `<ha-textfield>` elements replaced with native `<input type="number">` + surrounding label and suffix span
- CSS added: `.temp-field`, `.temp-label`, `.temp-input-row`, `.temp-input`, `.temp-suffix`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing TypeScript null vs undefined type error in room-card.ts**
- **Found during:** Task 1 TypeScript check
- **Issue:** `this.config.time_program` is typed `DailyProgram | null | undefined` but `programToDays()` only accepts `DailyProgram | undefined`. Error at line 542.
- **Fix:** Changed `programToDays(this.config.time_program)` to `programToDays(this.config.time_program ?? undefined)` in room-card.ts.
- **Files modified:** frontend/src/components/room-card.ts
- **Commit:** ca844b2 (bundled with Task 1)

**2. [Rule 2 - Missing functionality] Reset to default button not in existing codebase**
- **Found during:** Task 2 — plan specified "The 'Reset to default' button (_onResetToDefault) MUST continue to reset..." implying it existed, but it was absent from the current code
- **Fix:** Added `_onResetToDefault()` method and "Reset to default" button to the Configuration card as specified in D-13
- **Files modified:** frontend/src/components/global-settings-tab.ts
- **Commit:** 57b1c2a

**3. [Rule 1 - HA 2026.x fix] ha-textfield replaced in global-settings-tab.ts**
- **Found during:** Task 2 — existing code used `<ha-textfield>` which renders nothing in HA 2026.x
- **Fix:** Replaced all 4 `<ha-textfield>` elements with native `<input type="number">` + label + `°C` suffix span
- **Files modified:** frontend/src/components/global-settings-tab.ts
- **Commit:** 57b1c2a

**4. [Rule 3 - Blocking] node_modules not installed in worktree frontend**
- **Found during:** Task 1 TypeScript verification
- **Fix:** Ran `npm install` in the worktree's frontend directory to install local devDependencies (TypeScript, Vite)
- **Impact:** Build artifacts (panel.js) are generated in the worktree's www/ directory

## Known Stubs

None. All temperature inputs read from `this.config.period_temperatures` (live backend data). SearchPicker is generic and renders consumer-supplied items with no hardcoded content.

## Threat Flags

No new threat surface found beyond what is in the plan's threat model.

| Threat | Mitigation Applied |
|--------|-------------------|
| T-03-05-01: XSS via item.label/secondary | Lit html template auto-escapes interpolated values in search-picker items |
| T-03-05-02: Presence state exposure via secondary | Accepted — data already visible in HA frontend |
| T-03-05-03: O(n) filter on keystroke | Accepted — bounded to ~dozens of items |

## Self-Check: PASSED

- [x] `frontend/src/components/search-picker.ts` exists
- [x] `frontend/src/components/global-settings-tab.ts` contains `_renderTemperaturesCard`
- [x] `custom_components/climate_manager/www/panel.js` exists and contains "Temperatures"
- [x] Commit ca844b2 exists (Task 1)
- [x] Commit 57b1c2a exists (Task 2)
- [x] TypeScript passes (0 errors)
- [x] Vite build passes (97.75 kB output)
