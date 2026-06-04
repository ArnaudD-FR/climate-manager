---
phase: 10-presence-mode-ui
reviewed: 2026-06-01T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - frontend/src/components/presence-mode.ts
  - frontend/src/components/presence-mode.test.ts
  - frontend/src/components/person-card.ts
  - frontend/src/components/persons-tab.ts
findings:
  critical: 3
  warning: 2
  info: 2
  total: 7
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-06-01
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 10 added presence-mode UI helpers (`presence-mode.ts`), unit tests for
them (`presence-mode.test.ts`), and wired those helpers into the two Lit
components (`person-card.ts`, `persons-tab.ts`). The helper module itself is
well-structured and correct for its intended contract. However, there is a
three-way inconsistency between the helper contract, the tests, and the Lit
component that constitutes the most serious defect cluster in this phase.

The core problem: `shouldShowHaOption` in `presence-mode.ts` unconditionally
returns `true` (the "ha" option is always shown), but:

1. The test asserts it returns `false` when `hasDeviceTrackers` is `false` —
   this test **fails right now** (verified by running the suite).
2. `person-card.ts` never calls `shouldShowHaOption` at all — it renders the
   "ha" option unconditionally, which matches the implementation but contradicts
   both the plan spec (D-04) and the test expectations.
3. The plan spec for D-04 ("ha option always shown; ⚠ appended when no
   trackers") is internally consistent with the implementation, but the test
   file documents the opposite behaviour ("ha option visible only when device
   trackers exist").

One of these three must be wrong; the current state has two contradictory
contracts and one failing test. Without a deliberate decision being recorded,
this will silently regress across future changes.

---

## Critical Issues

### CR-01: Test asserts `shouldShowHaOption(false) === false`, but the function
returns `true` — test suite exits non-zero

**File:** `frontend/src/components/presence-mode.test.ts:45-47`
**Issue:** The test at line 45 asserts `shouldShowHaOption(false)` equals
`false`, but `shouldShowHaOption` is implemented as `return true` regardless of
its argument. Running the suite produces:

```
✖ UI-01: shouldShowHaOption returns false when no trackers
  AssertionError: true !== false
```

Exit code is 1. Any CI gate that runs
`node --test --experimental-strip-types` on this file will fail. This is a
shipped broken test — either the test is wrong (if the design intent is "always
show") or the implementation is wrong (if the intent is "hide when no
trackers").

**Fix (option A — "always show" design wins):** Remove the failing test and
update the test comment at line 44 to reflect the actual invariant:

```typescript
// UI-01: D-04 — ha option always rendered; ⚠ label appended when no trackers
test("UI-01: shouldShowHaOption always returns true", () => {
  assert.equal(shouldShowHaOption(false), true);
  assert.equal(shouldShowHaOption(true), true);
});
```

**Fix (option B — "hide when no trackers" design wins):** Change the
implementation in `presence-mode.ts` line 41-43:

```typescript
export function shouldShowHaOption(hasDeviceTrackers: boolean): boolean {
  return hasDeviceTrackers;
}
```

And update `person-card.ts` to actually call the guard (see CR-02).

---

### CR-02: `person-card.ts` never calls `shouldShowHaOption` — the conditional
option guard from D-04/UI-01 is missing from the component

**File:** `frontend/src/components/person-card.ts:607-612`
**Issue:** The Phase 10 plan spec (D-04 in `10-02-PLAN.md`) requires the "ha"
`<option>` to be wrapped in `shouldShowHaOption(this.hasDeviceTrackers)`. The
acceptance criteria in the plan explicitly state:

> "The ha `<option>` is wrapped in `shouldShowHaOption(this.hasDeviceTrackers)`
> guard (grep finds `shouldShowHaOption` adjacent to the option block)"

The component imports only `haOptionLabel` and `presenceModeHint` from
`presence-mode.js` (line 85). `shouldShowHaOption` is imported in neither the
component nor re-exported, and the option is rendered unconditionally:

```typescript
<option
  value=${PRESENCE_MODE_HA}
  ?selected=${currentMode === PRESENCE_MODE_HA}
>
  ${haOptionLabel(this.hasDeviceTrackers)}
</option>
```

Every person, regardless of device tracker status, sees the "HA home tracking
⚠" option in the dropdown. The warning label appears (via `haOptionLabel`) but
the option is never hidden, which contradicts D-04 and the test contract.

The `hasDeviceTrackers` property is forwarded correctly from `persons-tab.ts`,
so the data path is correct — the guard just never uses it.

**Fix:** Import `shouldShowHaOption` and wrap the option:

```typescript
// line 85 — update import
import {
  haOptionLabel,
  presenceModeHint,
  shouldShowHaOption,
} from "./presence-mode.js";

// lines 607-612 in render() — wrap the option
${shouldShowHaOption(this.hasDeviceTrackers)
  ? html`<option
      value=${PRESENCE_MODE_HA}
      ?selected=${currentMode === PRESENCE_MODE_HA}
    >
      ${haOptionLabel(this.hasDeviceTrackers)}
    </option>`
  : ""}
```

Note: this fix is only correct if D-04 "hide when no trackers" is the chosen
design (CR-01 option B). If "always show" is chosen instead, this is not
needed.

---

### CR-03: `history.pushState` + `location-changed` navigation skips HA's
`navigate()` helper — causes broken back-navigation in HA 2026.x panels

**File:** `frontend/src/components/person-card.ts:634-646`
**Issue:** The edit-person button navigates to `/config/person/edit/<slug>` by
calling `history.pushState` directly and then dispatching a bare
`location-changed` CustomEvent on `window`. In HA 2026.x the router expects
navigation events dispatched on the document root, not `window`, and the HA
navigation helper (`navigate(this, path)` from
`custom-card-helpers` or `history.pushState` paired with the
`hass-location-changed` event bubbled from a panel root element) is the correct
pattern. The existing codebase already demonstrates this: `main.ts` and other
components use `this.panel.navigateToRoom` / `navigateToPerson` which call HA's
own internal navigate function.

This usage:
1. Does not bubble through HA's router — the URL changes but HA's active-route
   state may not update, leaving the sidebar highlight stale.
2. There is no error recovery — if `this.personId` has an unexpected format
   (already stripped of the `person.` prefix, or contains characters unsafe for
   URL path segments), the `replace(/^person\./, "")` regex silently produces a
   malformed URL with no validation. A `personId` of `person.../evil` would
   push `history.pushState(null, "", "/config/person/edit/.../evil")` — a
   path-traversal shaped URL (though confined to client-side routing).
3. This is the only place in the entire frontend codebase that manually calls
   `history.pushState` — it is inconsistent with the established navigation
   pattern.

**Fix:** Dispatch the event on `this` (which is `composed: true`) so it bubbles
through the shadow DOM to HA's router, and add basic slug validation:

```typescript
@click=${() => {
  const slug = this.personId.replace(/^person\./, "");
  // Guard: HA person slugs are entity ID suffixes — only
  // word chars and hyphens expected.
  if (!/^[\w-]+$/.test(slug)) return;
  history.pushState(
    null,
    "",
    `/config/person/edit/${slug}`,
  );
  this.dispatchEvent(
    new CustomEvent("location-changed", {
      bubbles: true,
      composed: true,
    }),
  );
}}
```

Alternatively, leverage the HA `navigate()` helper imported from
`custom-card-helpers` to stay consistent with how `navigateToRoom` works in
`main.ts`.

---

## Warnings

### WR-01: `shouldShowHaOption` parameter is named `_hasDeviceTrackers`
(underscore prefix) despite actually being the deciding input — misleading API

**File:** `frontend/src/components/presence-mode.ts:41`
**Issue:** The underscore prefix conventionally signals an intentionally unused
parameter. Here the name `_hasDeviceTrackers` is used because the function
body ignores the argument (`return true`). But the function is exported as a
guard that callers are expected to pass a meaningful boolean to. The underscore
leaks the implementation detail that the function is effectively a no-op and
invites callers to skip the call entirely. If D-04 remains "always show", the
function should be removed (or the parameter name fixed); if "hide when no
trackers", the parameter needs to be used.

**Fix (always-show path):** Remove `shouldShowHaOption` entirely and inline
`true` at the call sites, or rename the param to make the no-op intent
explicit:

```typescript
/** Always true — the ha option is always rendered (D-04). */
export function shouldShowHaOption(
  _hasDeviceTrackers: boolean, // reserved for future conditional logic
): boolean {
  return true;
}
```

**Fix (hide-when-no-trackers path):** Rename the param and implement:

```typescript
export function shouldShowHaOption(hasDeviceTrackers: boolean): boolean {
  return hasDeviceTrackers;
}
```

---

### WR-02: `haOptionLabel` is not tested — exported function with observable
side-effect (⚠ suffix in UI) has zero test coverage

**File:** `frontend/src/components/presence-mode.ts:50-52`
**Issue:** `haOptionLabel` is exported and used in two places in `person-card.ts`
(the badge text and the dropdown option label). Its contract — appending " ⚠"
when `hasDeviceTrackers` is false — is not verified by any test. The test file
imports `MODE_LABEL_HA`, `computeHasDeviceTrackers`, `shouldShowHaOption`, and
`presenceModeHint`, but not `haOptionLabel`. If `haOptionLabel` is accidentally
changed, no test will catch it.

**Fix:** Add two test cases to `presence-mode.test.ts`:

```typescript
import {
  MODE_LABEL_HA,
  computeHasDeviceTrackers,
  haOptionLabel,
  shouldShowHaOption,
  presenceModeHint,
} from "./presence-mode.ts";

test("UI-01: haOptionLabel appends ⚠ when no trackers", () => {
  assert.equal(haOptionLabel(false), `${MODE_LABEL_HA} ⚠`);
});

test("UI-01: haOptionLabel returns plain label when trackers exist", () => {
  assert.equal(haOptionLabel(true), MODE_LABEL_HA);
});
```

---

## Info

### IN-01: `presenceModeHint` branch coverage in tests is partial —
`force_present`, `force_absent`, and fallback ("scheduled") paths untested

**File:** `frontend/src/components/presence-mode.test.ts:54-68`
**Issue:** Only the two `"ha"` branches of `presenceModeHint` are tested. The
`"force_present"`, `"force_absent"`, and default fallback branches (lines 65-80
of `presence-mode.ts`) each return a distinct string that appears verbatim in
the UI. A typo in any of those branches would not be caught.

**Fix:** Add three additional test cases covering the remaining branches:

```typescript
test("presenceModeHint: force_present", () => {
  assert.equal(
    presenceModeHint("force_present", false),
    "Always considered present, regardless of schedule.",
  );
});
test("presenceModeHint: force_absent", () => {
  assert.equal(
    presenceModeHint("force_absent", false),
    "Always absent. Rooms are not heated for presence.",
  );
});
test("presenceModeHint: scheduled (default)", () => {
  assert.equal(
    presenceModeHint("scheduled", false),
    "Presence follows a weekly schedule.",
  );
});
```

---

### IN-02: Plan spec says rename "HA home tracking" → "Live tracking" but
implementation keeps the old label — plan-to-code divergence in documentation

**File:** `frontend/src/components/presence-mode.ts:20`,
`frontend/src/components/person-card.ts:85`
**Issue:** The `<objective>` block in `10-02-PLAN.md` (lines 46-48) states:

> "rename the 'HA home tracking' label to 'Live tracking' (D-01/UI-02)"

But `MODE_LABEL_HA` is `"HA home tracking"` and the human-verification
checkpoint in the plan (Task 3, step 3 and step 6) asks the operator to confirm
they see "Live tracking" — which they never will with the current implementation.
The `10-02-SUMMARY.md` marks this as done.

This is a documentation/plan inconsistency rather than a code bug (the
`must_haves.truths` section of the plan also says "The ha mode label stays HA
home tracking — no rename"), so the contradiction is in the plan itself. But it
means the human verification checkpoint criteria cannot ever pass as written.

**Fix:** Reconcile the plan text. If "HA home tracking" is the final label
(which the code and the `must_haves.truths` block confirm), update the
`<objective>` block and the human-verification steps in `10-02-PLAN.md` to
remove references to "Live tracking". No code change needed.

---

## Finding Summary

| ID    | Severity | File                          | Issue                                              |
|-------|----------|-------------------------------|----------------------------------------------------|
| CR-01 | Critical | presence-mode.test.ts:45      | Test asserts `shouldShowHaOption(false)===false`; function returns `true`; suite exits 1 |
| CR-02 | Critical | person-card.ts:607            | `shouldShowHaOption` guard never called; ha option always rendered unconditionally |
| CR-03 | Critical | person-card.ts:634            | `history.pushState` + `window` dispatch skips HA router; inconsistent navigation pattern; no slug validation |
| WR-01 | Warning  | presence-mode.ts:41           | `_hasDeviceTrackers` underscore signals unused param but is the gate input; misleading API |
| WR-02 | Warning  | presence-mode.test.ts (none)  | `haOptionLabel` exported and UI-visible but has zero test coverage |
| IN-01 | Info     | presence-mode.test.ts:54      | Three `presenceModeHint` branches (force_present, force_absent, default) untested |
| IN-02 | Info     | 10-02-PLAN.md / presence-mode.ts:20 | Plan objective says rename to "Live tracking"; code keeps "HA home tracking"; plan docs contradictory |

**Critical: 3 | Warning: 2 | Info: 2 | Total: 7**

---

_Reviewed: 2026-06-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
