---
slug: zone-mode-change-delayed-period-update
status: investigating
trigger: manual
goal: find_and_fix
created: 2026-06-06
---

# Debug: Zone mode change does not immediately update rooms' current period

## Symptoms

When the user changes a zone mode via the UI (e.g. comfort → eco → away →
frost), the Rooms tab still shows the old `active_period` until the next
periodic `async_evaluate` tick fires (up to 1 minute later).

Expected: rooms' `active_period` updates immediately on mode change.

## Current Focus

**Hypothesis:** The `ws_set_zone_mode` handler fires
`coordinator._build_status_payload()` and the `{DOMAIN}_status_update` bus
event immediately after the mode write and *before* calling
`coordinator.async_evaluate()`. However, at the moment the early status event
is fired, `coordinator._last_zone_periods` and `coordinator._last_room_periods`
still hold the values from the **previous** evaluation cycle — they have not
been recomputed for the new mode. The zone evaluation loop inside
`async_evaluate` is what actually re-derives `_current_period` and then writes
it into `_last_zone_periods` / `_last_room_periods`. So the eager status push
reads stale period data.

**Next action:** Confirm hypothesis, then fix.

## Root Cause (confirmed)

In `websocket.py` `ws_set_zone_mode` (lines 747-754):

```python
# Fire status immediately so the panel badge updates without waiting
# for the full async_evaluate cycle (which pushes temps to TRVs first).
hass.bus.async_fire(
    f"{DOMAIN}_status_update",
    coord._build_status_payload(),   # ← reads stale _last_zone_periods
)
hass.async_create_task(coord.async_evaluate())   # ← this updates them
```

`_build_status_payload()` reads `self._last_zone_periods` (populated only
after `async_evaluate` runs the zone loop). Calling it *before*
`async_evaluate` means the rooms' `active_period` field still reflects the
mode that was active at the **last** periodic tick.

The `change_mode()` call on the live Zone object (line 746) does swap
`zone._mode` and update `zone._current_mode_name`, but it does NOT re-evaluate
the schedule — it does not write a new value into `zone._current_period` nor
update `coord._last_zone_periods` / `coord._last_room_periods`. So the status
payload still contains old period values.

## Evidence

- `ws_set_zone_mode` (websocket.py:750-754): fires `{DOMAIN}_status_update`
  calling `coord._build_status_payload()` *before* the awaited
  `async_evaluate` task can run.
- `_build_status_payload` (coordinator.py:842-953): uses
  `self._last_zone_periods` (line 941) and `self._last_room_periods` (line
  863) — both are only refreshed inside `async_evaluate` (lines 343-365).
- `Zone.change_mode()` (zone.py:325-352): swaps `_mode` and updates
  `_current_mode_name` but does NOT call the schedule evaluator, so
  `_current_period` keeps its old value.
- `async_evaluate` (coordinator.py:288-388): the only place that calls
  `zone.evaluate(ctx)` → writes `zone._current_period` → writes
  `_last_zone_periods` / `_last_room_periods` → fires the definitive status
  event.

## Fix

Remove the premature `hass.bus.async_fire` in `ws_set_zone_mode`. Let
`async_evaluate` (which is already scheduled via `hass.async_create_task`)
fire the status event at the end of its cycle as it normally does. The status
event at the end of `async_evaluate` (coordinator.py:385-388) will then carry
the freshly recomputed zone periods.

If the panel badge latency from the async task scheduling is a concern, the
alternative is to `await coord.async_evaluate()` directly (instead of
`hass.async_create_task`) so the WS handler does not return until the
evaluation is complete and the status is already pushed. However, this blocks
the WS response for the duration of the evaluation. A simpler and correct fix
is just to remove the premature early fire — the background task fires within
the same event-loop pass, so the latency is negligible.

## Resolution

- root_cause: The `ws_set_zone_mode` handler fires `_build_status_payload()`
  immediately after mutating the zone mode, before `async_evaluate` has
  re-derived `_last_zone_periods` / `_last_room_periods`, causing the panel
  to receive stale `active_period` values until the next periodic tick.
- fix: Remove the premature `hass.bus.async_fire` call in `ws_set_zone_mode`;
  rely on the status event emitted at the end of `async_evaluate`.
- status: applied
