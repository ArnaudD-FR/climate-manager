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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change                                  |
| --------- | ------ | ----- | ------------------------------------------- |
| v1.0      | 3      | 14    | Initial workflow established                |
| v1.1      | 3      | 9     | Snapshot-rollback pattern, zone sparse model |

### Cumulative Quality

| Milestone | Tests | Notes                                      |
| --------- | ----- | ------------------------------------------ |
| v1.0      | ~90   | Backend + frontend unit/integration        |
| v1.1      | 121   | Added zone CRUD + coordinator zone tests   |

### Top Lessons (Verified Across Milestones)

1. Always complete the previous milestone archive before starting the next one
2. HA web component APIs change between releases — verify against real HA early
3. Additive schema changes with DEFAULT_CONFIG fallback avoid all migration work
