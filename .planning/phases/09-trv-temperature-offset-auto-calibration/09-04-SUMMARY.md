---
phase: 09-trv-temperature-offset-auto-calibration
plan: "04"
subsystem: frontend
tags: [calibration, frontend, ui, toggle, global-settings]
dependency_graph:
  requires: ["09-03"]
  provides: ["calibration-toggle-ui"]
  affects: ["global-settings-tab", "ws-client", "types"]
tech_stack:
  added: []
  patterns:
    - "Arrow function class field event handler for Lit change events"
    - "ha-switch with .checked property binding and @change handler"
    - "Sparse optional fields on ClimateConfig interface"
key_files:
  created: []
  modified:
    - frontend/src/types.ts
    - frontend/src/ws-client.ts
    - frontend/src/components/global-settings-tab.ts
    - custom_components/climate_manager/www/panel.js
decisions:
  - "Used ha-switch per D-12; native checkbox fallback pending human verification (Pitfall 6)"
  - "Options card rendered as third card always (D-13) — not gated on TRV compatibility"
  - "Auto-save on change via _onCalibrationToggle, no Save button (D-12)"
  - "deploy ran from main repo workaround — worktree lacks Makefile.local, so panel.js deployed directly via scp"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-30T13:10:10Z"
  tasks_completed: 3
  tasks_total: 4
---

# Phase 9 Plan 04: Wire Calibration Toggle into Panel UI Summary

Frontend calibration toggle wired into Global Settings tab via ha-switch in a
new "Options" ha-card (third card), auto-saving to the backend
set_calibration_config WS command.

## What Was Built

### Task 1: Extend types and ws-client (commit 7cc6aac)

- Added `calibration_enabled?: boolean` and `calibration_threshold?: number`
  optional fields to `ClimateConfig` interface in `types.ts` (sparse-config
  model: absent = backend default)
- Added `setCalibrationConfig(enabled: boolean): Promise<{ success: boolean }>`
  method to `WsClient` in `ws-client.ts`, calling
  `climate_manager/set_calibration_config` via `sendMessagePromise`

### Task 2: Options card with calibration toggle (commit e1889d9)

- Added `_renderOptionsCard()` method to `GlobalSettingsTab` rendering an
  `ha-card` with header "Options" and a single toggle row
- Toggle uses `<ha-switch .checked=${enabled} @change=${this._onCalibrationToggle}>`
- Added `_onCalibrationToggle` as arrow-function class field (correct `this`
  binding for Lit event listeners) — auto-saves via `ws.setCalibrationConfig`,
  then `reloadConfig()`, then `showToast("Saved")`
- Added `.option-row` and `.option-label` CSS following `.status-row` naming
- Wired `${this._renderOptionsCard()}` as third card in `render()` after
  Temperatures card

### Task 3: Build and deploy (commit 1675433)

- `make test`: 153 passed (1 pre-existing failure in
  `test_phase06_acceptance.py::test_main_tab_overview_label` — confirmed
  pre-existing before my changes)
- `make lint`: clean after prettier reformatting of `panel.js`
- `make build`: successful — panel.js rebuilt at 154.29 kB
- `make deploy`: panel.js deployed directly via scp to
  `root@homeassistant.local` (worktree lacks Makefile.local; deployed
  from worktree panel.js directly); HA restarted successfully

### Task 4: Checkpoint (pending human verification)

Human verification required for Pitfall 6 (ha-switch visibility in HA 2026.x).

## Commits

| Hash | Message | Task |
|------|---------|------|
| 7cc6aac | feat(09-04): add calibration types and ws-client method | 1 |
| e1889d9 | feat(09-04): add Options card with calibration toggle | 2 |
| 1675433 | chore(09-04): build and deploy calibration UI | 3 |

## Deviations from Plan

### Auto-fixed Issues

None from Rules 1-3.

### Deployment Workaround

The worktree does not have a `Makefile.local` file (it exists only in the main
repo at `Makefile.local` with `HA_HOST=homeassistant.local`). As a result:

- `make deploy` from the worktree fails with "Could not resolve hostname
  homeassistant.local"
- Workaround: deployed the worktree's `panel.js` directly via `scp` to
  `root@homeassistant.local:/config/custom_components/climate_manager/www/panel.js`
  then ran `ssh root@homeassistant.local "ha core restart"` manually

This is a devops-level deviation, not a correctness issue. The correct panel.js
(with calibration changes) was deployed.

### Pre-existing Test Failure

`tests/test_phase06_acceptance.py::test_main_tab_overview_label` was already
failing before this plan's changes — confirmed by running the test on the clean
main branch baseline. Documented as pre-existing, not introduced by this plan.

## Known Stubs

None — the `calibration_enabled` field is wired to the actual WS command and
reads back from `this.config.calibration_enabled ?? false`.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary changes. The
Options card calls the existing `set_calibration_config` WS command already
registered in Plan 03.

## Human Verification Pending (Task 4)

Pitfall 6: `ha-switch` visibility in HA 2026.x needs live verification. If the
toggle renders nothing (like `ha-textfield`/`ha-tabs`/`ha-select` breakage),
fallback is to replace `<ha-switch>` with a styled native `<input type="checkbox">`
keeping identical `_onCalibrationToggle` auto-save behavior.

## Self-Check: PASSED

All files found, all commits verified, all content checks passed.
