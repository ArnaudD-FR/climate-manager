---
phase: quick-260526-plq
status: complete
completed: "2026-05-27"
---

# Quick Task 260526-plq — Summary

## Files Modified

- `custom_components/climate_manager/coordinator.py` —
  `_push_off_safely(entity_id, frost_temp)` now pushes
  `set_temperature(frost_temp)` before `set_hvac_mode=off`; dispatch updated to
  pass `desired_temp`.
- `tests/test_coordinator.py` — Updated
  `test_mode_off_uses_set_hvac_mode_off_when_supported` to assert both
  `set_temperature(frost)` and `set_hvac_mode=off` fire; updated anti-flap test
  to also assert single `set_temperature` per cycle.
- `frontend/src/components/room-card.ts` — Widened `_lastTimeProgram` type to
  `DailyProgram | null | undefined` (pre-existing TypeScript error). Section
  ordering was already correct from prior merge (4209962).
- `frontend/src/components/person-card.ts` — No changes needed; section ordering
  already correct from prior merge.
- `custom_components/climate_manager/www/panel.js` — Rebuilt bundle.

## Behavioral Changes

- **Backend**: MODE_OFF on off-capable TRV now issues `set_temperature(frost)`
  then `set_hvac_mode=off` (in that order). Anti-flap sentinel guards both calls
  on repeat ticks.
- **Frontend section order** (already applied before this session): Room card =
  Mode → Custom program → Persons → Climate entities; Person card = Presence
  mode → Presence schedule → Room associations.

## Test Results

- `uv run pytest tests/test_coordinator.py -x -q -k "mode_off or MODE_OFF or off_to_time"`
  — 4 passed
- `uv run pytest tests/test_coordinator.py -x -q` — 24 passed, 0 failures
- `npx tsc --noEmit` — 0 errors
- `npm run build` — exit 0, panel.js 115.19 kB

## Commits

- `9a28474` — feat(coordinator): push frost-protection temp before hvac=off in
  MODE_OFF
- `4eb0ff6` — fix(frontend): widen \_lastTimeProgram type to accept null;
  rebuild bundle
