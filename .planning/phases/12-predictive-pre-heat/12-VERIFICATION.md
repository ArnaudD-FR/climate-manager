---
phase: 12-predictive-pre-heat
verified: 2026-06-03T19:41:40Z
status: complete
score: 19/19 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 14/14
  gaps_closed:
    - "PREHEAT-01: preheat_enabled moved to zone scope (GAP-01 backend — coordinator, WS, storage)"
    - "PREHEAT-01: zone Pre-heat toggle in zone editor (GAP-01 frontend — zone-tab, types, ws-client)"
    - "PREHEAT-01: room card per-room toggle removed; max-lead gated on zone enable (GAP-01 frontend)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Enable pre-heat on a ZONE (via the zone editor Pre-heat toggle).
      Assign a room with a scheduled person to that zone. Observe the room
      card during the pre-heat window (or advance clock to within 60 min of
      a scheduled present period)."
    expected: "The room card shows 'Pre-heating (→ XX.X°C)' with the correct
      target temperature formatted to 1 decimal place. The max lead time
      input is visible. No per-room Pre-heat checkbox appears."
    why_human: "Lit template rendering of the pre-heat status line and the
      zone-scoped max-lead conditional require a live HA panel session.
      All data flows are confirmed; visual output needs a browser."
  - test: "Enable pre-heat on a zone that has a room whose only assigned
      person is in 'HA' (live tracking) mode. Open the Rooms tab."
    expected: "The room card shows 'Pre-heat disabled — presence cannot be
      scheduled'. Disabling the zone Pre-heat toggle makes the warning
      disappear."
    why_human: "The dual-gate condition (zone-derived enabled && preheat_suppressed)
      requires a real HA panel session to confirm the conditional branch and
      reactive update when the zone toggle changes."
  - test: "Toggle the zone Pre-heat checkbox ON and OFF in the zone editor.
      Observe the room card's max lead time input for a room in that zone."
    expected: "When the zone toggle is ON, the max lead time number input
      appears in the room card. When OFF, it disappears. Changing the max
      lead value triggers auto-save and shows a toast."
    why_human: "Zone-to-room data flow through panelConfig and conditional DOM
      rendering via Lit reactive properties require a browser."
---

# Phase 12: Predictive Pre-Heat Verification Report

**Phase Goal:** Rooms can opt in to pre-heat; the coordinator starts heating
before the next scheduled normal/comfort period using a learned inertia
factor; the panel shows pre-heating status and a suppression warning when
applicable. Zone-scoped pre-heat enable (PREHEAT-01) was corrected in
gap-closure plans 12-06/12-07 so preheat_enabled is per-zone not per-room.
**Verified:** 2026-06-03T09:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap-closure plans 12-06 and 12-07

## Re-verification Summary

Previous verification (2026-06-02T19:15:00Z) left status `human_needed` at
14/14 truths verified. Human UAT (plan 12-05) found GAP-01: preheat_enabled
granularity was wrong (per-room instead of per-zone). Gap-closure plans
12-06 (backend) and 12-07 (frontend) were executed. This re-verification
confirms all 19 must-haves (14 original + 5 GAP-01 additions) are satisfied
and no regressions were introduced.

**Gaps closed:** 3 (all GAP-01 backend and frontend corrections)
**Regressions:** 0 (219/219 tests pass, build clean)

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | next_occupied_at() returns the next present datetime for scheduled (single) persons | VERIFIED | `def next_occupied_at` in schedule.py; `test_next_occupied_scheduled_single` PASSES |
| 2  | next_occupied_at() respects ISO-week parity per future day for even_odd persons | VERIFIED | `target_date.isocalendar().week % 2` in `_next_occupied_scheduled`; `test_next_occupied_even_odd` and `test_next_occupied_even_odd_crosses_week_boundary` PASS |
| 3  | next_occupied_at() returns the calendar event boundary for calendar-mode persons | VERIFIED | `_next_occupied_calendar` dispatched; `test_next_occupied_calendar_absent` and `test_next_occupied_calendar_present` PASS |
| 4  | next_occupied_at() returns None for ha / force_present / force_absent modes | VERIFIED | `if mode in (PRESENCE_HA, PRESENCE_PRESENT, PRESENCE_ABSENT): return None`; `test_next_occupied_ha_returns_none` and `test_next_occupied_force_modes_return_none` PASS |
| 5  | DEFAULT_PREHEAT_MAX_LEAD_MINUTES and related constants exist in const.py | VERIFIED | const.py: `DEFAULT_PREHEAT_MAX_LEAD_MINUTES=120`, `PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD=3`, `PREHEAT_MAX_SAMPLES=5`, `PREHEAT_CONVERGENCE_THRESHOLD=0.2` |
| 6  | Stored persons[*].preheat_lead_minutes is migrated to wakeup_advance_minutes at load | VERIFIED | storage.py pop() rename loop; migration tests PASS |
| 7  | Coordinator takes earliest non-None next_occupied_at; pre-heat-enabled room receives set_temperature before transition | VERIFIED | `_async_preheat_room` iterates persons, computes earliest; `test_preheat_trigger_fires` PASSES |
| 8  | Pre-heat never fires for frost-locked / MODE_OFF rooms | VERIFIED | `self._frost_locked_rooms` checked before any set_temperature in `_async_preheat_room`; `test_preheat_respects_frost_lock` PASSES |
| 9  | Sample learning and convergence detection correct (D-07, D-08, D-09) | VERIFIED | Convergence records `{duration_minutes, timestamp}` capped at PREHEAT_MAX_SAMPLES; discard clears without sample; `test_sample_recorded_on_convergence`, `test_sample_discarded_when_period_starts`, `test_default_lead_time`, `test_learned_lead_average` PASS |
| 10 | climate_manager_preheat Store wired into ClimateManagerData | VERIFIED | `__init__.py` `preheat_store` and `preheat_samples` fields; Store constructed and loaded in async_setup_entry |
| 11 | Room status payload carries preheat_active, preheat_target, preheat_suppressed | VERIFIED | `_build_status_payload` and `ws_get_status` both add all three fields with `.get(area_id, default)` pattern; `test_status_payload_preheat_fields` and `test_ws_get_status_preheat_fields` PASS |
| 12 | set_room_config clamps preheat_max_lead_minutes [0,480] and silently drops preheat_enabled (GAP-01) | VERIFIED | websocket.py: int [0,480] drop-on-invalid for max_lead; `incoming_config.pop("preheat_enabled", None)` — deprecated room key silently dropped; `test_ws_set_room_preheat_config` and `test_ws_room_max_lead_clamped` PASS |
| 13 | set_person_config accepts and clamps wakeup_advance_minutes to [0,480] | VERIFIED | websocket.py legacy preheat_lead_minutes renamed then [0,480] int clamp; `test_ws_set_person_wakeup_advance` PASSES |
| 14 | RoomConfig/RoomStatus carry preheat fields; room card renders Pre-heat section with auto-save | VERIFIED | types.ts `preheat_max_lead_minutes?` on RoomConfig only (preheat_enabled removed); `preheat_active?/preheat_target?/preheat_suppressed?` on RoomStatus; room-card.ts `_renderPreheatSection`, `_onPreheatMaxLeadChange` present |
| 15 | preheat_enabled is read from the room's ZONE, not the room (GAP-01 backend) | VERIFIED | coordinator.py `_async_preheat_room`: reads `default_zone_preheat_enabled` (no zone_id) or `zones[zone_id].get("preheat_enabled", False)` (custom zone); no `room_config.get("preheat_enabled")` call exists |
| 16 | A new WS command persists preheat_enabled on a zone (Default or custom) | VERIFIED | `_make_ws_set_zone_preheat` registered at websocket.py line 110; dual-path: `zone_id=="default"` writes `default_zone_preheat_enabled`, UUID writes `zones[zone_id]["preheat_enabled"]`; CR-01 snapshot/rollback on save failure; `test_ws_set_zone_preheat` and `test_ws_set_zone_preheat_default` PASS |
| 17 | Existing rooms with preheat_enabled=True migrate to their zone on load | VERIFIED | storage.py lines 156-169: pop() on every room unconditionally; if was True, promote to zone or `default_zone_preheat_enabled`; `test_migration_room_preheat_to_zone` PASSES (custom-zone and Default-Zone variants) |
| 18 | Zone editor shows Pre-heat toggle that saves via set_zone_preheat (GAP-01 frontend) | VERIFIED | zone-tab.ts `_onPreheatToggle` arrow-fn calls `this.ws.setZonePreheat(this.zoneId, enabled)` then reloadConfig + showToast; checkbox bound to `zoneConfig?.preheat_enabled`; works for Default (`zoneId="default"`) and custom zones without branching |
| 19 | Room card has no per-room enable; max-lead gated on zone enable; status lines preserved | VERIFIED | `_onPreheatToggle` absent from room-card.ts; `_renderPreheatSection` derives `enabled` from `panelConfig.zones[zoneId].preheat_enabled` or `panelConfig.default_zone_preheat_enabled`; max-lead input rendered only when `enabled`; active/suppressed status lines read from `roomStatus` unchanged |

**Score:** 19/19 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/climate_manager/schedule.py` | next_occupied_at() pure-Python helper | VERIFIED | `def next_occupied_at` present; pure Python, no HA imports; all 8 next_occupied tests pass |
| `custom_components/climate_manager/const.py` | Phase 12 pre-heat constants + GAP-01 schema doc | VERIFIED | All four constants correct; schema doc updated: room `preheat_enabled` removed, zone + `default_zone_preheat_enabled` documented |
| `custom_components/climate_manager/storage.py` | wakeup_advance_minutes migration + GAP-01 room→zone migration | VERIFIED | D-02 pop() rename loop + GAP-01 room-preheat-to-zone promotion, unconditional pop |
| `tests/test_preheat.py` | 29 tests covering all phase behaviors | VERIFIED | 29 tests, all PASS in 0.94s |
| `custom_components/climate_manager/coordinator.py` | _async_preheat pass + zone-scoped enable read | VERIFIED | `_async_preheat`, `_async_preheat_room`; preheat_enabled read from zone/default, not room_config |
| `custom_components/climate_manager/__init__.py` | climate_manager_preheat Store wired | VERIFIED | preheat_store + preheat_samples on ClimateManagerData; Store loaded in async_setup_entry |
| `custom_components/climate_manager/websocket.py` | ws_get_status parity + clamps + set_zone_preheat command | VERIFIED | Three preheat fields in ws_get_status; preheat_max_lead clamp in ws_set_room_config; preheat_enabled dropped from room handler; set_zone_preheat registered |
| `frontend/src/types.ts` | preheat_enabled on ZoneConfig + default_zone_preheat_enabled on ClimateConfig; removed from RoomConfig | VERIFIED | ZoneConfig has `preheat_enabled?: boolean`; ClimateConfig has `default_zone_preheat_enabled?: boolean`; RoomConfig has only `preheat_max_lead_minutes?` (no preheat_enabled) |
| `frontend/src/ws-client.ts` | setZonePreheat(zoneId, enabled) method | VERIFIED | Method at line 134; sends `climate_manager/set_zone_preheat` |
| `frontend/src/components/zone-tab.ts` | Zone Pre-heat toggle with auto-save | VERIFIED | `_onPreheatToggle` handler + checkbox at render line 598 |
| `frontend/src/components/room-card.ts` | Removed room toggle; zone-scoped max-lead + status lines | VERIFIED | `_onPreheatToggle` absent; `_renderPreheatSection` reads `panelConfig` zone enable; max-lead and status lines preserved |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| tests/test_preheat.py | schedule.next_occupied_at | direct import | WIRED | import confirmed; all 8 next_occupied tests pass |
| storage.async_load | persons[*].wakeup_advance_minutes | post-merge pop() migration | WIRED | lines 148-154; migration tests pass |
| storage.async_load | zones[zone_id]/default_zone_preheat_enabled | GAP-01 room-to-zone migration | WIRED | lines 156-169; `test_migration_room_preheat_to_zone` passes |
| coordinator.async_evaluate | coordinator._async_preheat | awaited call after _async_calibrate | WIRED | `await self._async_preheat(config)` before bus.async_fire |
| coordinator._async_preheat_room | zone config preheat_enabled / default_zone_preheat_enabled | zone_id lookup | WIRED | zone_id branch and None-zone_id branch both verified; no room_config.get("preheat_enabled") |
| coordinator._async_preheat_room | schedule.next_occupied_at | earliest non-None across persons | WIRED | `next_occupied_at` called per person |
| coordinator._build_status_payload | room_entry preheat fields | _preheat_active/_preheat_target/_preheat_suppressed dicts | WIRED | `.get(area_id, default)` pattern |
| websocket.ws_get_status | coordinator._preheat_active/_preheat_target/_preheat_suppressed | room_entry field reads | WIRED | Direct dict reads; `test_ws_get_status_preheat_fields` passes |
| websocket.ws_set_zone_preheat | runtime_config zones / default_zone_preheat_enabled | dual-path default sentinel | WIRED | `zone_id=="default"` and UUID paths; CR-01 rollback on failure |
| frontend/zone-tab.ts | ws.setZonePreheat | auto-save on toggle change | WIRED | `_onPreheatToggle` calls `this.ws.setZonePreheat(this.zoneId, enabled)` |
| frontend/room-card.ts._renderPreheatSection | panelConfig zone preheat_enabled | zone_id lookup | WIRED | Reads `panelConfig.zones[zoneId].preheat_enabled` or `panelConfig.default_zone_preheat_enabled` |
| frontend/room-card.ts._renderPreheatSection | RoomStatus preheat_active/preheat_target/preheat_suppressed | this.roomStatus reads | WIRED | All three fields read with null-safe chaining |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| coordinator._async_preheat_room | preheat_enabled | Zone config lookup via zone_id (GAP-01); reads live runtime_config each cycle | Yes — live config from Store, not hardcoded | FLOWING |
| coordinator._build_status_payload | preheat_active/preheat_target/preheat_suppressed | `_preheat_active/_preheat_target/_preheat_suppressed` dicts populated by `_async_preheat_room` | Yes — set by convergence/trigger logic | FLOWING |
| websocket.ws_get_status room_entry | preheat_active/preheat_target/preheat_suppressed | Direct reads of coordinator instance dicts | Yes — same live dicts as push path | FLOWING |
| room-card._renderPreheatSection | enabled (zone-scoped) | `this.panelConfig.zones[zoneId].preheat_enabled` or `this.panelConfig.default_zone_preheat_enabled` | Yes — panelConfig is the authenticated get_config WS payload | FLOWING |
| room-card._renderPreheatSection | preheat_active/preheat_suppressed | `this.roomStatus` received from panel status push/fetch | Yes — bound to live coordinator state via WS | FLOWING |
| preheat_samples store | {duration_minutes, timestamp} | Written only on convergence in `_async_preheat_room`; read to compute learned lead | Yes — real measured convergence data | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 29 preheat tests pass | `.venv/bin/python -m pytest tests/test_preheat.py -v` | 29 passed in 0.94s | PASS |
| Full test suite (219 tests, no regressions) | `.venv/bin/python -m pytest tests/ -q` | 219 passed in 7.66s | PASS |
| Frontend bundle builds clean | `make build` | 181.83 kB panel.js, exit 0 | PASS |
| Coordinator reads zone-level, not room-level preheat_enabled | `grep "room_config.*preheat_enabled" coordinator.py` | no match | PASS |
| set_zone_preheat registered as WS command | `grep "set_zone_preheat" websocket.py` | `_make_ws_set_zone_preheat(entry)` registered at line 110 | PASS |
| Room-card has no per-room toggle | `grep "_onPreheatToggle" frontend/src/components/room-card.ts` | no match | PASS |
| Zone-tab has zone toggle | `grep "setZonePreheat" frontend/src/components/zone-tab.ts` | match at `_onPreheatToggle` line 225 | PASS |
| Storage migration pops deprecated room key unconditionally | storage.py line 161: `room_cfg.pop("preheat_enabled", None)` | confirmed | PASS |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PREHEAT-01 | 12-03, 12-04, 12-06, 12-07 | Pre-heat enable/disable per zone (corrected from per-room by GAP-01) + configurable max lead per room | SATISFIED | set_zone_preheat WS command; zone-tab toggle; room card shows max-lead only when zone enabled; ws_set_room_config drops preheat_enabled from room; all related tests pass |
| PREHEAT-02 | 12-01, 12-02 | Coordinator starts heating before next period using learned inertia; default 60 min | SATISFIED | `_async_preheat_room` triggers set_temperature within learned lead window; DEFAULT_PREHEAT_LEAD_MINUTES=60 until 3 samples |
| PREHEAT-03 | 12-02 | Learns thermal inertia; excludes non-converged samples | SATISFIED | Convergence branch records; discard branch skips; `test_sample_recorded_on_convergence` and `test_sample_discarded_when_period_starts` pass |
| PREHEAT-04 | 12-02, 12-03, 12-04, 12-07 | Panel shows "Pre-heating (→ XX.X°C)" and suppression warning | SATISFIED (partial human) | preheat_active/target/suppressed on all status paths; room-card renders both lines with correct gates; visual rendering requires human UAT |
| PREHEAT-05 | 12-01 | Compatible with even/odd week and calendar presence sources | SATISFIED | `_next_occupied_scheduled` uses target-day ISO-week parity; `_next_occupied_calendar` handles both event_means; tests pass |

**Note:** REQUIREMENTS.md §PREHEAT-01 still reads "per room" and the traceability
table does not list plans 12-06 and 12-07. This is a stale documentation
artifact only — the ROADMAP.md correctly documents the zone-scope change and
all 7 plans. The code correctly implements zone-scope enable.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| frontend/src/types.ts | 127 | `TODO(phase-10): no mutation path exists yet — backend const only` on `calibration_threshold` | Info | Pre-existing TODO from Phase 9/10 referencing a named follow-up phase; not introduced by Phase 12; not blocking |

No `TBD`, `FIXME`, or `XXX` markers found in any file modified by this phase.
No empty return stubs, no hardcoded empty data flowing to rendering.
No room-level `preheat_enabled` reads in coordinator, websocket, or frontend.

---

### Human Verification Required

All three visual checks require a re-run of UAT with the zone-scope UI in
place (GAP-01 blocked the original UAT session before these could be tested).

#### 1. Pre-heat status line renders during active pre-heat (zone-scope)

**Test:** Enable pre-heat on a zone via the zone editor toggle. Assign a
room with a scheduled person to that zone. Observe the room card during the
pre-heat window (advance clock to within 60 min of the next present period).
**Expected:** The room card shows "Pre-heating (→ XX.X°C)" with the correct
target temperature to 1 decimal place. No per-room Pre-heat checkbox appears.
The max lead time input is visible (zone pre-heat is enabled).
**Why human:** Lit template rendering and the `toFixed(1)` formatting require
a browser session. Data flows confirmed programmatically.

#### 2. Suppression warning renders only with both conditions true (zone-scope)

**Test:** Enable pre-heat on a zone. Assign a room whose only person is in
"HA" mode to that zone. Open the Rooms tab.
**Expected:** "Pre-heat disabled — presence cannot be scheduled" appears in
the room card. Disabling the zone Pre-heat toggle in the zone editor makes
the warning disappear.
**Why human:** The dual-gate condition (zone-derived `enabled && preheat_suppressed`)
and the reactive update when the zone config changes require a live panel
session.

#### 3. Max lead time input conditional on zone enable

**Test:** In the zone editor, toggle the Pre-heat checkbox ON. Open a room
card for a room in that zone. Toggle it OFF. Observe the room card.
**Expected:** Max lead time number input appears when zone pre-heat is ON and
disappears when OFF. Changing the max lead value triggers auto-save and toast.
**Why human:** Zone-to-room config data flow through panelConfig and conditional
DOM presence via Lit reactive properties require a browser.

---

### Gaps Summary

No gaps. All 19 must-haves are verified in the codebase with passing tests.
GAP-01 is fully closed: preheat_enabled is zone-scoped in coordinator,
websocket, storage migration, frontend types, WS client, zone editor, and
room card. 29 preheat tests and 219 total tests pass. Build is clean.

The three human verification items are visual/interactive behaviors requiring
a re-run of UAT now that the zone-scope UI exists. All underlying data flows,
wiring, and conditional logic are confirmed VERIFIED.

The REQUIREMENTS.md PREHEAT-01 text and traceability table are stale
(say "per room"; missing plans 12-06/12-07). This is a documentation gap
only — not a code gap.

---

_Verified: 2026-06-03T09:00:00Z_
_Verifier: Claude (gsd-verifier)_
