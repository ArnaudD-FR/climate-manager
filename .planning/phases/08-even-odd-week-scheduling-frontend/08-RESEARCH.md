# Phase 8: Even/Odd Week Scheduling — Frontend - Research

**Researched:** 2026-05-29
**Domain:** Lit 3 component modification — person-card.ts UI extension
**Confidence:** HIGH

## Summary

Phase 8 is a focused UI extension to a single component: `person-card.ts`. All
the backend plumbing (storage schema, evaluator logic, WebSocket protocol) was
completed in Phase 7 and is live. This phase wires the frontend: a schedule-type
`<select>` that appears in Scheduled mode, an Even/Odd CSS button-tab switcher
that appears when `schedule_type === "even_odd"`, dual memoized day-arrays for
the two week schedules, and an updated reset button whose label and target field
vary by active week.

All patterns required for this work already exist in the codebase. Nothing is
greenfield — this is adaptation of established patterns (memoized days, native
`<select>`, CSS button tabs) to a new conditional block inside an existing
`render()` method. No new WebSocket commands, no TypeScript type changes, no new
files.

The only discretionary decision is placement of `getWeekParity()`: a pure
ISO-week-number helper that the CONTEXT.md allows to live in `person-card.ts`
as a module-level export. The backend implementation (`week % 2 === 0` → even)
is the verified reference — the JS equivalent must match exactly.

**Primary recommendation:** Implement all changes inside `person-card.ts`.
Follow established patterns verbatim — memoization, native `<select>`,
`.tab-btn`/`.tab-btn.active`, auto-save on change. Add `getWeekParity()` as a
module-level export for testability.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Schedule-Type Control (SCHED-04)**
- D-01: Control lives inside the schedule section, just above the Even/Odd
  switcher (before the time-bar). Visible only when `mode === "scheduled"`.
- D-02: Native `<select>` with two options — "Single week" / "Even / Odd weeks".
- D-03: Section label above the `<select>`: "Schedule type".
- D-04: On change to "Even / Odd weeks": send
  `setPersonConfig(personId, { schedule_type: "even_odd" })`. No schedule
  payload — backend seeds from existing `schedule` automatically (Phase 7 D-01).
- D-05: On change to "Single week": send
  `setPersonConfig(personId, { schedule_type: "single" })`. Frontend reverts
  to single time-bar.

**Week-Switcher Toggle**
- D-06: CSS button tabs — `[Even] [Odd]` with `.tab-btn`/`.tab-btn.active`
  classes (same pattern as `main.ts` tab bar).
- D-07: Position: section label → `[Even] [Odd]` switcher → time-bar → reset
  button.
- D-08: Switcher only rendered when `schedule_type === "even_odd"`.

**Default Active Week**
- D-09: Default active week determined by current ISO week parity:
  `getWeekParity()` → `"even"` or `"odd"`. Even ISO week number → "Even" tab.
- D-10: `_activeWeek` is local `@state()` — not persisted to localStorage.
  Recalculates each time the card expands.

**Time-Bar Wiring**
- D-11: `_activeWeek === "even"` → time-bar receives `_daysEven`; saves
  `{ schedule_even: updatedSchedule }`.
- D-12: `_activeWeek === "odd"` → time-bar receives `_daysOdd`; saves
  `{ schedule_odd: updatedSchedule }`.
- D-13: Two additional memoization pairs: `_lastScheduleEven`/`_cachedDaysEven`
  and `_lastScheduleOdd`/`_cachedDaysOdd`, same pattern as existing
  `_lastSchedule`/`_cachedDays`.

**Reset Button**
- D-14: Single mode: label "Reset to default", saves `{ schedule: DEFAULT_SCHEDULE }`.
- D-15: Even/odd mode: dynamic label — "Reset Even week to default" or "Reset
  Odd week to default" based on `_activeWeek`. Saves only the active week's
  schedule field; the other week is untouched.

### Claude's Discretion

- `getWeekParity()` helper: pure function, module-level export in
  `person-card.ts`. Implementation must match backend parity: ISO week number
  % 2 === 0 → "even", else "odd".
- Hint text below the week switcher: may include a `.schedule-hint` showing the
  current week number. Claude's discretion.
- Schedule-type `<select>` visibility: only render when
  `currentMode === PRESENCE_MODE_SCHEDULED`.
- Even/Odd switcher CSS: scoped inside `PersonCard.styles` — re-declare `.tab-btn`
  locally or extract; Claude's discretion.

### Deferred Ideas (OUT OF SCOPE)

- Multi-language support — deferred milestone item.
- Backend evaluator — Phase 7, complete.
- New WebSocket commands — none needed.
- TypeScript type changes — done in Phase 7.
- TRV calibration — Phase 9.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCHED-04 | The persons UI shows a week-switcher toggle (Even/Odd) in the presence time-bar only when `schedule_type == "even_odd"`; editing affects only the selected week's schedule | All decisions in CONTEXT.md directly address this. Implementation is adaptation of existing patterns in `person-card.ts`. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schedule-type `<select>` | Browser/Client (person-card.ts) | — | Pure UI control; sends WS payload on change |
| Even/Odd tab switcher | Browser/Client (person-card.ts) | — | Local `@state()` — no server involvement |
| Time-bar week scoping | Browser/Client (person-card.ts) | — | Chooses which memoized days array to pass to time-bar |
| ISO week parity calculation | Browser/Client (getWeekParity()) | — | Pure JS computation matching backend Python logic |
| Schedule persistence | API/Backend (Phase 7 complete) | — | `set_person_config` WebSocket already handles even/odd fields |

## Standard Stack

This phase adds no new packages. All dependencies are already installed.

### Core (existing — no changes)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| Lit | ^3 | Web component framework — LitElement, html, css | Installed |
| TypeScript | ^5 | Type-safe component authoring | Installed |
| Vite | ^5 | Build tool — single-file panel.js output | Installed |

### Supporting (existing — no changes)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| home-assistant-js-websocket | latest | WS client — not touched in this phase | Installed |

### No New Packages
This phase is a pure UI modification of an existing component. No npm installs
are required. The Package Legitimacy Gate is not applicable.

## Package Legitimacy Audit

No packages are installed in this phase. Audit: not applicable.

## Architecture Patterns

### System Architecture Diagram

```
PersonCard.render()
  └─ isScheduled conditional block
       ├─ [existing] Presence mode <select>
       ├─ [NEW] Schedule type <select>  ─── @change ──► _onScheduleTypeChange()
       │                                                    └─► setPersonConfig({schedule_type})
       │                                                    └─► reloadConfig()
       │
       ├─ [NEW, if even_odd] Even/Odd tab switcher
       │    [Even btn] [Odd btn]          ─── @click ──► _activeWeek = "even"|"odd"
       │
       └─ time-bar ◄─────── _daysEven or _daysOdd (via _activeWeek)
            │
            └─ @periods-changed ──► _onSchedulePeriodsChanged()
                                        └─► setPersonConfig({schedule_even|schedule_odd})
                                        └─► reloadConfig()

Memoization:
  _lastScheduleEven / _cachedDaysEven  (programToDays(config.schedule_even))
  _lastScheduleOdd  / _cachedDaysOdd   (programToDays(config.schedule_odd))
  [existing] _lastSchedule / _cachedDays (unchanged, used in single mode)

Reset button:
  single mode    → label "Reset to default"
                 → saves { schedule: DEFAULT_SCHEDULE }
  even/odd mode → label "Reset Even/Odd week to default"
                 → saves { schedule_even|schedule_odd: DEFAULT_SCHEDULE }
```

### Recommended Project Structure

No structural changes. All work is within:

```
frontend/src/
└── components/
    └── person-card.ts    ← only file modified
```

### Pattern 1: Memoized Days Array (existing — replicate twice)

**What:** Prevents time-bar drag-preview flicker when status-only re-renders
pass a new array reference to the time-bar.

**When to use:** Every time-bar prop must go through a memoized getter.

```typescript
// Source: person-card.ts lines 97–106 (existing _days getter)
private _lastScheduleEven: DailyProgram | undefined = undefined;
private _cachedDaysEven: Period[][] = [];
private get _daysEven(): Period[][] {
  const schedule = this.config?.schedule_even;
  if (schedule !== this._lastScheduleEven) {
    this._lastScheduleEven = schedule;
    this._cachedDaysEven = programToDays(schedule);
  }
  return this._cachedDaysEven;
}

private _lastScheduleOdd: DailyProgram | undefined = undefined;
private _cachedDaysOdd: Period[][] = [];
private get _daysOdd(): Period[][] {
  const schedule = this.config?.schedule_odd;
  if (schedule !== this._lastScheduleOdd) {
    this._lastScheduleOdd = schedule;
    this._cachedDaysOdd = programToDays(schedule);
  }
  return this._cachedDaysOdd;
}
```

**[VERIFIED: codebase]** — Pattern confirmed in `person-card.ts` lines 97–106
and `room-card.ts` lines 68–77.

### Pattern 2: Native `<select>` with Auto-Save (existing)

**What:** Native `<select>` with `.mode-select` class, fires WS call immediately
on `@change`, then `reloadConfig()` + `showToast()`.

```typescript
// Source: person-card.ts _onModeChange pattern
private async _onScheduleTypeChange(e: Event) {
  const newType = (e.target as HTMLSelectElement).value as
    "single" | "even_odd";
  try {
    await this.ws.setPersonConfig(this.personId, {
      schedule_type: newType,
    });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

**[VERIFIED: codebase]** — Pattern confirmed in `person-card.ts` `_onModeChange`
and `room-card.ts`.

### Pattern 3: CSS Button Tab Switcher (existing)

**What:** Two `<button>` elements with `.tab-btn` / `.tab-btn.active` classes.
Active state toggled by local `@state()`.

```typescript
// Source: main.ts tab-bar implementation
// HTML template fragment:
html`
  <div class="week-switcher">
    <button
      class="tab-btn ${this._activeWeek === "even" ? "active" : ""}"
      @click=${() => { this._activeWeek = "even"; }}
    >Even</button>
    <button
      class="tab-btn ${this._activeWeek === "odd" ? "active" : ""}"
      @click=${() => { this._activeWeek = "odd"; }}
    >Odd</button>
  </div>
`
```

**CSS (scoped to PersonCard.styles):**
```css
.week-switcher {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}

.tab-btn {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--secondary-text-color);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-family: inherit;
  outline: none;
}

.tab-btn.active {
  border-bottom-color: var(--primary-color);
  color: var(--primary-color);
}
```

**[VERIFIED: codebase]** — Pattern confirmed in `main.ts` lines 106–129.

### Pattern 4: ISO Week Parity Helper

**What:** Pure function computing ISO week number and returning parity as
`"even" | "odd"`. Must match backend Python: `date.isocalendar().week % 2 === 0`
→ "even".

**Backend reference (Python):**
```python
# schedule.py lines 156–157 [VERIFIED: codebase]
week_parity = now.date().isocalendar().week % 2
schedule_key = "schedule_even" if week_parity == 0 else "schedule_odd"
```

**JS equivalent:**
```typescript
// Source: standard ISO week algorithm, consistent with Python isocalendar()
export function getISOWeekNumber(date: Date): number {
  const d = new Date(
    Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())
  );
  // ISO week: Thursday is the pivot day (ISO 8601)
  const dayNum = d.getUTCDay() || 7; // Sun=0 → 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(
    ((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7
  );
}

export function getWeekParity(date: Date): "even" | "odd" {
  return getISOWeekNumber(date) % 2 === 0 ? "even" : "odd";
}
```

**[ASSUMED]** — The ISO week algorithm is standard and well-established, but
this specific JS implementation has not been run against the Python backend for
equality verification. The parity logic (% 2 === 0 → "even") is
**[VERIFIED: codebase]** from `schedule.py` lines 156–157. The JS ISO week
algorithm is canonical (ISO 8601) and matches Python's `isocalendar()`.

**Known boundary limitation (WR-03, documented in Phase 7):** In years with
ISO week 53 (e.g. 2026, 2032), week 53 and the following week 1 are both "odd"
— two consecutive odd weeks, one skipped even week. This is accepted for v1.
Frontend inherits the same limitation by using the identical parity logic.

### Anti-Patterns to Avoid

- **Calling `programToDays()` directly in `render()`:** Creates a new array
  reference on every re-render → time-bar drag-preview flickers. Always use
  the memoized getter pattern.
- **Using `ha-tabs` or `paper-tab`:** Removed in HA 2026.x. Only CSS button
  tabs work. [VERIFIED: MEMORY.md]
- **Using `ha-select`:** Broken in HA 2026.x (no `.items` API). Only native
  `<select>` works. [VERIFIED: MEMORY.md]
- **Persisting `_activeWeek` to localStorage:** CONTEXT.md D-10 explicitly
  prohibits this. Recalculate from current date on each card expansion.
- **Sending both `schedule_even` AND `schedule_odd` on a single edit:** Each
  time-bar interaction sends only the active week's field. The other week must
  not be touched.
- **Line length violation:** TypeScript/JS files must stay within 80 chars per
  `.editorconfig`. Long template literals must be broken across lines.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ISO week number | Custom date arithmetic | Standard ISO 8601 algorithm | Week 53, leap year, year-boundary edge cases are already documented and accepted |
| Tab switcher CSS | New CSS classes | `.tab-btn`/`.tab-btn.active` from main.ts | Consistent with established HA 2026.x pattern in codebase |
| Schedule type select | New UI pattern | Native `<select>` with `.mode-select` | Already styled; consistent with all other dropdowns in the panel |
| Days array conversion | Inline loop | `programToDays()` from `global-settings-tab.ts` | Already exported; handles undefined/empty gracefully |

## Common Pitfalls

### Pitfall 1: Memoization Reference Equality

**What goes wrong:** `programToDays()` is called inside `render()` directly
(not via getter). On every status push, a new array reference is passed to the
time-bar. The time-bar's `updated()` hook sees a changed `days` prop and clears
`_dragPreviewDays`, causing the segment being dragged to snap back.

**Why it happens:** Status pushes arrive during long drag operations. Without
memoization, `days` is a new object every render even if the schedule data
hasn't changed.

**How to avoid:** Always use the private getter pattern with `_lastScheduleX`
identity comparison. This is the established pattern in `person-card.ts` (lines
97–106) and `room-card.ts` (lines 68–77).

**Warning signs:** Time-bar segments visibly snap or flicker during drag.

### Pitfall 2: Schedule Type Cleared on Mode Mismatch

**What goes wrong:** The schedule-type `<select>` is rendered outside the
`isScheduled` conditional and changes `schedule_type` for non-scheduled persons.

**Why it happens:** Template structure error — UI block placed at wrong nesting
depth.

**How to avoid:** D-01 is explicit — schedule-type UI renders only inside the
`isScheduled` conditional block, alongside the time-bar.

**Warning signs:** Schedule-type selector visible when Presence mode is "HA
home tracking" or "Force Present/Absent".

### Pitfall 3: Even/Odd State Lost on Tab Switch

**What goes wrong:** Switching between "Even" and "Odd" tabs triggers
`reloadConfig()`, which replaces `this.config` and resets `_activeWeek` if it
is derived from config rather than being independent local state.

**Why it happens:** Conflating server-derived state with local UI state.

**How to avoid:** `_activeWeek` is `@state()` local to the component —
D-10 explicitly prohibits localStorage persistence. It is NOT reset by
`reloadConfig()` because it is a component state property, not a config-derived
computed value. Only card expansion recalculates it.

**Warning signs:** Clicking "Odd" tab causes it to immediately revert to "Even".

### Pitfall 4: Wrong Field Sent on Schedule Edit

**What goes wrong:** `_onSchedulePeriodsChanged` sends `{ schedule: ... }`
instead of `{ schedule_even: ... }` or `{ schedule_odd: ... }` for an even/odd
person.

**Why it happens:** Copy-paste of the existing handler without adapting the
field name.

**How to avoid:** The handler must branch on `schedule_type` AND `_activeWeek`:

```typescript
const isEvenOdd =
  (this.config.schedule_type ?? "single") === "even_odd";
const field = isEvenOdd
  ? this._activeWeek === "even"
    ? "schedule_even"
    : "schedule_odd"
  : "schedule";
await this.ws.setPersonConfig(this.personId, { [field]: schedule });
```

**Warning signs:** Edits to Even week appear to change both weeks identically
(because the backend falls back to `schedule` which is unchanged).

### Pitfall 5: Reset Touches Wrong Week

**What goes wrong:** `_onResetSchedule` resets both `schedule_even` AND
`schedule_odd` when user clicks reset in even/odd mode.

**Why it happens:** Handler sends a combined payload without checking
`_activeWeek`.

**How to avoid:** D-15 is explicit — reset saves only the active week's
field. The other week is untouched. Same branching logic as Pitfall 4.

### Pitfall 6: 80-Character Line Length Violation

**What goes wrong:** Long Lit template literals or method chains exceed the
80-character limit, causing `make lint` (editorconfig pre-commit hook) to fail.

**Why it happens:** Lit HTML template strings can easily exceed 80 chars when
nesting class expressions with ternaries.

**How to avoid:** Break template lines at attribute boundaries. Use intermediate
variables for class strings:

```typescript
const weekCls = (w: "even" | "odd") =>
  `tab-btn ${this._activeWeek === w ? "active" : ""}`;
```

## Code Examples

### Updated `_onSchedulePeriodsChanged` with even/odd branching

```typescript
// Verified pattern: adapts existing handler for even/odd wiring
private async _onSchedulePeriodsChanged(e: CustomEvent) {
  const { dayIndex, periods } = e.detail as {
    dayIndex: number;
    periods: Period[];
  };
  const isEvenOdd =
    (this.config.schedule_type ?? "single") === "even_odd";
  const activeSchedule = isEvenOdd
    ? this._activeWeek === "even"
      ? this.config.schedule_even
      : this.config.schedule_odd
    : this.config.schedule;
  const base: DailyProgram = activeSchedule ?? {
    mon: [], tue: [], wed: [], thu: [], fri: [], sat: [], sun: [],
  };
  const updated: DailyProgram = { ...base };
  updated[dayIndexToKey(dayIndex)] = periods;
  const field = isEvenOdd
    ? this._activeWeek === "even" ? "schedule_even" : "schedule_odd"
    : "schedule";
  try {
    await this.ws.setPersonConfig(this.personId, {
      [field]: updated,
    });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
  e.stopPropagation();
}
```

### Updated `_onResetSchedule` with per-week logic

```typescript
// D-14, D-15: reset only the active week's schedule
private async _onResetSchedule() {
  const isEvenOdd =
    (this.config.schedule_type ?? "single") === "even_odd";
  const field = isEvenOdd
    ? this._activeWeek === "even" ? "schedule_even" : "schedule_odd"
    : "schedule";
  const label = isEvenOdd
    ? this._activeWeek === "even"
      ? "Reset Even week to default"
      : "Reset Odd week to default"
    : "Reset to default";
  try {
    await this.ws.setPersonConfig(this.personId, {
      [field]: DEFAULT_SCHEDULE,
    });
    await this.panel.reloadConfig();
    this.panel.showToast(label + " — done", false);
  } catch {
    this.panel.showToast("Reset failed — retrying...", true);
  }
}
```

### Schedule section HTML template (full even/odd block)

```typescript
// Layout order: section label → schedule-type select → switcher → time-bar
// → reset button
html`
  <div class="section-label"
    title="When this person is considered present">
    Presence schedule
  </div>

  <!-- D-01..D-03: schedule-type select, only in Scheduled mode -->
  <div class="section-label">Schedule type</div>
  <div class="select-wrapper">
    <select class="mode-select"
      @change=${this._onScheduleTypeChange}>
      <option value="single"
        ?selected=${scheduleType === "single"}>
        Single week
      </option>
      <option value="even_odd"
        ?selected=${scheduleType === "even_odd"}>
        Even / Odd weeks
      </option>
    </select>
  </div>

  <!-- D-06..D-08: week switcher, only when even_odd -->
  ${isEvenOdd ? html`
    <div class="week-switcher">
      <button
        class="tab-btn ${
          this._activeWeek === "even" ? "active" : ""}"
        @click=${() => { this._activeWeek = "even"; }}
      >Even</button>
      <button
        class="tab-btn ${
          this._activeWeek === "odd" ? "active" : ""}"
        @click=${() => { this._activeWeek = "odd"; }}
      >Odd</button>
    </div>
  ` : ""}

  <!-- time-bar: active week's days array -->
  <div class="schedule-section">
    <climate-manager-time-bar
      mode="presence"
      .days=${isEvenOdd
        ? (this._activeWeek === "even"
          ? this._daysEven : this._daysOdd)
        : this._days}
      @periods-changed=${this._onSchedulePeriodsChanged}
    ></climate-manager-time-bar>
  </div>

  <!-- D-14..D-15: dynamic reset button -->
  <button class="reset-btn"
    @click=${() => void this._onResetSchedule()}>
    ${resetLabel}
  </button>
`
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ha-tabs` / `paper-tab` | CSS button tabs | HA 2026.x | Must use `.tab-btn` pattern |
| `ha-select` | Native `<select>` | HA 2026.x | Must use HTML select element |
| `ha-textfield` | Native `<input>` | HA 2026.x | Not relevant to this phase |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | JS ISO week algorithm produces same week numbers as Python `isocalendar().week` for all dates | Code Examples (getISOWeekNumber) | Even/odd parity mismatch between frontend display and backend evaluation — user sees wrong week highlighted |

**Mitigation for A1:** The ISO 8601 week algorithm used is canonical and Python's
`isocalendar()` also implements ISO 8601. The risk is theoretical. A manual
cross-check against a known date (e.g., 2026-W22 = week 22 = even) is
recommended in the plan's verification step.

## Open Questions

1. **`getWeekParity` placement**
   - What we know: CONTEXT.md allows it in `person-card.ts` or
     `global-settings-tab.ts`
   - What's unclear: Whether it will be needed by other future components (e.g.,
     a schedule status display in the overview tab)
   - Recommendation: Place as a module-level export in `person-card.ts` for now.
     Easy to move to a `utils.ts` file later if needed.

2. **Schedule hint below week switcher**
   - What we know: CONTEXT.md marks this as Claude's discretion
   - What's unclear: Whether a hint like "Week 22 — currently Even" adds value
     or clutters the UI
   - Recommendation: Include a minimal hint showing current ISO week number so
     the user can verify the active week without counting manually.

## Environment Availability

Step 2.6: No external dependencies beyond what is already installed. This phase
modifies one TypeScript file and rebuilds using the existing Vite setup.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | `make build` | Assumed present | — | — |
| Vite | Frontend build | Installed in `frontend/node_modules` | ^5 | — |
| TypeScript | Type checking | Installed in `frontend/node_modules` | ^5 | — |

Build command: `make build` (runs `cd frontend && npm run build`)
Deploy command: `make deploy` (builds then scp + HA restart)

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python backend tests only) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `.venv/bin/python -m pytest tests/ -v -k "schedule"` |
| Full suite command | `.venv/bin/python -m pytest tests/ -v` |

### Notes on Frontend Testing

There is no automated frontend test harness in this project. The frontend is
validated via:

1. `make build` — TypeScript compilation catches type errors
2. `make deploy` — Live HA instance integration test
3. Manual verification against ROADMAP.md success criteria

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHED-04 | Schedule-type select appears only in Scheduled mode | manual | — | N/A |
| SCHED-04 | Even/Odd switcher absent for single-schedule persons | manual | — | N/A |
| SCHED-04 | Even/Odd switcher present for even_odd persons | manual | — | N/A |
| SCHED-04 | Time-bar edits in Even tab save to `schedule_even` | manual | — | N/A |
| SCHED-04 | Time-bar edits in Odd tab save to `schedule_odd` | manual | — | N/A |
| SCHED-04 | Switching Even/Odd tabs redraws time-bar; other week retained | manual | — | N/A |
| SCHED-04 | Changes persist after panel reload | manual | — | N/A |

**Frontend tests are manual-only** — no test framework is wired for the Lit
component layer. The plan should include a verification wave with explicit
manual test steps.

**Python backend tests (existing):** `tests/test_schedule.py` covers the
even/odd evaluator (SCHED-02). These are not affected by this phase but serve
as a confidence check that the backend is correct.

### Wave 0 Gaps

None — no new test infrastructure needed. The existing `tests/` suite is
unaffected by this frontend-only change.

## Security Domain

This phase adds UI controls that call `setPersonConfig` (an existing authenticated
WebSocket command). No new attack surface is introduced.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | WebSocket auth handled by HA (existing) |
| V5 Input Validation | minimal | `schedule_type` is a string constrained to `"single"\|"even_odd"` by TypeScript types |
| V6 Cryptography | no | — |

## Sources

### Primary (HIGH confidence)
- `frontend/src/components/person-card.ts` — Full source read. Memoization
  pattern, `_onModeChange`, `_onResetSchedule`, `_onSchedulePeriodsChanged`,
  `DEFAULT_SCHEDULE`, existing state/property layout. [VERIFIED: codebase]
- `frontend/src/main.ts` — CSS `.tab-btn`/`.tab-btn.active` pattern,
  `_setTab()` handler. [VERIFIED: codebase]
- `frontend/src/types.ts` lines 42–49 — `PersonConfig` interface with
  `schedule_type`, `schedule_even`, `schedule_odd`. [VERIFIED: codebase]
- `frontend/src/components/global-settings-tab.ts` lines 39–82 —
  `programToDays()`, `dayIndexToKey()` exports, memoization pattern.
  [VERIFIED: codebase]
- `frontend/src/components/room-card.ts` — native `<select>` with
  `.mode-select`, `_lastTimeProgram`/`_cachedDays` pattern. [VERIFIED: codebase]
- `frontend/src/ws-client.ts` — `setPersonConfig(personId, Partial<PersonConfig>)`.
  [VERIFIED: codebase]
- `frontend/src/shared-styles.ts` — `selectStyles`, `scheduleHintStyles`,
  `sectionLabelStyles` exports. [VERIFIED: codebase]
- `custom_components/climate_manager/schedule.py` lines 146–160 — Backend
  even/odd parity: `week % 2 === 0 → "even"`. [VERIFIED: codebase]
- `MEMORY.md` — HA 2026.x broken components (`ha-select`, `ha-tabs`,
  `ha-textfield`). [VERIFIED: project memory]
- `.editorconfig` — 80-char line limit for TS/JS. [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- None required — all research is codebase-internal.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; existing dependencies confirmed
- Architecture: HIGH — single file modification, all patterns verified in codebase
- Pitfalls: HIGH — drawn from actual code structure and established HA 2026.x
  memory entries
- ISO week algorithm: MEDIUM — standard ISO 8601, but JS-Python equality not
  explicitly tested

**Research date:** 2026-05-29
**Valid until:** Stable (no external dependencies; validity tied to HA version
staying at 2026.x)
