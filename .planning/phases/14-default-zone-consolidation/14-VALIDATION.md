---
phase: 14
slug: default-zone-consolidation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-03
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with pytest-homeassistant-custom-component |
| **Config file** | `pytest.ini` / `pyproject.toml` (project root) |
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
| 14-xx-01 | const/storage | 1 | ARCH-01 | — | N/A | unit | `make test` → `test_storage.py` | ✅ (needs new tests) | ⬜ pending |
| 14-xx-02 | storage compat | 1 | ARCH-01 | — | N/A | unit | `make test` → `test_storage.py` | ❌ W0 | ⬜ pending |
| 14-xx-03 | coordinator | 1 | ARCH-01 | — | N/A | unit | `make test` → `test_coordinator.py` | ❌ W0 | ⬜ pending |
| 14-xx-04 | websocket | 2 | ARCH-01 | — | N/A | unit | `make test` → `test_websocket.py` | ❌ W0 | ⬜ pending |
| 14-xx-05 | websocket status | 2 | ARCH-01 | — | N/A | unit | `make test` → `test_websocket.py` | ❌ W0 | ⬜ pending |
| 14-xx-06 | frontend types | 3 | ARCH-01 | — | N/A | build | `make build` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_storage.py` — add compat shim tests: old format → `default_zone` synthesised; new format → direct read; day-fill in both paths
- [ ] `tests/test_coordinator.py` — update `_make_runtime_config` helper to use `default_zone` shape; update all 40+ usages; add `_last_zone_periods` tracking tests
- [ ] `tests/test_websocket.py` — add `set_zone_mode("default", ...)` tests; update `set_global_mode` test to expect removal; update `reset_room_to_global_program` → `reset_room_to_default_zone_program` assertions

*Existing test infrastructure (pytest, conftest.py, hass fixture) covers all phase requirements — only test content needs updating, not new infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Panel loads without JS errors after config migration | ARCH-01 | Browser runtime only | Deploy, open panel, check browser console for undefined errors on `global_mode` / `global_time_program` reads |
| Zone tab shows Default Zone correctly after upgrade | ARCH-01 | Visual / browser | Open Zones tab, verify Default Zone name, mode, and time program render correctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
