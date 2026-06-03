---
status: resolved
trigger: "in v1.2, in person tab the rooms should be grouped per floor and then sorted by name (see screenshot)"
created: 2026-06-01
updated: 2026-06-01
slug: person-card-floor-grouping
---

## Symptoms

- **Bug**: Room chips in the person card (Room Associations section) appear as a
  flat list. They should be visually grouped by floor with a floor label header
  above each group, and rooms within each group sorted alphabetically — identical
  to the zone tab behaviour.

## Expected Behavior

Room chips in person cards are grouped by floor with a floor name + icon label
above each group (same `.floor-group-label` pattern as zone-tab.ts). Rooms
within each floor group are sorted by name ascending. Floors ordered descending
by level. Rooms with no floor fall at the bottom with no label.

## Actual Behavior

Room chips render as a flat sorted list — floor label headers are absent.
The previous session (person-card-sort-room-off-fix) sorted rooms by floor
order but did not add the floor-group-label UI.

## Error Messages

None — silent visual gap.

## Timeline

Previous fix (c1d74b9) added floor-based sort order but missed the visual
floor grouping headers. This session adds the grouping.

## Reproduction

Open Persons tab → expand any person card with rooms on multiple floors →
chips appear flat, no floor headers.

## Current Focus

```yaml
hypothesis: "resolved"
next_action: "done"
```

## Evidence

- `persons-tab.ts` stripped `floorId` from `RoomChoice` before passing to
  `person-card.ts` (line 89: `.map(({ id, name, secondary }) => ...)`).
  Without `floorId`, person-card could not group chips by floor.
- `floor-group-label` CSS lived only in `zone-tab.ts` inline styles, not in
  `shared-styles.ts` — not reusable.
- `_getFloorIcon` helper existed only in `zone-tab.ts`.
- `person-card.ts` had no `_getAssignedRoomGroups()` method and rendered
  chips as a single flat `.chips` div.

## Eliminated

- Backend changes — not needed; floor data already in `hass.areas`/`hass.floors`.
- Adding `hass` prop to person-card — not needed; `panel.hass` is accessible.

## Resolution

```yaml
root_cause: >
  persons-tab.ts dropped `floorId` when mapping RoomChoice objects, and
  person-card.ts lacked grouping logic and floor-group-label CSS.
fix: >
  1. Added `floorId: string | null` to RoomChoice interface in person-card.ts.
  2. persons-tab.ts now passes floorId through (removed the stripping map).
  3. Extracted floor-group-label CSS to shared-styles.ts as floorGroupLabelStyles.
  4. zone-tab.ts imports floorGroupLabelStyles instead of defining it locally.
  5. person-card.ts imports floorGroupLabelStyles and adds _getFloorIcon() and
     _getAssignedRoomGroups() helpers; render uses floor-grouped chip layout.
verification: "make build passes; make test 164/164 pass"
files_changed:
  - frontend/src/shared-styles.ts
  - frontend/src/components/zone-tab.ts
  - frontend/src/components/persons-tab.ts
  - frontend/src/components/person-card.ts
```
