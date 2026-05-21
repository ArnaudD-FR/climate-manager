---
status: partial
phase: 03-websocket-api-frontend-panel
source:
  - 03-01-SUMMARY.md
  - 03-02-SUMMARY.md
  - 03-03-SUMMARY.md
started: 2026-05-20T12:37:55Z
updated: 2026-05-20T12:37:55Z
---

## Current Test

number: 10
name: [testing complete]
awaiting: n/a

## Tests

### 1. Panel loads in HA sidebar
expected: The "Climate Manager" entry appears in the HA sidebar. Clicking it opens the panel without a blank screen or JS error. The header "Climate Manager" is visible, and three tabs (Global Settings, Rooms, Persons) are shown.
result: pass

### 2. Global Settings — Current Status section
expected: The Global Settings tab shows a "Current Status" card above the Configuration card. It displays the current global mode label (e.g. "Time program"), an "Active period" row, and a "Present persons" row. Values update live when the backend state changes — no page reload required.
result: pass

### 3. Global Settings — Global mode selector
expected: The Configuration card has a "Global mode" dropdown with three options (Off / Time program / Time program & presences). Changing the selection immediately saves (no Save button) and shows a "Saved" toast. The Current Status card reflects the new mode label.
result: pass

### 4. Global Settings — Default temperature inputs
expected: Four numeric inputs (Frost protection / Reduced / Normal / Comfort) are visible and show their current values with a °C suffix. Changing a value and committing (Tab or Enter) saves immediately and shows a "Saved" toast. After a page reload the new value is still shown.
result: pass

### 5. Global Settings — Global time program (default periods)
expected: The time-bar below "Global time program" shows all 7 days (Mon–Sun) with pre-populated default periods — not empty grey bars. A top and bottom time axis (00:00 / 06:00 / 12:00 / 18:00 / 24:00) is visible.
result: pass

### 6. Time bar — Split period action
expected: Clicking a period segment opens a popup with two actions: "Split period" and "Delete period". Clicking "Split period" divides the segment into two halves with different types. The change saves automatically and the bar updates.
result: pass

### 7. Time bar — Drag resize with live preview
expected: Hovering the border between two segments shows a drag handle. Dragging it moves the boundary in real-time (the segments visually resize as you drag). A time tooltip (e.g. "14:30") follows the mouse cursor during the drag. Releasing the mouse commits the change.
result: issue
reported: "releasing the drag handle open the period popup"
severity: major

### 8. Rooms tab — Room list and expansion
expected: The Rooms tab lists configured rooms. Each room can be expanded to show sensor entity fields (temperature_sensor, humidity_sensor) and a per-room time program toggle. Rooms with a custom time program appear first and expanded by default.
result: issue
reported: "shows 'no rooms discovered' even though HA Areas with climate/TRV entities are configured"
severity: major

### 9. Persons tab — Person list and presence mode
expected: The Persons tab lists configured persons with a presence-mode badge (Automatic / Present / Absent). Changing the presence mode via the dropdown saves immediately with a "Saved" toast.
result: issue
reported: "shows 'No persons found. Add person entities in Home Assistant.' even though person entities exist in HA"
severity: major

### 10. Save error handling — toast on failure
expected: If the backend rejects a save (e.g. connection lost), an error toast appears and persists until dismissed. It does NOT auto-dismiss after 3 seconds (unlike success toasts).
result: skipped
reason: "user skipped to prioritize adding new requirements"

## Summary

total: 10
passed: 6
issues: 3
pending: 0
skipped: 1

## Gaps

- truth: "Releasing the drag handle after resizing a period boundary should commit the change silently — no popup"
  status: failed
  reason: "User reported: releasing the drag handle open the period popup"
  severity: major
  test: 7
  artifacts: [frontend/src/components/time-bar.ts]
  missing: ["pointerup from drag must not propagate to _onSegmentClick"]

- truth: "Rooms tab lists all HA Areas that have climate entities assigned"
  status: failed
  reason: "User reported: shows 'no rooms discovered' even though HA Areas with climate/TRV entities are configured"
  severity: major
  test: 8
  artifacts: [custom_components/climate_manager/websocket.py, frontend/src/components/rooms-tab.ts]
  missing: ["room discovery logic finds HA areas with climate entities"]

- truth: "Persons tab lists all HA person entities"
  status: failed
  reason: "User reported: shows 'No persons found' even though person entities exist in HA"
  severity: major
  test: 9
  artifacts: [custom_components/climate_manager/websocket.py, frontend/src/components/persons-tab.ts]
  missing: ["person discovery logic finds HA person.* entities"]
