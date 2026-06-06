# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into
future planning.*

---

## Milestone: v1.0 — MVP

**Shipped:** 2026-05-26
**Phases:** 3 | **Plans:** 14

### What Was Built

- HACS-compatible HA integration with ConfigFlow, Store persistence,
  two-call TRV control
- Full scheduling engine: weekday time programs, four period modes,
  per-room override
- Person presence engine with periodic schedules and room associations
- Coordinator with concurrent asyncio.gather TRV dispatch (<1s vs 10s)
- WebSocket API (8 commands) + Lit/TypeScript Lovelace panel
- Interactive time-bar with Android touch support

### What Worked

- TDD approach: RED→GREEN→REFACTOR kept backend quality high
- Lit 3 + Shadow DOM composed naturally with HA `ha-*` web components
- Two-call TRV control pattern (heat mode → set_temperature) proved robust
  across Matter/Tado X quirks

### What Was Inefficient

- Android touch support required multiple debug cycles — would have been
  cleaner to prototype on device earlier
- HA version compatibility not tested early enough; several HA 2026.x
  breaking changes discovered late

### Patterns Established

- Factory-closure pattern for WebSocket handlers
- write-then-reload for all WS mutations (await ws.X → reloadConfig →
  showToast)
- Memoized days getter in time-bar to prevent drag flicker on re-renders

### Key Lessons

1. Test HA version compatibility early — the ha-* web component API shifts
   between HA releases
2. Shadow DOM isolation is required when embedding custom elements inside Lit
   templates — light DOM mutations displace ChildPart markers

---

## Milestone: v1.1 — Heating Zones

**Shipped:** 2026-05-28
**Phases:** 3 (Phases 4-6) | **Plans:** 9

### What Was Built

- Zone data model: `zones` dict in DEFAULT_CONFIG, `validate_zone_assignment`,
  TypeScript ZoneConfig — additive, STORAGE_VERSION unchanged
- Zone CRUD WebSocket API: 6 new commands (17 total), snapshot-rollback on
  delete
- Coordinator refactored to per-room zone-aware dispatch loop
- ZoneTab Lit component (~590 lines) with inline name edit, mode picker,
  memoized time-bar, chip room assignment
- Dynamic zone tabs with color palette (8 colors, dots on tabs and badges)

### What Worked

- Additive schema extension (no STORAGE_VERSION bump) — v1.0 data loads
  cleanly without any migration
- Snapshot-rollback pattern for delete_zone kept atomicity simple and testable
- Sparse model (absent zone_id = Default Zone) eliminated the need for a
  sentinel ID and simplified all assignment logic

### What Was Inefficient

- Discovered HA 2026.x breaking changes (ha-textfield, ha-select, ha-tabs all
  broken) mid-phase — required rework of UI components already partially built
- gsd-new-milestone was run before v1.1 archive was created, so v1.1
  REQUIREMENTS.md was deleted before archival; had to reconstruct from git
  history

### Patterns Established

- HA 2026.x compatibility rule: use only native `<input>`, `<select>` — no
  ha-textfield, ha-select, ha-tabs, paper-tab, ha-dialog
- Shadow DOM for `ha-icon` stubs in screenshot harness to avoid Lit ChildPart
  marker displacement
- MDI SVG rendering via @mdi/js + page.addInitScript injection in Playwright

### Key Lessons

1. Run `/gsd-complete-milestone` BEFORE `/gsd-new-milestone` — the new
   milestone workflow deletes REQUIREMENTS.md immediately
2. HA web component compatibility must be tested against the actual HA version
   in production before building UI components that depend on them
3. Zone IDs as UUIDs (not names) future-proofs rename operations

---

## Milestone: v1.2 — Presence & Calibration

**Shipped:** 2026-05-31
**Phases:** 3 (Phases 7-9) | **Plans:** 9

### What Was Built

- Even/odd week scheduling backend: additive person schema, ISO week parity
  selection in `resolve_presence()`, `copy.deepcopy` auto-seeding
- Pure `getISOWeekNumber`/`getWeekParity` TypeScript helpers matching Python
  exactly; 8 `node --test` assertions including year-boundary (WR-03)
- Even/odd week scheduling UI: schedule-type select, Even/Odd button-tab
  switcher, memoized dual day-array getters, week-scoped save/reset
- TRV calibration capability guard + `set_trv_offset` Tado X service helper
- TRV auto-calibration engine: delta threshold (0.5°C), periodic coordinator
  pass, silent skip for incompatible/sensor-less rooms
- `set_calibration_config` WS command + Global Settings Options card toggle
- 9 post-phase quick tasks: calibration table enhancements, floor grouping,
  Tado X refresh-rate banner, current offset display

### What Worked

- Additive schema pattern (again): absent `schedule_type` defaults to `single`,
  zero migration needed — same approach as zone sparse model in v1.1
- TDD with `node --experimental-strip-types` for frontend pure functions:
  separating helpers into `week-parity.ts` (no Lit deps) made them directly
  testable without a browser
- Phase 9 (calibration) ran independently of Phases 7-8 (scheduling) with
  no shared files — genuine parallelization opportunity
- ha-switch confirmed working in HA 2026.x despite prior uncertainty (Pitfall 6
  from PLAN turned out to be a non-issue)

### What Was Inefficient

- Verification files (08-VERIFICATION.md, 09-VERIFICATION.md) were left in
  `human_needed` state after human verification was completed in plan summaries
  — required manual close at milestone boundary
- Phase 8 progress table in ROADMAP.md showed "2/3" after Plan 03 completed
  — stale tracking not updated at plan completion

### Patterns Established

- Pure utility module pattern: extract node-testable logic from Lit components
  into a sibling `.ts` file with no browser/Lit dependencies
- TDD for frontend pure functions with `node --test --experimental-strip-types`
- Capability guard pattern for TRV features: attribute-first, service fallback,
  silent skip — avoids log spam for incompatible devices

### Key Lessons

1. Close VERIFICATION.md immediately after the human-verification plan
   completes — don't leave it as `human_needed` for the milestone close to fix
2. Pure TypeScript utilities that need unit testing must be in separate modules
   away from Lit component files (Lit decorators block Node's strip-types)
3. Test HA component behavior optimistically — ha-switch worked fine in 2026.x
   even though earlier components (ha-select, ha-textfield, ha-tabs) did not

---

## Milestone: v1.3 — Calendar Presence & Pre-heat

**Shipped:** 2026-06-06
**Phases:** 8 (Phases 10-17) | **Plans:** 35

### What Was Built

- Calendar presence backend: `calendar.*` sources, per-cycle `get_events`
  cache, `event_means` absent/present, per-period calendar state, three
  gap-handling modes, and the CAL-04 wake-up advance
- Predictive pre-heat: zone-scoped opt-in, per-room max lead, thermal-inertia
  learning (convergence after 3-5 cycles), pre-heating status + suppression UI
- Matter→Tado X real-time calibration: `state_changed` listener with
  cancel-and-rebuild lifecycle, drag-and-drop pairing UI
- Presence mode UI: "HA home tracking" label + ⚠ stuck-mode hint (always shown)
- Default Zone consolidated to a first-class `ZoneConfig` (ARCH-01); per-room
  `room_mode` override removed entirely (ARCH-02)
- Coordinator restructured into a Zone/Person/Room/TRVGroup domain graph via a
  per-cycle EvalContext, with structured presence/zone/heating log traces
  (OBS-01)
- Seven persona use-case docs whose screenshots are generated by the real
  coordinator (DOC-01)

### What Worked

- The Phase 16 domain-graph rewrite paid for itself immediately: structured log
  traces (OBS-01) fell out naturally once Zone/Person/Room were real objects
- Additive-schema + load-time migration patterns (carried from v1.1/v1.2) made
  the ARCH-01 Default Zone consolidation a non-breaking upgrade
- Running a milestone audit **before** tagging caught two real issues a
  task-completion view would have missed: the CAL-04 `wakeup_advance` no-op and
  the Phase 14 room-card flat-key regression (already fixed by a later commit)
- Use-case docs driven by the real coordinator (not hand-written status) keep
  screenshots and READMEs coherent

### What Was Inefficient

- **Recurring (lesson #4):** Phase 14 VERIFICATION.md was again left in
  `human_needed` after the blocking defect was fixed — only closed at the
  milestone audit
- CAL-04 shipped as a **no-op**: `wakeup_advance_minutes` was persisted, plumbed
  through the call chain, and documented as "Reserved... currently unused" —
  a half-wired feature that looked done but wasn't, caught only by the audit
- GSD tooling mismatch: `/gsd-quick` writes `<id>-SUMMARY.md` but `audit-open`
  and `/gsd-quick list` read `SUMMARY.md`, so 41 completed quick tasks showed as
  "open" — required a rename sweep at close

### Patterns Established

- Domain-object graph for the coordinator: Zone/Person/Room/TRVGroup evaluated
  via a per-cycle EvalContext (lazy calendar cache, dedup) — replaces the
  monolithic evaluate method and is the home for future observability
- Milestone audit as a hard gate before tag: goal-backward requirement
  cross-reference + cross-phase integration check catches half-wired features
- Pinned-time, coordinator-generated documentation screenshots

### Key Lessons

1. A persisted/plumbed parameter is not a shipped feature — if a value is
   "reserved but unused", either wire it or don't surface it. Verify behaviour
   at runtime, not just presence of the field (CAL-04)
2. Run `/gsd-audit-milestone` before `/gsd-complete-milestone` — it caught two
   issues that all phases-complete signals missed
3. Close VERIFICATION.md the moment the human sign-off lands (fourth milestone
   running into this — it is now a standing checklist item)
4. Keep tracking-artifact naming consistent with what the tooling reads; a
   prefixed-vs-unprefixed `SUMMARY.md` mismatch silently accrues "open" items

### Cost Observations

- Model mix: opus for planning/orchestration, sonnet for execution, haiku for
  plan-checks (per adaptive profile)
- Largest milestone so far by plans (35) and diff (+52k/-3.8k), driven by the
  Phase 16 coordinator rewrite touching every evaluation path

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change                                          |
| --------- | ------ | ----- | --------------------------------------------------- |
| v1.0      | 3      | 14    | Initial workflow established                        |
| v1.1      | 3      | 9     | Snapshot-rollback pattern, zone sparse model        |
| v1.2      | 3      | 9     | Pure module TDD, parallel phase execution, cap guard |
| v1.3      | 8      | 35    | Domain-object coordinator, milestone audit-before-tag gate |

### Cumulative Quality

| Milestone | Tests | Notes                                              |
| --------- | ----- | -------------------------------------------------- |
| v1.0      | ~90   | Backend + frontend unit/integration                |
| v1.1      | 121   | Added zone CRUD + coordinator zone tests           |
| v1.2      | ~140  | Added schedule parity, WS seeding, calibration TDD |
| v1.3      | 287   | Calendar/pre-heat/Matter + domain-graph coordinator |

### Top Lessons (Verified Across Milestones)

1. Always complete the previous milestone archive before starting the next one
2. HA web component APIs change between releases — verify against real HA early
   (HA 2026.x broke `ha-select`/`ha-tabs`/`ha-textfield` — use native elements)
3. Additive schema changes with DEFAULT_CONFIG fallback avoid all migration work
4. Close verification files immediately after human sign-off — don't leave
   them open for the milestone close to chase down (recurred in v1.0→v1.3)
5. Pure utility modules (no Lit deps) make frontend logic unit-testable with
   Node — a pattern worth establishing from the start in future phases
6. A persisted/plumbed parameter is not a shipped feature — verify behaviour at
   runtime, and run the milestone audit before tagging (v1.3 caught CAL-04)
