---
phase: 07-even-odd-week-scheduling-backend
verified: 2026-05-29T00:00:00Z
status: passed
score: 11/11 must-haves verified
overrides_applied: 0
---

# Phase 7: Even/Odd Week Scheduling Backend Verification Report

**Phase Goal:** Even/odd week scheduling backend — persons with
`schedule_type="even_odd"` evaluate from `schedule_even` on even ISO weeks
and `schedule_odd` on odd ISO weeks.
**Verified:** 2026-05-29
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                   | Status     | Evidence                                                                                              |
|----|--------------------------------------------------------------------------------------------------------|------------|-------------------------------------------------------------------------------------------------------|
| 1  | During an even ISO week, an even_odd person's presence is evaluated from schedule_even                  | ✓ VERIFIED | `schedule.py:142-144`: parity==0 selects `schedule_even`; confirmed by test T-07-S1 (week 2, parity 0) |
| 2  | During an odd ISO week, an even_odd person's presence is evaluated from schedule_odd                    | ✓ VERIFIED | `schedule.py:142-144`: parity==1 selects `schedule_odd`; confirmed by test T-07-S2 (week 3, parity 1) |
| 3  | A person with no schedule_type field behaves exactly as before (uses schedule)                          | ✓ VERIFIED | `schedule.py:146`: `else` branch returns `person_config.get("schedule", {})`; T-07-S3 passes           |
| 4  | A person with schedule_type=single behaves identically to absent schedule_type                          | ✓ VERIFIED | Same `else` branch covers "single"; T-07-S4 passes                                                    |
| 5  | An even_odd person missing the selected week schedule resolves to absent (no crash)                     | ✓ VERIFIED | `person_config.get(schedule_key, {})` defaults to `{}`; `if not periods: return False`; T-07-S5 passes |
| 6  | Switching a person to even_odd seeds schedule_even and schedule_odd from existing schedule              | ✓ VERIFIED | `websocket.py:461-478`: seeding block with `copy.deepcopy`; T-07-W1 passes                            |
| 7  | schedule_even and schedule_odd are independent objects after seeding (no shared reference)              | ✓ VERIFIED | Two separate `copy.deepcopy()` calls; T-07-W1 asserts `is not`                                        |
| 8  | A second switch to even_odd does not overwrite an already-stored schedule_even                          | ✓ VERIFIED | `websocket.py:470`: `"schedule_even" not in current_person` key-absence guard; T-07-W2 passes          |
| 9  | Reverting even_odd to single preserves schedule_even and schedule_odd in storage                        | ✓ VERIFIED | Revert path runs unmodified sparse-merge; T-07-W4 asserts both keys remain; T-07-W4 passes            |
| 10 | set_person_config handles all new fields — no new WS command added (D-03)                              | ✓ VERIFIED | `grep -c "@websocket_command" websocket.py` returns 0 for any new set_person_config type; existing handler extended |
| 11 | set_person_config with schedule_type=single does not add schedule_even/schedule_odd                     | ✓ VERIFIED | Seeding block guarded by `incoming.get("schedule_type") == "even_odd"`; T-07-W3 asserts absence       |

**Score:** 11/11 truths verified

---

### Required Artifacts

| Artifact                                                  | Expected                                             | Status     | Details                                                                                                            |
|-----------------------------------------------------------|------------------------------------------------------|------------|--------------------------------------------------------------------------------------------------------------------|
| `custom_components/climate_manager/schedule.py`           | resolve_presence() week-parity schedule selection    | ✓ VERIFIED | Lines 139-146: `schedule_type` read, `isocalendar().week % 2` computed, `schedule_even`/`schedule_odd` selected    |
| `custom_components/climate_manager/const.py`              | Persons sub-schema documents schedule_type/even/odd  | ✓ VERIFIED | Lines 144-147: `schedule_type`, `schedule_even`, `schedule_odd` documented with SCHED-01/03 references (4 matches) |
| `frontend/src/types.ts`                                   | PersonConfig optional even/odd fields for Phase 8    | ✓ VERIFIED | Lines 46-49: `schedule_type?`, `schedule_even?: DailyProgram`, `schedule_odd?: DailyProgram` present               |
| `tests/test_schedule.py`                                  | even/odd resolve_presence test coverage              | ✓ VERIFIED | 5 new test functions (T-07-S1 through S5) all pass                                                                 |
| `custom_components/climate_manager/websocket.py`          | set_person_config auto-seeding for even_odd switch   | ✓ VERIFIED | Lines 461-478: seeding block with key-absence guard and two independent deepcopy calls                             |
| `tests/test_websocket.py`                                 | WS seeding and revert-preservation test coverage     | ✓ VERIFIED | 4 new test functions (T-07-W1 through W4) all pass                                                                 |

---

### Key Link Verification

| From                                    | To                                             | Via                                              | Status     | Details                                                                    |
|-----------------------------------------|------------------------------------------------|--------------------------------------------------|------------|----------------------------------------------------------------------------|
| `schedule.py resolve_presence()`        | `person_config schedule_type/schedule_even/odd`| `now.date().isocalendar().week % 2` selection    | ✓ WIRED    | Lines 140-144; `.isocalendar().week` named attribute used (not `[1]`)      |
| `ws_set_person_config handler`          | `runtime_config persons[person_id] schedule`   | `copy.deepcopy` of existing schedule into payload| ✓ WIRED    | Line 473/477: `copy.deepcopy(current_person.get("schedule", {}))` called twice; inserted before setdefault sparse-merge |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase produces no UI rendering or data display components.
All artifacts are pure backend evaluator logic and schema documentation.

---

### Behavioral Spot-Checks

| Behavior                                           | Command                                                                           | Result                                    | Status  |
|----------------------------------------------------|-----------------------------------------------------------------------------------|-------------------------------------------|---------|
| Even-week person uses schedule_even                | `make test` (T-07-S1)                                                             | PASS (136 passed, 1 pre-existing failure) | ✓ PASS  |
| Odd-week person uses schedule_odd                  | `make test` (T-07-S2)                                                             | PASS                                      | ✓ PASS  |
| single→even_odd seeding via WS                     | `make test` (T-07-W1)                                                             | PASS                                      | ✓ PASS  |
| No HA imports in schedule.py (pure-Python)         | `grep -c "import homeassistant" schedule.py`                                      | 0                                         | ✓ PASS  |
| Frontend TypeScript compiles with new PersonConfig | `cd frontend && npm run build`                                                    | `built in 228ms`, 0 errors                | ✓ PASS  |

---

### Probe Execution

No probes declared in PLAN files. Step 7c: SKIPPED (no declared probes).

---

### Requirements Coverage

| Requirement | Source Plan  | Description                                                                                  | Status          | Evidence                                                                                    |
|-------------|-------------|----------------------------------------------------------------------------------------------|-----------------|---------------------------------------------------------------------------------------------|
| SCHED-01    | 07-01, 07-02| User can set schedule_type to "single" or "even_odd"; field accepted by WS write path        | ✓ SATISFIED     | `schedule_type` documented in const.py + types.ts; `websocket.py:466` reads `schedule_type` |
| SCHED-02    | 07-01       | Backend evaluator selects correct schedule based on ISO week parity at evaluation time        | ✓ SATISFIED     | `schedule.py:140-144` implements week-parity selection with `isocalendar().week % 2`         |
| SCHED-03    | 07-01       | Storage schema gains schedule_type, schedule_even, schedule_odd; existing persons default to single | ✓ SATISFIED | const.py documents all three fields; `person_config.get("schedule_type", "single")` default; T-07-S3/S4/S5 cover backward compat |
| SCHED-04    | Phase 8     | Persons UI week-switcher toggle (out of scope for Phase 7)                                   | DEFERRED        | Mapped to Phase 8 in REQUIREMENTS.md traceability table                                     |
| SCHED-05    | 07-02       | Switching single→even_odd seeds both schedule_even/odd from existing schedule                 | ✓ SATISFIED     | `websocket.py:461-478` seeding block; T-07-W1 covers seeding + independence (`is not`)      |
| SCHED-06    | 07-02       | Switching even_odd→single preserves schedule and leaves schedule_even/odd untouched           | ✓ SATISFIED     | No revert-path mutation in websocket.py; T-07-W4 asserts both keys preserved                |

All 5 Phase-7 requirement IDs (SCHED-01, SCHED-02, SCHED-03, SCHED-05, SCHED-06) are SATISFIED.
SCHED-04 is correctly deferred to Phase 8 and is not a gap.

---

### Anti-Patterns Found

Scanned all 6 files modified by phase-07 commits:
`schedule.py`, `const.py`, `types.ts`, `test_schedule.py`, `websocket.py`,
`test_websocket.py`.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | —    | —       | —        | No stubs, TBD/FIXME/XXX markers, empty returns, or placeholder text found in phase-07 files |

**Lint note:** `make lint` fails due to `panel.js` (prettier reformatted it).
This file was not modified by any phase-07 commit (verified via
`git diff-tree` for all 5 commits: 3737a90, 2ca2900, 4cd9231, bcbdafc, 48ae046).
The failure is pre-existing and out of scope for phase-07 verification.

---

### Human Verification Required

None. All behaviors are fully verifiable via automated tests and static code
analysis. The phase delivers pure backend logic with no UI rendering paths.

---

### Gaps Summary

No gaps. All 11 must-have truths are VERIFIED. All 6 required artifacts exist,
are substantive, and are correctly wired. Both key links verified. All 5
in-scope requirement IDs satisfied. Test suite: 136 passed, 1 pre-existing
failure (unrelated `test_main_tab_overview_label`), 0 regressions introduced
by phase 07.

---

_Verified: 2026-05-29_
_Verifier: Claude (gsd-verifier)_
