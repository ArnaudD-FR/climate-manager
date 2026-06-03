---
id: 260602-kzf
slug: calendar-gap-modes-and-wakeup-desc
title: Calendar gap modes + wake-up advance description
status: in_progress
created: 2026-06-02
---

## Goal

Two improvements to the calendar presence feature:

1. **Wake-up advance description** — add a hint line under the "Wake-up advance"
   input in `person-card.ts` explaining what the field does.

2. **Calendar gap handling** — new `gap_handling` field on `calendar_config`
   (stored in both `PersonConfig` and per-period `calendar_config`):
   - `"exact"` (default, current behavior): present during any gap between events
   - `"day_span"`: absent from first event start to last event end — gaps ignored
   - `"threshold"`: present only when gap > N minutes (`gap_threshold_minutes`)

## Affected Files

- `custom_components/climate_manager/const.py`
- `custom_components/climate_manager/schedule.py`
- `custom_components/climate_manager/coordinator.py`
- `custom_components/climate_manager/websocket.py`
- `frontend/src/types.ts`
- `frontend/src/components/person-card.ts`
- `tests/test_calendar.py`

## Task Breakdown

### T-01 — const.py: add gap handling constants

Add to `const.py`:
```python
GAP_HANDLING_EXACT = "exact"
GAP_HANDLING_DAY_SPAN = "day_span"
GAP_HANDLING_THRESHOLD = "threshold"
DEFAULT_GAP_THRESHOLD_MINUTES: int = 30
```

### T-02 — schedule.py: refactor resolve_calendar_presence()

Extract `_is_calendar_active()` private helper that centralises gap logic, then
`resolve_calendar_presence()` becomes a simple inversion.

```python
def _is_calendar_active(events, now, gap_handling, gap_threshold_minutes, sol):
    """True if now should be treated as inside a calendar period."""
    parsed = []
    for event in events:
        ...parse + skip invalid...
    if not parsed:
        return False
    parsed.sort(key=lambda e: e[0])

    if gap_handling == "day_span":
        return parsed[0][0] <= now < parsed[-1][1]

    elif gap_handling == "threshold":
        # In an event → always active
        for start, end in parsed:
            if start <= now < end:
                return True
        # In a gap → active only if gap shorter than threshold
        td = datetime.timedelta(minutes=gap_threshold_minutes)
        for i in range(len(parsed) - 1):
            gap_start, gap_end = parsed[i][1], parsed[i+1][0]
            if gap_start <= now < gap_end:
                return (gap_end - gap_start) <= td
        return False

    else:  # "exact"
        for start, end in parsed:
            if start <= now < end:
                return True
        return False


def resolve_calendar_presence(events, event_means, now,
                              gap_handling="exact",
                              gap_threshold_minutes=0,
                              preheat_lead_minutes=60,
                              start_of_local_day=None) -> bool:
    _sol = start_of_local_day or _local_day_fallback
    active = _is_calendar_active(events, now, gap_handling,
                                 gap_threshold_minutes, _sol)
    if event_means == "absent":
        return not active
    return active
```

Signature change is backward-compatible (new kwargs with defaults).

### T-03 — coordinator.py: pass gap fields to resolve_calendar_presence()

In `_compute_present_persons()` and `_apply_presence_overrides()`, extract
`gap_handling` and `gap_threshold_minutes` from `cal_cfg` before calling:

```python
gap_handling = cal_cfg.get("gap_handling", "exact")
gap_threshold_minutes = cal_cfg.get("gap_threshold_minutes", 0)
present = resolve_calendar_presence(
    events, event_means, now,
    gap_handling=gap_handling,
    gap_threshold_minutes=gap_threshold_minutes,
    ...
)
```

### T-04 — websocket.py: validate gap fields

In the `set_person_config` handler, inside the `"calendar_config"` validation
block, add after event_means validation:

```python
gap_handling = cal_cfg.get("gap_handling", "exact")
if gap_handling not in ("exact", "day_span", "threshold"):
    cal_cfg.pop("gap_handling", None)
    gap_handling = "exact"
else:
    cal_cfg["gap_handling"] = gap_handling

if gap_handling == "threshold":
    raw_thr = cal_cfg.get("gap_threshold_minutes", 30)
    try:
        thr = int(raw_thr)
        cal_cfg["gap_threshold_minutes"] = max(0, min(480, thr))
    except (TypeError, ValueError):
        cal_cfg["gap_threshold_minutes"] = 30
else:
    cal_cfg.pop("gap_threshold_minutes", None)
```

### T-05 — types.ts: extend calendar_config on PersonConfig and Period

```typescript
calendar_config?: {
  entity_id: string;
  event_means: "absent" | "present";
  gap_handling?: "exact" | "day_span" | "threshold";
  gap_threshold_minutes?: number;
};
```

Apply to both `PersonConfig.calendar_config` and the `Period` union member's
`calendar_config`.

### T-06 — person-card.ts: UI changes

**A. Wake-up advance description** — add hint line below the input:
```html
<p class="field-hint">
  Minutes to start heating before your first event of the day.
</p>
```

**B. Gap handling select** — below event_means select, in the calendar config
block:

```html
<label>Gap handling</label>
<select @change=${this._onGapHandlingChange}>
  <option value="exact">Return home between events</option>
  <option value="day_span">Absent all day (first to last event)</option>
  <option value="threshold">Return home only in long gaps</option>
</select>
```

**C. Gap threshold input** — shown only when gap_handling === "threshold":

```html
<label>Minimum gap to return home</label>
<input type="number" min="0" max="480" step="5" ...>
<span class="suffix">min</span>
```

Auto-save handlers `_onGapHandlingChange` and `_onGapThresholdChange` follow
same pattern as existing calendar handlers.

### T-07 — tests/test_calendar.py: new gap mode tests

Add 6 new tests:
- `test_day_span_absent_in_gap`: gap between events → absent
- `test_day_span_absent_until_last_event_ends`: now = after last event → present
- `test_day_span_present_before_first_event`: now = before first event → present
- `test_threshold_absent_short_gap`: gap < threshold → absent
- `test_threshold_present_long_gap`: gap > threshold → present
- `test_threshold_in_event`: in active event → always absent

## Commit Message

feat(calendar): gap handling modes + wake-up advance description
