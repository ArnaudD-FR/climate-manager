---
phase: 03-websocket-api-frontend-panel
plan: 11
subsystem: frontend
tags: [phase-03, gap-closure, frontend, styling, d-26, d-27]
dependency_graph:
  requires: []
  provides: [D-26-colors, D-27-ha-css-vars]
  affects:
    [
      frontend/src/types.ts,
      frontend/src/components/room-card.ts,
      frontend/src/components/global-settings-tab.ts,
      frontend/src/components/time-bar.ts,
      frontend/src/components/search-picker.ts,
      frontend/src/components/person-card.ts,
      frontend/src/toast.ts,
      frontend/src/main.ts,
    ]
tech_stack:
  added: []
  patterns:
    [unsafeCSS Lit pattern for injecting JS constants into static styles]
key_files:
  created: []
  modified:
    - frontend/src/types.ts
    - frontend/src/components/room-card.ts
    - frontend/src/components/global-settings-tab.ts
    - frontend/src/components/time-bar.ts
    - frontend/src/components/search-picker.ts
    - frontend/src/components/person-card.ts
    - frontend/src/toast.ts
    - frontend/src/main.ts
    - custom_components/climate_manager/www/panel.js
decisions:
  - "D-26: Use PERIOD_COLORS / PRESENCE_COLORS as single source of truth for
    period/presence hex values; applied via inline style= on badges"
  - "D-27: All non-period/presence colors use HA CSS variables;
    rgba(3,169,244,0.08) chip-add:hover replaced with
    var(--secondary-background-color) because HA does not standardize a
    primary-color-tint token"
  - "D-27: rgba(255,152,0,0.12) no-trv-badge background replaced with
    var(--secondary-background-color) (same rationale)"
  - "D-27: rgba(0,0,0,0.75) drag-tooltip background replaced with
    var(--app-header-background-color, rgba(0,0,0,0.75)) for tooltip readability"
  - "D-27: box-shadow values use var(--ha-card-box-shadow, ...) with original
    rgba as fallback"
  - "Lit unsafeCSS: used in global-settings-tab.ts :host {} to inject
    PRESENCE_COLORS.present as a CSS custom property; safe because value is a
    constant from our codebase"
metrics:
  duration: 222s
  completed_date: "2026-05-21"
  tasks: 3
  files_changed: 9
---

# Phase 03 Plan 11: D-26/D-27 Color Cleanup Summary

**One-liner:** Single source of truth for period/presence colors
(PERIOD_COLORS/PRESENCE_COLORS) with all other hardcoded colors replaced by HA
CSS custom properties.

## What Was Done

Enforced two styling constraints across the entire frontend codebase before Plan
03-12 ships the D-23 binding fix:

- **D-26:** `PERIOD_COLORS` and `PRESENCE_COLORS` in `types.ts` are the only
  place period/presence hex colors are written. Updated their values to the D-26
  spec. All prior inline hex literals encoding period/presence semantics now
  import from `types.ts`.
- **D-27:** Every other hardcoded color (bare hex, bare rgba) replaced with HA
  CSS custom properties. The only surviving hex literals outside `types.ts` are
  inside `var(--token, #fallback)` fallback expressions — explicitly permitted
  by D-27.

## Tasks Completed

| Task | Name                                                         | Commit  | Files                                                                                                            |
| ---- | ------------------------------------------------------------ | ------- | ---------------------------------------------------------------------------------------------------------------- |
| 1    | D-26 — update PERIOD_COLORS/PRESENCE_COLORS values           | ff2c012 | types.ts                                                                                                         |
| 2    | D-26 — route period/presence colors through imports          | 077d381 | room-card.ts, global-settings-tab.ts                                                                             |
| 3    | D-27 — replace remaining bare hex/rgba with HA CSS variables | d7797e5 | room-card.ts, time-bar.ts, search-picker.ts, person-card.ts, global-settings-tab.ts, toast.ts, main.ts, panel.js |

## Replacement Map (D-27 Changes)

| File                   | Original                                                  | Replacement                                              | Rationale                                                              |
| ---------------------- | --------------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------- |
| room-card.ts           | `background: rgba(255, 152, 0, 0.12)` (no-trv-badge)      | `var(--secondary-background-color)`                      | HA has no primary warning-tint token                                   |
| room-card.ts           | `color: #e65100` (no-trv-badge)                           | `var(--warning-color, #e65100)`                          | HA exposes `--warning-color`                                           |
| room-card.ts           | `background: rgba(3, 169, 244, 0.08)` (chip-add:hover)    | `var(--secondary-background-color)`                      | HA has no primary-color-tint token                                     |
| time-bar.ts            | `color: rgba(255, 255, 255, 0.9)` (segment)               | `var(--text-primary-color, white)`                       | HA token for on-colored-bg text                                        |
| time-bar.ts            | `background: rgba(0, 0, 0, 0.75)` (drag-tooltip)          | `var(--app-header-background-color, rgba(0,0,0,0.75))`   | Nearest dark bg token; rgba fallback preserved for tooltip readability |
| time-bar.ts            | `color: #fff` (drag-tooltip)                              | `var(--text-primary-color, white)`                       | HA token for on-colored-bg text                                        |
| time-bar.ts            | `box-shadow: 0 4px 16px rgba(0,0,0,0.25)` (popup)         | `var(--ha-card-box-shadow, 0 4px 16px rgba(0,0,0,0.25))` | HA card shadow token                                                   |
| search-picker.ts       | `background: rgba(3, 169, 244, 0.08)` (trigger-btn:hover) | `var(--secondary-background-color)`                      | Same as chip-add rationale                                             |
| search-picker.ts       | `box-shadow: 0 4px 16px rgba(0,0,0,0.15)` (popup)         | `var(--ha-card-box-shadow, 0 4px 16px rgba(0,0,0,0.15))` | HA card shadow token                                                   |
| person-card.ts         | `background: rgba(3, 169, 244, 0.08)` (chip-add:hover)    | `var(--secondary-background-color)`                      | Same as chip-add rationale                                             |
| global-settings-tab.ts | `background: rgba(3, 169, 244, 0.08)` (reset-btn:hover)   | `var(--secondary-background-color)`                      | Same as chip-add rationale                                             |
| toast.ts               | `box-shadow: 0 2px 8px rgba(0,0,0,0.2)`                   | `var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.2))`   | HA card shadow token                                                   |
| main.ts                | `color: #fff` (error-banner)                              | `var(--text-primary-color, white)`                       | HA token for on-error-bg text                                          |

## D-26 Changes (Task 1 + 2)

| Constant        | Key     | Old Value | New Value |
| --------------- | ------- | --------- | --------- |
| PERIOD_COLORS   | reduced | #64B5F6   | #0277BD   |
| PERIOD_COLORS   | normal  | #F57C00   | #2E7D32   |
| PERIOD_COLORS   | comfort | #D32F2F   | #E65100   |
| PRESENCE_COLORS | present | #388E3C   | #2E7D32   |

Note: D-26 intentionally uses the same value (#2E7D32) for `normal` and
`present` (both semantically green).

The `.program-badge.frost` static CSS rule was removed from room-card.ts;
replaced with inline `style=${badgeClass === "frost" ? \`background:
${PERIOD_COLORS.frost_protection}; color: white;\` : ""}` on the badge element.

The `.person-dot` `background: #388E3C` in global-settings-tab.ts was replaced
with `var(--present-color)` where `--present-color` is injected via
`unsafeCSS(PRESENCE_COLORS.present)` in the `:host` static style block — the
canonical Lit pattern for interpolating JS constants into `css\`\`` template
literals.

## color-mix Usage

`color-mix` was NOT used anywhere in this plan. The plan's interfaces noted it
as an option for chip-add:hover but recommended
`var(--secondary-background-color)` as the fallback.
`var(--secondary-background-color)` was chosen for all four chip-add:hover sites
for consistency and broad HA compatibility.

## Build Artifact

- Pre-change: 110.30 kB (gzip: 24.31 kB)
- Post-change: 110.55 kB (gzip: 24.31 kB)
- Delta: +0.25 kB uncompressed, identical gzip — no material regression.

## Deviations from Plan

None — plan executed exactly as written.

The `.period-badge.frost-protection/.reduced/.normal/.comfort` static CSS rules
mentioned in the plan interfaces were already absent from the current codebase
(they had been removed in a prior quick task). No action needed for those.

## Known Stubs

None — this plan is purely a styling/color-source cleanup with no data wiring.

## Threat Flags

None — no new network endpoints, auth paths, file access patterns, or schema
changes.

## Self-Check: PASSED

Files verified:

- frontend/src/types.ts — PERIOD_COLORS and PRESENCE_COLORS contain D-26 spec
  values
- frontend/src/components/room-card.ts — no bare hex/rgba; PERIOD_COLORS
  imported and used
- frontend/src/components/global-settings-tab.ts — no bare hex/rgba;
  PRESENCE_COLORS + unsafeCSS imported and used
- All other modified files — no bare hex/rgba primary values remaining
- Commits ff2c012, 077d381, d7797e5 exist in git log
- TypeScript check: PASSED
- Vite build: PASSED (110.55 kB, 28 modules)
