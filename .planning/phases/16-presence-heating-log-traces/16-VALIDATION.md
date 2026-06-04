---
phase: 16
slug: presence-heating-log-traces
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-04
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-homeassistant-custom-component |
| **Config file** | `pytest.ini` / `pyproject.toml` (existing) |
| **Quick run command** | `make test` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~60 seconds (249 baseline tests) |

---

## Sampling Rate

- **After every task commit:** Run `make test`
- **After every plan wave:** Run `make test` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-W0-01 | W0 | 0 | OBS-01 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 16-01-01 | 01 | 1 | OBS-01 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 1 | OBS-01 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 16-03-01 | 03 | 1 | OBS-01 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 16-04-01 | 04 | 2 | OBS-01 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 16-05-01 | 05 | 2 | OBS-01 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 16-06-01 | 06 | 3 | OBS-01 | — | N/A | integration | `make test` | Partial | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_eval_context.py` — EvalContext calendar cache: on-demand
  fetch, deduplication across multiple callers in same cycle
- [ ] `tests/test_zone.py` — Zone/ZoneMode state machine, INFO log on period
  change, anti-spam (no duplicate on same period), D-03 state format
- [ ] `tests/test_person.py` — Person/PersonMode presence evaluation, INFO log
  on `_last_home` flip, presence cache dedup in ctx, all five mode stubs
- [ ] `tests/test_room_domain.py` — Room.apply_setpoint delegation to TRVGroup,
  preheat/calibration state ownership
- [ ] Extended `tests/test_trv.py` — TRVGroup assembly from matter_mappings,
  anti-flap guard in TRV.push_temperature, DEBUG log fires on change/suppress
  on same, startup push fires
- [ ] Updated `tests/test_coordinator.py` — replace coordinator dict-access
  mocks with domain object method mocks; no new scenarios

*Existing `test_preheat.py`, `test_schedule.py`, `test_calendar.py` need no
structural changes — they test coordinator-level behaviour and schedule/calendar
pure functions that are unchanged.*

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
