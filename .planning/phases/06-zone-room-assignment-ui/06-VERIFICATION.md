---
phase: 06-zone-room-assignment-ui
verified: 2026-05-28T12:00:00Z
status: gaps_found
score: 3/5 must-haves verified
overrides_applied: 0
gaps:
  - truth: "User can assign rooms to a zone from the zone tab and from each room card — the assignment is reflected in both views"
    status: failed
    reason: |
      Three bugs in zone-tab.ts make zone assignment interactions broken or no-ops:
      CR-01: Default Zone mode change calls ws.setZoneMode('default', ...) which the backend rejects with ERR_NOT_FOUND.
        No isDefault branch exists in _onModeChange.
      CR-02: Default Zone time-bar calls ws.setZoneTimeProgram('default', ...) which the backend rejects with ERR_NOT_FOUND.
        No isDefault branch exists in _onPeriodsChanged.
      CR-03: _onRemoveRoom sends { zone_id: undefined } — JSON.stringify drops undefined keys, so the backend
        receives {} and the remove is a no-op. The same bug is present in room-card.ts _onZoneChange when the
        empty-string (Default Zone) option is selected.
      WR-01: _onAddRoom on the Default Zone tab sends { zone_id: 'default' } — backend validate_zone_assignment
        rejects 'default' as an unknown zone_id, so adding a room to the Default Zone from its tab always fails.
    artifacts:
      - path: "frontend/src/components/zone-tab.ts"
        issue: "Line 357: _onModeChange unconditionally calls ws.setZoneMode(this.zoneId, ...) — no branch for isDefault to route to ws.setGlobalMode()"
      - path: "frontend/src/components/zone-tab.ts"
        issue: "Line 372: _onPeriodsChanged unconditionally calls ws.setZoneTimeProgram(this.zoneId, ...) — no branch for isDefault to route to ws.setTimeProgram()"
      - path: "frontend/src/components/zone-tab.ts"
        issue: "Line 403: _onRemoveRoom builds patch = { zone_id: undefined }; JSON.stringify({zone_id: undefined}) === '{}' — key is silently dropped, backend receives no-op"
      - path: "frontend/src/components/room-card.ts"
        issue: "Line 458: _onZoneChange uses { zone_id: undefined } for empty string (Default Zone) — same JSON serialization no-op"
    missing:
      - "Branch on isDefault in _onModeChange: if (this.isDefault) { await this.ws.setGlobalMode(newMode); } else { await this.ws.setZoneMode(this.zoneId, newMode); }"
      - "Branch on isDefault in _onPeriodsChanged: if (this.isDefault) { await this.ws.setTimeProgram(program); } else { await this.ws.setZoneTimeProgram(this.zoneId, program); }"
      - "Replace zone_id: undefined with zone_id: null in _onRemoveRoom (and update backend to treat null as 'pop zone_id'), OR add a remove_room_from_zone WS command"
      - "Fix _onAddRoom for Default Zone: use the same null/clearing mechanism instead of sending zone_id: 'default'"
      - "Apply the same zone_id: null fix to room-card.ts _onZoneChange for the Default Zone option"

  - truth: "Tab bar shows Global Settings | Default Zone | [custom zones] | Rooms | Persons — new zone tabs appear immediately after creation, disappear after deletion"
    status: failed
    reason: |
      The first tab label is 'Overview', not 'Global Settings' as specified in the success criterion.
      The ROADMAP.md Success Criterion 1 explicitly states the order as 'Global Settings | Default Zone | ...'
      The actual tab bar in main.ts renders: Overview | Default Zone | [custom zones] | + | Rooms | Persons.
      Note: the + button (add-zone-btn) is present in the tab bar but the success criteria description does not
      mention it. The dynamic zone appearance/disappearance mechanism is correctly implemented — the tab naming
      discrepancy is the gap.
    artifacts:
      - path: "frontend/src/main.ts"
        issue: "Line 288: first tab button renders '>Overview</button>' — success criterion specifies 'Global Settings'"
    missing:
      - "Rename the first tab from 'Overview' to 'Global Settings' OR clarify that 'Overview' is acceptable and update the ROADMAP.md success criterion wording"
---

# Phase 06: Zone & Room Assignment UI Verification Report

**Phase Goal:** The panel exposes full zone management — zone tabs appear and disappear as zones are created or deleted, each zone is fully configurable inline, and every room card shows its zone membership and allows reassignment.
**Verified:** 2026-05-28
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Tab bar shows Global Settings \| Default Zone \| [custom zones] \| Rooms \| Persons | FAILED | First tab is labeled "Overview" (main.ts:288), not "Global Settings" as the success criterion requires. Dynamic zone tab rendering is correctly wired via Object.entries(this._config.zones). |
| 2 | Each zone tab displays zone name (inline editable), mode picker, weekly time-bar, and list of assigned rooms | VERIFIED | zone-tab.ts renders all four sections in order: click-to-edit name (h2.zone-name -> input.zone-name-input), native select for mode, climate-manager-time-bar, Assigned rooms chips + search-picker. Memoized _days getter present. |
| 3 | User can assign rooms to a zone from the zone tab and from each room card — the assignment is reflected in both views | FAILED | CR-01, CR-02, CR-03 (see Gaps Summary). Default Zone mode/time-program writes silently fail. Room removal from custom zone is a no-op. Room assignment to Default Zone from its tab fails. The zone picker in room-card also has the same CR-03 bug for Default Zone selection. |
| 4 | Every room card in the Rooms tab shows a zone badge with the zone name | VERIFIED | room-card.ts:651 renders `<span class="zone-badge">${this._getZoneName()}</span>` in the .card-header-top div. _getZoneName() correctly handles absent zone_id (returns default_zone_name) and stale zone_id references (defensive fallback). |
| 5 | Custom zone tabs show a delete button with confirmation dialog; the Default Zone tab has no delete button | VERIFIED | zone-tab.ts:503 gates the delete row on `!this.isDefault`. Custom zone shows Delete zone button -> inline "Delete zone? [Cancel] [Confirm]" row (no ha-dialog). Default Zone (isDefault=true) renders nothing in the delete slot. |

**Score:** 3/5 truths verified

---

### Deferred Items

None.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/ws-client.ts` | 6 zone WS methods + ZoneConfig import | VERIFIED | All 6 methods present (createZone, deleteZone, renameZone, setZoneMode, setZoneTimeProgram, resetZoneTimeProgram). ZoneConfig in type import block at line 16. All use sendMessagePromise pattern with correct backend message types. |
| `frontend/src/components/zone-tab.ts` | ClimateManagerZoneTab Lit component | VERIFIED (with bugs) | File exists, 589 lines, customElements.define("climate-manager-zone-tab") at line 583. All required properties present. Memoized _days getter. Uses native input/select (HA 2026.x compliant). Bugs in 3 handlers (see gaps). |
| `frontend/src/main.ts` | Dynamic zone tabs + + button + _validateActiveTab | VERIFIED | Side-effect import of zone-tab.js at line 32. _validateActiveTab() at line 161. _onCreateZone() at line 240. Tab bar rewritten to enumerate _config.zones dynamically. Two climate-manager-zone-tab render branches in _renderTabContent. |
| `frontend/src/components/room-card.ts` | Zone badge in header + Zone select in expanded content + _onZoneChange | VERIFIED (with bug) | .zone-badge CSS at line 140. _getZoneName() at line 448. Zone badge in header at line 651. Zone picker in expanded content at lines 693-706, below mode picker and above persons section. _onZoneChange at line 456 has CR-03 bug for Default Zone option. |
| `frontend/src/components/person-card.ts` | "HA home tracking" label in badge + option | VERIFIED | Line 373: `text: "HA home tracking"`. Line 411: `>HA home tracking</option>`. PRESENCE_MODE_HA constant "ha" unchanged at line 28. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `zone-tab.ts` | `ws-client.ts` | ws.setZoneMode / ws.setZoneTimeProgram / ws.renameZone / ws.deleteZone / ws.setRoomConfig | PARTIAL | All 5 ws calls are present. However _onModeChange (CR-01) and _onPeriodsChanged (CR-02) call the wrong command for the Default Zone case. |
| `zone-tab.ts` | `global-settings-tab.js` | `import { programToDays, dayIndexToKey }` | VERIFIED | Line 28: named import confirmed. Both helpers used in _days getter and _onPeriodsChanged. |
| `zone-tab.ts` | `search-picker.ts` | side-effect import + `<search-picker>` usage | VERIFIED | Line 31: `import "./search-picker.js"`. Line 569: `<search-picker ...>` in Assigned Rooms section. |
| `main.ts` | `zone-tab.ts` | side-effect import + `<climate-manager-zone-tab>` in _renderTabContent | VERIFIED | Line 32: `import "./components/zone-tab.js"`. Lines 325 and 343: two render branches confirmed. |
| `main.ts` | `ws-client.ts` | `this._ws.createZone(...)` | VERIFIED | Line 245: `const result = await this._ws.createZone(newName)`. |
| `room-card.ts` | `ws-client.ts` | ws.setRoomConfig with zone_id patch | PARTIAL | Present at line 459, but zone_id: undefined serialization bug (CR-03) makes Default Zone assignment a no-op. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `zone-tab.ts` | zoneConfig (mode, time_program, name) | Passed as prop from main.ts, which sources from _config.zones[zoneId] or synthesized from global_mode/global_time_program | Yes — data flows from getConfig() backend call through _config | FLOWING |
| `zone-tab.ts` | assignedRoomIds | _getAssignedRoomIds() iterates config.rooms entries | Yes — config.rooms from backend | FLOWING |
| `room-card.ts` | zone badge text | _getZoneName() reads config.zone_id then panelConfig.zones[zoneId].name | Yes — from backend config | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — no runnable entry points without a live Home Assistant instance. The panel is a HA Lovelace custom element; all behavioral verification requires browser + HA connection.

---

### Probe Execution

Step 7c: No probe scripts found for phase 06.

```
find /home/arnaud/dev/climate_manager/scripts -path '*/tests/probe-*.sh' 2>/dev/null — returned empty
```

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| ASSIGN-01 | 06-01 | User can assign rooms to a zone from within the zone tab | BLOCKED | search-picker and chip UI rendered in zone-tab.ts. _onAddRoom wired. But: Default Zone add is broken (WR-01) and remove from custom zone is a no-op (CR-03). |
| ASSIGN-02 | 06-03 | User can assign/change a room's zone from within the room card | BLOCKED | Zone picker rendered in room-card.ts expanded content. Custom zone assignment works. Default Zone selection is a no-op (CR-03). |
| ASSIGN-03 | 06-03 | Room card shows a zone badge (zone name) for every room | SATISFIED | Zone badge rendered in card-header-top for all rooms. _getZoneName() handles Default Zone fallback correctly. |
| UI-01 | 06-02 | Tab bar order: Global Settings \| Default Zone \| [custom zone tabs] \| Rooms \| Persons | BLOCKED | Tab bar is implemented but first tab reads "Overview" not "Global Settings". All other ordering is correct. |
| UI-02 | 06-02 | Custom zone tabs added and removed dynamically as zones are created or deleted | SATISFIED | Object.entries(this._config.zones).map() renders dynamic tabs. _validateActiveTab() removes stale zone_ tabs after deletion. |
| UI-03 | 06-01 / 06-02 | User can create a new zone from the panel | SATISFIED | + button present, _onCreateZone() calls ws.createZone(), switches tab, attempts auto-focus. |
| UI-04 | 06-01 | Every zone tab shows zone name (inline editable), mode picker, weekly time program, assigned rooms list | PARTIALLY SATISFIED | All four elements rendered. But mode picker and time-bar on Default Zone tab silently fail (CR-01, CR-02). |
| UI-05 | 06-01 | Custom zone tabs have delete button with confirmation; Default Zone tab does not | SATISFIED | isDefault guards delete row. Inline confirm pattern (no ha-dialog) implemented. |
| UI-06 | 06-03 | Rooms tab shows all rooms with zone badge and zone picker on each room card | PARTIALLY SATISFIED | Badge is present and correct. Picker is present but Default Zone assignment is broken (CR-03). |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `zone-tab.ts` | 357 | `ws.setZoneMode(this.zoneId, ...)` with no isDefault branch | BLOCKER | Default Zone mode changes always fail with backend ERR_NOT_FOUND |
| `zone-tab.ts` | 372 | `ws.setZoneTimeProgram(this.zoneId, ...)` with no isDefault branch | BLOCKER | Default Zone time-bar changes always fail with backend ERR_NOT_FOUND |
| `zone-tab.ts` | 403 | `{ zone_id: undefined }` — JSON.stringify drops undefined keys | BLOCKER | Removing a room from a custom zone is always a no-op |
| `zone-tab.ts` | 388 | `{ zone_id: this.zoneId }` when zoneId === "default" — backend rejects "default" as unknown zone | WARNING | Adding a room to Default Zone from its tab always fails |
| `room-card.ts` | 458 | `{ zone_id: undefined }` when empty-string selected — same JSON.stringify no-op | BLOCKER | Changing a room to Default Zone from the room card picker is always a no-op |
| `main.ts` | 44 | `@state() private _unsubStatus` — Promise stored as reactive state triggers unnecessary re-render when subscription is established | INFO | Minor: extra re-render on subscribe; no user-visible impact |

---

### Human Verification Required

No items requiring human-only testing — the gaps identified above are all code-verifiable bugs. The structural UI (tab rendering, badge display, edit affordances) passes automated code inspection; the behavioral failures are in wiring bugs confirmed by code reading.

The following would normally require human verification but are overridden by the confirmed code bugs:
- Default Zone mode save: confirmed broken at code level (no isDefault branch, wrong WS command sent)
- Room removal from zone: confirmed broken at code level (JSON.stringify({ zone_id: undefined }) === '{}')

---

### Gaps Summary

Two categories of gaps prevent the phase goal from being achieved:

**Category A — Wrong WebSocket command for Default Zone (CR-01, CR-02):**
`_onModeChange` and `_onPeriodsChanged` in `zone-tab.ts` call `ws.setZoneMode` and `ws.setZoneTimeProgram` unconditionally, even when `this.zoneId === "default"`. The backend handlers for these commands explicitly reject `zone_id="default"` with `ERR_NOT_FOUND`. The Default Zone's mode must be changed via `ws.setGlobalMode()` and its time program via `ws.setTimeProgram()`. The fix requires adding a branch on `this.isDefault` in both handlers — about 4 lines of code total.

**Category B — JSON serialization drops `zone_id: undefined` (CR-03, WR-01):**
Both `_onRemoveRoom` in `zone-tab.ts` (line 403) and `_onZoneChange` in `room-card.ts` (line 458) use `{ zone_id: undefined }` to signal "remove zone assignment". `JSON.stringify` silently drops keys with `undefined` values, so the backend receives `{}` and performs no-op. No room can be moved to the Default Zone via either UI path. The fix requires either: (a) sending `zone_id: null` and adding a backend branch to treat `null` as "pop zone_id", or (b) a dedicated `remove_room_from_zone` backend command. Additionally, `_onAddRoom` on the Default Zone tab sends `{ zone_id: "default" }` which the backend rejects because "default" is not a valid zone UUID in `config.zones`.

These bugs affect all interactive mutation paths for the Default Zone tab and for moving rooms back to the Default Zone. The structural scaffolding (tab bar, zone tab component, zone badge, zone picker UI) is correctly implemented and working.

**Tab label mismatch (Success Criterion 1):**
The ROADMAP success criterion specifies the first tab as "Global Settings" but the implementation renders "Overview". This is either a deliberate naming decision that predates Phase 6 (the comment at line 16 of main.ts still says "Global Settings") or an unresolved discrepancy. The tab has been named "Overview" since Phase 3 and was not changed in Phase 6. Given the roadmap SC explicitly states "Global Settings", this is a FAILED truth even if the tab functionality is correct.

---

_Verified: 2026-05-28_
_Verifier: Claude (gsd-verifier)_
