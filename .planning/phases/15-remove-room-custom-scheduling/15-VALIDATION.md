---
phase: 15
slug: remove-room-custom-scheduling
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-04
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest-homeassistant-custom-component |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `make test` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `make test`
- **After every plan wave:** Run `make test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | ARCH-02 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | ARCH-02 | — | N/A | unit | `make test` | existing | ⬜ pending |
| 15-02-01 | 02 | 2 | ARCH-02 | — | `set_room_config` drops `room_mode` silently | unit | `make test` | existing | ⬜ pending |
| 15-02-02 | 02 | 2 | ARCH-02 | — | N/A | unit | `make test` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 3 | ARCH-02 | — | N/A | unit | `make test` | existing | ⬜ pending |
| 15-04-01 | 04 | 3 | ARCH-02 | — | N/A | build | `make build` | existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_storage.py` — Phase 15 compat shim test: verify `room_mode`
  and `time_program` are absent from room records after `async_load()` when
  stored data contains them (mirrors `test_load_legacy_flat_keys_builds_default_zone`
  pattern from Phase 14)
- [ ] `tests/test_websocket.py` — verify `reset_room_to_default_zone_program`
  command no longer exists (send it, expect `success: False` — mirrors existing
  `test_ws_reset_room_to_global_program_is_removed` pattern)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Room card UI no longer shows mode picker or inline time-bar | ARCH-02 | Frontend visual inspection | Load Rooms tab; confirm no mode select dropdown, no inline time-bar, no room mode badge in header |
| Rooms still show active period status and zone name | ARCH-02 | Frontend visual inspection | Verify room header shows e.g. "Normal — 20°C" and zone name chip |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
