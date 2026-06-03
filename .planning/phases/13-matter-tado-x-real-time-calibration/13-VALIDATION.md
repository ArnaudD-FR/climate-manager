---
phase: 13
slug: matter-tado-x-real-time-calibration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-03
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-homeassistant-custom-component |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `make test` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make test`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-??-01 | TBD | 0 | MCALIB-01 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 13-??-02 | TBD | 0 | MCALIB-01 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 13-??-03 | TBD | 0 | MCALIB-01 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 13-??-04 | TBD | 0 | MCALIB-02 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 13-??-05 | TBD | 0 | MCALIB-02 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 13-??-06 | TBD | 0 | MCALIB-02 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_coordinator.py` — new test functions for Matter listener lifecycle (MCALIB-02), calibration routing (MCALIB-01), and `to_set` entity dispatch (D-03)
- [ ] `tests/test_websocket.py` — new test functions for `set_matter_mapping` WS handler (persist, sparse removal, listener refresh trigger)

*Existing test infrastructure and conftest.py cover the framework setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Matter entity `current_temperature` change triggers sub-minute calibration on live Tado X + Matter setup | MCALIB-01 | Requires real hardware with Matter and tado_x integrations active | Pair a Matter entity via UI, change room temp, confirm calibration fires within one HA event loop turn |
| device_id sharing between tado_x and matter integrations for same physical valve | D-05 | Requires live Tado X + Matter hardware setup | Check entity registry in HA Developer Tools: verify same `device_id` on both tado_x and matter entities for the same physical valve |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
