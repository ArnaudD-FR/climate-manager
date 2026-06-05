---
phase: 17-person-scheduling-use-case-docs
reviewed: 2026-06-05T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - docs/screenshot.js
  - Makefile
  - docs/use-cases/simple-schedule/Makefile
  - docs/use-cases/business-calendar/Makefile
  - docs/use-cases/student-mixed-schedule/Makefile
  - docs/use-cases/rotating-shift-worker/Makefile
  - docs/use-cases/shared-custody-odd-even-weeks/Makefile
  - docs/use-cases/simple-schedule/harness.html
  - docs/use-cases/business-calendar/harness.html
  - docs/use-cases/student-mixed-schedule/harness.html
  - docs/use-cases/rotating-shift-worker/harness.html
  - docs/use-cases/shared-custody-odd-even-weeks/harness.html
  - docs/use-cases/simple-schedule/README.md
  - docs/use-cases/business-calendar/README.md
  - docs/use-cases/student-mixed-schedule/README.md
  - docs/use-cases/rotating-shift-worker/README.md
  - docs/use-cases/shared-custody-odd-even-weeks/README.md
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-06-05
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 17 adds five `docs/use-cases/` persona scenarios, each with a Makefile,
a harness HTML, and a README. The implementation is structurally sound: the
`OUTPUT_DIR` / `HARNESS_PATH` env-var extension to `screenshot.js` is
backward-compatible, all per-scenario `PROJECT_ROOT` depth computations are
correct (`cd ../../..` from three levels deep), `panel.js` paths use absolute
URLs, and no real credentials or PII appear in any mock CONFIG.

Three issues warrant attention before relying on `make screenshots` in CI or
reproducing screenshots on future machines.

---

## Warnings

### WR-01: Path-boundary check in static server is a no-op

**File:** `docs/screenshot.js:55-56`

**Issue:** The `normalized` variable is intended to prevent directory-traversal
by verifying the resolved file path starts with `PROJECT_ROOT`. However, the
ternary on line 55 appends `""` in **both** branches:

```js
const normalized = filePath + (filePath.endsWith(path.sep) ? "" : "");
//                                                      ^^^   ^^^
//                                       both branches return ""
```

`normalized` is therefore identical to `filePath`. The missing second branch
should append `path.sep` so that a PROJECT_ROOT of `/app` does not accidentally
match a sibling path like `/appX/…` via `startsWith`. As written, if the docker
image ever had a directory `/appX` at root level, the check would return `true`
and serve that file. In the current docker environment this is not exploitable
(no such directory exists beside `/app`), but the guard is broken by
construction and silently misleads future readers.

**Fix:**

```js
const normalized = filePath.endsWith(path.sep)
  ? filePath
  : filePath + path.sep;
if (!normalized.startsWith(PROJECT_ROOT + path.sep)) {
```

---

### WR-02: `expandFirstCard` fails silently in scenario mode

**File:** `docs/screenshot.js:147-172` (called at lines 187, 205)

**Issue:** `expandFirstCard` resolves successfully even when the card is not
found — it only emits `console.warn` inside the `page.evaluate` callback.
There is no throw or return value check on the Node side. In scenario mode
(the new code path) the call sequence is:

```js
await expandFirstCard("climate-manager-persons-tab");
await page.screenshot({ path: out("persons.png") });
```

If the persons-tab card fails to render (wrong CONFIG schema, timing, harness
load error), the screenshot is taken of the **unexpanded** card with no error
reported and exit code 0. The committed PNG looks like a successful capture but
shows the wrong state.

This was latent in the original standard mode too, but scenario mode makes it
more likely to trigger silently because the harness CONFIG is scenario-specific
and easier to misconfigure.

**Fix:** Return a boolean from the `page.evaluate` call and throw on the Node
side, matching the pattern used in `clickTab`:

```js
async function expandFirstCard(componentTag) {
  const found = await page.evaluate((tag) => {
    // … existing find logic …
    if (!header) return false;
    header.click();
    return true;
  }, componentTag);
  if (!found) throw new Error(`Card not found in <${componentTag}>`);
  await page.waitForTimeout(900);
}
```

---

### WR-03: Hardcoded completion message always says `docs/screenshots/`

**File:** `docs/screenshot.js:228`

**Issue:** The final log line reads:

```js
console.log("\nDone! Screenshots saved to docs/screenshots/");
```

In scenario mode, `SCREENSHOTS_DIR` resolves to the per-scenario
`docs/use-cases/<slug>/screenshots/` directory (from `OUTPUT_DIR`). The message
is factually wrong in every scenario-mode invocation, which will confuse anyone
reading the docker output while debugging a capture failure.

**Fix:**

```js
console.log(`\nDone! Screenshots saved to ${SCREENSHOTS_DIR}`);
```

---

## Info

### IN-01: Inconsistent use of `$(SLUG)` vs. literal slug in `HARNESS_PATH`

**File:** `docs/use-cases/simple-schedule/Makefile:11`,
`docs/use-cases/business-calendar/Makefile:11`,
`docs/use-cases/student-mixed-schedule/Makefile:12`

**Issue:** Three Makefiles hard-code the slug literal in the `HARNESS_PATH`
value instead of referencing `$(SLUG)`:

```makefile
# simple-schedule/Makefile
-e HARNESS_PATH=/docs/use-cases/simple-schedule/harness.html \

# rotating-shift-worker/Makefile (consistent)
-e HARNESS_PATH=/docs/use-cases/$(SLUG)/harness.html \
```

Both forms produce identical output today because `$(SLUG)` expands to the
same string. But if a slug folder is ever renamed, the three literal forms
require two edits (both `SLUG :=` and the path) rather than one. It is also
a minor cognitive inconsistency: two of the five Makefiles use `$(SLUG)` for
both `OUTPUT_DIR` and `HARNESS_PATH`, while three mix the approaches.

**Fix:** Replace the literal slug in the three affected Makefiles with
`$(SLUG)`:

```makefile
-e HARNESS_PATH=/docs/use-cases/$(SLUG)/harness.html \
```

---

### IN-02: `scenario mode` capture does not check the Overview screenshot title

**File:** `docs/screenshot.js:182-183`

**Issue:** In scenario mode the first screenshot (`overview.png`) is taken
immediately after the 800 ms Lit-settle wait, before any tab interaction. The
overview tab is the default landing state of the panel. This is correct
behaviour, but the filename `overview.png` is captured for every scenario even
for use cases that only have a persons card to show (D-05, `rotating-shift-worker`).
The READMEs for those scenarios reference only `screenshots/persons.png`, so
`overview.png` is committed but unreferenced in the README. Not wrong, just
generates an unlinked file per scenario.

This is noted for awareness rather than an action item, since an extra PNG
in `screenshots/` does no harm and the Research document (Pattern 5) explicitly
names both `overview.png` and `persons.png` as the scenario-mode capture set.

**Fix:** No action required unless the project wants to suppress the overview
screenshot for HA-tracker-mode scenarios to keep the folder minimal.

---

_Reviewed: 2026-06-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
