---
status: resolved
trigger: "in v1.2: rooms in person card are not sorted per floor. Do the same as zone card. When a room set as off, do the same as when the zone is off with climate entities set as off"
created: 2026-06-01
updated: 2026-06-01
slug: person-card-sort-room-off-fix
---

## Symptoms

- **Bug 1 – Person card room sort**: Rooms listed inside person cards are not sorted per floor, while zone cards already sort rooms by floor. The fix should apply the same floor-based sort to person cards.
- **Bug 2 – Room OFF state**: When a room's mode is set to OFF (room_mode = frost_protection), the climate entities in that room are not being set to the HVAC off state. The expectation is that the same behaviour applied when a zone mode is OFF (climate entities set to hvac_mode=off / frost-protect setpoint) should also apply when a room-level mode is OFF.

## Expected Behavior

- Bug 1: Rooms in person cards appear sorted by floor (same ordering logic as zone cards).
- Bug 2: When room mode is OFF, the TRV climate entities for that room are set to off (or frost-protect), identical to what happens when the enclosing zone mode is OFF.

## Actual Behavior

- Bug 1: Rooms in person cards appear in unordered / insertion order.
- Bug 2: When room mode is set to OFF, climate entities remain at their current setpoint; they are not turned off.

## Error Messages

None reported — silent incorrect behavior.

## Timeline

Introduced in v1.2 or earlier; both bugs present in current v1.3 branch (to be fixed on v1.2 branch then rebased).

## Reproduction

- Bug 1: Open the Persons tab, expand a person card — rooms listed do not follow floor order.
- Bug 2: Set a room mode to OFF via the UI; observe the TRV climate entity state in HA — it does not change to off.

## Current Focus

```yaml
hypothesis: "confirmed — root causes identified in persons-tab.ts and coordinator.py"
next_action: "apply fixes"
```

## Evidence

- timestamp: 2026-06-01T00:00:00Z
  file: frontend/src/components/persons-tab.ts
  finding: >
    _getRoomChoices() builds roomChoices from a Set of area IDs in insertion
    order with no sorting. The resulting array is passed to person-card.ts
    which renders currentRoomIds via .map() in insertion order. No floor
    grouping or level-based sort is applied anywhere in the person card path.
    By contrast, zone-tab.ts has _getSortedAssignedRoomGroups() which groups
    rooms by floor_id and sorts floor groups by floor.level descending.

- timestamp: 2026-06-01T00:00:00Z
  file: custom_components/climate_manager/coordinator.py
  finding: >
    _compute_desired_temps(): when room_mode == ROOM_MODE_FROST
    (the frost_protection value used for room-level "Off"), the room is added
    to frost_locked_rooms but NOT to mode_off_rooms. Only rooms in
    mode_off_rooms get _push_off_safely() called in _push_temperatures(),
    which is what issues set_hvac_mode=off on off-capable TRVs. Zone-level
    MODE_OFF adds rooms to both frost_locked_rooms and mode_off_rooms (line
    224), but room-level ROOM_MODE_FROST only adds to frost_locked_rooms.
    Fix: add the room to mode_off_rooms in the ROOM_MODE_FROST branch so that
    the same push-off behaviour is applied as for zone-level OFF.

## Eliminated

- "room_mode OFF is a different constant from zone MODE_OFF" — confirmed they
  are different but the fix path is clear: reuse mode_off_rooms for
  ROOM_MODE_FROST branch.

## Resolution

```yaml
root_cause: >
  Bug 1: persons-tab.ts _getRoomChoices() returns rooms in insertion order;
  person-card.ts renders them with no floor-based sort. Zone-tab has a full
  floor grouping implementation that was not ported to the person card path.
  Bug 2: coordinator.py _compute_desired_temps() does not add ROOM_MODE_FROST
  rooms to mode_off_rooms, so _push_temperatures() never calls
  _push_off_safely() for them, and TRVs are not turned off.
fix: >
  Bug 1: sort roomChoices in persons-tab.ts by floor level descending then
  room name ascending before passing to person-card. Also sort the rendered
  currentRoomIds chips in person-card.ts by the same order.
  Bug 2: add mode_off_rooms.add(area_id) in the ROOM_MODE_FROST branch of
  coordinator.py _compute_desired_temps(), mirroring the zone MODE_OFF branch.
verification: make test
files_changed:
  - frontend/src/components/persons-tab.ts
  - frontend/src/components/person-card.ts
  - custom_components/climate_manager/coordinator.py
```
