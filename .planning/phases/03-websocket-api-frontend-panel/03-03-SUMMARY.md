---
phase: 03-websocket-api-frontend-panel
plan: "03"
subsystem: frontend-panel
tags: [frontend, vite, lit, typescript, time-bar, panel, build-pipeline]
dependency_graph:
  requires:
    [
      websocket-api-8-commands,
      subscribe-status-push,
      panel-registration,
      static-path,
    ]
  provides:
    [
      frontend-build-pipeline,
      climate-manager-panel,
      climate-manager-time-bar,
      climate-manager-toast,
      ws-client,
    ]
  affects: [03-04-tab-bodies]
tech_stack:
  added:
    - lit@3.3.3
    - vite@5.4.21
    - typescript@5.x (devDependency)
    - home-assistant-js-websocket@latest
  patterns:
    - vite-library-mode-single-file
    - lit-element-property-state
    - pointer-event-drag-capture
    - custom-event-periods-changed
    - restore-www-gitignore-plugin
key_files:
  created:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/tsconfig.json
    - frontend/vite.config.ts
    - frontend/src/types.ts
    - frontend/src/ws-client.ts
    - frontend/src/toast.ts
    - frontend/src/main.ts
    - frontend/src/components/time-bar.ts
    - custom_components/climate_manager/www/.gitignore
  modified:
    - Makefile
    - .gitignore
decisions:
  - "Both Task 1 and Task 2 implemented in one commit — time-bar.ts needed for
    main.ts import to compile; separate stub would have required two build
    passes"
  - "restoreWwwGitignore Vite plugin added to recreate www/.gitignore after
    emptyOutDir:true deletes it on each build"
  - "package-lock.json committed for reproducible builds"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-18"
  tasks: 2
  files: 12
---

# Phase 3 Plan 3: Frontend Build Pipeline + Panel Skeleton + Time-Bar Summary

Vite 5 + Lit 3 + TypeScript frontend project producing a single `panel.js` into
`custom_components/climate_manager/www/`, with the root
`<climate-manager-panel>` element (3-tab shell, WS bootstrap), the shared
`<climate-manager-time-bar>` component (split/edit/drag/copy-paste),
`<climate-manager-toast>`, and `make build` / `make deploy` wiring.

## What Was Built

### Task 1 + Task 2 (combined in one commit — see Deviations)

**frontend/package.json:**

- `name: "climate-manager-panel"`, `"type": "module"`
- `dependencies: { lit: "^3", home-assistant-js-websocket: "latest" }`
- `devDependencies: { typescript: "^5", vite: "^5" }`

**frontend/tsconfig.json:**

- `target: ES2022`, `moduleResolution: "bundler"`,
  `experimentalDecorators: true`, `useDefineForClassFields: false` (required for
  Lit decorators)
- `strict: true`, `lib: ["ES2022", "DOM", "DOM.Iterable"]`

**frontend/vite.config.ts:**

- `build.lib.entry = src/main.ts`, `formats: ["es"]`, `fileName: "panel"`
- `outDir: "../custom_components/climate_manager/www"`, `emptyOutDir: true`
- `rollupOptions.output.inlineDynamicImports: true`,
  `entryFileNames: "panel.js"`, `cssCodeSplit: false`
- `restoreWwwGitignore` plugin: recreates `www/.gitignore` in `closeBundle()`
  hook after `emptyOutDir` deletes it

**frontend/src/types.ts:**

- `Period`, `DailyProgram`, `ClimateConfig`, `RoomConfig`, `PersonConfig`,
  `StatusPayload`, `Hass` interfaces
- `PERIOD_COLORS` (frost_protection=#1565C0, reduced=#64B5F6, normal=#F57C00,
  comfort=#D32F2F)
- `PRESENCE_COLORS` (present=#388E3C, absent=#9E9E9E)
- `PERIOD_LABELS` (F/R/N/C, P/A) for accessibility

**frontend/src/ws-client.ts:**

- `WsClient` class: typed methods for all 8 commands
- `getConfig()`, `getStatus()`, `setGlobalMode()`, `setPeriodTemperatures()`,
  `setTimeProgram()`, `setRoomConfig()`, `setPersonConfig()`,
  `subscribeStatus()`

**frontend/src/toast.ts:**

- `<climate-manager-toast>`: `show(message, isError)`, success auto-dismisses
  3s, error persistent
- `mdi:check-circle` (success, `var(--primary-color)`), `mdi:alert-circle`
  (error, `var(--error-color)`)
- `pointer-events: none`, `role="status"`, `aria-live="polite"`

**frontend/src/main.ts:**

- `<climate-manager-panel>`: `@property hass, narrow, panel`;
  `@state _config, _status, _activeTab, _unsubStatus, _wsError`
- `connectedCallback`: `_loadConfig()` via `ws-client.getConfig()`,
  `_subscribeStatus()` via `ws-client.subscribeStatus()`
- `disconnectedCallback`: unsubscribes via `_unsubStatus?.then(u => u())`
- Loading state: `<ha-circular-progress>` while `_config` is null
- Error banner: "Connection lost. Reconnecting…" when `_wsError` is true
- Tab shell: `<ha-tabs>` with Global Settings / Rooms / Persons tabs
- Placeholder text per tab (filled in next plan)
- Public `showToast(message, isError)` delegating to `<climate-manager-toast>`
- `customElements.define("climate-manager-panel", ClimateManagerPanel)` — name
  matches `PANEL_COMPONENT_NAME`
- Side-effect import of `./components/time-bar.js`

**frontend/src/components/time-bar.ts:**

- `<climate-manager-time-bar>`: `@property days: Period[][]` (7 elements,
  Mon–Sun), `@property mode: "schedule"|"presence"`
- 7 day rows: 3-letter label (40px), 40px colored bar, Copy + Paste icon buttons
- Shared time axis below all rows: 00:00 / 06:00 / 12:00 / 18:00 / 24:00
- Segment colors from `PERIOD_COLORS` / `PRESENCE_COLORS` keyed by period.mode
  or period.state
- Single-character labels (F/R/N/C, P/A) rendered when segment > 2.7% width
  (~40px), with `aria-label`
- Bar always fully covered: implicit 00:00 fill if first period doesn't start
  there
- Helpers: `_snapToMinutes`, `_pixelToMinutes`, `_minutesToHHMM`
- **D-04 Split**: click bar background → mode popup "Split at HH:MM" → select
  mode → insert + sort + dedup → emit `periods-changed` on popup close
- **D-05 Edit/Delete**: click segment → edit popup with time range + Change mode
  (opens mode picker) + Delete period (merges into left neighbor by removing
  period from array) → emit on popup close
- **D-06 Drag**: pointerdown on drag handle → `setPointerCapture` → pointermove
  updates tooltip only (no emit) → pointerup applies snapped boundary with
  15-min minimum enforcement → emit `periods-changed`
- **D-07 Copy/Paste**: Copy stores deep copy in `_clipboard`; Paste overwrites
  target day → emit immediately
- **D-09**: `periods-changed` emitted only on: popup close (split/edit),
  pointerup (drag), paste — never during pointermove
- `customElements.define("climate-manager-time-bar", ClimateManagerTimeBar)`

**custom_components/climate_manager/www/.gitignore:** ignores `panel.js` and
`*.map`

**Makefile:**

- `build:` target:
  `cd frontend && npm install --no-audit --no-fund && npm run build`
- `deploy: build` prerequisite (always rebuilds before rsync)
- `build` added to `.PHONY`

**.gitignore:** `frontend/node_modules/` and `frontend/dist/` added

## Build Results

```
npm run build:
vite v5.4.21 building for production...
✓ 22 modules transformed.
../custom_components/climate_manager/www/panel.js  49.76 kB │ gzip: 13.54 kB
✓ built in ~145ms

Verification checks:
- Exactly 1 .js file in www/: PASS
- panel.js contains "climate-manager-panel": PASS
- panel.js contains "climate-manager-time-bar": PASS
- panel.js contains "periods-changed": PASS
- panel.js contains "1565C0" (D-03 period color): PASS
- Makefile has build: target: PASS
- Makefile has deploy: build: PASS
- www/.gitignore ignores panel.js: PASS
- .gitignore has frontend/node_modules/: PASS
- No sendMessagePromise in time-bar.ts: PASS (no WS calls)
- No _emitChange in _onPointerMove: PASS (emit only on pointerup/popup/paste)
```

## Deviations from Plan

### Structural Deviation (No Rule Trigger — Build Constraint)

**1. Tasks 1 and 2 combined in single commit**

- **Found during:** Task 1 implementation
- **Issue:** `frontend/src/main.ts` contains `import "./components/time-bar.js"`
  as required by Task 2. The Vite TypeScript build immediately resolves all
  imports — if time-bar.ts did not exist, `npm run build` would fail with a
  module resolution error. A stub would have required either a second build pass
  or removing/re-adding the import between tasks.
- **Fix:** Implemented the complete time-bar.ts (as specified in Task 2)
  alongside Task 1. Both tasks' acceptance criteria are met in commit 10348ad.
- **Files modified:** `frontend/src/components/time-bar.ts`,
  `frontend/src/main.ts`
- **Commit:** 10348ad

**2. [Rule 2 - Missing Critical Functionality] `restoreWwwGitignore` Vite
plugin**

- **Found during:** Task 1 first build attempt
- **Issue:** Vite's `emptyOutDir: true` deletes ALL files in the output
  directory on each build, including `www/.gitignore`. Without the plugin, the
  .gitignore would be deleted every time `make build` runs, causing `panel.js`
  to appear as an untracked file in git after every build.
- **Fix:** Added a `closeBundle()` hook Rollup plugin inside `vite.config.ts`
  that recreates `www/.gitignore` after each build. This is a build correctness
  requirement (missing it causes constant git noise).
- **Files modified:** `frontend/vite.config.ts`
- **Commit:** 10348ad

## Known Stubs

- Tab bodies in `main.ts`: each tab renders placeholder text only
  ("implementation in next plan"). This is intentional — the next plan (03-04)
  wires the actual tab content. The placeholder is sufficient for the
  build/visual check per Task 1 done criteria.

## Threat Surface Scan

| Flag                   | File                 | Description                                                                                                                                                                     |
| ---------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| threat_flag: tampering | frontend/src/main.ts | Root panel element reads hass.connection directly — all WS commands go through the authenticated hass object. Covered by T-03-12 (component name matches PANEL_COMPONENT_NAME). |

T-03-10 (stale panel.js): `make deploy` always runs `make build` first;
`cache_headers=False` set in Wave 2. T-03-11 (multi-chunk):
`inlineDynamicImports: true` + single entry confirmed by build output (1 file).
T-03-12 (component name mismatch):
`customElements.define("climate-manager-panel", ...)` matches
`PANEL_COMPONENT_NAME = "climate-manager-panel"` in `__init__.py`.

## Self-Check: PASSED

- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-ad02304a029c807fe/frontend/package.json`
  — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-ad02304a029c807fe/frontend/tsconfig.json`
  — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-ad02304a029c807fe/frontend/vite.config.ts`
  — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-ad02304a029c807fe/frontend/src/types.ts`
  — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-ad02304a029c807fe/frontend/src/ws-client.ts`
  — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-ad02304a029c807fe/frontend/src/toast.ts`
  — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-ad02304a029c807fe/frontend/src/main.ts`
  — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-ad02304a029c807fe/frontend/src/components/time-bar.ts`
  — FOUND
- `/home/arnaud/dev/climate_manager/.claude/worktrees/agent-ad02304a029c807fe/custom_components/climate_manager/www/.gitignore`
  — FOUND
- Commit 10348ad — FOUND (Tasks 1+2: full scaffold + time-bar)
- `npm run build` — ✓ 49.76 kB panel.js, exactly 1 .js file
- panel.js contains climate-manager-panel, climate-manager-time-bar,
  periods-changed, 1565C0 ✓
- No WS calls in time-bar.ts ✓
- No \_emitChange in \_onPointerMove ✓
