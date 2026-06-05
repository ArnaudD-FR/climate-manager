# Phase 17: Person Scheduling Use-Case Docs — Research

**Researched:** 2026-06-05
**Domain:** Documentation + screenshot tooling (Playwright / Makefile / mock harness)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Screenshots from the existing mock panel harness (`docs/test-harness.html`
  + `docs/screenshot.js` driving the built `panel.js`), not from a live HA instance.
- **D-02:** Each use case is a distinct folder `docs/use-cases/<slug>/` containing
  `README.md`, `screenshots/`, and a local `Makefile`.
- **D-03:** Root Makefile delegates — the `screenshots` target (or a sub-target it
  depends on) iterates use-case folders and invokes each local `Makefile`. The
  existing 6 panel-tab screenshots in `docs/screenshots/` remain untouched.
- **D-04:** Screenshot set is per-scenario — always includes expanded Persons-tab
  person card; additional views (Overview, Rooms) only where illustrative.
- **D-05:** HA-tracker scenario (`rotating-shift-worker`) has no schedule editor.
  Its person card shows mode selector + explanatory state. Deliberately contrasts
  schedule-driven cards.
- **D-06:** READMEs are conceptual showcases, not click-by-click guides. Contents:
  persona intro + config summary table (presence mode, schedule shape, assigned
  rooms) + annotated screenshots. No numbered reproduction walkthrough.
- **D-07:** `simple-schedule` → Scheduled, single week. Home mornings/evenings,
  away ~09:00–17:00 weekdays, home all weekend.
- **D-08:** `business-calendar` → Calendar mode. Presence driven by a work
  `calendar.*` entity; events mean away.
- **D-09:** `student-mixed-schedule` → Scheduled, single week with varied per-weekday
  hours; home weekends.
- **D-10:** `rotating-shift-worker` → HA person-entity tracking (`ha` mode).
- **D-11:** `shared-custody-odd-even-weeks` → Scheduled, even/odd weeks. Even week =
  child present all week, odd week = absent.

### Claude's Discretion

- Exact wording/layout of config summary table and annotations.
- Exact schedule times within each persona.
- Whether root delegation is a new `use-case-docs` target that `screenshots`
  depends on, or folded directly into `screenshots`.
- Screenshot file naming within each `screenshots/` folder.

### Deferred Ideas (OUT OF SCOPE)

- `force_present` / `force_absent` "guest" use case (6th scenario).
- Step-by-step reproducible setup guides.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID     | Description | Research Support |
|--------|-------------|-----------------|
| DOC-01 | Five person-scheduling use-case documents with screenshots exist under `docs/use-cases/`; `make screenshots` captures all scenario screenshots cleanly | Tooling mechanics below; mock CONFIG schemas per scenario detailed in Architecture Patterns section |

</phase_requirements>

---

## Summary

Phase 17 is a documentation-and-tooling phase: no backend or frontend source changes.
It extends the existing Playwright / mock-harness screenshot pipeline to produce
five persona-specific screenshot sets, and adds five `docs/use-cases/<slug>/` folders
each containing a README and the generated PNGs.

The existing `docs/screenshot.js` driver is **single-config and single-output-dir
hard-coded**. `SCREENSHOTS_DIR` is fixed to `docs/screenshots/`, and the CONFIG and
STATUS objects are inlined in `docs/test-harness.html`. There is no existing
parameterisation mechanism. The per-scenario pipeline requires two small, targeted
changes: (1) a way to inject a per-scenario CONFIG into the harness without modifying
the shared file, and (2) a way to pass a custom output directory to the driver. Both
can be done via the environment / query-string pattern already used by the static
server — no rewrite needed.

The five persona CONFIG objects are fully specifiable from the confirmed `PersonConfig`
schema (`mode`, `schedule_type`, `schedule`, `schedule_even`, `schedule_odd`,
`calendar_config`, `room_ids`). The panel renders each mode differently — the
scheduled variants expose the time-bar, the calendar variant exposes the entity/
gap/preheat selectors, and the `ha` variant shows the mode selector + hint only (no
schedule editor). This makes each screenshot visually distinct and captures the full
mode coverage as required by DOC-01.

**Primary recommendation:** Introduce a thin per-scenario harness overlay — a
`scenario-harness.html` per use-case folder that embeds that scenario's CONFIG and
imports the shared `docs/screenshot.js` driver with `OUTPUT_DIR` sourced from an
environment variable. The root Makefile `screenshots` target gains a
`use-case-screenshots` prerequisite that iterates `docs/use-cases/*/Makefile`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Screenshot generation | Build tooling (docker / Playwright) | — | Deterministic PNG capture from a static HTML harness |
| Mock config injection | Build tooling (env var / HTML file) | — | Each scenario needs its own CONFIG object; no runtime |
| README authoring | Documentation | — | Static Markdown, no automation |
| Root Makefile delegation | Build tooling | — | Orchestrates per-folder Makefiles |
| Panel rendering of modes | Frontend (built `panel.js`) | — | Already compiled; no source change needed |

---

## Standard Stack

This phase adds no new dependencies. Existing tools already installed:

### Core (already in `docs/package.json`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| playwright | 1.49.0 | Headless Chromium capture | Pinned; docker image `mcr.microsoft.com/playwright:v1.49.0-noble` matches |
| @mdi/js | ^7.4.47 | MDI icon SVG paths injected via `window.__MDI__` | Harness stubs `ha-icon` need these |

### Infrastructure

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | host-installed | Runs the Playwright capture in a sandboxed container |
| GNU make | host-installed | Root and per-scenario orchestration |

**Installation:** No new packages. `docs/npm install` already runs as part of
`make screenshots` → `cd /app/docs && npm install …`.

---

## Package Legitimacy Audit

No new packages are introduced in this phase.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| playwright | npm | ~5 yrs | 10M+/wk | github.com/microsoft/playwright | n/a (existing) | Approved — already locked in `docs/package.json` |
| @mdi/js | npm | ~7 yrs | 4M+/wk | github.com/Templarian/MaterialDesign-JS | n/a (existing) | Approved — already locked |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Per-use-case capture flow
─────────────────────────

docs/use-cases/<slug>/Makefile
  │
  ├── sets OUTPUT_DIR=docs/use-cases/<slug>/screenshots
  ├── sets CONFIG_FILE=docs/use-cases/<slug>/scenario-config.js  (or inline HTML)
  │
  └── docker run playwright image
        └── node /app/docs/screenshot.js
              │
              ├── starts http.createServer (port 7654, serves PROJECT_ROOT)
              ├── goto http://localhost:7654/docs/use-cases/<slug>/harness.html
              │         (per-scenario HTML that embeds that CONFIG object and
              │          loads panel.js from /custom_components/…/www/panel.js)
              ├── waits for shadowRoot .tab-bar  ← same readiness gate
              ├── calls clickTab / expandFirstCard helpers (same API)
              └── writes PNGs to OUTPUT_DIR (injected via env var)

Root make screenshots
─────────────────────

make screenshots
  ├── build  (rebuild panel.js)
  ├── existing-screenshots  (docs/screenshots/ — unchanged, 6 PNGs)
  └── use-case-screenshots
        └── for each docs/use-cases/*/Makefile → $(MAKE) -C <slug_dir>
```

### Recommended Project Structure

```
docs/
├── screenshot.js              # shared driver — extended to honour OUTPUT_DIR env
├── test-harness.html          # unchanged — the panel-tab capture harness
├── screenshots/               # unchanged — 6 existing panel-tab PNGs
└── use-cases/
    ├── simple-schedule/
    │   ├── Makefile
    │   ├── harness.html       # per-scenario mock CONFIG + STATUS
    │   ├── README.md
    │   └── screenshots/       # generated PNGs committed here
    ├── business-calendar/
    │   └── …
    ├── student-mixed-schedule/
    │   └── …
    ├── rotating-shift-worker/
    │   └── …
    └── shared-custody-odd-even-weeks/
        └── …
```

### Pattern 1: screenshot.js OUTPUT_DIR Parameterisation

`docs/screenshot.js` currently hard-codes:

```javascript
// Source: docs/screenshot.js line 34
const SCREENSHOTS_DIR = path.join(__dirname, "screenshots");
```

The smallest change is to honour an environment variable override:

```javascript
// Source: docs/screenshot.js (proposed minimal patch)
const SCREENSHOTS_DIR =
  process.env.OUTPUT_DIR
    ? path.resolve(process.env.OUTPUT_DIR)
    : path.join(__dirname, "screenshots");
```

`fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true })` already creates the
directory, so no other change is needed to the output path logic.

### Pattern 2: Per-Scenario Harness HTML

Each `docs/use-cases/<slug>/harness.html` is a copy of `docs/test-harness.html`
with **only the inline `<script type="module">` block replaced** to embed the
scenario-specific `CONFIG` and `STATUS` objects. The `ha-icon` / `ha-card` /
`ha-switch` stubs, CSS variables, and the panel.js `<script type="module">` tag
are **identical** to the shared harness. The `panel.js` load path
`/custom_components/climate_manager/www/panel.js` works unchanged because the
static server resolves all paths from `PROJECT_ROOT`.

The `goto` URL in `screenshot.js` must point to the scenario harness, not the
shared one. Add a second env var:

```javascript
// Source: docs/screenshot.js (proposed minimal patch)
const HARNESS_PATH =
  process.env.HARNESS_PATH || "/docs/test-harness.html";
// …
await page.goto(`http://localhost:${PORT}${HARNESS_PATH}`);
```

### Pattern 3: Per-Scenario Makefile

Each `docs/use-cases/<slug>/Makefile` runs the shared driver with overrides.
The path to `screenshot.js` must be absolute-from-project-root because docker
maps the project root to `/app`.

```makefile
# Source: pattern (to be instantiated per scenario)
SLUG := simple-schedule
PROJECT_ROOT := $(shell cd ../.. && pwd)

.PHONY: screenshots

screenshots:
	docker run --rm --ipc=host \
		-v "$(PROJECT_ROOT):/app" \
		-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
		-e OUTPUT_DIR=/app/docs/use-cases/$(SLUG)/screenshots \
		-e HARNESS_PATH=/docs/use-cases/$(SLUG)/harness.html \
		mcr.microsoft.com/playwright:v1.49.0-noble \
		bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null && node screenshot.js"
```

Key path pitfall: docker `-v` must bind the **project root** (two levels up from
the use-case directory), not the use-case directory. `PROJECT_ROOT` resolved from
within the `Makefile` via `$(shell cd ../.. && pwd)` is reliable. The docker
working directory is set to `/app/docs` (matching the root Makefile recipe) so
relative `require('./…')` paths inside `screenshot.js` resolve correctly.

### Pattern 4: Root Makefile Delegation

Add a `use-case-screenshots` target and make `screenshots` depend on it:

```makefile
# Source: Makefile (root) — proposed addition
.PHONY: use-case-screenshots

use-case-screenshots:
	@for dir in docs/use-cases/*/; do \
		if [ -f "$$dir/Makefile" ]; then \
			echo "--- $$dir ---"; \
			$(MAKE) -C "$$dir" screenshots; \
		fi \
	done

screenshots: build
	@mkdir -p docs/screenshots
	docker run --rm --ipc=host \
		-v "$$(pwd):/app" \
		-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
		mcr.microsoft.com/playwright:v1.49.0-noble \
		bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null && node screenshot.js"
	$(MAKE) use-case-screenshots
```

`$(MAKE) -C "$$dir"` passes `MAKE` through so nested invocations inherit the
same make binary. The `build` prerequisite ensures `panel.js` is fresh before
any harness loads it.

### Pattern 5: Per-Scenario capture sequence

The driver helper API is:

- `clickTab(label: string)` — finds `.tab-btn` by textContent in the panel
  shadowRoot, clicks it, waits 700 ms.
- `expandFirstCard(componentTag: string)` — finds the first card inside
  `<componentTag>` shadow DOM, clicks `.card-header-row`, waits 900 ms.

For scenarios where only the Persons card is needed (D-04), the capture sequence
per-scenario harness.html variant is:

```javascript
// minimum capture sequence for a persons-tab scenario
await clickTab("Persons");
await expandFirstCard("climate-manager-persons-tab");
await page.screenshot({ path: out("persons-expanded.png") });
```

For scenarios that also illustrate the Overview (global mode state):

```javascript
await page.screenshot({ path: out("overview.png") });  // already on Overview tab
await clickTab("Persons");
await expandFirstCard("climate-manager-persons-tab");
await page.screenshot({ path: out("persons-expanded.png") });
```

The driver can either be a modified shared `screenshot.js` (driven by env vars)
or each scenario ships its own small capture script. The env-var approach is
simpler and avoids duplication. However, the per-scenario capture sequence (which
tabs to screenshot) must still vary. The cleanest solution: the shared driver
captures Overview + Persons expanded only (the common subset), and a
`SCENARIO_TABS` env var controls whether Rooms is also captured.

Alternative: each scenario harness ships its own tiny
`capture.js` that imports helpers from `screenshot.js` (refactored to export
them). This avoids env-var proliferation but requires a light refactor. Either
approach is valid; the env-var approach requires zero exports.

---

## PersonConfig Field Reference

From `frontend/src/types.ts` (source of truth for the mock CONFIG schema):

```typescript
interface PersonConfig {
  mode?: string;         // "scheduled" | "ha" | "calendar" |
                         // "force_present" | "force_absent"
  room_ids?: string[];
  schedule?: DailyProgram;          // single-week presence schedule
  schedule_type?: "single" | "even_odd";
  schedule_even?: DailyProgram;     // even weeks only
  schedule_odd?: DailyProgram;      // odd weeks only
  calendar_config?: CalendarConfig; // calendar mode config
  wakeup_advance_minutes?: number;  // calendar pre-heat advance (default 60)
}

type DailyProgram = Record<
  "mon"|"tue"|"wed"|"thu"|"fri"|"sat"|"sun", Period[]
>;

// For presence schedules:
type Period = { start: string; state: "present" | "absent" | "calendar"; … }
```

### PersonMode → card rendering

| mode | Schedule editor shown | Calendar config shown | schedule_type selector |
|------|-----------------------|-----------------------|------------------------|
| `scheduled` / `single` | Yes — single time-bar | No | Yes (single / even_odd) |
| `scheduled` / `even_odd` | Yes — even+odd tabs | No | Yes |
| `calendar` | No | Yes (entity, event_means, gap_handling, wakeup_advance_minutes) | No |
| `ha` | No | No | No |
| `force_present` / `force_absent` | No | No | No |

Mode badge text (from `_getBadgeInfo()` in `person-card.ts`):
- `scheduled` → `"Scheduled"` (grey badge)
- `ha` → result of `haOptionLabel(hasDeviceTrackers)` — in harness,
  `hasDeviceTrackers` defaults to false → badge text is `"⚠ HA (no trackers)"`
  unless explicitly set true. For documentation purposes, set
  `hasDeviceTrackers: true` equivalent via the STATUS/hass.states so the HA
  option shows cleanly. The `hasDeviceTrackers` prop is computed in `persons-tab`
  from `hass.states[personId].attributes.device_trackers`. Setting
  `attributes: { device_trackers: ['device_tracker.phone'] }` in mockHass.states
  for that person entity makes it render the clean `"HA"` label.
- `calendar` → `"Calendar"` (grey badge)
- `force_present` → `"Force Present"` (blue border badge)
- `force_absent` → `"Force Absent"` (grey badge)

---

## Per-Scenario Mock CONFIG Objects

These are the exact `persons` map entries required for each scenario harness.

### D-07: simple-schedule (scheduled / single)

```javascript
persons: {
  'person.emma': {
    mode: 'scheduled',
    schedule_type: 'single',
    room_ids: ['bedroom', 'living_room'],
    schedule: {
      mon: [
        { start: '00:00', state: 'absent' },
        { start: '07:00', state: 'present' },
        { start: '09:00', state: 'absent' },
        { start: '17:30', state: 'present' },
        { start: '23:00', state: 'absent' },
      ],
      tue: /* same as mon */ …,
      wed: /* same as mon */ …,
      thu: /* same as mon */ …,
      fri: /* same as mon */ …,
      sat: [{ start: '00:00', state: 'present' }],
      sun: [{ start: '00:00', state: 'present' }],
    },
  },
}
```

### D-08: business-calendar (calendar mode)

```javascript
persons: {
  'person.noah': {
    mode: 'calendar',
    room_ids: ['office', 'bedroom'],
    calendar_config: {
      entity_id: 'calendar.work_meetings',
      event_means: 'absent',
      gap_handling: 'day_span',
    },
    wakeup_advance_minutes: 60,
  },
}
```

The mock `hass.states` must include a
`'calendar.work_meetings': { state: 'off', attributes: { friendly_name: 'Work meetings' } }`
entry so the entity select renders a friendly name.

### D-09: student-mixed-schedule (scheduled / single, varied weekdays)

```javascript
persons: {
  'person.lena': {
    mode: 'scheduled',
    schedule_type: 'single',
    room_ids: ['bedroom'],
    schedule: {
      mon: [
        { start: '00:00', state: 'absent' },
        { start: '08:00', state: 'present' },
        { start: '09:00', state: 'absent' },
        { start: '12:00', state: 'present' },
        { start: '13:00', state: 'absent' },
        { start: '17:00', state: 'present' },
      ],
      tue: [
        { start: '00:00', state: 'absent' },
        { start: '08:00', state: 'present' },
        { start: '10:00', state: 'absent' },
        { start: '18:00', state: 'present' },
      ],
      wed: [{ start: '00:00', state: 'present' }],  // no class Wednesday
      thu: /* similar to mon */ …,
      fri: [
        { start: '00:00', state: 'absent' },
        { start: '08:00', state: 'present' },
        { start: '11:00', state: 'absent' },
        { start: '14:00', state: 'present' },
      ],
      sat: [{ start: '00:00', state: 'present' }],
      sun: [{ start: '00:00', state: 'present' }],
    },
  },
}
```

### D-10: rotating-shift-worker (ha mode)

```javascript
persons: {
  'person.marc': {
    mode: 'ha',
    room_ids: ['bedroom'],
  },
}
```

`hass.states` must include:
```javascript
'person.marc': {
  state: 'not_home',
  attributes: {
    friendly_name: 'Marc',
    device_trackers: ['device_tracker.marc_phone'],  // makes HA option clean
  },
}
```

This is the D-05 "no schedule editor" scenario. The card expands to show only
the mode selector, mode hint, and room associations.

### D-11: shared-custody-odd-even-weeks (scheduled / even_odd)

```javascript
persons: {
  'person.sofia': {
    mode: 'scheduled',
    schedule_type: 'even_odd',
    room_ids: ['bedroom'],
    schedule_even: {
      mon: [{ start: '00:00', state: 'present' }],
      tue: [{ start: '00:00', state: 'present' }],
      wed: [{ start: '00:00', state: 'present' }],
      thu: [{ start: '00:00', state: 'present' }],
      fri: [{ start: '00:00', state: 'present' }],
      sat: [{ start: '00:00', state: 'present' }],
      sun: [{ start: '00:00', state: 'present' }],
    },
    schedule_odd: {
      mon: [{ start: '00:00', state: 'absent' }],
      tue: [{ start: '00:00', state: 'absent' }],
      wed: [{ start: '00:00', state: 'absent' }],
      thu: [{ start: '00:00', state: 'absent' }],
      fri: [{ start: '00:00', state: 'absent' }],
      sat: [{ start: '00:00', state: 'absent' }],
      sun: [{ start: '00:00', state: 'absent' }],
    },
  },
}
```

When `schedule_type` is `even_odd`, the card renders the Even/Odd week-switcher
tabs. The active week at capture time is computed from `getWeekParity(new Date())`
in the panel — this is week-parity dependent and not controllable from the
harness. The `_activeWeek` state defaults to `'even'` and is re-evaluated on
expand. Since 2026-06-05 is ISO week 23 (odd), the card will open on the Even
tab (the default initialisation) and then immediately recalculate to `'odd'` in
`updated()`. The screenshot will show the Odd week schedule. This is acceptable
— both even and odd weeks are just all-present or all-absent blocks. If a
specific parity is needed for the screenshot, `page.evaluate` can toggle the
tab button after `expandFirstCard`.

---

## Harness Gap Analysis — What Exists vs. What Must Be Added

| Item | Current state | Action required |
|------|--------------|-----------------|
| `SCREENSHOTS_DIR` | Hard-coded to `docs/screenshots/` | Add `OUTPUT_DIR` env var override (2-line change) |
| Harness URL | Hard-coded to `/docs/test-harness.html` | Add `HARNESS_PATH` env var override (2-line change) |
| Per-scenario harness | Does not exist | Create `harness.html` per use-case folder (copy + replace CONFIG block) |
| Per-scenario capture sequence | Does not exist | Decide: env-var-driven shared driver vs. per-scenario `capture.js` |
| `docs/use-cases/` directory | Does not exist | Create 5 slug subdirectories |
| Per-scenario `Makefile` | Does not exist | Create per slug (docker run + env vars) |
| Root `use-case-screenshots` target | Does not exist | Add to root Makefile |
| Root `screenshots` depends on use-cases | Does not exist | Chain `$(MAKE) use-case-screenshots` at end of `screenshots` |

The two patches to `screenshot.js` are **additive** (new env var honour) and
backward-compatible — the existing `make screenshots` run with no env vars
continues to work identically.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Headless browser rendering | Custom puppeteer wrapper | Existing `screenshot.js` + Playwright docker | Already working, pinned version |
| Static file serving | Custom server | Existing `http.createServer` in `screenshot.js` | Serves the whole project root; URL routing already handled |
| HA component stubs | New web component stubs | Existing stubs in `test-harness.html` (`ha-icon`, `ha-card`, `ha-switch`, `ha-icon-button`, `ha-circular-progress`) | Tested and rendering correctly |
| MDI icon injection | Re-bundle icons | Existing `window.__MDI__` injection in `screenshot.js` | Already pre-filters the 18 keys the panel needs |

---

## Common Pitfalls

### Pitfall 1: docker CWD and module resolution

**What goes wrong:** If the docker working directory is set to the use-case
folder instead of `/app/docs`, the `require('playwright')` and `require('@mdi/js')`
calls in `screenshot.js` fail because `node_modules` lives in `docs/`, not in the
use-case subfolder.

**Why it happens:** Per-use-case Makefile CDs or sets docker workdir incorrectly.

**How to avoid:** Always run `cd /app/docs && node screenshot.js` in the docker
bash command, regardless of which use-case folder the Makefile lives in. The
`OUTPUT_DIR` and `HARNESS_PATH` env vars control the scenario; the working
directory should always be `/app/docs`.

**Warning signs:** `Cannot find module 'playwright'` or `Cannot find module '@mdi/js'`
in docker output.

### Pitfall 2: `panel.js` path from use-case harness

**What goes wrong:** A `harness.html` under `docs/use-cases/<slug>/` that
uses a relative path (`../../custom_components/…/www/panel.js`) fails when
served by the static server, because the server resolves from project root.

**Why it happens:** Relative HTML `src=` paths behave differently under a server
vs. the filesystem.

**How to avoid:** Use the absolute URL path
`/custom_components/climate_manager/www/panel.js` in every harness (same as the
shared harness, line 147).

**Warning signs:** `[page error] Failed to fetch` or blank panel.

### Pitfall 3: Even/Odd week parity in screenshots

**What goes wrong:** The `schedule_type: 'even_odd'` card auto-selects the
current ISO week parity when the card expands (hardcoded in `updated()` of
`person-card.ts`). The captured screenshot may show Even or Odd depending on
when `make screenshots` is run.

**Why it happens:** `getWeekParity(new Date())` is called at expand time, inside
the Playwright browser, using the docker container's system clock.

**How to avoid:** For the `shared-custody-odd-even-weeks` scenario, either:
(a) accept that the screenshot shows whichever parity is current, and annotate
the README to mention both tabs exist, or (b) after `expandFirstCard`, do an
additional `clickTab`-equivalent on the Even/Odd week button via `page.evaluate`.
Option (a) is simpler and sufficient for a showcase README.

**Warning signs:** Screenshot shows Odd schedule when Even was expected (or vice
versa) on re-runs.

### Pitfall 4: `hass.states` missing calendar entity

**What goes wrong:** The calendar mode card's entity `<select>` renders
"No calendar entities found in Home Assistant" instead of the configured entity.

**Why it happens:** The calendar entity must exist in `mockHass.states` for the
`panel.hass?.states` filter (`id.startsWith("calendar.")`) to find it.

**How to avoid:** Include a `'calendar.work_meetings': { state: 'off',
attributes: { friendly_name: '…' } }` entry in every calendar-mode scenario's
mock `hass.states`.

**Warning signs:** Select renders "No calendar entities found" in screenshot.

### Pitfall 5: Font rendering variance between docker runs

**What goes wrong:** PNG pixel diff between runs on different machines/CI if
system font differs.

**Why it happens:** Docker image `playwright:v1.49.0-noble` ships Noto fonts;
the harness CSS specifies `font-family: Roboto, "Noto Sans", sans-serif`. Noto
Sans is the fallback that actually renders in docker. This is consistent across
runs of the same image.

**How to avoid:** Do not pin to exact-pixel comparisons. Screenshots are committed
as documentation PNGs, not test fixtures; visual acceptance is manual.

**Warning signs:** Only a problem if someone adds pixel-diff CI checks.

### Pitfall 6: Root Makefile `screenshots` dependency ordering

**What goes wrong:** Use-case screenshots start before `panel.js` is built.

**Why it happens:** If `use-case-screenshots` is not chained **after** the
existing docker Playwright run (which itself follows `build`), the use-case
Makefiles run against a stale `panel.js`.

**How to avoid:** Append `$(MAKE) use-case-screenshots` at the **end** of the
`screenshots` recipe body (after the docker run), so `build` has already run.

---

## Code Examples

### Minimal `screenshot.js` patch (backward-compatible)

```javascript
// Source: docs/screenshot.js lines 33-34 (proposed replacement)
const SCREENSHOTS_DIR =
  process.env.OUTPUT_DIR
    ? path.resolve(process.env.OUTPUT_DIR)
    : path.join(__dirname, "screenshots");

// Source: docs/screenshot.js line 108 (proposed replacement)
const HARNESS_PATH =
  process.env.HARNESS_PATH || "/docs/test-harness.html";
// …
await page.goto(`http://localhost:${PORT}${HARNESS_PATH}`);
```

### Existing wait-for-ready gate (unchanged)

```javascript
// Source: docs/screenshot.js lines 111-118
await page.waitForFunction(
  () => {
    const el = document.querySelector("#mount climate-manager-panel");
    return el?.shadowRoot?.querySelector(".tab-bar") != null;
  },
  undefined,
  { timeout: 20000 },
);
await page.waitForTimeout(800); // let Lit settle
```

This gate is robust: it waits for the actual `.tab-bar` DOM node in the shadow
root, which only appears after the mock `hass` fires `get_config` and the panel
renders. The 800 ms Lit settle is conservative and already tested to be
sufficient.

### Existing root Makefile `screenshots` recipe (reference)

```makefile
# Source: Makefile lines 39-45
screenshots: build
	@mkdir -p docs/screenshots
	docker run --rm --ipc=host \
		-v "$$(pwd):/app" \
		-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
		mcr.microsoft.com/playwright:v1.49.0-noble \
		bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null \
		  && node screenshot.js"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate HA test panel captures | Mock harness-driven Playwright | Phase ~5 | CI-safe, docker-reproducible |
| `global_mode` / `default_zone_name` flat keys | `default_zone` object | Phase 14 | Harness already updated; no further change |
| `room_mode` per-room override | Rooms always follow zone (no `room_mode`) | Phase 15 | Mock CONFIG needs no `room_mode` key |
| `STATUS.global_mode` / `active_period` at root | `STATUS.zones` record keyed by zone id | Phase 14 | Harness already updated |

**Deprecated/outdated:**
- `room_mode`: removed. Phase 15 (D-07). Do NOT include in scenario CONFIG rooms.
- `global_mode`, `global_time_program`, `default_zone_name`: replaced by
  `default_zone` object in Phase 14.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | docker container clock uses UTC; ISO week parity will be consistent across CI runs on the same day | Pitfall 3 | Screenshots may flip parity between CI runs on week boundaries — mitigated by accepting either parity |
| A2 | `$(MAKE) -C "$$dir"` in a shell `for` loop correctly inherits the root Makefile's `MAKE` variable across GNU make versions present on the host | Architecture Patterns §4 | Nested make may invoke wrong binary — fallback: use `make -C` explicitly |
| A3 | The persons-tab `hasDeviceTrackers` prop is populated from `hass.states[personId].attributes.device_trackers` (array) — a non-empty array makes HA option show clean label | Per-Scenario CONFIG §D-10 | Badge renders `"⚠ HA (no trackers)"` instead of `"HA"` — cosmetic only for docs |

---

## Open Questions

1. **Per-scenario capture sequence granularity**
   - What we know: `clickTab` and `expandFirstCard` exist in the shared driver.
     The driver currently captures 6 fixed screenshots.
   - What's unclear: Should each scenario ship its own capture sequence script,
     or should the shared driver support a `CAPTURE_SEQUENCE` env var (e.g.,
     `"overview,persons"`) that selects which screenshots to take?
   - Recommendation: For simplicity, each scenario harness ships its own capture
     script (20–30 lines), importing the helpers exported from a refactored
     `screenshot.js`. If the planner prefers zero refactoring, the shared driver
     can default to capturing Overview + Persons-expanded only when `HARNESS_PATH`
     is set (i.e., when running in scenario mode).

2. **even_odd week-switcher screenshot**
   - What we know: `_activeWeek` recalculates on expand; cannot be controlled
     from the harness CONFIG.
   - What's unclear: Whether the README should show both Even and Odd tabs, or
     just one.
   - Recommendation: Capture one screenshot showing whichever week is active,
     then use a `page.evaluate` click on the tab button to capture the other
     week. Both PNGs are included in the scenario `screenshots/` folder and
     referenced from the README.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | All screenshot Makefiles | Assumed present (used by existing `make screenshots`) | host-dependent | None — required |
| GNU make | Root + per-use-case Makefiles | Assumed present | host-dependent | None — required |
| node / npm | `docs/npm install` inside docker | ✓ (inside docker image) | docker-bundled | — |
| `panel.js` build | All harness.html files | ✓ if `make build` ran | — | Run `make build` first |

**Missing dependencies with no fallback:** None beyond what existing `make
screenshots` already requires.

---

## Validation Architecture

`nyquist_validation` is enabled in `.planning/config.json`.

This phase has no automated unit tests — all correctness is demonstrated by the
presence of committed PNGs and the exit code of `make screenshots`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Shell exit-code validation + file-existence checks |
| Config file | none |
| Quick run command | `make screenshots 2>&1 \| tail -5` |
| Full suite command | `make screenshots` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | Five `docs/use-cases/<slug>/` directories each contain `README.md` and at least one PNG in `screenshots/` | smoke | `find docs/use-cases -name 'README.md' \| wc -l` (expect 5) and `find docs/use-cases -name '*.png' \| wc -l` (expect ≥5) | ❌ Wave 0 |
| DOC-01 | `make screenshots` exits 0 | smoke | `make screenshots` | n/a — command |

### Sampling Rate

- **Per task commit:** Visual inspection of generated PNGs
- **Per wave merge:** `make screenshots` full run (exit 0)
- **Phase gate:** `find docs/use-cases -name 'README.md' | wc -l` returns 5,
  `make screenshots` exits 0, PNGs committed

### Wave 0 Gaps

- [ ] `docs/use-cases/` directory — created in Wave 0 (5 slug subdirs)
- [ ] `docs/use-cases/*/Makefile` — created per scenario
- [ ] `docs/use-cases/*/harness.html` — created per scenario
- [ ] `docs/screenshot.js` — 2-line env-var patch applied
- [ ] Root `Makefile` `use-case-screenshots` target — added

---

## Security Domain

This phase introduces no network endpoints, authentication, user input handling,
or secrets. It is documentation-only tooling. ASVS categories V2–V6 do not apply.

---

## Sources

### Primary (HIGH confidence)

- `docs/screenshot.js` — read directly; all API/contract claims verified
- `docs/test-harness.html` — read directly; CONFIG/STATUS schema verified
- `frontend/src/types.ts` — read directly; PersonConfig field names verified
- `frontend/src/components/person-card.ts` — read directly; render logic,
  mode constants, schedule_type handling verified
- `Makefile` (root) — read directly; `screenshots` recipe verified
- `.planning/phases/17-person-scheduling-use-case-docs/17-CONTEXT.md` —
  locked decisions

### Secondary (MEDIUM confidence)

- `docs/architecture.md` — read for architecture context
- `.planning/REQUIREMENTS.md` — DOC-01 text confirmed

### Tertiary (LOW confidence)

None.

---

## Metadata

**Confidence breakdown:**
- Screenshot pipeline mechanics: HIGH — read directly from source files
- PersonConfig schema and mode rendering: HIGH — read directly from types.ts
  and person-card.ts
- Root→local Makefile delegation: HIGH — standard GNU make, no exotic features
- Docker CWD pitfalls: HIGH — derived directly from existing Makefile recipe
- Even/odd parity behaviour: HIGH — read directly from person-card.ts `updated()`

**Research date:** 2026-06-05
**Valid until:** 2026-07-05 (stable codebase; no planned changes to harness
or PersonConfig schema before this phase executes)
