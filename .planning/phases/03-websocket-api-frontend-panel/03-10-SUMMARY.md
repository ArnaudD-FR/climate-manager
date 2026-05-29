---
phase: "03-websocket-api-frontend-panel"
plan: "10"
subsystem: "backend-websocket"
tags: [phase-03, gap-closure, backend, d-24, d-25, websocket, coordinator]
dependency_graph:
  requires: []
  provides:
    - "rooms_status[].present_person_count: int in both
      coordinator._build_status_payload and ws_get_status"
    - "get_config response climate_entities: list[str] sorted all climate.*
      entity IDs"
  affects:
    - "custom_components/climate_manager/coordinator.py"
    - "custom_components/climate_manager/websocket.py"
tech_stack:
  added: []
  patterns:
    - "persons-room-ids join: set(_last_present_persons) intersected with
      person_config.get('room_ids', [])"
    - "merge dict without mutation: {**runtime_config, 'climate_entities':
      climate_entities}"
    - "entity registry filter: entry.entity_id.split('.')[0] == 'climate'
      (matches discovery.py:46)"
key_files:
  created: []
  modified:
    - "custom_components/climate_manager/coordinator.py"
    - "custom_components/climate_manager/websocket.py"
    - "tests/test_coordinator.py"
    - "tests/test_websocket.py"
decisions:
  - "present_person_count computed identically in both code paths (coordinator +
    websocket) without merging — symmetric design per plan spec"
  - "climate_entities uses {**runtime_config, 'climate_entities': ...} merge to
    avoid mutating stored config"
  - "entity registry import added at module level (not inside handler) per
    Python convention"
metrics:
  duration: "~3m"
  completed: "2026-05-21"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 4
---

# Phase 03 Plan 10: D-24 + D-25 Backend Fields Summary

Two backend additions (plan 03-10): `present_person_count` per room in
rooms_status (D-24) and `climate_entities` in get_config response (D-25), both
implemented with TDD (RED/GREEN/REFACTOR).

## What Was Built

### D-24: `present_person_count` in rooms_status

- **coordinator.py `_build_status_payload` (lines 353-396):** Before the room
  loop, captures `persons_config = self._data.runtime_config.get("persons", {})`
  and `present_set = set(self._last_present_persons)`. Inside the loop, assigns
  `room_entry["present_person_count"] = sum(1 for person_id, person_config in persons_config.items() if area_id in person_config.get("room_ids", []) and person_id in present_set)`.
  Added at line 373.

- **websocket.py `ws_get_status` (lines 84-157):** Symmetric implementation.
  After extracting `present_persons` from coordinator, pre-computes
  `persons_config = runtime_config.get("persons", {})` and
  `present_set = set(present_persons)`. Assignment
  `room_entry["present_person_count"] = ...` at line 144 (same sum expression).

Both paths always emit the key with value `0` when no persons are
present-and-assigned — never omitted.

### D-25: `climate_entities` in get_config

- **websocket.py `ws_get_config` (lines 166-196):** Added
  `from homeassistant.helpers import entity_registry as er` at module level
  (line 32). Handler now builds
  `climate_entities = sorted(entry.entity_id for entry in entity_reg.entities.values() if entry.entity_id.split(".")[0] == "climate")`.
  Returns
  `{**entry.runtime_data.runtime_config, "climate_entities": climate_entities}`
  — new dict, runtime_config never mutated.

## Persons-Room-IDs Join Shape (for Plan 03-12)

```python
persons_config = runtime_config.get("persons", {})  # {person_id: {"room_ids": [area_id, ...], ...}}
present_set = set(_last_present_persons)             # set of currently present person_ids
count = sum(
    1
    for person_id, person_config in persons_config.items()
    if area_id in person_config.get("room_ids", []) and person_id in present_set
)
```

Plan 03-12 can rely on `room_entry["present_person_count"]` being present in
every rooms_status entry — no frontend-side array intersection needed.

## Runtime Config Mutation Confirmation

The `ws_get_config` handler builds a **new dict** via
`{**entry.runtime_data.runtime_config, "climate_entities": ...}`. It does NOT
call `.update()` on `runtime_config` and does NOT assign
`runtime_config["climate_entities"]`. Verified by
`grep -n 'runtime_config\["climate_entities"\]' websocket.py` returning 0
matches.

## TDD Gate Compliance

### Task 1 (D-24)

- RED commit: `649aca2` — 2 failing tests added
- GREEN commit: `5400f8b` — implementation makes tests pass

### Task 2 (D-25)

- RED commit: `ab25f97` — 2 failing tests added
- GREEN commit: `a3b2243` — implementation makes tests pass

## Tests Added

| Test                                                             | File                      | Status |
| ---------------------------------------------------------------- | ------------------------- | ------ |
| `test_build_status_payload_includes_present_person_count`        | tests/test_coordinator.py | PASSED |
| `test_ws_get_status_includes_present_person_count`               | tests/test_websocket.py   | PASSED |
| `test_ws_get_config_includes_climate_entities`                   | tests/test_websocket.py   | PASSED |
| `test_ws_get_config_climate_entities_empty_when_none_registered` | tests/test_websocket.py   | PASSED |

Full test suite: **82 tests pass**.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. Both fields are fully computed from real data (entity registry,
coordinator state).

## Threat Flags

No new network endpoints or auth paths introduced. Both changes are additions to
existing WS command response payloads. Entity registry access is read-only. No
new trust surface.

## Self-Check: PASSED

All implementation files present. All 4 task commits found in git log. 82 tests
pass in full suite.
