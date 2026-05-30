---
phase: 08-even-odd-week-scheduling-frontend
reviewed: 2026-05-30T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - frontend/src/components/person-card.ts
  - frontend/src/components/week-parity.test.ts
  - frontend/src/components/week-parity.ts
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-05-30
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files reviewed: the new `week-parity.ts` pure-function module, its
accompanying test file, and the updated `person-card.ts` component. The
`week-parity.ts` algorithm itself is mathematically correct for all tested
cases, matching the Python `isocalendar().week % 2` reference. One critical
correctness bug was found in `person-card.ts` — an async event handler calls
`stopPropagation()` after multiple `await` expressions, making the call a
guaranteed no-op. Three warnings cover a timezone-sensitive test suite, an
incomplete "has schedule" guard, and misleading toast copy. Two info items cover
encapsulation and silent error swallowing.

## Critical Issues

### CR-01: `stopPropagation()` placed after `await` — always a no-op

**File:** `frontend/src/components/person-card.ts:419`

**Issue:** `_onSchedulePeriodsChanged` is an `async` handler. It calls
`e.stopPropagation()` on line 419, but only after two `await` expressions
(lines 411 and 414). When the first `await` suspends the function, control
returns to the event dispatch mechanism. Because the `"periods-changed"` event
is emitted with `bubbles: true` and `composed: true` (confirmed in
`time-bar.ts:475-476`), it propagates across shadow DOM boundaries and up the
full ancestor chain before `stopPropagation()` is ever reached. By the time
the function resumes, propagation is complete; the call is a no-op.

Any ancestor element in the composed tree that listens for `"periods-changed"`
— including future listeners added during refactoring — will receive the event
unintentionally.

**Fix:** Move `stopPropagation()` to the top of the handler, before the first
`await`:

```typescript
private async _onSchedulePeriodsChanged(e: CustomEvent) {
  e.stopPropagation(); // Must precede all awaits to actually stop propagation
  const { dayIndex, periods } = e.detail as {
    dayIndex: number;
    periods: Period[];
  };
  // ... rest of handler unchanged
}
```

## Warnings

### WR-01: Test suite is timezone-sensitive — fails in UTC- timezones

**File:** `frontend/src/components/week-parity.test.ts:18-43`

**Issue:** Every test constructs dates via ISO string literals such as
`new Date("2026-05-25")`. Per the ECMAScript specification, ISO date-only
strings are parsed as **UTC midnight**, not local midnight. The
`getISOWeekNumber` function then reads the local-time fields `getFullYear()`,
`getMonth()`, and `getDate()` from the resulting `Date` object. In any UTC-
timezone (UTC-1 through UTC-12), those local fields return the **previous
calendar day**, causing `getISOWeekNumber` to compute a different week number
than the test asserts.

Concrete example: in UTC-5, `new Date("2026-05-25").getDate()` returns `24`
(May 24, not May 25). The algorithm then returns ISO week 21, but the test
asserts week 22, causing a failure.

This bug does not affect the production code path — `getWeekParity(new Date())`
uses the current local instant where `getFullYear/Month/Date` correctly reflect
the local date.

**Fix:** Construct test dates with the three-argument `Date` constructor, which
uses local time and is timezone-invariant:

```typescript
// Before (timezone-sensitive):
assert.equal(getISOWeekNumber(new Date("2026-05-25")), 22);

// After (timezone-safe):
assert.equal(getISOWeekNumber(new Date(2026, 4, 25)), 22); // May = month 4
```

Apply this change to all `new Date("YYYY-MM-DD")` calls in the test file
(lines 19, 23, 27, 31, 35, 39, 43, and the array on lines 48-53).

### WR-02: D-22 schedule-seed check ignores `schedule_even` / `schedule_odd`

**File:** `frontend/src/components/person-card.ts:313-315`

**Issue:** When the user switches to `"scheduled"` mode, the code seeds
`DEFAULT_SCHEDULE` only if `hasSchedule` is false. `hasSchedule` is computed
solely from `config.schedule` (the single-week field). If the person already
has data in `config.schedule_even` or `config.schedule_odd` (i.e., they
previously used even/odd mode), `hasSchedule` will be `false` (the single-week
field is absent), and `DEFAULT_SCHEDULE` will be written to `config.schedule`
anyway, overwriting nothing but wasting a backend round-trip and potentially
confusing future schedule type switches.

More importantly: if the intent is "don't seed when the person already has any
schedule data", the check should cover all three schedule fields.

**Fix:**

```typescript
const hasSchedule =
  (!!this.config?.schedule &&
    Object.values(this.config.schedule).some((day) => day.length > 0)) ||
  (!!this.config?.schedule_even &&
    Object.values(this.config.schedule_even).some((day) => day.length > 0)) ||
  (!!this.config?.schedule_odd &&
    Object.values(this.config.schedule_odd).some((day) => day.length > 0));
```

### WR-03: Toast copy says "retrying…" but no retry logic exists

**File:** `frontend/src/components/person-card.ts:328, 344, 359, 378, 417`

**Issue:** All five `catch` blocks display the toast message
`"Save failed — retrying..."` (or `"Reset failed — retrying..."`), but there
is no retry mechanism anywhere in the file. The user is given a false
expectation that the operation will be reattempted. If the backend is
temporarily unavailable, the change is silently lost with no indication to the
user that they need to act.

**Fix:** Either implement actual retry logic, or change the toast message to
accurately describe the failure:

```typescript
// Accurate without retry:
this.panel.showToast("Save failed — please try again", true);

// Or implement a simple single retry before showing the error.
```

## Info

### IN-01: `_expanded` @state is not declared `private`

**File:** `frontend/src/components/person-card.ts:98`

**Issue:** `@state() _expanded = false;` is missing the `private` access
modifier. Lit tracks state changes correctly regardless, but the missing
modifier allows parent components to read and set `_expanded` directly,
bypassing the collapse/expand logic (which also recalculates `_activeWeek`
in `updated()`). The underscore naming convention signals intent-to-be-private
but TypeScript does not enforce it without the keyword. `_activeWeek` on
line 101 correctly carries `private`.

**Fix:**

```typescript
@state() private _expanded = false;
```

### IN-02: All `catch` blocks swallow errors with no diagnostic logging

**File:** `frontend/src/components/person-card.ts:327, 343, 358, 377, 416`

**Issue:** Every `catch` block discards the caught error object entirely — the
error is not logged to the console or any diagnostic channel. When a save
silently fails in production, there is no way to diagnose the root cause from
browser DevTools. This compounds WR-03: the user sees a vague toast message and
the developer has no stacktrace.

**Fix:** Log the error before showing the toast:

```typescript
} catch (err) {
  console.error("[PersonCard] setPersonConfig failed:", err);
  this.panel.showToast("Save failed — please try again", true);
}
```

---

_Reviewed: 2026-05-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
