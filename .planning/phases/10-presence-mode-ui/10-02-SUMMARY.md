---
phase: 10-presence-mode-ui
plan: 02
subsystem: ui
tags: [lit, typescript, presence-mode, person-card, device-trackers]

# Dependency graph
requires:
  - phase: 10-01
    provides: >
      MODE_LABEL_HA, computeHasDeviceTrackers, shouldShowHaOption,
      presenceModeHint pure helpers in presence-mode.ts

provides:
  - person-card.ts wired with hasDeviceTrackers prop, conditional ha
    option, and presenceModeHint-backed schedule-hint
  - persons-tab.ts computes per-person hasDeviceTrackers from
    hass.states and forwards it to each PersonCard

affects: [10-03, any phase reading persons-tab or person-card]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Import pure helper module (presence-mode.js) into Lit component
      using .js specifier for Vite build resolution
    - Per-person attribute map built in render() before sortedIds.map()
    - Conditional option rendered via ternary +
      html`<option>` : "" pattern (not disabled/display:none)

key-files:
  created: []
  modified:
    - frontend/src/components/person-card.ts
    - frontend/src/components/persons-tab.ts

key-decisions:
  - "D-01 confirmed: label stays MODE_LABEL_HA (HA home tracking),
    no rename; PATTERNS.md Live tracking references were stale"
  - "D-04: ha option removed from DOM (not hidden) via
    shouldShowHaOption guard — native select retains stuck value
    per T-10-05 accept disposition"
  - "D-05: stuck-mode warning delegated to presenceModeHint; no
    ws/setPersonConfig call fires at render time"
  - "computeHasDeviceTrackers receives raw attribute value from
    hass.states — no length check duplicated in persons-tab"

patterns-established:
  - "Pure helper imported with .js specifier from Lit component"
  - "Map<string, boolean> built once per render() from hass.states
    for per-entity derived data"

requirements-completed: [UI-01, UI-02]

# Metrics
duration: 20min
completed: 2026-06-01
---

# Phase 10 Plan 02: Presence Mode UI Wiring Summary

**Wired presence-mode helpers into person-card and persons-tab:
conditional HA option, stuck-mode warning, and per-person
device-tracker forwarding from hass.states**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-06-01T00:00:00Z
- **Completed:** 2026-06-01
- **Tasks:** 2 of 3 complete (Task 3 = checkpoint: pending human
  review)
- **Files modified:** 2

## Accomplishments

- `person-card.ts`: imports `MODE_LABEL_HA`, `shouldShowHaOption`,
  `presenceModeHint` from `./presence-mode.js`; exposes
  `@property({ type: Boolean }) hasDeviceTrackers = false`; gates
  ha `<option>` on `shouldShowHaOption`; delegates schedule-hint
  to `presenceModeHint` (D-05 stuck-mode warning included)
- `persons-tab.ts`: imports `computeHasDeviceTrackers`; builds
  `hasDeviceTrackersMap` per person from `hass.states` attributes;
  forwards `.hasDeviceTrackers` to each `<climate-manager-person-card>`
- `make build` succeeds (Vite, 167 kB panel.js); `make lint` passes;
  8/8 presence-mode unit tests green; no new TypeScript errors in
  modified files

## Task Commits

Each task was committed atomically:

1. **Task 1: Add hasDeviceTrackers prop + conditional option +
   stuck-mode hint in person-card.ts** - `2dda782` (feat)
2. **Task 2: Compute hasDeviceTrackers per person in persons-tab.ts
   and forward to each card** - `05fa8c6` (feat)
3. **Task 3: Visual verify label, conditional option, stuck-mode
   warning in live panel** — checkpoint pending human review

## Files Created/Modified

- `frontend/src/components/person-card.ts` — added `hasDeviceTrackers`
  prop, gated ha option, replaced hint ternary with `presenceModeHint`
- `frontend/src/components/persons-tab.ts` — added
  `computeHasDeviceTrackers` import, `hasDeviceTrackersMap`
  computation, `.hasDeviceTrackers` prop forwarding

## Decisions Made

- Label stays `MODE_LABEL_HA = "HA home tracking"` (D-01 confirmed).
  PATTERNS.md contained stale "Live tracking" references — ignored per
  `<label_decision>` directive.
- `computeHasDeviceTrackers` receives raw `attributes.device_trackers`
  value; the helper owns all Array.isArray / length logic (T-10-03
  mitigated).
- Conditional ha `<option>` uses empty-string fallback (`... : ""`)
  matching existing conditional blocks in the file; no `disabled` or
  `display:none` (D-04 anti-pattern avoided).

## Deviations from Plan

None — plan executed exactly as written (stale "Live tracking"
references in PATTERNS.md correctly ignored per label_decision).

## Checkpoint: Pending Human Review

**Task 3** (`type="checkpoint:human-verify"`) requires visual
verification in the live HA panel. Execution paused here per
plan spec.

Verification steps (from plan):

1. `make deploy`, then hard-refresh panel (Ctrl-Shift-R)
2. Open Climate Manager panel → Persons tab
3. Person WITH device trackers: confirm dropdown shows "HA home
   tracking" option (4 options total); selecting it shows hint
   "Presence mirrors Home Assistant home/away tracking."
4. Person WITHOUT device trackers: confirm dropdown shows 3
   options only (no "HA home tracking")
5. Person stuck on mode=ha with no trackers: confirm inline warning
   "HA home tracking requires a device tracker linked to this
   person in HA." and mode did NOT change silently
6. Collapsed person on ha mode: confirm badge reads
   "HA home tracking"

## Issues Encountered

None — `make build` and `make lint` both passed cleanly. No new
TypeScript errors introduced in modified files.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced.
The only data flow is `hass.states[personId].attributes.device_trackers`
→ `computeHasDeviceTrackers` → boolean (read-only, no mutation).
T-10-03 and T-10-04 mitigations confirmed present.

## Known Stubs

None — all data paths wired: `hasDeviceTrackersMap` reads live
`hass.states` on every render cycle.

## Next Phase Readiness

- UI-01 and UI-02 data path fully wired; build and lint clean
- Awaiting human visual verification (Task 3 checkpoint)

## Self-Check

- `frontend/src/components/person-card.ts` exists: FOUND
- `frontend/src/components/persons-tab.ts` exists: FOUND
- Commit `2dda782` exists: FOUND
- Commit `05fa8c6` exists: FOUND

## Self-Check: PASSED

---
*Phase: 10-presence-mode-ui*
*Completed: 2026-06-01 (checkpoint pending)*
