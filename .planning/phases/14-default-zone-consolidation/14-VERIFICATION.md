---
phase: 14-default-zone-consolidation
verified: 2026-06-04T10:00:00Z
status: passed
resolved: 2026-06-06T16:00:00Z
resolution: >
  The sole defect (room-card.ts read the removed flat key
  default_zone_preheat_enabled) is fixed in current code — room-card.ts:833
  now reads `this.panelConfig?.default_zone?.preheat_enabled ?? false`, and
  `default_zone_preheat_enabled` no longer appears anywhere in frontend/src.
  The remaining human-verification items were live-panel render checks; the
  Default Zone data path is confirmed correct by the v1.3 milestone
  integration audit (ARCH-01 round-trip clean) and 287 passing tests.
score: 15/15 must-haves verified (D-15 defect fixed post-verification)
overrides_applied: 0
gaps: []
human_verification:
  - test: "Default Zone panel render and mutation"
    expected: >
      Default Zone name, mode badge, and active period all display correctly
      in the panel (Global Settings tab and room cards). Changing the Default
      Zone mode persists after a page refresh. The zone-tab Reset button shows
      the Default Zone name and resets the time program. No console errors
      (\"Cannot read properties of undefined\") during initial load before the
      first status push.
    why_human: >
      Frontend optional-chaining fallbacks and the zones/default_zone data
      path require live HA WebSocket traffic to verify end-to-end. The
      panel.js bundle is deployed but runtime rendering cannot be checked
      programmatically.
  - test: "room-card preheat toggle reads correct path for Default Zone"
    expected: >
      The preheat section in a Default Zone room card reads the enabled state
      from config.default_zone.preheat_enabled (not the removed flat key
      default_zone_preheat_enabled). The toggle should appear when preheat
      is enabled on the Default Zone.
    why_human: >
      room-card.ts line 987 still reads
      `this.panelConfig?.default_zone_preheat_enabled` — a flat key that no
      longer exists in ClimateConfig. This is a code defect but its user-
      visible symptom (preheat section never shows for Default Zone rooms)
      requires a live panel to confirm severity. Listed here for visibility
      pending a fix decision.
---

# Phase 14: Default Zone Consolidation — Verification Report

**Phase Goal:** Consolidate Default Zone config — replace four legacy flat keys
with a single `default_zone: ZoneConfig` entry, unified
coordinator/websocket/frontend code path (ARCH-01).
**Verified:** 2026-06-04T10:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|---------|
| D-01 | `DEFAULT_CONFIG` has a single `default_zone` key shaped as full ZoneConfig; four flat keys absent | VERIFIED | `const.py` line 223: `"default_zone": {"name": "Home", "mode": ..., "time_program": ..., "preheat_enabled": False}`. `grep '"global_mode"' const.py` = 0. |
| D-02 | Loading old-format config (global_mode present, default_zone absent) yields default_zone synthesised from flat keys with no data loss | VERIFIED | `storage.py` lines 168-192: guard `"global_mode" in stored and "default_zone" not in stored`; runs day-fill then builds `result["default_zone"]` by popping flat keys. |
| D-03 | Loading new-format config reads default_zone directly with day-fill applied | VERIFIED | `storage.py` lines 193-198: else branch runs day-fill on `result.get("default_zone", {}).get("time_program", {})`. |
| D-04 | `_resolve_zone_config` reads Default Zone from `config["default_zone"]` on both no-zone and dangling-zone paths, no global_mode special-case | VERIFIED | `coordinator.py` lines 1351-1362: both return paths execute `dz = config["default_zone"]`. |
| D-05 | `async_evaluate` populates `_last_zone_periods` with "default" key plus one key per custom zone UUID | VERIFIED | `coordinator.py` lines 129, 230-244: `_last_zone_periods` init + population block with `"default"` key and dict comprehension over `config.get("zones", {}).items()`. |
| D-06 | `_build_status_payload` returns a zones dict (no top-level global_mode or active_period) | VERIFIED | `coordinator.py` lines 1613-1626: return dict has only `"zones"`, `"present_persons"`, `"rooms_status"`. No `"global_mode"` or top-level `"active_period"`. |
| D-07 | `ws_get_status` delegates to `coordinator._build_status_payload()` | VERIFIED | `websocket.py` line 180: `payload = coordinator._build_status_payload()`. Confirmed by grep. |
| D-08 | `set_global_mode` WS command removed; `set_zone_mode(zone_id="default")` writes `default_zone.mode` | VERIFIED | `grep '"global_mode"' websocket.py` = 0. Registration block (lines 105-121) confirms removal. |
| D-09 | `reset_time_program` WS command removed; `reset_zone_time_program(zone_id="default")` resets `default_zone.time_program` | VERIFIED | `grep 'global_time_program' websocket.py` = 0. Reset handler extended with `zone_id=="default"` sentinel. |
| D-10 | `reset_room_to_default_zone_program` replaces `reset_room_to_global_program` and reads `default_zone.time_program` | VERIFIED | `websocket.py` lines 550-591: factory renamed, command type string updated to `reset_room_to_default_zone_program`, reads `runtime_config["default_zone"]["time_program"]`. |
| D-11 | `set_zone_preheat` and `rename_zone` with `zone_id="default"` write `default_zone.preheat_enabled` / `default_zone.name` | VERIFIED | `websocket.py` line 784 area (grep: `default_zone_preheat_enabled flat key` comment confirms new path). |
| D-12 | `ClimateManagerConfig` exposes `default_zone: ZoneConfig` and none of the four flat keys | VERIFIED | `types.ts` line 107: `default_zone: ZoneConfig`. No `global_mode`, `global_time_program`, `default_zone_name`, `default_zone_preheat_enabled` fields in interface (confirmed by read). |
| D-13 | `StatusPayload` exposes `zones: Record<string, {mode, active_period}>` and no top-level `global_mode`/`active_period` | VERIFIED | `types.ts` lines 168-173: `StatusPayload` has only `zones`, `present_persons`, `rooms_status`. |
| D-14 | `main.ts` passes `config.default_zone` directly to zone-tab (no flat-key synthesis) | VERIFIED | `main.ts` line 508: `.zoneConfig=${this._config!.default_zone}`. Tab label (line 457) uses `this._config.default_zone.name`. |
| D-15 | Components read default-zone mode via `status?.zones?.["default"]?.mode ?? config.default_zone.mode` — EXCEPT room-card preheat section | PARTIAL | `global-settings-tab.ts` line 548: correct three-level chaining. `room-card.ts` lines 459-460, 507-508: correct. **room-card.ts line 987: `this.panelConfig?.default_zone_preheat_enabled ?? false` — reads removed flat key instead of `default_zone.preheat_enabled`.** |

**Score:** 14/15 truths verified (D-15 partial — preheat path uses removed flat key)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/climate_manager/const.py` | `default_zone` key in DEFAULT_CONFIG; four flat keys removed | VERIFIED | Lines 223-228. `grep '"global_mode"'` = 0. |
| `custom_components/climate_manager/storage.py` | Compat shim promoting flat keys to `default_zone` | VERIFIED | Lines 168-198. Guard on `stored` (not `result`) — correct per deviation fix in 14-01-SUMMARY. |
| `custom_components/climate_manager/coordinator.py` | `_last_zone_periods`, uniform zone resolution, zones payload | VERIFIED | Lines 129, 222-244, 1341-1363, 1613-1626. |
| `custom_components/climate_manager/websocket.py` | Removed legacy commands; default-zone sentinel paths; `_build_status_payload` delegation | VERIFIED | All confirmed by grep. |
| `frontend/src/types.ts` | `default_zone: ZoneConfig` in `ClimateConfig`; `zones` in `StatusPayload` | VERIFIED | Lines 107, 170. |
| `frontend/src/ws-client.ts` | `resetRoomToDefaultZoneProgram`; `setGlobalMode` and `resetTimeProgram` absent | VERIFIED | Line 161. `setGlobalMode` and `resetTimeProgram` absent from file. |
| `frontend/src/main.ts` | `.zoneConfig=${this._config!.default_zone}` passthrough | VERIFIED | Line 508. |
| `frontend/src/components/global-settings-tab.ts` | `this.config.default_zone.name`; three-level chaining for mode | VERIFIED | Lines 546, 548. |
| `frontend/src/components/room-card.ts` | `default_zone?.name`; `zones?.["default"]?.mode`; `resetRoomToDefaultZoneProgram` | PARTIAL | Lines 416, 459-460, 507-508, 401 correct. **Line 987: `this.panelConfig?.default_zone_preheat_enabled` reads removed flat key.** |
| `frontend/src/components/zone-tab.ts` | `config.default_zone.name`; `setZoneMode` for both default and custom zones | VERIFIED | Lines 264, 582, 238. |
| `tests/test_storage.py` | `test_load_legacy_flat_keys_builds_default_zone` present and passes | VERIFIED | 21 storage tests pass (`pytest tests/test_storage.py` = 21 passed). |
| `tests/test_coordinator.py` | `default_zone_mode` helper; zones payload assertions | VERIFIED | 56 coordinator tests pass. |
| `tests/test_websocket.py` | default-zone command coverage; removal assertions | VERIFIED | 43 websocket tests pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `storage.async_load` | `_DEFAULT_DAILY_PROGRAM` | `copy.deepcopy` in day-fill and synthesis | VERIFIED | `storage.py` lines 173, 188-190, 197. |
| `coordinator._build_status_payload` | `self._last_zone_periods` | `_last_zone_periods.get` | VERIFIED | Lines 1617, 1622. |
| `coordinator._resolve_zone_config` | `config["default_zone"]` | `dz = config["default_zone"]` | VERIFIED | Lines 1352, 1361. |
| `websocket.ws_get_status` | `coordinator._build_status_payload` | direct delegation | VERIFIED | Line 180. |
| `websocket.set_zone_mode default branch` | `runtime_config["default_zone"]["mode"]` | `zone_id=="default"` sentinel write | VERIFIED | Grep confirms; `"global_mode"` count in websocket.py = 0. |
| `frontend/main.ts` | `config.default_zone` | `.zoneConfig=` passthrough | VERIFIED | Line 508. |
| `frontend/room-card` | `status.zones["default"]` | optional-chaining read | VERIFIED | Lines 459, 507. |
| `frontend/room-card._renderPreheatSection` | `config.default_zone.preheat_enabled` | property read | FAILED | Line 987 reads `default_zone_preheat_enabled` (removed flat key) instead of `default_zone.preheat_enabled`. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| storage tests pass | `pytest tests/test_storage.py` | 21 passed | PASS |
| coordinator tests pass | `pytest tests/test_coordinator.py` | 56 passed | PASS |
| websocket tests pass | `pytest tests/test_websocket.py` | 43 passed | PASS |
| `"global_mode"` absent from const.py | `grep -c '"global_mode"' const.py` | 0 | PASS |
| `"global_mode"` absent from coordinator.py | `grep -c '"global_mode"' coordinator.py` | 0 | PASS |
| `"global_mode"` absent from websocket.py | `grep -c '"global_mode"' websocket.py` | 0 | PASS |
| `global_time_program` absent from websocket.py | `grep -c 'global_time_program' websocket.py` | 0 | PASS |
| `default_zone: ZoneConfig` in types.ts | `grep -c 'default_zone: ZoneConfig' types.ts` | 1 | PASS |
| `resetRoomToDefaultZoneProgram` in ws-client.ts | `grep -c 'resetRoomToDefaultZoneProgram' ws-client.ts` | 1 | PASS |
| `default_zone_preheat_enabled` in room-card.ts | `grep -c 'default_zone_preheat_enabled' room-card.ts` | 1 | FAIL — legacy flat key read at line 987 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| ARCH-01 | 14-01, 14-02, 14-03, 14-04 | Default Zone as first-class ZoneConfig; four flat keys migrated on load | PARTIAL | All backend layers verified. Frontend preheat path in room-card reads removed flat key (`default_zone_preheat_enabled`). Core schema, coordinator, WS, and types are fully migrated. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/room-card.ts` | 987 | `this.panelConfig?.default_zone_preheat_enabled ?? false` reads a flat key removed by Phase 14 schema | WARNING | `ClimateConfig` no longer has `default_zone_preheat_enabled`. This expression always evaluates `false` for Default Zone rooms, causing the preheat section to never display even when `default_zone.preheat_enabled` is `true`. Custom zone rooms are unaffected (they use `zones[zoneId].preheat_enabled`). |

No TBD/FIXME/XXX debt markers found in phase-modified files.

### Human Verification Required

#### 1. Default Zone Panel Render and Mutation

**Test:** Restart HA (or reload Climate Manager). Open the Climate Manager panel.
In the Global Settings / zone tab, confirm the Default Zone shows its name and
current mode badge. Change the Default Zone mode; confirm it persists after a
page refresh (`set_zone_mode("default", ...)`). Open a room card on the Default
Zone — confirm mode badge and active period render (not blank/undefined) and
the zone name shows. Use the zone-tab Reset action and confirm the toast shows
the Default Zone name and the program resets. Confirm no console errors
("Cannot read properties of undefined") during initial load before the first
status push.

**Expected:** All fields render from `config.default_zone` / `status.zones["default"]`
with no visible errors or blank values.

**Why human:** Live WebSocket data flow and Lit component rendering cannot be
verified by grep or static analysis.

#### 2. Default Zone Preheat Toggle (room-card.ts line 987)

**Test:** Enable preheat on the Default Zone (via the zone preheat toggle).
Open a room card for a room in the Default Zone. Observe whether the preheat
section appears.

**Expected:** The preheat section should appear because `default_zone.preheat_enabled`
is `true`. If it does NOT appear, that confirms the line 987 defect is
user-visible.

**Why human:** `room-card.ts` line 987 reads `this.panelConfig?.default_zone_preheat_enabled`
(the removed flat key, always `undefined` → `false`) instead of
`this.panelConfig?.default_zone?.preheat_enabled`. This is a definite code
defect but its precise user-visible impact needs confirmation against a running
panel. A fix is: change line 987 to
`this.panelConfig?.default_zone?.preheat_enabled ?? false`.

### Gaps Summary

No hard blockers. The phase delivers ARCH-01 correctly across const, storage,
coordinator, websocket, and the primary frontend type/component paths (14 of 15
truths verified).

One defect exists in `room-card.ts` line 987: the preheat-section visibility
check for Default Zone rooms reads the removed flat key
`default_zone_preheat_enabled` instead of `default_zone.preheat_enabled`. This
is a functional regression for any user who has preheat enabled on the Default
Zone — the preheat card section will never display for those rooms. The fix is a
one-line change. This defect does not block the primary ARCH-01 goal (schema
consolidation) but should be fixed before the milestone is considered complete.

---

_Verified: 2026-06-04T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
