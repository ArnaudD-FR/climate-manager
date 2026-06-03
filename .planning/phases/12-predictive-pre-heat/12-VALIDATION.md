---
phase: 12
slug: predictive-pre-heat
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-02
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-homeassistant-custom-component |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_preheat.py -v` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_preheat.py -v`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-??-01 | 01 | 1 | PREHEAT-01 | — | Clamp preheat_max_lead_minutes to [0,480] | unit | `pytest tests/test_preheat.py::test_room_preheat_config_stored -x` | ❌ W0 | ⬜ pending |
| 12-??-02 | 01 | 1 | PREHEAT-02 | — | N/A | unit | `pytest tests/test_preheat.py::test_preheat_trigger_fires -x` | ❌ W0 | ⬜ pending |
| 12-??-03 | 01 | 1 | PREHEAT-02 | — | N/A | unit | `pytest tests/test_preheat.py::test_default_lead_time -x` | ❌ W0 | ⬜ pending |
| 12-??-04 | 01 | 1 | PREHEAT-03 | — | N/A | unit | `pytest tests/test_preheat.py::test_sample_recorded_on_convergence -x` | ❌ W0 | ⬜ pending |
| 12-??-05 | 01 | 1 | PREHEAT-03 | — | N/A | unit | `pytest tests/test_preheat.py::test_learned_lead_average -x` | ❌ W0 | ⬜ pending |
| 12-??-06 | 01 | 1 | PREHEAT-04 | — | N/A | unit | `pytest tests/test_preheat.py::test_status_payload_preheat_fields -x` | ❌ W0 | ⬜ pending |
| 12-??-07 | 01 | 1 | PREHEAT-05 | — | N/A | unit | `pytest tests/test_preheat.py::test_next_occupied_even_odd -x` | ❌ W0 | ⬜ pending |
| 12-??-08 | 01 | 1 | PREHEAT-05 | — | N/A | unit | `pytest tests/test_preheat.py::test_next_occupied_calendar -x` | ❌ W0 | ⬜ pending |
| 12-??-09 | 01 | 1 | D-02 | — | N/A | unit | `pytest tests/test_preheat.py::test_wakeup_advance_migration -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_preheat.py` — stub all 9 test cases covering PREHEAT-01..05
  and the wakeup_advance_minutes migration (D-02)
- Existing `tests/conftest.py` has shared fixtures — no new conftest needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Room card shows "Pre-heating (→ XX.X°C)" | PREHEAT-04 | Frontend UI rendering | Enable pre-heat on a room with a scheduled person; trigger a cycle and observe room card |
| Room card shows "Pre-heat disabled — presence cannot be scheduled" | PREHEAT-04 | Frontend UI rendering | Enable pre-heat on a room whose only person is in HA mode; verify suppression warning |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
