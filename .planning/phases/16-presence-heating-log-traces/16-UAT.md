---
status: complete
phase: 16-presence-heating-log-traces
source: [16-01-SUMMARY.md, 16-02-SUMMARY.md, 16-03-SUMMARY.md, 16-04-SUMMARY.md, 16-05-SUMMARY.md, 16-06-SUMMARY.md, 16-07-SUMMARY.md]
started: 2026-06-05T19:53:29Z
updated: 2026-06-05T19:53:29Z
---

## Current Test

[testing complete]

## Tests

### 1. Zone period-change log (schedule-driven)
expected: When the zone schedule rolls to a new period, an INFO line is emitted —
  `zone | zone=<name> state=<old>[<mode>]→<new>[<mode>] reason=time_program:<period>`
result: pass
evidence: |
  Server log 2026-06-05 14:34:09 and 14:39:35 —
  `zone | zone=default state=normal[time_program_presences]→reduced[time_program_presences] reason=time_program:reduced`
  `zone | zone=default state=normal[time_program]→frost_protection[off] reason=time_program:frost_protection`

### 2. Zone mode-change log (user-driven)
expected: Switching a zone's mode from the panel emits an INFO line —
  `zone | zone=<name> state=<period>[<old_mode>]→<period>[<new_mode>] reason=user:<old>→<new>`
result: pass
evidence: |
  Server log 2026-06-05 14:34:40 / 14:39:19 —
  `zone | zone=default state=reduced[time_program_presences]→reduced[time_program] reason=user:time_program_presences→time_program`
  `zone | zone=default state=normal[time_program_presences]→normal[off] reason=user:time_program_presences→off`

### 3. Presence flip log
expected: When a person's home/away result flips, one INFO line is emitted —
  `presence | person=<name> home=<bool> reason=<mode>` (anti-spam: only on flip)
result: pass
evidence: |
  Server log 2026-06-05 14:33:36–14:34:20 —
  `presence | person=arnaud home=True reason=scheduled`,
  `presence | person=thomas home=False reason=calendar`,
  `presence | person=arnaud home=False reason=scheduled`. Single person change
  no longer logs all persons (carry-forward of _last_home on rebuild).

### 4. Presence-aware heating per room
expected: In a Time & presence zone, an empty room (0 present) drops to Reduced
  while an occupied room (>=1 present) stays Normal/Comfort — independently per room.
result: pass
evidence: |
  ROOMS screenshot 2026-06-05 14:55 — Bureau/Lucie/Thomas (0/1) show Reduced·18°C;
  Chambre des parents (1/2) and Cuisine (1/4) show Normal·20°C. Fixed per-room
  period tracking (Room._last_period) so the status badge matches the TRV push.

### 5. Boiler excluded from TRV pushes
expected: Boiler/HVAC climate entities (max_temp > 45°C) are never sent a room
  setpoint; no recurring push-failure warnings.
result: pass
evidence: |
  Pre-fix: `Failed to push temperature to climate.e3_vitodens_200_0821_heating`
  every minute. Post-fix (is_trv_entity filter in TRVGroup.from_room_config):
  last warning 2026-06-05 14:45:41, silent through 14:56:30+.

### 6. Heating DEBUG trace
expected: With logger at debug, each setpoint push emits —
  `heating | room=<name> temp=<T>°C zone=<name> slot=<period>`
result: pass
evidence: |
  Accepted on automated evidence — tests/test_trv.py
  ::test_trv_push_temperature_first_call_pushes_and_logs asserts the exact
  caplog DEBUG format on push, and ::test_trv_push_temperature_repeat_same_
  setpoint_no_push_no_log asserts anti-spam (no duplicate). DEBUG level is off
  by default in the live HA (integration runs at info), so not surfaced in
  production logs by design.

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

<!-- none reported -->
