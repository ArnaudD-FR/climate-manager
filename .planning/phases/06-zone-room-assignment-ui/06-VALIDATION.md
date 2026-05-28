---
phase: "06"
slug: zone-room-assignment-ui
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-28
audited: 2026-05-28
gaps_found: 7
gaps_resolved: 7
gaps_escalated: 0
---

# Phase 06 — Validation Strategy

> Nyquist validation audit for Phase 6: zone-room-assignment-ui.
> Reconstructed from PLAN + SUMMARY artifacts (State B — no prior VALIDATION.md).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (asyncio_mode=auto) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_websocket.py tests/test_phase06_acceptance.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_websocket.py tests/test_phase06_acceptance.py -q`
- **After every plan wave:** `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green (128 tests)
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 06-01-T1 | 01 | 1 | UI-04 / UI-05 | structural | `uv run pytest tests/test_phase06_acceptance.py::test_zone_tab_isdefault_hides_delete tests/test_phase06_acceptance.py::test_zone_tab_isdefault_routes_global_endpoints -x` | ✅ green |
| 06-01-T2 | 01 | 1 | UI-04 / UI-05 / ASSIGN-01 | integration | `uv run pytest tests/test_websocket.py::test_ws_set_zone_time_program_accepts_full_program tests/test_websocket.py::test_ws_set_zone_mode tests/test_websocket.py::test_ws_rename_zone_custom tests/test_websocket.py::test_ws_rename_zone_default -x` | ✅ green |
| 06-02-T1 | 02 | 2 | UI-01 / UI-02 / UI-03 | structural + integration | `uv run pytest tests/test_phase06_acceptance.py::test_main_tab_global_settings_label tests/test_websocket.py::test_ws_create_zone_returns_zone_config tests/test_websocket.py::test_ws_create_zone_copies_global_program -x` | ✅ green |
| 06-03-T1 | 03 | 2 | ASSIGN-02 / ASSIGN-03 / UI-06 | structural | `uv run pytest tests/test_phase06_acceptance.py::test_room_card_zone_badge_present tests/test_phase06_acceptance.py::test_null_zone_id_payload_present -x` | ✅ green |
| 06-03-T2 | 03 | 2 | UI-06 (person-card label) | structural | `uv run pytest tests/test_phase06_acceptance.py::test_null_zone_id_payload_present -x` | ✅ green |
| 06-04-T1 | 04 | 3 | ASSIGN-01 / ASSIGN-02 | integration | `uv run pytest tests/test_websocket.py -k "set_room_config" tests/test_storage.py::test_validate_zone_assignment_rejects_explicit_null -x` | ✅ green |
| 06-04-T2 | 04 | 3 | UI-01 / UI-04 / ASSIGN-01 / ASSIGN-02 | structural + smoke | `uv run pytest tests/test_phase06_acceptance.py -x` | ✅ green |

---

## Wave 0 Requirements

Existing infrastructure covered all phase requirements — no Wave 0 installs needed.

- `tests/test_websocket.py` — extended with 4 new zone WS tests (Phase 5) + 4 new Phase 6 handler tests
- `tests/test_storage.py` — extended with `test_validate_zone_assignment_rejects_explicit_null`
- `tests/test_phase06_acceptance.py` — created by Nyquist audit (6 structural + 1 smoke)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zone tabs appear/disappear dynamically when zone is created/deleted | UI-02 | Requires browser DOM observation; no E2E framework configured | Open HA panel → + button → verify tab appears; Delete zone → verify tab disappears, active tab falls back to Global Settings |
| Click-to-edit zone name: click h2 → input appears; blur/Enter saves; Escape cancels | UI-04 | Requires user interaction and focus events in browser | Click zone name → verify input field; type new name → blur → verify name updated; try Escape → verify cancel |
| Time-bar drag shows live preview without flicker | UI-04 | Requires real browser rendering and drag events | Drag time-bar segment → verify preview updates smoothly with no flicker on intermediate renders |
| Zone badge shows correct name after zone rename | ASSIGN-03 | Requires round-trip through HA WebSocket + DOM re-render | Rename a zone → verify room card badge updates to new name immediately |
| "HA home tracking" label displays in person card badge and mode picker | D-13 | Visual verification in running panel | Open Persons tab → verify "HA home tracking" in both badge pill and mode select option |
| Default Zone tab has no Delete button visible | UI-05 | Requires visual browser check (structural test covers source; runtime check manual) | Navigate to Default Zone tab → verify no Delete button visible |

---

## Validation Audit 2026-05-28

| Metric | Count |
|--------|-------|
| Gaps found | 7 |
| Resolved (automated tests written) | 7 |
| Escalated to manual-only | 0 |
| Tests added to test_websocket.py | 1 |
| Tests added to test_phase06_acceptance.py | 6 |
| Total test suite size after audit | 128 |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands
- [x] Sampling continuity: no requirement without at least one automated check
- [x] Wave 0: existing pytest infrastructure covers all phase requirements
- [x] No watch-mode flags
- [x] Feedback latency < 5s (full suite: ~4.7s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-28
