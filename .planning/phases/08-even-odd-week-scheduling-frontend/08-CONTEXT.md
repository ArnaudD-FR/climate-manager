# Phase 8: Even/Odd Week Scheduling — Frontend - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a schedule-type control and week-switcher toggle to `person-card.ts`.
When a person's `schedule_type` is `"even_odd"`, an Even/Odd tab switcher
appears inside the "Presence schedule" section and scopes time-bar edits to
`schedule_even` or `schedule_odd`. Single-schedule persons are unaffected.

**In scope:**

- `person-card.ts`: schedule-type `<select>` (visible when mode === "scheduled")
  + Even/Odd CSS button tab switcher (visible when schedule_type === "even_odd")
  + time-bar wired to the active week's schedule
  + dynamic reset button label per active week
- `ws-client.ts`: no new methods — `setPersonConfig` already accepts arbitrary
  partial payload; frontend sends `{schedule_type, schedule_even, schedule_odd}`
  as needed through the existing call
- TypeScript types: already updated in Phase 7 (`schedule_type`, `schedule_even`,
  `schedule_odd` optional on `PersonConfig`)

**Out of scope:**

- Backend evaluator (Phase 7, complete)
- Any new WebSocket commands
- TypeScript type changes (done in Phase 7)
- TRV calibration (Phase 9)

</domain>

<decisions>
## Implementation Decisions

### Schedule-Type Control (SCHED-04)

- **D-01:** The schedule-type control lives **inside the schedule section**,
  just above the Even/Odd switcher (i.e., before the time-bar). It is only
  visible when `mode === "scheduled"`.
- **D-02:** Control type: native `<select>` with two options — "Single week" /
  "Even / Odd weeks". Consistent with presence mode selector and zone picker;
  no new CSS pattern needed.
- **D-03:** Section label above the `<select>`: "Schedule type" — matches the
  style of "Presence mode" label elsewhere in the card.
- **D-04:** On change to "Even / Odd weeks": send
  `setPersonConfig(personId, { schedule_type: "even_odd" })`. The backend
  seeds `schedule_even` and `schedule_odd` from `schedule` automatically
  (Phase 7 D-01) — frontend sends no schedule payload.
- **D-05:** On change back to "Single week": send
  `setPersonConfig(personId, { schedule_type: "single" })`. The backend
  preserves `schedule` unchanged (Phase 7 D-02). Frontend reverts to showing
  the single-schedule time-bar.

### Week-Switcher Toggle

- **D-06:** Appearance: CSS button tabs — two buttons `[Even]` `[Odd]` styled
  with `.tab-btn` / `.tab-btn.active` classes (same pattern as `main.ts` tab
  bar). This is the established HA 2026.x tab pattern already in the codebase.
- **D-07:** Position: below the "Presence schedule" section label, above the
  time-bar. Layout order: section label → `[Even] [Odd]` switcher → time-bar →
  reset button.
- **D-08:** The switcher is only rendered when
  `schedule_type === "even_odd"` — absent for single-schedule persons.

### Default Active Week

- **D-09:** When the card expands for an even/odd person, the default active
  week is determined by the current ISO week parity:
  `new Date()` → `getWeekParity()` helper → `"even"` or `"odd"`. If today is
  an even ISO week, "Even" tab is active; odd week → "Odd" tab active.
- **D-10:** `_activeWeek` is local `@state()` — not persisted to localStorage.
  Recalculates from the current date each time the card expands.

### Time-Bar Wiring

- **D-11:** When `schedule_type === "even_odd"` and `_activeWeek === "even"`:
  time-bar receives `_daysEven` (memoized from `config.schedule_even`);
  `_onSchedulePeriodsChanged` saves `{ schedule_even: updatedSchedule }`.
- **D-12:** When `_activeWeek === "odd"`: time-bar receives `_daysOdd`
  (memoized from `config.schedule_odd`); saves `{ schedule_odd: updatedSchedule }`.
- **D-13:** Memoization: two additional `_lastScheduleEven`/`_cachedDaysEven`
  and `_lastScheduleOdd`/`_cachedDaysOdd` pairs, same pattern as the existing
  `_lastSchedule`/`_cachedDays`.

### Reset Button

- **D-14:** In single mode: button label "Reset to default" (unchanged).
  Saves `{ schedule: DEFAULT_SCHEDULE }` (unchanged).
- **D-15:** In even/odd mode: button label is dynamic — "Reset Even week to
  default" or "Reset Odd week to default" based on `_activeWeek`. Saves only
  the active week: `{ schedule_even: DEFAULT_SCHEDULE }` or
  `{ schedule_odd: DEFAULT_SCHEDULE }`. The other week's schedule is untouched.

### Claude's Discretion

- `getWeekParity()` helper: pure function, can live as a module-level export in
  `person-card.ts` or `global-settings-tab.ts`. Implementation:
  `Math.floor((Date.UTC(y, 0, 4) + (day - mon + 7) % 7 * 86400000) ...)`
  or simpler: use the same `isocalendar`-equivalent JS approach already used
  in Python backend (`date.isocalendar().week % 2`). In JS:
  use a lightweight ISO week computation. Parity: `weekNum % 2 === 0` → "even".
- Hint text below the week switcher: "Even weeks" and "Odd weeks" may benefit
  from a short `.schedule-hint` explaining which real dates are "even" (e.g.,
  the current week number). Claude's discretion on whether to include this.
- Schedule-type `<select>` visibility: only render when
  `currentMode === PRESENCE_MODE_SCHEDULED`. No schedule-type UI for other modes.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Primary Modification Target

- `frontend/src/components/person-card.ts` — Full source. The only file
  requiring significant changes. Adds: schedule-type `<select>`,
  `_activeWeek` state, Even/Odd CSS button tabs, dual memoized day arrays,
  updated `_onSchedulePeriodsChanged` and `_onResetSchedule`.

### Types (already updated in Phase 7 — read-only)

- `frontend/src/types.ts` lines 42–49 — `PersonConfig` interface with
  `schedule_type?: "single" | "even_odd"`, `schedule_even?`, `schedule_odd?`.
  No changes needed.

### Patterns to Follow

- `frontend/src/components/global-settings-tab.ts` — `programToDays()` /
  `dayIndexToKey()` helpers (exported), `_lastTimeProgram`/`_cachedDays`
  memoization pattern. Duplicate for even/odd pair.
- `frontend/src/main.ts` — CSS button tab pattern (`.tab-btn` / `.tab-btn.active`),
  `_setTab()` click handler. Even/Odd switcher uses the same CSS classes.
- `frontend/src/components/room-card.ts` — native `<select>` pattern with
  `.mode-select` class and auto-save on `@change`. Schedule-type select follows
  the same pattern.

### WS Client (no changes needed)

- `frontend/src/ws-client.ts` — `setPersonConfig(personId, partial)` already
  accepts any `Partial<PersonConfig>`. No new methods needed.

### Requirements & Roadmap

- `.planning/REQUIREMENTS.md` — SCHED-04 (the single requirement for this phase).
- `.planning/ROADMAP.md` — Phase 8 success criteria (4 observable behaviors).

### Prior Phase Context (backend decisions)

- `.planning/phases/07-even-odd-week-scheduling-backend/07-CONTEXT.md` —
  D-01 (backend seeds on switch), D-02 (even_odd→single preserves schedule),
  D-03 (extend set_person_config only). Frontend behavior relies on these.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `programToDays(schedule)` / `dayIndexToKey(index)` — exported from
  `global-settings-tab.ts`. Used as-is for `_daysEven` and `_daysOdd`.
- `_lastSchedule`/`_cachedDays` memoization pattern in `person-card.ts`
  lines 97–106. Clone for `_lastScheduleEven`/`_cachedDaysEven` and
  `_lastScheduleOdd`/`_cachedDaysOdd`.
- `.tab-btn` / `.tab-btn.active` CSS classes from `main.ts` — copy or import
  for the Even/Odd switcher buttons.
- `DEFAULT_SCHEDULE` constant (person-card.ts line 46) — reused for even/odd
  reset.
- `_onSchedulePeriodsChanged` handler pattern — adapts to send
  `schedule_even` or `schedule_odd` based on `_activeWeek`.

### Established Patterns

- **CSS button tabs (HA 2026.x):** `.tab-btn` + `.tab-btn.active` is the only
  working tab pattern. No `ha-tabs`. Even/Odd switcher follows this.
- **Native `<select>` for dropdowns (HA 2026.x):** `.mode-select` class with
  auto-save on `@change`. Schedule-type control follows this.
- **Auto-save on change:** All pickers fire WS call immediately → `reloadConfig()`
  → `showToast()`. Schedule-type change follows the same.
- **Memoized days array:** mandatory for time-bar — prevents drag-preview flicker
  on status re-renders. Two pairs needed for even/odd.

### Integration Points

- `person-card.ts` `render()` — extends the `isScheduled` conditional block to
  also render schedule-type select and (when even_odd) the week switcher.
- `_onSchedulePeriodsChanged` — needs to check `_activeWeek` to determine which
  field to update in the WS payload.
- `_onResetSchedule` — needs to check `schedule_type` and `_activeWeek` to
  determine the correct field and button label.

</code_context>

<specifics>
## Specific Ideas

- ISO week parity in JS: a simple `getISOWeekNumber(date)` helper returning
  `weekNum % 2 === 0 ? "even" : "odd"`. Can compute using
  `Math.round((date - new Date(date.getFullYear(), 0, 1)) / 86400000)` or
  a standard ISO week formula. The parity result is all that matters.
- Reset button label examples:
  - Single mode: `Reset to default`
  - Even/odd, Even tab: `Reset Even week to default`
  - Even/odd, Odd tab: `Reset Odd week to default`
- Even/Odd switcher CSS: scoped inside `PersonCard.styles`, not shared.
  The `.tab-btn` classes can be re-declared locally (4 lines) or the
  shared pattern can be extracted — Claude's discretion.

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)

- **"Rename 'ha' person presence mode to a clearer label in the UI"** —
  Already done in Phase 6 D-13. No action.
- **"Even/odd week presence scheduling for shared custody"** — THIS phase.
  Not deferred.
- **"Add multi-language support"** — deferred milestone item, out of scope.

</deferred>

---

*Phase: 8-Even/Odd Week Scheduling — Frontend*
*Context gathered: 2026-05-29*
