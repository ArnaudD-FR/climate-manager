---
status: resolved
slug: trv-stays-off-after-mode-exit
trigger:
  "TRVs stay in HVACMode.OFF after switching from global mode off to schedule
  mode. Temperature not updated either."
created: 2026-05-26
updated: 2026-05-26
---

# Debug Session: trv-stays-off-after-mode-exit

## Symptoms

- **Expected:** After switching global mode from "off" → "time_program", TRVs
  immediately receive HVACMode.HEAT + schedule temperature (e.g. Normal · 20°C)
- **Actual:** TRV shows "Off" and stale temperature (18°C) — not pushed.
  Screenshot: Tado-Bureau in Off mode at 18°C while period badge shows "Normal ·
  20°C"
- **Error messages:** None — push silently skipped
- **Timeline:** Introduced in 260526-ffr (MODE_OFF "off" sentinel added to
  \_last_pushed)
- **Reproduction:** Set global mode to "off" (TRVs push HVACMode.OFF), then
  switch back to "time_program"

## Current Focus

```
hypothesis: CONFIRMED — _push_if_changed manual override hold check fires spuriously when _last_pushed == "off" sentinel; float(reported) != "off" is always True in Python 3, causing every push to be skipped after MODE_OFF exit
test: Code inspection — coordinator.py:474-488
expecting: After clearing the "off" sentinel (treat as None), _push_if_changed proceeds to push schedule temperature normally
next_action: Fix _push_if_changed to treat string sentinel as None; add regression test for off→time_program transition
reasoning_checkpoint:
tdd_checkpoint:
```

## Evidence

- timestamp: 2026-05-26T23:14:46 screenshot: TRV "Tado - Bureau" shows "Off" /
  18°C after switching to schedule mode with Normal·20°C period
- timestamp: 2026-05-26T23:14:46 finding: coordinator.py:474 — last =
  self.\_last_pushed.get(entity_id) → "off" (string sentinel)
- timestamp: 2026-05-26T23:14:46 finding: coordinator.py:486 — float(reported)
  != last → float(18.0) != "off" → True (Python 3 cross-type compare) → spurious
  return
- timestamp: 2026-05-26T23:14:46 finding: tests/test_coordinator.py — no test
  covers off→time_program transition; 3 MODE_OFF tests cover
  entry/fallback/anti-flap only

## Eliminated Hypotheses

- Push fires but TRV ignores it: ELIMINATED — logs would show service calls;
  guard in \_push_if_changed is the block point

## Resolution

```
root_cause: _push_if_changed (coordinator.py:474) — when _last_pushed[entity_id] == "off" (string sentinel from _push_off_safely), the D-03 manual override hold check evaluates float(reported) != "off". Python 3 cross-type comparison never raises; any float != "off" is always True → return fires → push silently skipped on every tick after MODE_OFF exit.
fix: At entry of _push_if_changed, if isinstance(last, str): last = None — clears the stale off sentinel so both D-02 and D-03 treat this as a first push (no prior record). Push proceeds normally.
verification: 32/32 tests pass (regression test added); vite build 0 errors; commit 8931ff9
files_changed:
  - custom_components/climate_manager/coordinator.py
  - tests/test_coordinator.py (new regression test: off→time_program)
```
