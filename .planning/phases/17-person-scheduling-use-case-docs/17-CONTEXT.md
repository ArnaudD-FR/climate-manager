# Phase 17: Person Scheduling Use-Case Docs - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver five persona-driven documentation packages under `docs/use-cases/`,
each demonstrating one way to configure person presence scheduling. Each package
is a self-contained folder with a `README.md`, a `screenshots/` folder, and a
local `Makefile` that regenerates its screenshots from the mock panel harness.
The root `make screenshots` delegates to every use-case Makefile so all scenario
screenshots are produced cleanly in one command.

The five scenarios are fixed by ROADMAP.md (DOC-01): `simple-schedule`,
`business-calendar`, `student-mixed-schedule`, `rotating-shift-worker`,
`shared-custody-odd-even-weeks`.

**Not in scope:** any change to the integration's runtime behaviour, the panel
UI, or the presence-evaluation logic. This phase only documents and screenshots
existing capabilities, and extends the screenshot tooling.

</domain>

<decisions>
## Implementation Decisions

### Screenshot source & build structure
- **D-01:** Screenshots are generated from the existing **mock panel harness**
  (`docs/test-harness.html` + `docs/screenshot.js` driving the built
  `panel.js`), not from the live HA instance. Deterministic, CI/docker-friendly,
  no live HA required — satisfies the "`make screenshots` runs cleanly" success
  criterion.
- **D-02:** Each use case is a **distinct folder** under `docs/use-cases/<slug>/`
  containing `README.md`, `screenshots/`, and a **local `Makefile`** that builds
  that scenario's screenshots from a per-scenario mock config.
- **D-03:** The **root Makefile delegates** — the `screenshots` target (or a
  dedicated use-cases target it depends on) iterates the use-case folders and
  invokes each local `Makefile`. The existing 6 panel-tab screenshots
  (`docs/screenshots/`) remain as-is, separate from the per-use-case sets.

### Screenshots per use case
- **D-04:** Screenshot sets are **per-scenario** — not a fixed uniform set. The
  expanded **Persons-tab person card** (showing that persona's presence mode +
  schedule editor) is **always** included; additional views (Overview to show
  the resulting present/absent state, Rooms to show driven rooms) are added
  only where they illustrate that specific scenario's effect.
- **D-05:** The HA-tracker scenario (rotating-shift, see D-09) has **no schedule
  editor** — its person card shows the mode selector + explanatory state. Its
  screenshot deliberately contrasts the schedule-driven cards.

### README content & depth
- **D-06:** READMEs are **conceptual showcases**, not click-by-click guides.
  Each contains: a persona intro, a **config summary table** (presence mode,
  schedule shape, assigned rooms), and **annotated screenshots**. No numbered
  step-by-step reproduction walkthrough.

### Scenario definitions (mode per persona)
- **D-07:** `simple-schedule` → Scheduled, **single week**. Home mornings/
  evenings, away ~09:00–17:00 weekdays, home all weekend. The baseline example.
- **D-08:** `business-calendar` → **Calendar** mode. Presence driven by a work
  `calendar.*` entity; events mean away (meetings/travel). Showcases calendar
  integration (event_means / gap handling).
- **D-09:** `student-mixed-schedule` → Scheduled, **single week** with varied
  per-weekday hours (different class times each day); home weekends. Showcases
  that a single-week schedule can differ day to day.
- **D-10:** `rotating-shift-worker` → **HA person-entity tracking** (`ha` mode).
  Presence follows the HA `person.*` / device_tracker state directly —
  illustrates the "irregular shifts best tracked by real location" case and
  covers the `ha` mode in the doc set.
- **D-11:** `shared-custody-odd-even-weeks` → Scheduled, **even/odd weeks**.
  Even week = child present all week, odd week = absent. Showcases the even/odd
  week scheduling feature.
- **Mode coverage across the five docs:** single-week (simple, student),
  calendar (business), HA tracker (rotating-shift), even/odd (shared-custody).
  `force_present` / `force_absent` (guest) is intentionally not covered.

### Claude's Discretion
- Exact wording/layout of the config summary table and annotations.
- Exact schedule times within each persona (must match the described shape).
- Whether the root delegation is a new `use-case-docs` target that
  `screenshots` depends on, or folded directly into `screenshots` — pick
  whatever keeps the single-command success criterion true.
- Screenshot file naming within each `screenshots/` folder.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirement
- `.planning/REQUIREMENTS.md` — DOC-01 (the five use-case docs requirement).

### Screenshot tooling (to extend)
- `docs/screenshot.js` — Playwright driver: serves files, loads the harness,
  waits for `.tab-bar`, has `clickTab(label)` / `expandFirstCard(tag)` helpers,
  captures named PNGs. The per-scenario builds reuse this driver.
- `docs/test-harness.html` — mock `hass` + `CONFIG`/`STATUS` objects fed to the
  built `panel.js`. Each scenario's mock config mirrors this shape (current
  schema: `default_zone` object, `persons` map, no `room_mode`).
- `Makefile` (root) — the `screenshots` / `build` targets; `screenshots`
  rebuilds `panel.js` then runs the docker Playwright capture. Root delegation
  to per-use-case Makefiles is added here.

### Panel surface being documented
- `frontend/src/components/person-card.ts` — the Persons-tab card: presence-mode
  selector, single/even-odd schedule editor, calendar config, room associations.
  Defines what each scenario screenshot shows.
- `docs/architecture.md` §"Frontend Panel" — panel structure / tab routing.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docs/screenshot.js` harness driver and its tab/card helpers — reuse verbatim;
  parameterise by scenario config rather than rewriting capture logic.
- `docs/test-harness.html` mock `CONFIG`/`STATUS` shape (just corrected to the
  current schema this session) — the template for each scenario's mock config.
- Existing root `make screenshots` (build → docker Playwright) — the delegation
  host.

### Established Patterns
- A scenario is expressed as a **mock `CONFIG` object** (one `persons` entry in
  the relevant mode) fed to the live `panel.js`; the panel renders it exactly as
  in production. PersonMode values: `scheduled` (single / even_odd),
  `ha`, `calendar`, `force_present`, `force_absent`.
- Screenshots are committed PNGs (binary) under `docs/`.

### Integration Points
- Root `Makefile` `screenshots` target → per-use-case `docs/use-cases/<slug>/
  Makefile`.
- Each local Makefile → shared harness/driver invoked with that scenario's
  config, output into its own `screenshots/`.

</code_context>

<specifics>
## Specific Ideas

- Folder-per-use-case with a **local Makefile** per folder, orchestrated by the
  root Makefile — explicit user instruction, this is the structural anchor.
- READMEs read as showcases ("here's a household like yours and how to set it
  up") aimed at a new user choosing which scheduling mode fits.
- The real deployment already uses calendar-mode persons (`emploi_du_temps_*`
  calendars) — the business-calendar / school-timetable framings are realistic.

</specifics>

<deferred>
## Deferred Ideas

- A `force_present` / `force_absent` "guest" use case — a 6th scenario; not in
  the DOC-01 fixed five. Note for a future docs pass if desired.
- Step-by-step reproducible setup guides (rejected in favour of conceptual
  showcases) — could be a separate "getting started" doc later.

</deferred>

---

*Phase: 17-person-scheduling-use-case-docs*
*Context gathered: 2026-06-05*
