---
slug: no-default-time-periods
status: root_cause_found
trigger: "there is no default time periods for each week days"
created: 2026-05-18
---

# Debug Session: no-default-time-periods

## Symptoms

When the Global Settings panel loads for the first time (fresh install or no saved
`global_time_program`), the time-bar shows empty grey bars for all 7 weekdays with
"Click the bar to add your first period." hint text. No default periods are pre-populated.

## Hypotheses

1. **[CONFIRMED — ROOT CAUSE]** Backend `DEFAULT_CONFIG` defines `global_time_program`
   as `{day: [] for day in days}` — all empty lists. On fresh install the storage layer
   returns this empty default, so `get_config` returns an empty program. There is no
   seeding of sensible default periods anywhere in the backend.

2. **[RULED OUT]** Frontend fails to pass defaults to the time-bar. `global-settings-tab.ts`
   calls `programToDays(this.config.global_time_program)` which maps each day key to its
   array. If backend sends empty arrays, frontend faithfully passes empty arrays — no
   frontend fault.

3. **[RULED OUT]** Time-bar has a broken default-period mechanism. `time-bar.ts` has no
   default-period generation; it renders an empty hint when `periods.length === 0`. The
   component is purely presentational — it does not invent defaults.

## Evidence

- `custom_components/climate_manager/const.py` line 61:
  `_EMPTY_DAILY_PROGRAM: dict = {day: [] for day in _DAYS_ORDERED}`
- `const.py` line 120:
  `"global_time_program": copy.deepcopy(_EMPTY_DAILY_PROGRAM)` — all 7 days empty
- `storage.py` `async_load()` returns `copy.deepcopy(DEFAULT_CONFIG)` on fresh install —
  no migration or seeding step fills in default periods
- `websocket.py` `ws_get_config` returns `entry.runtime_data.runtime_config` verbatim —
  empty program reaches the frontend unchanged
- `global-settings-tab.ts` `programToDays()` maps missing days to `[]` — correct but
  cannot add periods that do not exist in the source data

## Current Focus

**Root cause:** `DEFAULT_CONFIG` uses an empty daily program. The fix must define
sensible default periods in `const.py` — a typical weekday heating schedule
(e.g. frost_protection overnight, normal during the day) — so that both fresh installs
and any storage migration path deliver a pre-populated schedule.

**Next action:** Update `_EMPTY_DAILY_PROGRAM` → `_DEFAULT_DAILY_PROGRAM` with a
representative default schedule; apply to `DEFAULT_CONFIG`.

## Resolution

### Root Cause
`DEFAULT_CONFIG["global_time_program"]` was initialised with empty period arrays
(`[]`) for every weekday via `_EMPTY_DAILY_PROGRAM`. Storage `async_load()` returns
this deep-copy verbatim on fresh install, so the frontend receives empty days and the
time-bar renders blank bars.

### Fix
Replace `_EMPTY_DAILY_PROGRAM` with `_DEFAULT_DAILY_PROGRAM` in `const.py` that
provides a sensible all-week default: frost_protection 00:00–06:00, normal 06:00–22:00,
frost_protection 22:00–24:00. Applied to `DEFAULT_CONFIG["global_time_program"]`.
