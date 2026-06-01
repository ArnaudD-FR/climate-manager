---
slug: d04-ha-option-always-visible
status: complete
date: 2026-06-01
commit: 44ebcdd
---

# D-04 Fix — HA option always visible

## What changed

**presence-mode.ts**
- `shouldShowHaOption` now always returns `true` (previously gated on
  `hasDeviceTrackers`, hiding the option entirely).
- New `haOptionLabel(hasDeviceTrackers)` helper returns
  `"HA home tracking ⚠"` when no trackers, else `"HA home tracking"`.

**person-card.ts**
- Removed `shouldShowHaOption` conditional wrapper — HA `<option>` always
  rendered, using `haOptionLabel` for its text.
- Hint paragraph now conditionally appends a `ha-icon-button`
  (icon: `mdi:account-edit`) when `mode === "ha" && !hasDeviceTrackers`.
  Click handler: `history.pushState` to `/config/person/edit/${personId}`
  + dispatches `location-changed` for HA's SPA router.

## Result

Users can always select "HA home tracking" from the dropdown. When no
device trackers are linked the option is labelled with ⚠ and the warning
hint shows a one-click button to edit the person in HA settings.
