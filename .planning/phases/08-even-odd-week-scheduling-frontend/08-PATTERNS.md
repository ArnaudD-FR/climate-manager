# Phase 8: Even/Odd Week Scheduling — Frontend - Pattern Map

**Mapped:** 2026-05-29
**Files analyzed:** 1 (single-file modification)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/components/person-card.ts` | component | event-driven | `frontend/src/components/room-card.ts` | exact |

## Pattern Assignments

### `frontend/src/components/person-card.ts` (component, event-driven)

This is the only file modified. All changes are additions or replacements of
existing internal patterns. The file is read in full above — key patterns
extracted below by category.

---

#### A. Memoized Days Array (replicate twice for even/odd)

**Analog:** `frontend/src/components/person-card.ts` lines 95–106 (existing
`_days` getter) — also confirmed in `room-card.ts` lines 68–77.

**Existing pattern to clone** (person-card.ts lines 95–106):
```typescript
// Memoize days array — same pattern as global-settings-tab to prevent
// time-bar drag-preview from clearing on status-only re-renders.
private _lastSchedule: DailyProgram | undefined = undefined;
private _cachedDays: Period[][] = [];
private get _days(): Period[][] {
  const schedule = this.config?.schedule;
  if (schedule !== this._lastSchedule) {
    this._lastSchedule = schedule;
    this._cachedDays = programToDays(schedule);
  }
  return this._cachedDays;
}
```

**New pairs to add** (cloned from the above — one per week):
```typescript
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

**Place after:** the existing `_days` getter (line 106), before `connectedCallback`.

---

#### B. Local `@state()` for Active Week

**Analog:** `frontend/src/main.ts` `_activeTab` state (line 45) — local state
that drives tab rendering without server involvement.

**Pattern from main.ts** (line 45):
```typescript
@state() private _activeTab: string =
  localStorage.getItem("climate-manager-tab") ?? "global";
```

**New state for person-card** (NOT persisted to localStorage per D-10):
```typescript
@state() private _activeWeek: "even" | "odd" = "even";
```

This is initialized as `"even"` at declaration; the actual ISO-week-parity
value is set inside `connectedCallback()` (or `updated()` on `_expanded`
becoming true) using `getWeekParity(new Date())`.

**Place after:** `@state() _expanded = false;` (person-card.ts line 92).

---

#### C. `getWeekParity()` Module-Level Export

**Analog:** `frontend/src/components/global-settings-tab.ts` lines 53–61 —
module-level pure-function exports (`programToDays`, `dayIndexToKey`) that are
re-used by other components.

**Pattern from global-settings-tab.ts** (lines 53–61):
```typescript
/** Convert a DailyProgram into a 7-element Period[][] array. */
export function programToDays(
  program: DailyProgram | undefined,
): Period[][] {
  return DAY_KEYS.map((key) =>
    program?.[key] ? [...program[key]] : [],
  );
}

/** Convert a day index (0=Mon..6=Sun) back to a DailyProgram key. */
export function dayIndexToKey(
  index: number,
): keyof DailyProgram {
  return DAY_KEYS[index] ?? "mon";
}
```

**New helpers to add** at module level in person-card.ts (before the class):
```typescript
/** Return the ISO 8601 week number for a given date. */
export function getISOWeekNumber(date: Date): number {
  const d = new Date(
    Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()),
  );
  const dayNum = d.getUTCDay() || 7; // Sun=0 → treat as 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(
    ((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7,
  );
}

/** Return "even" or "odd" matching Python isocalendar().week % 2. */
export function getWeekParity(date: Date): "even" | "odd" {
  return getISOWeekNumber(date) % 2 === 0 ? "even" : "odd";
}
```

**Place after:** the `DEFAULT_SCHEDULE` constant block (person-card.ts line 74).

---

#### D. CSS Button Tab Switcher

**Analog:** `frontend/src/main.ts` lines 106–129 (`.tab-btn` / `.tab-btn.active`
CSS) and lines 381–398 (HTML template usage).

**CSS pattern from main.ts** (lines 106–129):
```typescript
.tab-btn {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 12px 16px;
  margin-bottom: -1px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--secondary-text-color);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  white-space: nowrap;
  outline: none;
  transition: color 0.15s;
}

.tab-btn.active {
  border-bottom-color: var(--primary-color);
  color: var(--primary-color);
}
```

**HTML template pattern from main.ts** (lines 381–398 — simplified excerpt):
```typescript
<button
  class="tab-btn ${this._activeTab === "global" ? "active" : ""}"
  @click=${() => this._setTab("global")}
>
  Overview
</button>
```

**New even/odd switcher in person-card** (scoped inside `PersonCard.styles`,
added to the existing `css\`...\`` block):
```typescript
// Inside static styles css`` block — add after existing .reset-btn:hover rule
.week-switcher {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}

.week-switcher .tab-btn {
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

.week-switcher .tab-btn.active {
  border-bottom-color: var(--primary-color);
  color: var(--primary-color);
}
```

**HTML template** (inside the `isScheduled` conditional block):
```typescript
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
```

---

#### E. Native `<select>` with Auto-Save

**Analog:** `frontend/src/components/person-card.ts` lines 399–425
(`_onModeChange` + mode select HTML) — confirmed also in `room-card.ts` same
pattern.

**Handler pattern from person-card.ts** (lines 244–266):
```typescript
private async _onModeChange(e: Event) {
  const newMode = (e.target as HTMLSelectElement).value;
  if (!newMode) return;
  try {
    // ... (some logic) ...
    await this.ws.setPersonConfig(this.personId, { mode: newMode });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

**HTML select pattern from person-card.ts** (lines 399–425):
```typescript
<div class="select-wrapper">
  <select class="mode-select" @change=${this._onModeChange}>
    <option
      value=${PRESENCE_MODE_SCHEDULED}
      ?selected=${currentMode === PRESENCE_MODE_SCHEDULED}
    >
      Scheduled
    </option>
    <!-- ... more options ... -->
  </select>
</div>
```

**New schedule-type handler** (copy + adapt — only inside `isScheduled` block):
```typescript
private async _onScheduleTypeChange(e: Event) {
  const newType = (e.target as HTMLSelectElement)
    .value as "single" | "even_odd";
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

**New schedule-type select HTML** (inside `isScheduled` conditional, before
the week-switcher):
```typescript
<div class="section-label">Schedule type</div>
<div class="select-wrapper">
  <select
    class="mode-select"
    @change=${this._onScheduleTypeChange}
  >
    <option
      value="single"
      ?selected=${scheduleType === "single"}
    >
      Single week
    </option>
    <option
      value="even_odd"
      ?selected=${scheduleType === "even_odd"}
    >
      Even / Odd weeks
    </option>
  </select>
</div>
```

Where `scheduleType` is a local render variable:
```typescript
const scheduleType =
  this.config?.schedule_type ?? "single";
const isEvenOdd = scheduleType === "even_odd";
```

---

#### F. `_onSchedulePeriodsChanged` — Adapted with Even/Odd Branching

**Analog:** `frontend/src/components/person-card.ts` lines 296–324 (existing
handler).

**Existing handler** (lines 296–324):
```typescript
private async _onSchedulePeriodsChanged(e: CustomEvent) {
  const { dayIndex, periods } = e.detail as {
    dayIndex: number;
    periods: Period[];
  };
  const currentSchedule = this.config.schedule ?? {
    mon: [], tue: [], wed: [], thu: [], fri: [], sat: [], sun: [],
  };
  const schedule: DailyProgram = { ...currentSchedule };
  const key = dayIndexToKey(dayIndex);
  schedule[key] = periods;
  try {
    await this.ws.setPersonConfig(this.personId, { schedule });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
  e.stopPropagation();
}
```

**Replacement** (adds even/odd branching per D-11, D-12):
```typescript
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
    ? this._activeWeek === "even"
      ? "schedule_even"
      : "schedule_odd"
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

---

#### G. `_onResetSchedule` — Adapted with Per-Week Logic

**Analog:** `frontend/src/components/person-card.ts` lines 284–294 (existing
handler).

**Existing handler** (lines 284–294):
```typescript
private async _onResetSchedule() {
  try {
    await this.ws.setPersonConfig(this.personId, {
      schedule: DEFAULT_SCHEDULE,
    });
    await this.panel.reloadConfig();
    this.panel.showToast("Reset to defaults", false);
  } catch {
    this.panel.showToast("Reset failed — retrying...", true);
  }
}
```

**Replacement** (adds per-week branching per D-14, D-15):
```typescript
private async _onResetSchedule() {
  const isEvenOdd =
    (this.config.schedule_type ?? "single") === "even_odd";
  const field = isEvenOdd
    ? this._activeWeek === "even"
      ? "schedule_even"
      : "schedule_odd"
    : "schedule";
  try {
    await this.ws.setPersonConfig(this.personId, {
      [field]: DEFAULT_SCHEDULE,
    });
    await this.panel.reloadConfig();
    this.panel.showToast("Reset done", false);
  } catch {
    this.panel.showToast("Reset failed — retrying...", true);
  }
}
```

**Reset button label** (computed in `render()` for template use):
```typescript
const resetLabel = isEvenOdd
  ? this._activeWeek === "even"
    ? "Reset Even week to default"
    : "Reset Odd week to default"
  : "Reset to default";
```

---

#### H. Time-Bar Wiring in `render()`

**Analog:** `frontend/src/components/person-card.ts` lines 488–509 (existing
`isScheduled` block).

**Existing time-bar binding** (lines 497–508):
```typescript
<div class="schedule-section">
  <climate-manager-time-bar
    mode="presence"
    .days=${this._days}
    @periods-changed=${this._onSchedulePeriodsChanged}
  ></climate-manager-time-bar>
</div>
<button
  class="reset-btn"
  @click=${() => void this._onResetSchedule()}
>
  Reset to default
</button>
```

**Replacement** (adds even/odd week selection):
```typescript
<div class="schedule-section">
  <climate-manager-time-bar
    mode="presence"
    .days=${isEvenOdd
      ? (this._activeWeek === "even"
        ? this._daysEven
        : this._daysOdd)
      : this._days}
    @periods-changed=${
      this._onSchedulePeriodsChanged}
  ></climate-manager-time-bar>
</div>
<button
  class="reset-btn"
  @click=${() => void this._onResetSchedule()}
>
  ${resetLabel}
</button>
```

---

#### I. `_activeWeek` Initialization on Card Expansion

**Analog:** `frontend/src/components/person-card.ts` lines 114–125 (`updated()`
lifecycle hook that reacts to `autoExpand`).

**Existing `updated()` hook** (lines 114–125):
```typescript
updated(changedProperties: PropertyValues) {
  if (changedProperties.has("autoExpand") && this.autoExpand) {
    this._expanded = true;
    setTimeout(() => {
      const rect = this.getBoundingClientRect();
      this.scrollIntoView({
        behavior: "smooth",
        block: rect.height <= window.innerHeight
          ? "nearest"
          : "start",
      });
    }, 0);
  }
}
```

**Extend** to recalculate `_activeWeek` when `_expanded` becomes true (D-09,
D-10 — recalculates from current date each time card expands, not persisted):
```typescript
updated(changedProperties: PropertyValues) {
  if (changedProperties.has("_expanded") && this._expanded) {
    this._activeWeek = getWeekParity(new Date());
  }
  if (changedProperties.has("autoExpand") && this.autoExpand) {
    this._expanded = true;
    setTimeout(() => {
      const rect = this.getBoundingClientRect();
      this.scrollIntoView({
        behavior: "smooth",
        block: rect.height <= window.innerHeight
          ? "nearest"
          : "start",
      });
    }, 0);
  }
}
```

---

## Shared Patterns

### Auto-Save + Reload + Toast
**Source:** `frontend/src/components/person-card.ts` (all save handlers, e.g.
lines 244–266, 284–294, 296–324).
**Apply to:** `_onScheduleTypeChange`, `_onSchedulePeriodsChanged`,
`_onResetSchedule`.

Pattern:
```typescript
try {
  await this.ws.setPersonConfig(this.personId, { /* delta */ });
  await this.panel.reloadConfig();
  this.panel.showToast("Saved", false);
} catch {
  this.panel.showToast("Save failed — retrying...", true);
}
```

### Native `<select>` Styling
**Source:** `frontend/src/shared-styles.ts` lines 98–119 (`selectStyles` export
with `.mode-select` class).
**Apply to:** Schedule-type `<select>` — reuses existing `.mode-select` class
already imported in `person-card.ts` (line 31).

### Section Label
**Source:** `frontend/src/shared-styles.ts` lines 86–95 (`sectionLabelStyles`
export with `.section-label` class).
**Apply to:** "Schedule type" label above the new `<select>`. Already imported
in `person-card.ts` (line 30).

### Shared-Styles Imports (already present — no changes)
**Source:** `frontend/src/components/person-card.ts` lines 29–34.
```typescript
import {
  chipStyles,
  sectionLabelStyles,
  selectStyles,
  expandIconStyles,
  scheduleHintStyles,
} from "../shared-styles.js";
```
All needed style tokens (`selectStyles`, `sectionLabelStyles`,
`scheduleHintStyles`) are already imported — no new imports required.

### `programToDays` / `dayIndexToKey` Imports (already present — no changes)
**Source:** `frontend/src/components/person-card.ts` line 27.
```typescript
import { programToDays, dayIndexToKey }
  from "./global-settings-tab.js";
```

### TypeScript Types (already updated in Phase 7 — no changes)
**Source:** `frontend/src/types.ts` lines 42–50.
```typescript
export interface PersonConfig {
  mode?: string;
  room_ids?: string[];
  schedule?: DailyProgram;
  // Phase 7: even/odd week scheduling (SCHED-01, SCHED-03)
  schedule_type?: "single" | "even_odd";
  schedule_even?: DailyProgram;
  schedule_odd?: DailyProgram;
}
```

### `setPersonConfig` Signature (no changes)
**Source:** `frontend/src/ws-client.ts` lines 178–187.
```typescript
setPersonConfig(
  personId: string,
  config: Partial<PersonConfig>,
): Promise<{ success: boolean }>
```
Accepts any `Partial<PersonConfig>` — the new `schedule_type`, `schedule_even`,
`schedule_odd` fields flow through without any ws-client changes.

---

## No Analog Found

None. All patterns required exist verbatim in the codebase. The ISO week parity
helper is standard ISO 8601 — no novel algorithm needed.

---

## Render Template Integration Map

Full layout of the `isScheduled` conditional block after all changes (showing
insertion order per D-07):

```
isScheduled ? html`
  1. "Presence schedule" section-label  [EXISTING — line 491]
  2. "Schedule type" section-label      [NEW — D-03]
  3. schedule-type <select>             [NEW — D-02, D-01]
  4. week-switcher div (if isEvenOdd)   [NEW — D-06, D-07, D-08]
       [Even btn] [Odd btn]
  5. .schedule-section + time-bar       [MODIFIED — D-11, D-12]
       .days=${isEvenOdd ? (even/odd) : this._days}
  6. reset-btn                          [MODIFIED — D-14, D-15]
       label=${resetLabel}
` : ""
```

---

## Metadata

**Analog search scope:** `frontend/src/` (all component and utility files)
**Files scanned:** 6
(`person-card.ts`, `main.ts`, `global-settings-tab.ts`, `room-card.ts`,
`shared-styles.ts`, `ws-client.ts`)
**Pattern extraction date:** 2026-05-29
