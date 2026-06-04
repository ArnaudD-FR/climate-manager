---
id: 260601-vaz
slug: fix-notif-dismiss-watcher
title: Fix non-dismissible HA notification watcher
date: "2026-06-01"
status: in-progress
---

## Goal

Notification is not recreated after user dismisses it because watcher 2 uses
`async_track_state_change_event` on `persistent_notification.*` — but in modern
HA, persistent notifications are stored in `hass.data["persistent_notification"]`
and fire a `persistent_notifications_updated` bus event. No state entity is
created, so the state-change watcher never fires.

## Fix

In `coordinator._check_ha_tracker_warnings`, replace watcher 2
(`async_track_state_change_event` on `persistent_notification.<notif_id>`) with
`hass.bus.async_listen("persistent_notifications_updated", _on_notifications_updated)`.

In the callback, check:
1. `notif_id NOT in hass.data.get("persistent_notification", {})` — notification gone
2. `notif_id in _ha_tracker_notif_active` — not a programmatic dismiss

If both true → recreate immediately.

## Task

- [ ] Edit `coordinator.py`: replace watcher 2 in `_check_ha_tracker_warnings`
- [ ] Run `make test` to verify no regressions
- [ ] Commit and deploy
