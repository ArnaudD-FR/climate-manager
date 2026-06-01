---
slug: d04-ha-option-always-visible
date: 2026-06-01
status: in-progress
---

# D-04 Fix: HA option always visible with ⚠ + edit link

## Goal

Always show the "HA home tracking" option in the presence-mode selector.
When no device trackers are linked, append ⚠ to the option label and show
a warning hint with an ha-icon-button that navigates to
/config/person/edit/${personId} via history.pushState.

## Changes

### presence-mode.ts

1. Update `shouldShowHaOption` to always return `true` and update its
   docstring to reflect new behavior (option always shown, ⚠ indicates
   unavailability rather than hiding).
2. Add `haOptionLabel(hasDeviceTrackers: boolean): string` — returns
   `"HA home tracking ⚠"` when no trackers, else `"HA home tracking"`.

### person-card.ts

1. Import `haOptionLabel` from presence-mode.ts.
2. Remove the `shouldShowHaOption` conditional wrapper; always render the
   HA `<option>`, using `haOptionLabel(this.hasDeviceTrackers)` for the label.
3. Replace the static `<p class="schedule-hint">` block with a conditional
   template: when `mode === "ha" && !hasDeviceTrackers`, render the hint text
   PLUS an `ha-icon-button` (icon: mdi:account-edit) that calls
   `history.pushState(null, "", "/config/person/edit/${this.personId}")` and
   dispatches `location-changed`.

## Tasks

- [ ] Edit presence-mode.ts
- [ ] Edit person-card.ts
- [ ] make build && make deploy
