---
quick_id: 260520-svm
slug: investigate-trv-used-for-bureau-instead-
date: 2026-05-20
status: complete
commits: []
files_modified: []
---

# Quick Task 260520-svm: Investigate TRV used for Bureau — Summary

Investigation confirmed the sensor priority chain works correctly in HA
2026.5.3.

Key findings:

- `AreaEntry` in HA 2026.5 uses `__slots__` (not `__dict__`) — `vars()` fails
  but `getattr` works
- `getattr(_area, 'temperature_entity_id', None)` correctly returns
  `sensor.meter_plus_fc_temperature`
- Sensor state is `21.7` (available, not unavailable/unknown)
- Auto-discovery independently finds the same sensor as consistent fallback
- No code change needed — the fix from 260520-s9s is working correctly

Diagnostic method: temporary `_LOGGER.warning` in `ws_get_status`, deployed 3×,
confirmed via `ha core logs`. The user's report was likely based on a transient
post-restart window or pre-fix state.
