---
quick_id: 260603-o8e
slug: auto-detect-matter-tado-x-mapping
status: complete
---

# Auto-detect Matter/Tado X mapping — Summary

## One-liner

Auto-detection of Matter→Tado X entity pairings via area-name matching,
exposed as a read-only WS command and an "Auto-detect" button in the room card.

## Tasks completed

### Task 1 — discovery.py: suggest_matter_mappings function

Implemented `suggest_matter_mappings(hass)` in
`custom_components/climate_manager/discovery.py`. The function scans the HA
entity registry for Matter climate entities and Tado X climate entities, groups
them by HA area, and returns a mapping `{tado_entity_id: [matter_entity_id, …]}`
for pairs that share the same area. Three tests added in `tests/test_discovery.py`
(TDD: RED commit then GREEN commit).

### Task 2 — websocket.py: suggest_matter_mappings WS command

Added `_make_ws_suggest_matter_mappings(entry)` factory function in
`custom_components/climate_manager/websocket.py`. The command is read-only
(no mutation, no `async_evaluate` trigger). Registered alongside the existing 20
commands; module docstring updated to 21 commands. The test
`test_ws_suggest_matter_mappings_returns_mappings` in `tests/test_websocket.py`
was already present (added in Task 1 branch); all 244 tests pass.

### Task 3 — Frontend: ws-client.ts + room-card.ts

Added `suggestMatterMappings()` method to `WsClient` in
`frontend/src/ws-client.ts` (calls the new WS command and unwraps the
`mappings` key from the result).

Added `_onAutoDetectMatter()` async method and an "Auto-detect" button to
`RoomCard` in `frontend/src/components/room-card.ts`. The handler fetches all
suggestions, filters to TRVs in the current room, calls `setMatterMapping()`
for each match, and shows a toast on success or failure. The button uses the
existing `reset-btn` CSS class. Frontend build (`make build`) succeeds.

### Task 4 — Lint

`make lint` passes with no violations across all Python and TypeScript files.

## Deviations from plan

**1. [Rule 2 - Missing CSS] `action-button` class not defined**
- **Found during:** Task 3
- **Issue:** The plan specified `class="action-button"` but no such CSS class
  exists in room-card.ts or shared-styles.ts, which would produce an unstyled
  button.
- **Fix:** Used the existing `reset-btn` class instead, which provides the
  correct visual appearance (outlined primary-color border button).
- **Files modified:** `frontend/src/components/room-card.ts`

## Self-Check: PASSED

- `custom_components/climate_manager/discovery.py` — exists
- `custom_components/climate_manager/websocket.py` — updated
- `frontend/src/ws-client.ts` — updated
- `frontend/src/components/room-card.ts` — updated
- Commits: d2b0e61 (Task 2 WS), 5cc7cdb (Task 3 frontend)
- All 244 tests pass
- Lint clean
