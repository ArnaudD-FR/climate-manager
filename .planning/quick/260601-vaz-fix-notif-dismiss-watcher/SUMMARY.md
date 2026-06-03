---
id: 260601-vaz
slug: fix-notif-dismiss-watcher
status: complete
commit: a4cd591
date: "2026-06-01"
---

## What changed

Replaced all event-listener approaches for detecting user dismissal with a
tick-based check. On every evaluation tick (≤1 min), `_check_ha_tracker_warnings`
queries `hass.data["persistent_notification"]` directly. If the notification
should be shown but is absent from the dict, it is recreated.

Removed `_ha_tracker_notif_active` set and the bus/state event watcher for
dismissal detection. Kept only the `_on_tracker_restored` state-change watcher
for immediate dismissal when `device_trackers` is re-added to the person.

## Why previous attempts failed

- `async_track_state_change_event` on `persistent_notification.*`: no state
  entity is created for persistent notifications in modern HA.
- `hass.bus.async_listen("persistent_notifications_updated", ...)`: event name
  or data structure unreliable across HA versions.

## Final approach

Query the source of truth (`hass.data["persistent_notification"]`) on every
tick. Simple, version-agnostic, verified working on HA 2026.5.4.
