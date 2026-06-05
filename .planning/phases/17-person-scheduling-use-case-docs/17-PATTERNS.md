# Phase 17: Person Scheduling Use-Case Docs — Pattern Map

**Mapped:** 2026-06-05
**Files analyzed:** 13 (2 modified + 5×harness.html + 5×Makefile + 5×README.md)
**Analogs found:** 13 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `docs/screenshot.js` | build-tooling / driver | batch (env-driven) | `docs/screenshot.js` itself | self (modify) |
| `Makefile` (root) | build-tooling / orchestrator | batch | `Makefile` itself | self (modify) |
| `docs/use-cases/simple-schedule/harness.html` | build-tooling / mock config | request-response | `docs/test-harness.html` | exact (copy + swap CONFIG block) |
| `docs/use-cases/business-calendar/harness.html` | build-tooling / mock config | request-response | `docs/test-harness.html` | exact (copy + swap CONFIG block) |
| `docs/use-cases/student-mixed-schedule/harness.html` | build-tooling / mock config | request-response | `docs/test-harness.html` | exact (copy + swap CONFIG block) |
| `docs/use-cases/rotating-shift-worker/harness.html` | build-tooling / mock config | request-response | `docs/test-harness.html` | exact (copy + swap CONFIG block) |
| `docs/use-cases/shared-custody-odd-even-weeks/harness.html` | build-tooling / mock config | request-response | `docs/test-harness.html` | exact (copy + swap CONFIG block) |
| `docs/use-cases/simple-schedule/Makefile` | build-tooling | batch | root `Makefile` `screenshots` target | role-match |
| `docs/use-cases/business-calendar/Makefile` | build-tooling | batch | root `Makefile` `screenshots` target | role-match |
| `docs/use-cases/student-mixed-schedule/Makefile` | build-tooling | batch | root `Makefile` `screenshots` target | role-match |
| `docs/use-cases/rotating-shift-worker/Makefile` | build-tooling | batch | root `Makefile` `screenshots` target | role-match |
| `docs/use-cases/shared-custody-odd-even-weeks/Makefile` | build-tooling | batch | root `Makefile` `screenshots` target | role-match |
| `docs/use-cases/<slug>/README.md` ×5 | documentation | — | `docs/architecture.md` | role-match (Markdown structure) |

---

## Pattern Assignments

### `docs/screenshot.js` — MODIFY (env-var parameterisation)

**Analog:** `docs/screenshot.js` (self)

**Current hard-coded values to replace** (lines 33–34 and 108):

```javascript
// BEFORE — docs/screenshot.js line 33-34
const PROJECT_ROOT = path.resolve(__dirname, "..");
const SCREENSHOTS_DIR = path.join(__dirname, "screenshots");

// AFTER — replace line 34 only
const SCREENSHOTS_DIR =
  process.env.OUTPUT_DIR
    ? path.resolve(process.env.OUTPUT_DIR)
    : path.join(__dirname, "screenshots");
```

```javascript
// BEFORE — docs/screenshot.js line 108
await page.goto(`http://localhost:${PORT}/docs/test-harness.html`);

// AFTER — replace with two lines: declare HARNESS_PATH then use it
const HARNESS_PATH =
  process.env.HARNESS_PATH || "/docs/test-harness.html";
// ...
await page.goto(`http://localhost:${PORT}${HARNESS_PATH}`);
```

**Existing readiness gate — keep verbatim** (lines 111–120):

```javascript
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

**Existing helper API — keep verbatim** (lines 126–169):

```javascript
async function clickTab(label) { … }           // lines 126-137
async function expandFirstCard(componentTag) { … } // lines 144-169
```

**`out()` helper and capture logic — keep verbatim** (lines 174–211):

```javascript
const out = (p) => path.join(SCREENSHOTS_DIR, p);
```

**Critical constraint:** `SCREENSHOTS_DIR` is created at line 83 with
`fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true })` — this already handles
non-existent per-scenario `screenshots/` subdirectories without any change.

**Backward compatibility:** When `OUTPUT_DIR` and `HARNESS_PATH` are unset the
existing `make screenshots` run is completely unchanged.

---

### Root `Makefile` — MODIFY (add `use-case-screenshots` target)

**Analog:** root `Makefile` (self), specifically the `screenshots` target at
lines 39–45.

**Current `screenshots` recipe** (lines 39–45 — keep unchanged, append to it):

```makefile
screenshots: build
	@mkdir -p docs/screenshots
	docker run --rm --ipc=host \
		-v "$$(pwd):/app" \
		-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
		mcr.microsoft.com/playwright:v1.49.0-noble \
		bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null && node screenshot.js"
```

**Additions required:**

1. Append `$(MAKE) use-case-screenshots` as the last line of the `screenshots`
   recipe body (after the docker run), so `build` has already completed.
2. Add `.PHONY: use-case-screenshots` to the `.PHONY` line.
3. Add the new target:

```makefile
use-case-screenshots:
	@for dir in docs/use-cases/*/; do \
		if [ -f "$$dir/Makefile" ]; then \
			echo "--- $$dir ---"; \
			$(MAKE) -C "$$dir" screenshots; \
		fi \
	done
```

**Indent rule:** The root `Makefile` uses tab indentation (matches `.editorconfig`
`Makefile` rule). The `for` loop body lines inside the recipe must also be
tab-indented.

**`.PHONY` line** — current line 8:
```makefile
.PHONY: build deploy test lint logs screenshots release
```
becomes:
```makefile
.PHONY: build deploy test lint logs screenshots use-case-screenshots release
```

---

### `docs/use-cases/<slug>/harness.html` ×5 — CREATE

**Analog:** `docs/test-harness.html` (full file, 273 lines)

**Copy strategy:** Copy `docs/test-harness.html` verbatim, then replace
**only the inline `<script type="module">` block** (lines 150–271) with the
per-scenario CONFIG and STATUS objects. Everything else is identical:

- Lines 1–145: HTML head, CSS variables, HA web component stubs — **identical**
- Line 147: `<script type="module" src="/custom_components/climate_manager/www/panel.js">` — **identical** (absolute URL path required; relative paths break under the static server)
- Lines 150–271: mock `<script type="module">` block — **replaced per scenario**

**Shared structure of the replacement `<script type="module">` block:**

```html
<script type="module">
  const CONFIG = {
    period_temperatures: {
      frost_protection: 7, reduced: 16, normal: 20, comfort: 22
    },
    default_zone: {
      name: 'Home', mode: 'time_program', time_program: { /* weekday/weekend prog */ }
    },
    zones: {},
    rooms: {
      bedroom:     {},
      living_room: {},
    },
    persons: {
      /* SCENARIO-SPECIFIC ENTRY — see per-scenario CONFIG sections below */
    },
    climate_entities: [],
  };

  const STATUS = {
    global_mode: 'time_program',
    active_period: 'normal',
    present_persons: [],
    rooms_status: [],
  };

  const mockHass = {
    connection: {
      sendMessagePromise(msg) {
        if (msg.type === 'climate_manager/get_config')
          return Promise.resolve(JSON.parse(JSON.stringify(CONFIG)));
        if (msg.type === 'climate_manager/get_status')
          return Promise.resolve(JSON.parse(JSON.stringify(STATUS)));
        return Promise.resolve({ success: true });
      },
      subscribeMessage(callback) {
        setTimeout(() => callback(JSON.parse(JSON.stringify(STATUS))), 100);
        return Promise.resolve(() => {});
      },
    },
    states: {
      /* SCENARIO-SPECIFIC STATES — see per-scenario CONFIG sections below */
    },
    areas: {},
    floors: {},
    callService() { return Promise.resolve(); },
  };

  const panel = document.createElement('climate-manager-panel');
  panel.hass   = mockHass;
  panel.narrow = false;
  panel.panel  = {};
  document.getElementById('mount').appendChild(panel);
  window.__panelReady = true;
  console.log('[harness] panel appended with hass');
</script>
```

**Source for panel element wiring:** `docs/test-harness.html` lines 263–270.

#### Per-scenario CONFIG.persons and mockHass.states values

##### D-07: `simple-schedule` (scheduled / single week)

```javascript
// CONFIG.persons
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
    tue: [
      { start: '00:00', state: 'absent' },
      { start: '07:00', state: 'present' },
      { start: '09:00', state: 'absent' },
      { start: '17:30', state: 'present' },
      { start: '23:00', state: 'absent' },
    ],
    wed: [
      { start: '00:00', state: 'absent' },
      { start: '07:00', state: 'present' },
      { start: '09:00', state: 'absent' },
      { start: '17:30', state: 'present' },
      { start: '23:00', state: 'absent' },
    ],
    thu: [
      { start: '00:00', state: 'absent' },
      { start: '07:00', state: 'present' },
      { start: '09:00', state: 'absent' },
      { start: '17:30', state: 'present' },
      { start: '23:00', state: 'absent' },
    ],
    fri: [
      { start: '00:00', state: 'absent' },
      { start: '07:00', state: 'present' },
      { start: '09:00', state: 'absent' },
      { start: '17:30', state: 'present' },
      { start: '23:00', state: 'absent' },
    ],
    sat: [{ start: '00:00', state: 'present' }],
    sun: [{ start: '00:00', state: 'present' }],
  },
}

// mockHass.states entry
'person.emma': { state: 'home', attributes: { friendly_name: 'Emma' } }
```

##### D-08: `business-calendar` (calendar mode)

```javascript
// CONFIG.persons
'person.noah': {
  mode: 'calendar',
  room_ids: ['office', 'bedroom'],
  calendar_config: {
    entity_id: 'calendar.work_meetings',
    event_means: 'absent',
    gap_handling: 'day_span',
  },
  wakeup_advance_minutes: 60,
}

// mockHass.states entries — calendar entity MUST be present or select
// renders "No calendar entities found in Home Assistant"
'person.noah':              { state: 'home',    attributes: { friendly_name: 'Noah' } },
'calendar.work_meetings':  { state: 'off',     attributes: { friendly_name: 'Work meetings' } },
```

##### D-09: `student-mixed-schedule` (scheduled / single, varied weekdays)

```javascript
// CONFIG.persons
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
    wed: [{ start: '00:00', state: 'present' }],
    thu: [
      { start: '00:00', state: 'absent' },
      { start: '08:00', state: 'present' },
      { start: '09:30', state: 'absent' },
      { start: '13:00', state: 'present' },
      { start: '14:30', state: 'absent' },
      { start: '17:00', state: 'present' },
    ],
    fri: [
      { start: '00:00', state: 'absent' },
      { start: '08:00', state: 'present' },
      { start: '11:00', state: 'absent' },
      { start: '14:00', state: 'present' },
    ],
    sat: [{ start: '00:00', state: 'present' }],
    sun: [{ start: '00:00', state: 'present' }],
  },
}

// mockHass.states entry
'person.lena': { state: 'not_home', attributes: { friendly_name: 'Lena' } }
```

##### D-10: `rotating-shift-worker` (ha mode)

```javascript
// CONFIG.persons
'person.marc': {
  mode: 'ha',
  room_ids: ['bedroom'],
}

// mockHass.states entries — device_trackers array required for clean "HA" badge
// (non-empty array → hasDeviceTrackers: true → label "HA" not "⚠ HA (no trackers)")
'person.marc': {
  state: 'not_home',
  attributes: {
    friendly_name: 'Marc',
    device_trackers: ['device_tracker.marc_phone'],
  },
}
```

##### D-11: `shared-custody-odd-even-weeks` (scheduled / even_odd)

```javascript
// CONFIG.persons
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
}

// mockHass.states entry
'person.sofia': { state: 'home', attributes: { friendly_name: 'Sofia' } }
```

---

### `docs/use-cases/<slug>/Makefile` ×5 — CREATE

**Analog:** root `Makefile` lines 39–45 (`screenshots` recipe with docker run)

**Template — instantiate with the slug for each use case:**

```makefile
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
		bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null \
		  && node screenshot.js"
```

**Critical constraints from the analog:**
- `docker run` flags are identical to the root: `--rm --ipc=host`,
  `-v "$(PROJECT_ROOT):/app"`, `-e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`
- The docker bash command MUST be `cd /app/docs && node screenshot.js` —
  working dir must be `/app/docs` so `require('playwright')` and
  `require('@mdi/js')` resolve from `docs/node_modules/`
- `PROJECT_ROOT` is derived two levels up from the use-case folder:
  `$(shell cd ../.. && pwd)` — the `-v` bind must be the project root, not the
  use-case directory
- `OUTPUT_DIR` and `HARNESS_PATH` use absolute `/app/…` paths (inside docker)
- Indent: tab characters (Makefile convention, enforced by `.editorconfig`)

**Slug values for the five Makefiles:**

| Use-case folder | SLUG value |
|---|---|
| `simple-schedule` | `simple-schedule` |
| `business-calendar` | `business-calendar` |
| `student-mixed-schedule` | `student-mixed-schedule` |
| `rotating-shift-worker` | `rotating-shift-worker` |
| `shared-custody-odd-even-weeks` | `shared-custody-odd-even-weeks` |

---

### `docs/use-cases/<slug>/README.md` ×5 — CREATE

**Analog:** `docs/architecture.md` (Markdown structure, heading hierarchy)

**Template structure** (per D-06: conceptual showcase, no step-by-step guide):

```markdown
# <Persona Name> — <Use Case Title>

<One-sentence persona summary>. This example shows how to use the
**<mode name>** presence mode.

## Configuration Summary

| Property | Value |
|---|---|
| Presence mode | `<mode>` |
| Schedule shape | <e.g. "Single week, weekdays 09:00–17:00 absent"> |
| Assigned rooms | <room list> |

## Screenshots

### Persons tab — <persona> card expanded

![<persona> person card expanded](<filename>.png)

<One-sentence annotation explaining what the screenshot shows.>

<!-- Add additional screenshot sections only where a second view
     (Overview or Rooms) adds information not visible in the card. -->
```

**Code-style constraints** (from AGENT.md / `.editorconfig`):
- 2-space indent, max 80 characters per line
- LF line endings, final newline
- No trailing whitespace

---

## Shared Patterns

### Static server path resolution
**Source:** `docs/screenshot.js` lines 40–77, `docs/test-harness.html` line 147

The static server in `screenshot.js` resolves ALL paths relative to
`PROJECT_ROOT = path.resolve(__dirname, "..")` (the repo root). Therefore:

- `panel.js` must always be loaded as `/custom_components/climate_manager/www/panel.js`
  (absolute URL path) in every harness — including per-scenario harness.html files.
  A relative `../../custom_components/…` path fails under the server.
- `HARNESS_PATH` in the env var is likewise an absolute URL path: `/docs/use-cases/<slug>/harness.html`

### Docker invocation contract
**Source:** root `Makefile` lines 39–45

Every docker run (root and per-scenario) shares the same flags:
```makefile
docker run --rm --ipc=host \
    -v "<PROJECT_ROOT>:/app" \
    -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    mcr.microsoft.com/playwright:v1.49.0-noble \
    bash -c "cd /app/docs && npm install --no-audit --no-fund 2>/dev/null && node screenshot.js"
```
Per-scenario runs add `-e OUTPUT_DIR=…` and `-e HARNESS_PATH=…` but otherwise
match this structure exactly.

### HA component stubs
**Source:** `docs/test-harness.html` lines 40–144

The five stubs (`ha-icon`, `ha-icon-button`, `ha-card`, `ha-circular-progress`,
`ha-switch`) are **copied verbatim** into every per-scenario harness.html.
Do not re-implement or simplify them — the `ha-icon` stub in particular
(shadow DOM + MDI path lookup via `window.__MDI__`) is non-trivial and tested.

### mockHass connection contract
**Source:** `docs/test-harness.html` lines 230–259

The `mockHass.connection.sendMessagePromise` must handle exactly these two
message types:
```javascript
if (msg.type === 'climate_manager/get_config') return Promise.resolve(…CONFIG…);
if (msg.type === 'climate_manager/get_status')  return Promise.resolve(…STATUS…);
return Promise.resolve({ success: true });
```
And `subscribeMessage` must push STATUS on the next tick:
```javascript
subscribeMessage(callback) {
  setTimeout(() => callback(JSON.parse(JSON.stringify(STATUS))), 100);
  return Promise.resolve(() => {});
},
```

### PersonConfig schema — current (do NOT use deprecated fields)
**Source:** RESEARCH.md §State of the Art + `docs/test-harness.html` line 202

Valid top-level CONFIG keys as of Phase 15+:
- `default_zone` object (NOT the old `global_mode` / `default_zone_name` flat keys)
- `zones` record (keyed by UUID string)
- `rooms` — no `room_mode` key per room (removed Phase 15)
- `persons` — see PersonConfig fields: `mode`, `schedule_type`, `schedule`,
  `schedule_even`, `schedule_odd`, `calendar_config`, `room_ids`,
  `wakeup_advance_minutes`

---

## No Analog Found

All files have close analogs in the codebase. No entries in this section.

---

## Metadata

**Analog search scope:** `docs/`, root `Makefile`
**Files scanned:** 4 source files (screenshot.js, test-harness.html, Makefile,
architecture.md)
**Pattern extraction date:** 2026-06-05
