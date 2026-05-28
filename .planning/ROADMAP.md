# Roadmap: Climate Manager

## Milestones

- ✅ **v1.0 MVP** — Phases 1-3 (shipped 2026-05-26)
- 🚧 **v1.1 Heating Zones** — Phases 4-6 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) — SHIPPED 2026-05-26</summary>

- [x] Phase 1: Foundation (3/3 plans) — completed 2026-05-16
- [x] Phase 2: Backend Engines & Coordinator (2/2 plans) — completed 2026-05-17
- [x] Phase 3: WebSocket API & Frontend Panel (9/9 plans) — completed 2026-05-21

See: `.planning/milestones/v1.0-ROADMAP.md` for full phase details.

</details>

### 🚧 v1.1 Heating Zones (In Progress)

**Milestone Goal:** Rooms can be grouped into named heating zones, each with its own mode and weekly schedule. The backend evaluation hierarchy (room custom → zone → global) is enforced automatically, and the panel exposes full zone management.

- [x] **Phase 4: Zone Data Model & Storage** — Schema for zones, Default Zone invariant, v1.0 migration (completed 2026-05-27)
- [x] **Phase 5: Zone CRUD & Evaluation Engine** — WebSocket API for zone operations + full evaluation hierarchy (completed 2026-05-27)
- [ ] **Phase 6: Zone & Room Assignment UI** — Panel zones tabs, room zone badges, and assignment controls

## Phase Details

### Phase 4: Zone Data Model & Storage
**Goal**: The storage layer understands zones — every room always belongs to exactly one zone, the Default Zone always exists, and v1.0 installs migrate transparently on first load.
**Depends on**: Phase 3
**Requirements**: ZONE-01, ZONE-02, ZONE-03, ZONE-04
**Success Criteria** (what must be TRUE):
  1. Storage schema additions (`zones`, `default_zone_name`) load cleanly from existing v1.0 data with no error or data loss (STORAGE_VERSION stays at 2 — additive-only, per D-04)
  2. All rooms without a `zone_id` are interpreted as belonging to the Default Zone on first load after upgrade (no migration code needed; absent zone_id = Default Zone member per D-06)
  3. A new install always has a Default Zone present (virtual concept backed by `global_mode` + `global_time_program` + `default_zone_name` per D-01/D-02/D-03) and it cannot be removed from storage because it has no storage entry to remove
  4. Attempting to save a room with a `zone_id` referencing a non-existent zone, or two rooms sharing the same `zone_id`, is rejected at the data layer (`validate_zone_assignment` in storage.py, ZONE-04)
**Plans**: 2 plans
- [x] 04-01-PLAN.md — Python backend: const.py DEFAULT_CONFIG additions, storage.py validate_zone_assignment helper + async_save hook, tests
- [x] 04-02-PLAN.md — Frontend TypeScript stubs: ZoneConfig interface, RoomConfig.zone_id, ClimateConfig.zones/default_zone_name in types.ts

### Phase 5: Zone CRUD & Evaluation Engine
**Goal**: Users can create, rename, configure, and delete zones through the WebSocket API, and the coordinator evaluates zone mode and schedule as the authoritative layer between room-custom and global.
**Depends on**: Phase 4
**Requirements**: ZONE-05, ZONE-06, ZONE-07, ZONE-08, ZONE-09, EVAL-01, EVAL-02, EVAL-03, EVAL-04, EVAL-05
**Success Criteria** (what must be TRUE):
  1. A newly created zone with mode=off causes its assigned rooms to receive frost-protection temperature at the next coordinator evaluation cycle
  2. A zone with mode=time_program runs its own weekly schedule; rooms in it follow zone periods, not the global program
  3. Deleting a custom zone via the API moves all its rooms to the Default Zone — no room is left without a zone
  4. When global mode=time_program_presences, presence heating applies to rooms in all zones regardless of each zone's own mode
  5. A room with a custom schedule override is unaffected by its zone's mode or schedule
**Plans**: 3 plans
- [x] 05-01-PLAN.md — WS: create_zone + rename_zone + set_zone_mode handlers and 5 tests (Wave 1; ZONE-05/06/08)
- [x] 05-02-PLAN.md — WS: delete_zone + set_zone_time_program + reset_zone_time_program handlers and 5 tests (Wave 2; depends on 05-01 — same files; ZONE-07/09)
- [x] 05-03-PLAN.md — Coordinator: per-room zone-aware dispatch refactor + _resolve_zone_config helper + 5 EVAL-01..05 tests (Wave 1; parallel with 05-01; EVAL-01..05)

### Phase 6: Zone & Room Assignment UI
**Goal**: The panel exposes full zone management — zone tabs appear and disappear as zones are created or deleted, each zone is fully configurable inline, and every room card shows its zone membership and allows reassignment.
**Depends on**: Phase 5
**Requirements**: ASSIGN-01, ASSIGN-02, ASSIGN-03, UI-01, UI-02, UI-03, UI-04, UI-05, UI-06
**Success Criteria** (what must be TRUE):
  1. Tab bar shows Global Settings | Default Zone | [custom zones] | Rooms | Persons — new zone tabs appear immediately after creation, disappear after deletion
  2. Each zone tab displays zone name (inline editable), mode picker, weekly time-bar, and list of assigned rooms
  3. User can assign rooms to a zone from the zone tab and from each room card — the assignment is reflected in both views
  4. Every room card in the Rooms tab shows a zone badge with the zone name
  5. Custom zone tabs show a delete button with confirmation dialog; the Default Zone tab has no delete button
**Plans**: 3 plans
- [ ] 06-01-PLAN.md — WsClient zone methods (createZone/deleteZone/renameZone/setZoneMode/setZoneTimeProgram/resetZoneTimeProgram) + new zone-tab.ts component (name edit, mode picker, time-bar, assigned-rooms chips + search-picker, inline delete confirm)
- [ ] 06-02-PLAN.md — main.ts dynamic zone tab rendering (Overview | Default Zone | [custom zones] | + | Rooms | Persons), + button create handler, _activeTab broadened to string with stale-UUID fallback
- [ ] 06-03-PLAN.md — room-card.ts zone badge in collapsed header + zone <select> in expanded content; person-card.ts D-13 label rename "HA" → "HA home tracking"
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 3/3 | Complete | 2026-05-16 |
| 2. Backend Engines & Coordinator | v1.0 | 2/2 | Complete | 2026-05-17 |
| 3. WebSocket API & Frontend Panel | v1.0 | 9/9 | Complete | 2026-05-21 |
| 4. Zone Data Model & Storage | v1.1 | 2/2 | Complete   | 2026-05-27 |
| 5. Zone CRUD & Evaluation Engine | v1.1 | 3/3 | Complete   | 2026-05-27 |
| 6. Zone & Room Assignment UI | v1.1 | 0/3 | Not started | - |
