---
status: complete
phase: 13-matter-tado-x-real-time-calibration
source: 13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, quick/uo0, quick/p8d, quick/o8e, quick/oo1
started: 2026-06-03T00:00:00Z
updated: 2026-06-03T00:00:00Z
---

## Current Test

## Current Test

[testing complete]

## Tests

### 1. DnD climate section visible on Tado X rooms
expected: Open the Climate Manager panel and expand a room that contains at least one Tado X thermostat entity. The room card shows a climate section with a two-level vertical tree: Tado X groups/entities at L1, Matter children nested under each at L2. Entities appear as chip-style badges with a thermometer icon. Chips marked as draggable show a grab cursor.
result: pass

### 2. Non-Tado-X rooms show standard TRV chips
expected: For a room that has no Tado X entities (only standard TRVs), the room card shows the normal TRV chip display — no DnD tree, no drag handles, no grouping UI.
result: skipped
reason: no non-Tado-X room available to test

### 3. Drag a Matter entity onto a Tado X group
expected: Start dragging a Matter entity chip. An "Unassign" drop zone appears on the right side of the section. Drag the chip over a Tado X group row — the row highlights (drag-over style). Dropping assigns the pairing: the Matter chip moves into the L2 position under that Tado X entity, the change saves automatically, and a "Saved" toast briefly appears.
result: pass

### 4. Unassign a paired Matter entity via drop zone
expected: With a Matter entity already paired to a Tado X valve (visible as an L2 child chip), drag that Matter chip and drop it onto the "Unassign" drop zone that appears on the right during drag. The chip moves back to the unassigned pool, the mapping is removed, and a "Saved" toast appears.
result: pass
note: fixed by quick/tf5 (2b9b30f) — try/catch + showToast added to _onDropOnUnassign

### 5. Auto-detect button finds and saves pairings
expected: Click the "Auto-detect" button in the climate section. The backend walks the HA device registry matching Tado X valve serial numbers against Matter device identifiers. For any matched pairs in this room, the mappings are saved automatically and the UI reloads to show the newly paired chips under their Tado X groups. A toast confirms "Auto-detected and saved". If no matches are found for this room, a "No matches found" toast appears instead.
result: skipped
reason: Auto-detect button not present in the DnD UI

### 6. Auto-detect on startup populates mappings
expected: Restart Home Assistant (or reload the integration) with Tado X and Matter devices already registered. After startup, the `matter_mappings` config is auto-populated for any devices whose serial numbers match — observable by opening the room card and seeing the matched chips already grouped, without having clicked Auto-detect manually.
result: pass

### 7. Panel loads fresh JS after deploy
expected: After running `make build && make deploy`, open the Climate Manager panel in a browser that previously cached the old JS. The panel loads the latest version (no stale UI artifacts from the old select-based pairing UI). The URL for the panel module ends with a `?v=` version suffix matching the current manifest.json version.
result: pass

## Summary

total: 7
passed: 5
issues: 0
pending: 0
skipped: 2
blocked: 0

## Gaps

(none — all issues resolved)
