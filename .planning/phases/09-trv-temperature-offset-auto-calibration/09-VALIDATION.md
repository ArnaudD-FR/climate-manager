---
phase: 9
slug: trv-temperature-offset-auto-calibration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-30
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-homeassistant-custom-component |
| **Config file** | `setup.cfg` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_trv.py tests/test_coordinator.py -v` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_trv.py tests/test_coordinator.py -v`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 1 | CALIB-03 | — | `supports_offset_calibration` returns `True` when `temperature_offset` attribute present | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-01-02 | 01 | 1 | CALIB-03 | — | `supports_offset_calibration` returns `True` when service registered but attribute absent | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-01-03 | 01 | 1 | CALIB-03 | — | `supports_offset_calibration` returns `False` when neither attribute nor service present | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-01-04 | 01 | 1 | CALIB-03 | — | `supports_offset_calibration` returns `False` when entity state is `None` | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-01-05 | 01 | 1 | CALIB-02 | — | `set_trv_offset` issues one `tado_x.set_temperature_offset` call with correct entity_id and offset | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-01-06 | 01 | 1 | CALIB-02 | — | `set_trv_offset` silently skips unavailable entity | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-01-07 | 01 | 1 | CALIB-02 | — | `set_trv_offset` silently skips missing entity | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-02-01 | 02 | 2 | CALIB-04 | — | `calibration_enabled: False` → zero offset service calls | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-02-02 | 02 | 2 | CALIB-05 | — | Room without `temperature_sensor` → zero offset service calls | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-02-03 | 02 | 2 | CALIB-03 | — | Incompatible TRV (no attribute, no service) → zero offset calls | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-02-04 | 02 | 2 | CALIB-04 | — | Delta ≤ 0.5°C → zero offset calls | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-02-05 | 02 | 2 | CALIB-04 | — | Delta > 0.5°C → one offset call with `new_offset = existing_offset + delta` | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-02-06 | 02 | 2 | CALIB-02 | — | Sensor state "unavailable" → zero offset calls | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-02-07 | 02 | 2 | CALIB-02 | — | Sensor state "unknown" → zero offset calls | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-02-08 | 02 | 2 | CALIB-02 | — | `current_temperature` is `None` → zero offset calls | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-03-01 | 03 | 3 | CALIB-01 | T-03-04 | `set_calibration_config {"enabled": true}` persists `calibration_enabled: True` | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-03-02 | 03 | 3 | CALIB-01 | T-03-04 | `set_calibration_config {"enabled": false}` persists `calibration_enabled: False` | unit | `make test` | ❌ W0 | ⬜ pending |
| 9-04-01 | 04 | 4 | CALIB-01 | — | Options card renders with ha-switch in Global Settings tab | manual | n/a | n/a | ⬜ pending |
| 9-04-02 | 04 | 4 | CALIB-01 | — | Toggle auto-saves on change; persists after reload | manual | n/a | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All new tests extend existing files — no new test files are needed for backend:

- [ ] `tests/test_trv.py` — add `supports_offset_calibration` tests (9-01-01 through 9-01-04)
- [ ] `tests/test_trv.py` — add `set_trv_offset` tests (9-01-05 through 9-01-07)
- [ ] `tests/test_coordinator.py` — add calibration pass tests (9-02-01 through 9-02-08)
- [ ] `tests/test_websocket.py` — add `set_calibration_config` WS command tests (9-03-01, 9-03-02)

*Existing test infrastructure covers all phase requirements — no new files, no
new fixtures needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Options card visible in Global Settings tab | CALIB-01 | Frontend rendering requires live HA 2026.x instance | Navigate to Global Settings; confirm "Options" ha-card with calibration toggle appears as third card |
| Toggle auto-saves on change | CALIB-01 | WS integration requires live panel | Click toggle; reload page; confirm persisted state matches |
| ha-switch renders (vs. invisible fallback) | CALIB-01 | HA 2026.x component compatibility | If toggle is invisible, fall back to native `<input type="checkbox">` per CONTEXT.md D-12 specifics |
| Calibration applies offset on real Tado X hardware | CALIB-02 | Live TRV hardware required | Enable calibration; set room sensor 1°C above TRV reading; wait one evaluate cycle; confirm `temperature_offset` attribute changes |
| Incompatible TRV silently skipped on live HA | CALIB-03 | Hardware-dependent service registry | With a non-Tado X TRV room, enable calibration; confirm no errors and no offset service calls in HA logs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
