---
phase: 7
slug: even-odd-week-scheduling-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-homeassistant-custom-component (latest) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `make test` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~30 seconds |

Baseline: 127 passed, 1 pre-existing failure
(`test_phase06_acceptance.py::test_main_tab_overview_label`) unrelated to
Phase 7.

---

## Sampling Rate

- **After every task commit:** Run `make test`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green (127+ passed)
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 1 | SCHED-02 | — | N/A | unit | `make test` | ✅ extend | ⬜ pending |
| 7-01-02 | 01 | 1 | SCHED-02 | — | N/A | unit | `make test` | ✅ extend | ⬜ pending |
| 7-01-03 | 01 | 1 | SCHED-03 | — | N/A | unit | `make test` | ✅ extend | ⬜ pending |
| 7-02-01 | 02 | 1 | SCHED-01, SCHED-05 | T-03-06 | malformed schedule_type falls through to "single" | unit | `make test` | ✅ Wave 0 | ⬜ pending |
| 7-02-02 | 02 | 1 | SCHED-05 | — | N/A | unit | `make test` | ✅ Wave 0 | ⬜ pending |
| 7-02-03 | 02 | 1 | SCHED-06 | — | N/A | unit | `make test` | ✅ Wave 0 | ⬜ pending |
| 7-03-01 | 03 | 2 | SCHED-03 | — | N/A | — | `make test` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_schedule.py` — stubs for T-07-S1..S5 (SCHED-01..03)
- [ ] `tests/test_websocket.py` — stubs for T-07-W1..W4 (SCHED-05, SCHED-06)

Specific test cases to add (from RESEARCH.md):

**`tests/test_schedule.py`:**
- `test_resolve_presence_even_odd_even_week_uses_schedule_even` (T-07-S1)
  — 2026-01-05 (ISO week 2, even) → `schedule_even` → present
- `test_resolve_presence_even_odd_odd_week_uses_schedule_odd` (T-07-S2)
  — 2026-01-12 (ISO week 3, odd) → `schedule_odd` → absent
- `test_resolve_presence_no_schedule_type_uses_schedule` (T-07-S3)
  — absent `schedule_type` → falls back to `schedule` (backward compat)
- `test_resolve_presence_explicit_single_uses_schedule` (T-07-S4)
  — explicit `schedule_type: "single"` → uses `schedule`
- `test_resolve_presence_even_odd_missing_week_schedule_returns_false`
  (T-07-S5) — `even_odd` with no `schedule_even` → `{}` → absent

**`tests/test_websocket.py`:**
- `T-07-W1` — `set_person_config` with `schedule_type="even_odd"` seeds both
  `schedule_even` and `schedule_odd` from existing `schedule` (SCHED-05)
- `T-07-W2` — seed guard: second `set_person_config` with
  `schedule_type="even_odd"` does NOT overwrite already-set `schedule_even`
- `T-07-W3` — `set_person_config` with `schedule_type="single"` does NOT touch
  `schedule_even` / `schedule_odd` (D-02)
- `T-07-W4` — after `even_odd→single` revert, `schedule_even` and `schedule_odd`
  remain in the stored person dict (D-02 preservation)

*Existing test infrastructure is in place; only new test functions are needed,
not new files or framework setup.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
