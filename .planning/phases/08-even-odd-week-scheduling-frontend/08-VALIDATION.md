---
phase: 8
slug: even-odd-week-scheduling-frontend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python backend); frontend is manual-only |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `.venv/bin/python -m pytest tests/ -v -k "schedule"` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds (Python suite) |

**Note:** There is no automated frontend test harness. Lit component behavior
is verified by TypeScript compilation (`make build`) and manual inspection
against ROADMAP success criteria.

---

## Sampling Rate

- **After every task commit:** Run `make build` — TypeScript compilation is the
  automated gate
- **After every plan wave:** Run `make build && .venv/bin/python -m pytest
  tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green + manual verification
  of all SCHED-04 behaviors
- **Max feedback latency:** Build feedback ~30 seconds; manual verification
  ~5 minutes

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | SCHED-04 | — | N/A | build | `make build` | ✅ | ⬜ pending |
| 08-01-02 | 01 | 1 | SCHED-04 | — | N/A | build | `make build` | ✅ | ⬜ pending |
| 08-01-03 | 01 | 1 | SCHED-04 | — | N/A | build | `make build` | ✅ | ⬜ pending |
| 08-02-01 | 02 | 2 | SCHED-04 | — | N/A | manual | — | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

No new test files, no new pytest fixtures, and no new framework installation
are needed. `frontend/src/components/person-card.ts` is built with the
existing Vite/TypeScript setup via `make build`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Schedule-type select appears only in Scheduled mode | SCHED-04 | No frontend test harness | Open a person card in HA panel; set Presence mode to "Scheduled" → schedule-type select is visible; set to any other mode → select disappears |
| Even/Odd switcher absent for single-schedule persons | SCHED-04 | No frontend test harness | Set a person to Single schedule → confirm Even/Odd buttons are not rendered in the DOM |
| Even/Odd switcher present for even_odd persons | SCHED-04 | No frontend test harness | Set schedule_type to "Even / Odd weeks" → confirm `[Even]` and `[Odd]` buttons appear above the time-bar |
| Default active week matches current ISO week parity | SCHED-04 | No frontend test harness | Expand a newly-opened even/odd person card → active tab must match current ISO week (even week 22 → Even tab active) |
| Time-bar edits in Even tab save to `schedule_even` only | SCHED-04 | No frontend test harness | Click "Even" tab → drag a time segment → reload → verify `schedule_even` changed but `schedule_odd` is unchanged (check via WS response payload) |
| Time-bar edits in Odd tab save to `schedule_odd` only | SCHED-04 | No frontend test harness | Click "Odd" tab → drag a time segment → reload → verify `schedule_odd` changed but `schedule_even` unchanged |
| Switching tabs redraws time-bar without losing other week | SCHED-04 | No frontend test harness | Edit Even week → switch to Odd → edit Odd week → switch back to Even → Even week edits must be preserved |
| Changes persist after reload | SCHED-04 | No frontend test harness | Make schedule edits on both Even and Odd weeks → reload panel → both weeks' schedules match what was saved |
| Reset Even week resets only Even schedule | SCHED-04 | No frontend test harness | Set Even/Odd person → edit both weeks → click "Reset Even week to default" → Even week resets; Odd week unchanged |
| Single-mode reset button label and behavior unchanged | SCHED-04 | No frontend test harness | Set person to Single schedule → reset button shows "Reset to default" and resets `schedule` field |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify (build) or listed in manual table
- [ ] Sampling continuity: `make build` runs after each implementation task
- [ ] Wave 0 covers all MISSING references (none needed)
- [ ] No watch-mode flags in any verification command
- [ ] Feedback latency: `make build` < 60s for automated; manual < 5 min
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
