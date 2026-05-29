---
phase: 260525-lmn
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - custom_components/climate_manager/const.py
autonomous: true
---

<objective>
Update the default global time program in const.py to differentiate weekdays from weekends.

Weekdays (mon–fri): 00:00 reduced → 06:00 normal → 08:00 reduced → 17:00 normal
→ 22:00 reduced

Weekends (sat–sun): 00:00 reduced → 07:00 normal → 22:00 reduced

The existing single `_DEFAULT_DAY_PERIODS` becomes two separate lists:
`_DEFAULT_WEEKDAY_PERIODS` and `_DEFAULT_WEEKEND_PERIODS`.
`_DEFAULT_DAILY_PROGRAM` maps each day key to the appropriate list
(deep-copied).

The frontend reset button already calls the backend `reset_time_program` command
(task 260525-l0p) which deep-copies `_DEFAULT_DAILY_PROGRAM` — no frontend
changes needed. </objective>

<tasks>
<task type="auto">
  <name>Task 1: Split default periods into weekday/weekend in const.py</name>
  <files>custom_components/climate_manager/const.py</files>
  <action>
Replace the current `_DEFAULT_DAY_PERIODS` + `_DEFAULT_DAILY_PROGRAM` block with:

```python
_DEFAULT_WEEKDAY_PERIODS: list[dict] = [
    {"start": "00:00", "mode": PERIOD_REDUCED},
    {"start": "06:00", "mode": PERIOD_NORMAL},
    {"start": "08:00", "mode": PERIOD_REDUCED},
    {"start": "17:00", "mode": PERIOD_NORMAL},
    {"start": "22:00", "mode": PERIOD_REDUCED},
]

_DEFAULT_WEEKEND_PERIODS: list[dict] = [
    {"start": "00:00", "mode": PERIOD_REDUCED},
    {"start": "07:00", "mode": PERIOD_NORMAL},
    {"start": "22:00", "mode": PERIOD_REDUCED},
]

_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
_WEEKEND = ["sat", "sun"]

_DEFAULT_DAILY_PROGRAM: dict = {
    **{day: copy.deepcopy(_DEFAULT_WEEKDAY_PERIODS) for day in _WEEKDAYS},
    **{day: copy.deepcopy(_DEFAULT_WEEKEND_PERIODS) for day in _WEEKEND},
}
```

Update the comment block above the section to document the new schedules.
</action> <verify> <automated>cd /home/arnaud/dev/climate_manager && uv run
pytest tests/ -x -q 2>&1 | tail -5</automated> </verify> <done>Tests pass;
const.py has weekday/weekend split; \_DEFAULT_DAILY_PROGRAM has correct 5-period
weekdays and 3-period weekends.</done> </task> </tasks>
