---
phase: 08-even-odd-week-scheduling-frontend
verified: 2026-05-30T09:00:00Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
human_verification:
  - test: >
      Set a person's Presence mode to 'Scheduled'. Confirm the 'Schedule type'
      select is visible. Change mode to 'HA home tracking', 'Force Present', or
      'Force Absent' and confirm the select disappears.
    expected: >
      Schedule type select appears only in Scheduled mode (D-01). In all other
      modes the select — and the Even/Odd switcher — are absent.
    why_human: >
      Conditional rendering in the Lit template cannot be confirmed by grep;
      requires live DOM inspection in the panel.
  - test: >
      Set schedule type to 'Even / Odd weeks'. Expand the card. Confirm the
      active tab matches the current ISO week parity (today 2026-05-30 is ISO
      week 22, which is even → 'Even' tab should be active by default).
    expected: >
      'Even' tab is active on initial expand. Collapsing and re-expanding
      should always reset the active tab to the current week parity (D-09,
      D-10).
    why_human: >
      Active-state CSS class application and parity-driven tab selection at
      runtime require live panel interaction.
  - test: >
      Edit the Even week time-bar, then reload the panel. Then edit the Odd
      week time-bar and reload. Confirm each week's edits persisted
      independently (schedule_even and schedule_odd unchanged by the other
      week's edits).
    expected: >
      schedule_even and schedule_odd persist independently. Editing one week
      does not affect the other (D-11, D-12, D-13). Both survive a full panel
      reload (ROADMAP success criterion 4).
    why_human: >
      Persistence of WebSocket round-trip writes to backend storage and panel
      reload behaviour cannot be verified by static code inspection.
  - test: >
      In even/odd mode, click the 'Reset Even week to default' button. Reload.
      Confirm Even week is reset and Odd week is unchanged. Switch to the Odd
      tab and confirm the reset button now reads 'Reset Odd week to default'.
      Switch back to Single week — confirm button reads 'Reset to default'.
    expected: >
      Reset is scoped to the active week only (D-14, D-15). Button label
      updates dynamically with the active tab.
    why_human: >
      Dynamic label rendering and backend reset persistence require live
      interaction.
---

# Phase 8: Even/Odd Week Scheduling Frontend — Verification Report

**Phase Goal:** A user can configure both week schedules for an even/odd person
directly in the panel, with a clear Even/Odd toggle that scopes time-bar edits
to one week at a time, and the toggle never appears for single-schedule persons.

**Verified:** 2026-05-30T09:00:00Z
**Status:** passed
**Re-verification:** Closed 2026-05-31 — all 10 SCHED-04 behaviors confirmed
in live panel per 08-03-SUMMARY.md human verification checkpoint

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | getWeekParity(new Date()) returns same parity as Python backend | VERIFIED | week-parity.ts line 37: `getISOWeekNumber(date) % 2 === 0 ? "even" : "odd"` — exact match to schedule.py `week_parity = now.date().isocalendar().week % 2; schedule_key = "schedule_even" if week_parity == 0 else "schedule_odd"` |
| 2 | getISOWeekNumber returns ISO 8601 week numbers matching Python isocalendar().week | VERIFIED | 8/8 node --test assertions pass including W22, W23, W01-2027, W53-2026 (WR-03 boundary), and totality property |
| 3 | Schedule-type select visible only in Scheduled mode | VERIFIED (code) / HUMAN | Code: select is inside `${isScheduled ? html\`...\` : ""}` block (line 592–668). Runtime rendering requires human confirmation. |
| 4 | Selecting Even/Odd weeks sends `{schedule_type: 'even_odd'}` with no schedule payload | VERIFIED | `_onScheduleTypeChange` (lines 348–361): sends only `{ schedule_type: newType }` — no `schedule` field in the payload |
| 5 | Even/Odd switcher appears only when schedule_type === 'even_odd' | VERIFIED | Template line 620: switcher is inside `${isEvenOdd ? html\`...\` : ""}` guard |
| 6 | Default active week on card expand matches getWeekParity(new Date()) | VERIFIED | `updated()` hook (lines 147–161): `this._activeWeek = getWeekParity(new Date())` triggered by `changedProperties.has("_expanded") && this._expanded` |
| 7 | Time-bar edits on Even tab write to schedule_even, on Odd to schedule_odd | VERIFIED | `_onSchedulePeriodsChanged` (lines 382–420): computes `field` as `schedule_even` (even) / `schedule_odd` (odd) / `schedule` (single); sends only that field |
| 8 | Reset button label and target follow active week | VERIFIED | `resetLabel` computed at render (lines 455–459); `_onResetSchedule` (lines 363–380) sends `{[field]: DEFAULT_SCHEDULE}` using the same field logic |
| 9 | No forbidden HA 2026.x components used | VERIFIED | grep for ha-select, ha-tabs, ha-textfield returns 0 matches in person-card.ts |
| 10 | Changes persist across reload and match backend parity | HUMAN NEEDED | Code paths are wired correctly; persistence requires live WebSocket round-trip verification against running HA instance |

**Score:** 9/10 truths verified by code analysis. Truth 10 (persistence) and
runtime behaviour for Truth 3 (conditional rendering in DOM) require human
confirmation per Plan 03.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/components/week-parity.ts` | `getISOWeekNumber` + `getWeekParity` pure exports | VERIFIED | Lines 20, 36: both `export function` declarations present; implementation follows ISO 8601 algorithm |
| `frontend/src/components/week-parity.test.ts` | 8 node --test assertions | VERIFIED | 8 tests, all pass: `node --test --experimental-strip-types` exits 0 |
| `frontend/src/components/person-card.ts` | All SCHED-04 UI state, getters, handlers, template | VERIFIED | _activeWeek, _daysEven, _daysOdd, _onScheduleTypeChange, updated() hook, schedule-type select, week-switcher, dynamic .days binding, ${resetLabel} all present |
| `custom_components/climate_manager/www/panel.js` | Built bundle with SCHED-04 UI | VERIFIED | 150 KB bundle present at path; Vite build exits 0 cleanly |

**Note on Plan 01 artifact deviation:** The PLAN specified `person-card.ts`
should contain `export function getWeekParity` (function declaration). Instead,
the implementation places the function in `week-parity.ts` and re-exports via
`export { getISOWeekNumber, getWeekParity }` from `person-card.ts` (line 80).
This deviation is architecturally correct — Lit legacy decorators block
`node --experimental-strip-types` from importing `person-card.ts`, making
the planned verify command physically impossible. The SUMMARY.md documents this
as an auto-fixed Rule 3 deviation. Both exports function identically; callers
can import from either module.

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `week-parity.test.ts` | `week-parity.ts` | `import { getISOWeekNumber, getWeekParity } from "./week-parity.ts"` | WIRED | Line 16 of test file; module resolves and all 8 tests pass |
| `person-card.ts` | `week-parity.ts` | `import { getISOWeekNumber, getWeekParity } from "./week-parity.js"` | WIRED | Line 79; used in `updated()` (line 150) and in render template (lines 623–624) |
| `_onSchedulePeriodsChanged` | `ws.setPersonConfig` | computed `field` = `schedule_even` \| `schedule_odd` \| `schedule` | WIRED | Lines 405–412: field is computed then sent as `{ [field]: updated }` |
| `render()` | `_daysEven` / `_daysOdd` | `.days` binding selected by `_activeWeek` | WIRED | Lines 653–657: ternary picks `_daysEven` or `_daysOdd` when `isEvenOdd`, else `_days` |
| `person card panel UI` | `backend schedule_even / schedule_odd` | `setPersonConfig` WebSocket | HUMAN NEEDED | Code sends correct payload; persistence requires live HA instance |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `person-card.ts` render | `_daysEven` / `_daysOdd` | `this.config?.schedule_even` / `this.config?.schedule_odd` via memoized getters (lines 120–138) | Real data when `schedule_even`/`schedule_odd` present on config (seeded by Phase 7 backend); empty fallback when absent | FLOWING |
| `_onScheduleTypeChange` | `schedule_type: newType` | select element value, TypeScript-constrained to `"single" \| "even_odd"` | Real user input | FLOWING |
| `_onSchedulePeriodsChanged` | `{ [field]: updated }` | Cloned active schedule + edited day; field computed from `isEvenOdd` + `_activeWeek` | Real config mutation | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Week parity test suite | `cd frontend && node --test --experimental-strip-types src/components/week-parity.test.ts` | 8 pass, 0 fail | PASS |
| TypeScript build | `cd frontend && npm run build` | Exit 0; 31 modules, 152.89 kB bundle | PASS |
| No forbidden components | `grep -c "ha-select\|ha-tabs\|paper-tab" person-card.ts` | 0 | PASS |
| `_onScheduleTypeChange` sends only schedule_type | grep shows only `schedule_type: newType` in handler body, no `schedule:` field | payload is minimal | PASS |

### Probe Execution

No probe scripts exist for this phase (`scripts/*/tests/probe-*.sh` absent).
Phase is a frontend UI phase with no runnable backend probes.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SCHED-04 | 08-01, 08-02, 08-03 | Persons UI shows week-switcher toggle only when schedule_type == "even_odd"; editing affects only selected week's schedule | SATISFIED (code) / HUMAN for runtime | All code paths for week-switcher conditional, per-week save, per-week reset, and ISO-parity default tab are implemented. Runtime persistence requires human verification (Plan 03 checkpoint). |

**REQUIREMENTS.md traceability note:** The traceability table at the bottom of
REQUIREMENTS.md shows `SCHED-04 | Phase 8 | TBD` for the Plan column. This is
a stale documentation entry — Plans 08-01, 08-02, and 08-03 all declare
`requirements: [SCHED-04]` in their frontmatter. No code impact; documentation
only.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | — |

No TBD, FIXME, XXX, HACK, or PLACEHOLDER markers found in any file modified
by this phase. No stub implementations detected. No forbidden HA 2026.x
components (ha-select, ha-tabs, ha-textfield) used.

### Human Verification Required

#### 1. Schedule-Type Select Visibility (D-01)

**Test:** Open the Climate Manager panel. Expand a person card. Set Presence
mode to "Scheduled" and confirm the "Schedule type" select appears. Then set
mode to "HA home tracking", "Force Present", and "Force Absent" in turn —
confirm the select disappears in all three non-Scheduled modes.

**Expected:** Select is visible only in Scheduled mode. Even/Odd switcher also
absent when Presence mode is not Scheduled.

**Why human:** Conditional rendering in the Lit template cannot be confirmed
by grep; requires live DOM inspection.

#### 2. ISO Parity Default Tab on Expand (D-09, D-10)

**Test:** Set a person to "Even / Odd weeks". Collapse the card, then expand
it. Confirm the active tab (Even or Odd) matches the current ISO week parity.
Today 2026-05-30 is ISO week 22 (even) so the "Even" tab should be active on
expand.

**Expected:** Active tab always matches `getWeekParity(new Date())` at expand
time, not persisted across collapse/expand cycles.

**Why human:** `@state() _activeWeek` initialization in `updated()` requires
runtime Lit reactivity cycle to observe.

#### 3. Per-Week Persistence After Reload (ROADMAP SC-4, D-11, D-12, D-13)

**Test:** In even/odd mode, edit the Even week time-bar, then do a full panel
reload. Confirm the Even week edit persisted and the Odd week is unchanged.
Then edit the Odd week, reload again — confirm Odd persisted, Even unchanged.

**Expected:** `schedule_even` and `schedule_odd` persist independently in
backend storage and survive a full panel reload.

**Why human:** Requires live WebSocket round-trip to a running HA instance with
Phase 7 backend. Cannot verify storage persistence by code analysis alone.

#### 4. Reset Scoping and Label (D-14, D-15)

**Test:** In even/odd mode on the Even tab, click reset. Reload and confirm
only the Even week was reset (Odd week untouched). Switch to the Odd tab —
confirm reset button reads "Reset Odd week to default". Switch back to "Single
week" — confirm reset button reads "Reset to default".

**Expected:** Reset is scoped to the active week. Button label is dynamic.

**Why human:** Requires live backend interaction to confirm that
`{ schedule_even: DEFAULT_SCHEDULE }` is correctly applied by the backend and
that `schedule_odd` is not affected.

### Gaps Summary

No code gaps detected. All SCHED-04 artifacts are present, substantive, and
wired. The 4 human verification items above are the only outstanding items —
they require a live HA instance, not code changes. Plan 03 is a blocking
human-checkpoint plan designed for exactly this.

The ROADMAP.md progress table correctly shows Phase 8 at 2/3 plans complete
and status "In Progress". The phase is complete from an implementation
standpoint; it is awaiting Plan 03 human sign-off.

---

_Verified: 2026-05-30T09:00:00Z_
_Verifier: Claude (gsd-verifier)_
