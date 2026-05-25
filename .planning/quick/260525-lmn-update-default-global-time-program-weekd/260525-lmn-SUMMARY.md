---
status: complete
quick_id: 260525-lmn
date: 2026-05-25
commit: cc97a0c
---

## Summary

Updated `const.py` to split the default time program into weekday and weekend schedules.

**Weekdays (mon–fri):** 5-period schedule — reduced overnight, short normal window in the morning (06:00–08:00), reduced during work hours (08:00–17:00), normal in the evening (17:00–22:00), reduced at night (22:00+).

**Weekends (sat–sun):** 3-period schedule — reduced overnight, normal all day (07:00–22:00), reduced at night.

Also updated `storage.py` to use `_DEFAULT_DAILY_PROGRAM[day]` instead of the removed `_DEFAULT_DAY_PERIODS` when seeding empty days in migrated configs. Updated `test_ws_reset_time_program_writes_defaults` to assert the correct weekday/weekend period starts.

All 84 tests pass.
