---
phase: 12-predictive-pre-heat
verified: 2026-06-02T19:15:00Z
status: human_needed
score: 14/14 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Enable pre-heat on a room with a scheduled person. Wait for the
      next pre-heat window (or set clock forward). Observe 'Pre-heating
      (→ XX.X°C)' status line appears in the room card."
    expected: "The room card shows the active pre-heat status line with the
      correct target temperature rounded to 1 decimal place."
    why_human: "Visual Lit template rendering in a real HA panel session cannot
      be verified programmatically. The data flows are confirmed; the visual
      output requires a browser."
  - test: "Enable pre-heat on a room whose only assigned person is in 'HA'
      (ha) mode. Open the Rooms tab."
    expected: "The room card shows 'Pre-heat disabled — presence cannot be
      scheduled' suppression warning, and NOT the active pre-heating line."
    why_human: "Conditional rendering gate (preheat_enabled && preheat_suppressed)
      requires a live panel session to confirm the correct branch is displayed
      and that it disappears when the toggle is off."
  - test: "Toggle the Pre-heat checkbox off on a room that has it enabled.
      Verify the max lead time input disappears."
    expected: "The max lead time number input is rendered only when
      preheat_enabled is true. Turning the checkbox off collapses it."
    why_human: "Conditional DOM rendering via Lit reactive properties requires
      a browser."
---

# Phase 12: Predictive Pre-Heat Verification Report

**Phase Goal:** Add predictive pre-heat — rooms begin warming before
occupancy based on learned inertia, configurable per room from the panel.
**Verified:** 2026-06-02T19:15:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | D-03: next_occupied_at() returns the next present datetime for scheduled (single) persons | VERIFIED | `def next_occupied_at` in schedule.py line 375; `_next_occupied_scheduled` walks 7-day lookahead; `test_next_occupied_scheduled_single` PASSES |
| 2  | D-03: next_occupied_at() respects ISO-week parity per future day for even_odd persons | VERIFIED | `target_date.isocalendar().week % 2` used in `_next_occupied_scheduled`; `test_next_occupied_even_odd` and `test_next_occupied_even_odd_crosses_week_boundary` PASS |
| 3  | D-03: next_occupied_at() returns the calendar event boundary for calendar-mode persons | VERIFIED | `_next_occupied_calendar` dispatched from `next_occupied_at`; `test_next_occupied_calendar_absent` and `test_next_occupied_calendar_present` PASS |
| 4  | D-03: next_occupied_at() returns None for ha / force_present / force_absent modes | VERIFIED | `if mode in (PRESENCE_HA, PRESENCE_PRESENT, PRESENCE_ABSENT): return None` line 409; `test_next_occupied_ha_returns_none` and `test_next_occupied_force_modes_return_none` PASS |
| 5  | D-01: DEFAULT_PREHEAT_MAX_LEAD_MINUTES and related constants exist in const.py | VERIFIED | const.py lines 64-70: `DEFAULT_PREHEAT_MAX_LEAD_MINUTES=120`, `PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD=3`, `PREHEAT_MAX_SAMPLES=5`, `PREHEAT_CONVERGENCE_THRESHOLD=0.2` |
| 6  | D-02: Stored persons[*].preheat_lead_minutes is migrated to wakeup_advance_minutes at load | VERIFIED | storage.py lines 140-154: pop() rename loop after sparse-merge; `test_wakeup_advance_migration`, `test_wakeup_advance_migration_noop_when_new_key_present`, `test_wakeup_advance_migration_absent_key` all PASS |
| 7  | D-04: Coordinator takes earliest non-None next_occupied_at; pre-heat-enabled room receives set_temperature before transition | VERIFIED | `_async_preheat_room` in coordinator.py iterates assigned persons, computes earliest next_occupied_at; `test_preheat_trigger_fires` PASSES |
| 8  | Pre-heat never fires for frost-locked / MODE_OFF rooms | VERIFIED | `self._frost_locked_rooms` snapshot stored each cycle (coordinator line 194); checked at line 696 `if next_occupied is None or area_id in self._frost_locked_rooms:` before any set_temperature; `test_preheat_respects_frost_lock` PASSES |
| 9  | D-07/D-08/D-09: Sample learning and convergence detection correct | VERIFIED | Convergence branch records `{duration_minutes, timestamp}`, capped at PREHEAT_MAX_SAMPLES; discard branch clears without sample; learned lead = avg of samples capped at max; `test_sample_recorded_on_convergence`, `test_sample_discarded_when_period_starts`, `test_default_lead_time`, `test_learned_lead_average` all PASS |
| 10 | D-06: climate_manager_preheat Store wired into ClimateManagerData | VERIFIED | `__init__.py` lines 98-101: `preheat_store: "Store | None" = field(default=None)`, `preheat_samples: dict = field(default_factory=dict)`; constructed at lines 151-154 |
| 11 | D-10: Room status payload carries preheat_active, preheat_target, preheat_suppressed | VERIFIED | `_build_status_payload` in coordinator.py and `ws_get_status` in websocket.py lines 233-240 both add all three fields; `test_status_payload_preheat_fields` and `test_ws_get_status_preheat_fields` PASS |
| 12 | D-01: set_room_config clamps preheat_max_lead_minutes [0,480] and coerces preheat_enabled to bool | VERIFIED | websocket.py lines 443-457: int [0,480] drop-on-invalid for max_lead; bool() coerce for enabled; `test_ws_set_room_preheat_config`, `test_ws_room_max_lead_clamped`, `test_ws_room_enabled_coerced_bool` PASS |
| 13 | set_person_config accepts and clamps wakeup_advance_minutes to [0,480] | VERIFIED | websocket.py lines 572-588: legacy preheat_lead_minutes renamed then same [0,480] int clamp applied; `test_ws_set_person_wakeup_advance` PASSES |
| 14 | D-01/D-10/D-11: RoomConfig/RoomStatus carry preheat fields; room card renders Pre-heat section with auto-save | VERIFIED | types.ts: `preheat_enabled?:boolean`, `preheat_max_lead_minutes?:number` on RoomConfig (lines 70, 75); `preheat_active?`, `preheat_target?`, `preheat_suppressed?` on RoomStatus (lines 139, 144, 149); room-card.ts: `_renderPreheatSection`, `_onPreheatToggle`, `_onPreheatMaxLeadChange` present; section inserted after `_renderTrvSection` at line 880 |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/climate_manager/schedule.py` | next_occupied_at() pure-Python helper | VERIFIED | `def next_occupied_at` at line 375; pure Python, no HA imports; `_next_occupied_calendar`, `_next_occupied_scheduled` helpers present |
| `custom_components/climate_manager/const.py` | Phase 12 pre-heat constants | VERIFIED | All four constants at lines 64-70 with correct values |
| `custom_components/climate_manager/storage.py` | wakeup_advance_minutes migration | VERIFIED | Pop-rename loop at lines 140-154 |
| `tests/test_preheat.py` | Unit tests — 24 tests | VERIFIED | 24 tests, all PASS in 1.79s |
| `custom_components/climate_manager/coordinator.py` | _async_preheat pass + sample learning + status fields | VERIFIED | `_async_preheat`, `_async_preheat_room`, three status dicts, frost-lock guard, bus.async_fire moved after preheat |
| `custom_components/climate_manager/__init__.py` | climate_manager_preheat Store wired | VERIFIED | Fields on ClimateManagerData, Store constructed and loaded in async_setup_entry |
| `custom_components/climate_manager/websocket.py` | Pre-heat status in ws_get_status + room/person config validation | VERIFIED | Three preheat fields in ws_get_status; clamp in ws_set_room_config; wakeup_advance rename in ws_set_person_config |
| `frontend/src/types.ts` | Pre-heat fields on RoomConfig + RoomStatus; wakeup_advance_minutes on PersonConfig | VERIFIED | All fields present; no `preheat_lead_minutes` on PersonConfig |
| `frontend/src/components/room-card.ts` | _renderPreheatSection with auto-save | VERIFIED | `_renderPreheatSection`, `_onPreheatToggle`, `_onPreheatMaxLeadChange` present; called after `_renderTrvSection` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| tests/test_preheat.py | schedule.next_occupied_at | direct import | WIRED | `from custom_components.climate_manager.schedule import` confirmed; all 8 next_occupied tests pass |
| storage.async_load | persons[*].wakeup_advance_minutes | post-merge migration loop | WIRED | `wakeup_advance_minutes` pop() at lines 149-154; migration tests pass |
| coordinator.async_evaluate | coordinator._async_preheat | awaited call | WIRED | `await self._async_preheat(config)` at coordinator line 223, after `_async_calibrate`, before bus.async_fire |
| coordinator._async_preheat_room | schedule.next_occupied_at | earliest non-None across persons | WIRED | `next_occupied_at` called per person in `_async_preheat_room` |
| coordinator._build_status_payload | room_entry preheat fields | _preheat_active/_preheat_target/_preheat_suppressed dicts | WIRED | `.get(area_id, False/None/False)` pattern at coordinator lines matching D-10 |
| websocket.ws_get_status | coordinator._preheat_active/_preheat_target/_preheat_suppressed | room_entry field reads | WIRED | `coordinator._preheat_active.get(area_id, False)` etc. at websocket.py lines 233-240 |
| websocket.ws_set_room_config | rooms[room_id] preheat keys | clamp + sparse update | WIRED | Clamp block at lines 443-457 runs BEFORE the setdefault/update |
| frontend/src/components/room-card.ts | ws.setRoomConfig | auto-save on toggle/number change | WIRED | `this.ws.setRoomConfig(this.roomId, { preheat_enabled: enabled })` in `_onPreheatToggle`; `{ preheat_max_lead_minutes: val }` in `_onPreheatMaxLeadChange` |
| frontend/src/components/room-card.ts | RoomStatus.preheat_active/preheat_target/preheat_suppressed | this.roomStatus reads in _renderPreheatSection | WIRED | `this.roomStatus?.preheat_active`, `this.roomStatus?.preheat_suppressed` in _renderPreheatSection |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| coordinator._build_status_payload | preheat_active / preheat_target / preheat_suppressed | `_preheat_active/_preheat_target/_preheat_suppressed` dicts populated by `_async_preheat_room` during every eval cycle | Yes — set by convergence/trigger logic, not hardcoded | FLOWING |
| websocket.ws_get_status room_entry | preheat_active / preheat_target / preheat_suppressed | Reads coordinator instance dicts directly via `.get(area_id, default)` | Yes — same live dicts as push path | FLOWING |
| room-card._renderPreheatSection | preheat_active, preheat_suppressed | `this.roomStatus` received from panel status push/fetch | Yes — bound to live coordinator state via WS | FLOWING |
| preheat_samples store | {duration_minutes, timestamp} samples | Written only on convergence (`current_temp >= target - threshold`) by `_async_preheat_room`; read to compute learned lead | Yes — real measured data, not hardcoded | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 24 preheat tests pass | `.venv/bin/python -m pytest tests/test_preheat.py -v` | 24 passed in 1.79s | PASS |
| Constants importable with correct values | `.venv/bin/python -c "from custom_components.climate_manager import const; assert const.DEFAULT_PREHEAT_MAX_LEAD_MINUTES == 120 and const.PREHEAT_MAX_SAMPLES == 5"` | exit 0 | PASS (values confirmed in source) |
| next_occupied_at pure Python — no HA imports | `grep "import homeassistant" schedule.py` | no match | PASS |
| wakeup_advance_minutes migration uses pop() | `grep "pop.*preheat_lead_minutes" storage.py` | lines 149, 154 confirmed | PASS |
| frost_locked_rooms checked before set_temperature in _async_preheat_room | `grep "_frost_locked_rooms" coordinator.py` | guard at line 696, before trigger at line 746 | PASS |
| bus.async_fire after _async_preheat | `grep -n "async_preheat\|async_fire" coordinator.py` | `_async_preheat` at line 223, `async_fire` at line 228 | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PREHEAT-01 | 12-03, 12-04 | Per-room enable/disable + configurable max lead time from panel | SATISFIED | ws_set_room_config validates preheat_enabled/preheat_max_lead_minutes; room-card.ts checkbox + number input with auto-save |
| PREHEAT-02 | 12-01, 12-02 | Coordinator starts heating before next period using learned inertia; default 60 min | SATISFIED | `_async_preheat_room` triggers set_temperature within learned lead window; DEFAULT_PREHEAT_LEAD_MINUTES=60 used until 3 samples |
| PREHEAT-03 | 12-02 | Learns thermal inertia from heating cycles; excludes non-converged samples | SATISFIED | Convergence branch records sample; discard branch explicitly skips recording; `test_sample_recorded_on_convergence` and `test_sample_discarded_when_period_starts` pass |
| PREHEAT-04 | 12-02, 12-03, 12-04 | Panel shows "Pre-heating (→ XX.X°C)" and suppression warning | SATISFIED (partial human) | preheat_active/preheat_target/preheat_suppressed on all status paths; room-card renders both status lines with correct gates; visual rendering requires human |
| PREHEAT-05 | 12-01 | Compatible with even/odd week and calendar presence sources | SATISFIED | `_next_occupied_scheduled` uses target-day ISO-week parity; `_next_occupied_calendar` handles absent/present event_means; `test_next_occupied_even_odd` and calendar tests pass |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| const.py | 174 | Comment doc still says `"preheat_lead_minutes": 60` in the persons sub-schema | Info | Documentation-only; the storage comment block describes the schema shape before D-02 migration. The migration itself is correct; the comment is a minor stale doc, not blocking. |

No `TBD`, `FIXME`, or `XXX` markers found in any file modified by this phase.
No empty return stubs, no hardcoded empty data flowing to rendering.

### Human Verification Required

#### 1. Pre-heating status line renders correctly

**Test:** Enable pre-heat on a room assigned to a scheduled person. Observe
the room card in the Rooms tab during the pre-heat window (or advance the
system clock to within 60 min of a scheduled present period).
**Expected:** The room card displays "Pre-heating (→ XX.X°C)" where XX.X is
the upcoming period's target temperature formatted to 1 decimal place.
**Why human:** Lit template rendering and the `toFixed(1)` formatting require
a browser session. All upstream data flows are confirmed; the visual output
cannot be asserted via grep.

#### 2. Suppression warning renders only when both conditions are true

**Test:** Set a room's only assigned person to "HA" mode, then enable
pre-heat on that room. Open the Rooms tab.
**Expected:** "Pre-heat disabled — presence cannot be scheduled" appears in
the room card. Disabling the pre-heat checkbox should make the warning
disappear.
**Why human:** The dual-gate condition (`preheat_enabled && preheat_suppressed`)
requires a real HA panel session to confirm the conditional branch and the
reactive update when the checkbox is toggled.

#### 3. Max lead time input conditional display

**Test:** Toggle the Pre-heat checkbox on a room. Observe that the max lead
time number input appears. Toggle it off. Observe the input disappears.
**Expected:** The `<input type="number">` for max lead time is rendered only
when `preheat_enabled` is true; removing focus or changing the value triggers
auto-save and shows a toast.
**Why human:** Conditional DOM presence and toast interaction require a browser.

### Gaps Summary

No gaps. All 14 must-haves are verified in the codebase with passing tests.
The three human verification items are visual/interactive behaviors that
cannot be confirmed programmatically — all their underlying data flows,
wiring, and logic are confirmed VERIFIED.

---

_Verified: 2026-06-02T19:15:00Z_
_Verifier: Claude (gsd-verifier)_
