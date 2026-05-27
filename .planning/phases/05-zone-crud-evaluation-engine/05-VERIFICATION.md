---
phase: 05-zone-crud-evaluation-engine
verified: 2026-05-27T22:00:00Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 5: Zone CRUD & Evaluation Engine Verification Report

**Phase Goal:** Complete the zone CRUD WebSocket API and wire the coordinator's evaluation engine to per-room zone-aware dispatch, so the panel (Phase 6) can drive every zone operation and temperature evaluation dispatches correctly per room's assigned zone.
**Verified:** 2026-05-27T22:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | WS command create_zone returns {zone_id, name, mode, time_program}, persists to runtime_config["zones"], and triggers coordinator.async_evaluate | VERIFIED | `_make_ws_create_zone` at websocket.py:508; returns full zone dict; `hass.async_create_task(coordinator.async_evaluate())` at line 548; test `test_ws_create_zone_returns_zone_config` passes |
| 2 | WS command rename_zone updates runtime_config["zones"][zone_id]["name"] for custom zones, and updates runtime_config["default_zone_name"] when zone_id=="default" | VERIFIED | `_make_ws_rename_zone` at websocket.py:553; sentinel branch at line 576-577; test `test_ws_rename_zone_default` asserts `"default" not in runtime_config.get("zones", {})` |
| 3 | WS command set_zone_mode updates runtime_config["zones"][zone_id]["mode"] and rejects modes outside VALID_MODES at the schema layer | VERIFIED | `_make_ws_set_zone_mode` at websocket.py:594; `vol.In(VALID_MODES)` in schema at line 601; test `test_ws_set_zone_mode` sends "bogus" and asserts failure |
| 4 | Each new handler persists via store.async_save BEFORE send_result, and dispatches coordinator.async_evaluate as a background task | VERIFIED | All 6 zone handlers follow: `async_save` → `send_result` → `async_create_task(async_evaluate())`; confirmed by reading websocket.py lines 537-548, 586-589, 624-628, 685-687, 729-732, 778-780 |
| 5 | All three create/rename/set_zone_mode handlers return ERR_NOT_FOUND when given an unknown zone_id | VERIFIED | rename_zone line 582, set_zone_mode line 620; create_zone has no zone_id lookup (creates new); test `test_ws_set_zone_mode` seeding + not_found paths covered; rename_zone "default" sentinel prevents key collision |
| 6 | delete_zone moves all rooms with zone_id==target to Default Zone (via pop, never None) and removes the zone in a single save | VERIFIED | `_make_ws_delete_zone` at websocket.py:632; rooms pop at line 673 BEFORE del at line 675; test `test_ws_delete_zone_migrates_rooms` asserts `"zone_id" not in rooms["area_a"]` |
| 7 | delete_zone failure (validate_zone_assignment raises ValueError) restores BOTH runtime_config["zones"] AND runtime_config["rooms"] from snapshots (CR-01) | VERIFIED | CR-01 snapshot at lines 667-668; restore block at lines 681-682 on ValueError; both zones_backup and rooms_backup restored |
| 8 | WS command set_zone_time_program validates via validate_daily_program BEFORE any mutation; invalid program returns ERR_INVALID_FORMAT and leaves time_program unchanged | VERIFIED | `_make_ws_set_zone_time_program` at websocket.py:692; validate called at line 714 before any runtime_config access; test `test_ws_set_zone_time_program_rejects_partial` asserts deep-equal after rejection |
| 9 | WS command reset_zone_time_program with target='default' restores _DEFAULT_DAILY_PROGRAM; target='global' restores runtime_config["global_time_program"] — both via deepcopy | VERIFIED | `_make_ws_reset_zone_time_program` at websocket.py:737; deepcopy at lines 771 and 774-775; tests `test_ws_reset_zone_time_program_default` and `test_ws_reset_zone_time_program_global` both verify isolation |
| 10 | Coordinator's async_evaluate no longer branches on global_mode at the top level — per-room zone dispatch via _resolve_zone_config | VERIFIED | `grep 'if global_mode ==' coordinator.py` → 0 matches; _resolve_zone_config at coordinator.py:245; called at lines 150 and 194 inside async_evaluate |
| 11 | EVAL-01..04: zone.mode=off → frost; zone.mode=time_program → zone schedule; zone.mode=presences → presence override; global_mode=off affects only Default Zone rooms | VERIFIED | Tests test_zone_mode_off_pushes_frost_temp, test_zone_mode_time_program_uses_zone_schedule, test_zone_mode_presences_applies_presence, test_global_mode_off_does_not_affect_custom_zones — all pass |
| 12 | EVAL-05: room_mode=custom always uses room.time_program, short-circuits zone resolution entirely | VERIFIED | coordinator.py lines 137-147: ROOM_MODE_CUSTOM branch `continue`s before _resolve_zone_config; test `test_room_mode_custom_wins_over_zone` passes (zone.mode=off, room gets Comfort 22.0) |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/climate_manager/websocket.py` | 6 zone handler factories + 17 registered commands | VERIFIED | `_make_ws_create_zone`, `_make_ws_rename_zone`, `_make_ws_set_zone_mode`, `_make_ws_delete_zone`, `_make_ws_set_zone_time_program`, `_make_ws_reset_zone_time_program` all present; `grep -c '^    websocket_api.async_register_command'` → 17 |
| `custom_components/climate_manager/coordinator.py` | `_resolve_zone_config` helper + refactored `async_evaluate` | VERIFIED | `_resolve_zone_config` at line 245; `async_evaluate` has unified per-room loop; `_evaluate_time_program` and `_evaluate_time_program_presences` both absent |
| `tests/test_websocket.py` | 19 total WS tests (9 original + 5 Plan 01 + 5 Plan 02) | VERIFIED | `grep -c '^async def test_ws_'` → 19 |
| `tests/test_coordinator.py` | `_make_runtime_config` extended with `zones_config`; 5 EVAL tests | VERIFIED | `"zones": zones_config or {}` at line 95; `"default_zone_name": "Home"` at line 96; 5 EVAL tests at lines 991-1182 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `async_register_commands` | all 6 zone factories | `websocket_api.async_register_command(hass, factory(entry))` | VERIFIED | Lines 91-96 in websocket.py; count=17 matches plan spec |
| `_make_ws_create_zone` | `runtime_config["global_time_program"]` | `copy.deepcopy(...)` — D-02 | VERIFIED | `copy.deepcopy(runtime_config["global_time_program"])` at line 535 |
| `_make_ws_delete_zone` | `runtime_config["rooms"][area_id].pop("zone_id", None)` | room migration loop | VERIFIED | `room_cfg.pop("zone_id", None)` at line 673; `del runtime_config["zones"][zone_id]` at line 675 (pop BEFORE del — Pitfall 1) |
| `_make_ws_set_zone_time_program` | `validate_daily_program(msg["program"])` | pre-save gate | VERIFIED | Line 714; `return` on `not ok` at line 716 before any runtime_config access |
| `_make_ws_reset_zone_time_program` | `copy.deepcopy(_DEFAULT_DAILY_PROGRAM)` and `copy.deepcopy(runtime_config["global_time_program"])` | target selector | VERIFIED | Lines 771 and 774-775 |
| `async_evaluate per-room loop` | `_resolve_zone_config(area_id, config)` | called for rooms without room_mode short-circuit | VERIFIED | Lines 150 and 194 in coordinator.py |
| `_resolve_zone_config` | `config.get("zones", {}).get(zone_id)` | zone lookup with Default Zone fallback | VERIFIED | Lines 252-262 in coordinator.py; fallback to `(config["global_mode"], config["global_time_program"])` for None or dangling zone_id |
| `async_evaluate` | `self._hass.bus.async_fire(f"{DOMAIN}_status_update", ...)` | end-of-evaluate event — unchanged contract | VERIFIED | Lines 240-243 in coordinator.py |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `coordinator.async_evaluate` | `desired_temps[area_id]` | per-room zone resolution via `_resolve_zone_config` + `evaluate_schedule` | Yes — reads from `runtime_config["zones"]` or `global_time_program`; not static | FLOWING |
| `ws_create_zone` | `new_zone` | `runtime_config["global_time_program"]` via `copy.deepcopy` | Yes — reads live runtime state | FLOWING |
| `ws_delete_zone` | rooms migration | iterates `runtime_config.get("rooms", {}).values()` | Yes — real room state read and mutated | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 19 WS tests pass | `uv run pytest tests/test_websocket.py -x -q` | 19 passed | PASS |
| All 5 EVAL tests pass | `uv run pytest tests/test_coordinator.py -x -k "zone_mode or global_mode_off or room_mode_custom" -q` | 5 passed | PASS |
| Full suite (117 tests) passes | `uv run pytest tests/ -x -q` | 117 passed in 3.77s | PASS |
| 17 WS commands registered | `grep -c '^    websocket_api.async_register_command' websocket.py` | 17 | PASS |
| No top-level global_mode branch | `grep 'if global_mode ==' coordinator.py \| grep -v '#'` | 0 matches | PASS |
| _evaluate_time_program removed | `grep -c 'async def _evaluate_time_program' coordinator.py` | 0 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ZONE-05 | 05-01 | User can create a new custom zone with a name | SATISFIED | `_make_ws_create_zone`; tests `test_ws_create_zone_returns_zone_config`, `test_ws_create_zone_copies_global_program` |
| ZONE-06 | 05-01 | User can rename any zone including the Default Zone | SATISFIED | `_make_ws_rename_zone` sentinel branch; tests `test_ws_rename_zone_custom`, `test_ws_rename_zone_default` |
| ZONE-07 | 05-02 | User can delete a custom zone — rooms moved to Default Zone; Default Zone cannot be deleted | SATISFIED | `_make_ws_delete_zone`; pop ordering; CR-01 snapshot; tests `test_ws_delete_zone_migrates_rooms`, `test_ws_delete_zone_not_found` |
| ZONE-08 | 05-01 | User can set any zone's mode (Off / Time program / Presences) | SATISFIED | `_make_ws_set_zone_mode` with `vol.In(VALID_MODES)`; test `test_ws_set_zone_mode` rejects "bogus" |
| ZONE-09 | 05-02 | User can edit any zone's weekly time program | SATISFIED | `_make_ws_set_zone_time_program` (validate-before-mutate) + `_make_ws_reset_zone_time_program` (deepcopy); 3 tests |
| EVAL-01 | 05-03 | Zone mode=off → frost protection | SATISFIED | coordinator.py line 152-157; test `test_zone_mode_off_pushes_frost_temp` |
| EVAL-02 | 05-03 | Zone mode=time_program → zone schedule | SATISFIED | coordinator.py line 159-167; test `test_zone_mode_time_program_uses_zone_schedule` |
| EVAL-03 | 05-03 | Zone mode=time_program_presences → presence override | SATISFIED | coordinator.py PASS 2 lines 172-215; test `test_zone_mode_presences_applies_presence` |
| EVAL-04 | 05-03 | D-10 interpretation: global_mode=off affects Default Zone rooms only; custom zones independent | SATISFIED | _resolve_zone_config returns (global_mode, global_time_program) only for zone_id=None rooms; test `test_global_mode_off_does_not_affect_custom_zones` |
| EVAL-05 | 05-03 | Per-room custom schedule wins over zone schedule | SATISFIED | coordinator.py ROOM_MODE_CUSTOM branch lines 137-147; test `test_room_mode_custom_wins_over_zone` |

**Note on EVAL-04:** REQUIREMENTS.md states "Global mode=time_program_presences → presence heating applies to all rooms regardless of zone mode." The CONTEXT.md (D-10) formally reinterprets this as: the statement means Default Zone behavior only — custom zones with mode=time_program are not overridden by global_mode. This deviation is explicitly documented in the phase context; it is a design decision, not a gap.

**Orphan check:** Requirements ASSIGN-01..03, UI-01..06 are mapped to Phase 6 in REQUIREMENTS.md — not orphaned. No Phase 5 requirements are mapped to this phase that are absent from the plans.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX markers found | — | None |
| — | — | No stub return null/empty patterns found in new handlers | — | None |
| — | — | No hardcoded empty data in rendering paths | — | None |

All new handler bodies contain real implementations: UUID generation, deepcopy, ERR_NOT_FOUND guards, CR-01 snapshots, validate-before-mutate gate. No placeholders.

---

### Probe Execution

No `probe-*.sh` scripts declared or expected for this phase. SUMMARY files reference pytest runs. Step 7c: SKIPPED (no conventional probe files; test-based verification performed in spot-checks above).

---

### Human Verification Required

None. All truths are verifiable programmatically via the test suite. Phase 6 (UI panel) requires human visual verification; that is out of scope for Phase 5.

---

## Gaps Summary

No gaps. All 12 must-have truths verified against the codebase. All 10 requirement IDs (ZONE-05 through ZONE-09, EVAL-01 through EVAL-05) satisfied by implementation and tests. Full test suite (117 tests) passes including the 19 new WS tests and 5 new EVAL tests introduced in this phase.

---

_Verified: 2026-05-27T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
