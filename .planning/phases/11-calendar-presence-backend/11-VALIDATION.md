---
phase: 11
slug: calendar-presence-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-02
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-homeassistant-custom-component |
| **Config file** | `pyproject.toml` — `asyncio_mode = "auto"`, `testpaths = ["tests"]` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_calendar.py -v -x` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -v` (or `make test`) |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_calendar.py -v -x`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| constants | 01 | 1 | CAL-01 | PRESENCE_CALENDAR constant defined | unit | `pytest tests/test_calendar.py::test_constants` | ❌ W0 | ⬜ pending |
| schedule-helper | 01 | 1 | CAL-01 | event active → absent (event_means=absent) | unit | `pytest tests/test_calendar.py::test_calendar_mode_absent_during_event` | ❌ W0 | ⬜ pending |
| schedule-helper | 01 | 1 | CAL-01 | no event → present (event_means=absent) | unit | `pytest tests/test_calendar.py::test_calendar_mode_present_no_event` | ❌ W0 | ⬜ pending |
| schedule-helper | 01 | 1 | CAL-01 | error → fallback absent, WARNING logged once | unit | `pytest tests/test_calendar.py::test_calendar_fallback_on_error` | ❌ W0 | ⬜ pending |
| schedule-period | 01 | 1 | CAL-03 | period state "calendar" resolves via calendar_config | unit | `pytest tests/test_calendar.py::test_calendar_period_state_resolves` | ❌ W0 | ⬜ pending |
| preheat | 01 | 1 | CAL-04 | event ending ≤ lead_minutes → present | unit | `pytest tests/test_calendar.py::test_preheat_triggers_at_boundary` | ❌ W0 | ⬜ pending |
| preheat | 01 | 1 | CAL-04 | event ending > lead_minutes → absent | unit | `pytest tests/test_calendar.py::test_preheat_no_trigger_before_boundary` | ❌ W0 | ⬜ pending |
| coordinator-cache | 02 | 1 | CAL-02 | two persons sharing entity → one get_events call | integration | `pytest tests/test_calendar.py::test_calendar_cache_deduplication` | ❌ W0 | ⬜ pending |
| coordinator-cache | 02 | 1 | CAL-02 | cache resets per evaluate cycle | integration | `pytest tests/test_calendar.py::test_calendar_cache_reset_per_cycle` | ❌ W0 | ⬜ pending |
| all-day-events | 02 | 1 | CAL-01 | all-day event (DATE string) handled without TypeError | unit | `pytest tests/test_calendar.py::test_allday_event_handling` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_calendar.py` — new file; create in Wave 1 alongside the
  implementation (test file and implementation co-created, no separate
  Wave 0 setup task needed)
- [ ] Existing `tests/conftest.py` — verify `hass` fixture available (already
  installed via pytest-homeassistant-custom-component)

*Existing infrastructure covers the harness; only new test file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Calendar entity picker populates from hass.states | CAL-01 (frontend) | Requires live HA + registered calendar.* entities | Load panel, add person in Calendar mode, verify entity picker lists available calendar.* entities |
| Person card section reorder (scheduling above rooms) | D-14 (frontend layout) | Visual layout assertion | Load panel, open person card, verify scheduling section renders above rooms list |
| event_means toggle persists on reload | D-16 (frontend) | Requires round-trip through WS + HA state | Toggle event_means, reload panel, verify selection retained |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
