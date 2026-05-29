# Phase 7: Even/Odd Week Scheduling — Backend - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `schedule_type` / `schedule_even` / `schedule_odd` fields to the person
storage schema and update `resolve_presence()` in `schedule.py` to select the
correct weekly schedule based on ISO week parity. Extend `set_person_config` WS
handler with auto-seeding logic for the single→even_odd conversion. Persons
without `schedule_type` continue to behave exactly as before.

**In scope:**

- `resolve_presence()` in `schedule.py`: pick `schedule_even` or `schedule_odd`
  when `schedule_type == "even_odd"` based on `date.isocalendar().week % 2`
- `ws_set_person_config` handler in `websocket.py`: auto-seed `schedule_even`
  and `schedule_odd` from `schedule` when switching to `even_odd` and the
  person has no `schedule_even` yet
- `const.py` schema comment: document the three new person fields
- Tests: new test cases in `test_schedule.py` and `test_coordinator.py` for
  even/odd week selection and seeding
- TypeScript type stub in `frontend/src/types.ts`: add
  `schedule_type?: "single" | "even_odd"`, `schedule_even?`, `schedule_odd?`
  to `PersonConfig` (needed by Phase 8 UI — cheap to do here while touching
  the schema)

**Out of scope:**

- UI week-switcher toggle (Phase 8)
- Any new WebSocket commands — extend existing `set_person_config` only
- STORAGE_VERSION bump — purely additive, no migration needed
- TRV calibration (Phase 9)

</domain>

<decisions>
## Implementation Decisions

### Seeding Responsibility

- **D-01:** Backend auto-seeds on type switch. When `set_person_config`
  receives `schedule_type: "even_odd"` and the person currently has no
  `schedule_even` in storage, the handler deep-copies `person_config.get
  ("schedule", {})` into both `schedule_even` and `schedule_odd` before the
  sparse-merge. Frontend sends only `{person_id, schedule_type: "even_odd"}` —
  no need to read and re-send the existing schedule.
- **D-02:** On revert (even_odd → single), `schedule_even` and `schedule_odd`
  are preserved silently in storage. `schedule` (the single canonical) remains
  unchanged. If the user switches back to even_odd later, the per-week schedules
  are still there.

### WS API Shape

- **D-03:** Extend `set_person_config` only. No new WS command. Frontend
  sends `schedule_type`, `schedule_even`, `schedule_odd` via the standard
  sparse-merge payload — the same mechanism used for `mode`, `room_ids`, and
  `schedule` today.
- **D-04:** `get_config` already returns the full `persons` dict from
  `runtime_config`. New fields pass through automatically — no read-path
  handler changes needed. Frontend reads them from the existing persons payload.

### Storage Version

- **D-05:** No STORAGE_VERSION bump. Absent `schedule_type` defaults to
  `"single"` at read time. The sparse-merge pattern in `storage.py` preserves
  unknown fields — this is a zero-migration additive extension.

### Claude's Discretion

- `resolve_presence()` modification: add schedule-selection block in the
  automatic branch before the existing day-lookup. Compute
  `week_parity = now.date().isocalendar().week % 2`. If
  `schedule_type == "even_odd"`: select `schedule_even` (even week, parity 0)
  or `schedule_odd` (odd week, parity 1). Otherwise use `schedule` (default).
  This keeps the existing logic path intact for all non-even_odd persons.
- Auto-seeding guard: if `schedule_type == "even_odd"` is incoming AND the
  stored `schedule_even` is already set, do NOT overwrite it (the user may
  have edited the even-week schedule already).
- `const.py` persons sub-schema comment: add documentation for
  `schedule_type` ("single" | "even_odd", default "single"),
  `schedule_even` (same structure as `schedule`, used when even week),
  `schedule_odd` (same structure as `schedule`, used when odd week).

### Folded Todos

- **"Even/odd week presence scheduling for shared custody"**
  (2026-05-27): This IS Phase 7 — the person schema + evaluator work
  described in the todo is exactly what this phase delivers.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Primary Modification Targets

- `custom_components/climate_manager/schedule.py` — `resolve_presence()`
  function (lines 117–158): the primary change. Reads `person_config.get
  ("schedule", {})` — extend to select `schedule_even`/`schedule_odd` first
  when `schedule_type == "even_odd"`.
- `custom_components/climate_manager/websocket.py` — `_make_ws_set_person_config`
  factory (line 441+): seeding logic goes here, before the sparse-merge.
- `custom_components/climate_manager/const.py` — `DEFAULT_CONFIG` persons
  sub-schema comment (lines 130–151): update to document new fields.

### Schema & Storage Patterns

- `custom_components/climate_manager/storage.py` — sparse-merge pattern
  (lines 104–121) and migration precedents (lines 129–137). New fields follow
  the same additive extension model used for zones in v1.1.
- `custom_components/climate_manager/const.py` — `STORAGE_VERSION = 2` (no
  bump), `DEFAULT_CONFIG` persons schema, presence mode constants
  (`PRESENCE_AUTOMATIC = "scheduled"`).

### Coordinator (read-path — no changes expected)

- `custom_components/climate_manager/coordinator.py` — calls
  `resolve_presence(person_config, now)` in two places: PASS 2 presence
  override (line ~206) and `_compute_present_persons` (line ~328). No
  coordinator changes needed — `resolve_presence` signature is unchanged.

### Requirements & Roadmap

- `.planning/REQUIREMENTS.md` — SCHED-01, SCHED-02, SCHED-03, SCHED-05,
  SCHED-06 (all five backend requirements for this phase).
- `.planning/ROADMAP.md` — Phase 7 success criteria (4 observable behaviors).

### Tests (patterns to follow)

- `tests/test_coordinator.py` — existing `resolve_presence` call patterns and
  presence test fixtures. Add even/odd week test cases following the same
  `datetime(...)` fixture approach.
- `tests/test_schedule.py` — if it exists: add `resolve_presence` tests for
  the new week-parity branch.

### Frontend Types (cheap to extend here)

- `frontend/src/types.ts` — `PersonConfig` interface: add `schedule_type`,
  `schedule_even`, `schedule_odd` as optional fields so Phase 8 doesn't need
  a backend-touching plan.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `copy.deepcopy` — already imported in `const.py`; use the same import in
  `websocket.py` for seeding `schedule_even`/`schedule_odd` from `schedule`.
- `resolve_presence(person_config, now)` current shape: reads `mode`, then
  for `scheduled` mode reads `person_config.get("schedule", {})`, looks up
  `day_name`, walks sorted periods. The even/odd selection fits cleanly before
  the `schedule = person_config.get("schedule", {})` line.
- Sparse-merge pattern (storage.py): `target.update(source)` for top-level
  keys; new fields just appear after the merge. No migration required.

### Established Patterns

- **No HA imports in `schedule.py`**: pure Python only. The
  `now.date().isocalendar().week` call is stdlib — keeps the file HA-free.
- **Sparse person storage**: only non-default fields are stored. Absent
  `schedule_type` is treated as `"single"` at read time (not at write time) —
  consistent with how absent `mode` defaults to `PRESENCE_AUTOMATIC`.
- **`set_person_config` sparse-merge**: `entry.runtime_data.runtime_config
  .setdefault("persons", {}).setdefault(msg["person_id"], {}).update(payload)`
  — the seeding logic runs before this merge, injecting seeds into `payload`.

### Integration Points

- `coordinator.py` → `schedule.py`: `resolve_presence` is called with the
  raw `person_config` dict from `runtime_config["persons"]`. The `schedule_type`
  field will be present (or absent) in that dict — no coordinator change.
- `websocket.py` → `runtime_config`: the `ws_set_person_config` handler
  reads and writes `runtime_config["persons"][person_id]` directly via the
  runtime_data object. The seeding logic reads the existing stored dict before
  the merge.

</code_context>

<specifics>
## Specific Ideas

- ISO week parity formula: `now.date().isocalendar().week % 2 == 0` → even
  week → use `schedule_even`. `% 2 == 1` → odd week → use `schedule_odd`.
- Seeding guard (D-01): check `"schedule_even" not in current_person_config`
  (not just falsy) so an explicitly empty schedule isn't overwritten.
- TypeScript types: `schedule_type?: "single" | "even_odd"` with optional
  `schedule_even?: DailyProgram` and `schedule_odd?: DailyProgram` where
  `DailyProgram` is the existing per-day schedule type already in `types.ts`.

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)

- **"Rename 'ha' person presence mode to a clearer label in the UI"** (score
  0.9) — Already completed in Phase 6 D-13 ("HA home tracking"). No action.
- **"Multi-zone heating"** (score 0.6) — Delivered in Phases 4-6. No action.
- **"Pronote scheduling source"** (score 0.6) — v2 external calendar feature,
  out of scope.
- **"Add multi-language support"** (score 0.5) — deferred milestone item.
- **"Boiler demand control"** (score 0.4) — v2 feature, separate milestone.
- **"TRV temperature offset calibration"** (score 0.4) — Phase 9, not this
  phase.

</deferred>

---

*Phase: 7-Even/Odd Week Scheduling — Backend*
*Context gathered: 2026-05-29*
