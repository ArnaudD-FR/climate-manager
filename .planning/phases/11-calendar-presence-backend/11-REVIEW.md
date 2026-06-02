---
phase: 11-calendar-presence-backend
reviewed: 2026-06-02T10:45:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - custom_components/climate_manager/const.py
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/schedule.py
  - custom_components/climate_manager/websocket.py
  - frontend/src/components/person-card.ts
  - frontend/src/components/time-bar.ts
  - frontend/src/types.ts
  - tests/test_calendar.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-06-02T10:45:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

Phase 11 adds calendar-driven presence resolution: a new `calendar` person
mode, a `calendar` period state within scheduled-mode persons, a per-cycle
`calendar.get_events` prefetch in the coordinator, preheat lead-time logic in
`schedule.py`, and corresponding frontend UI in `person-card.ts`. The design
is sound and the security validation layer (T-11-06, entity_id prefix check)
is present. Two critical defects were found: a crash-path from unguarded
`fromisoformat()` calls on data returned by HA's calendar service, and a
silent data-loss path in the frontend where an unsaved `event_means` change
is dropped when no calendar entity has been selected yet. Several warnings
cover log-spam from a misleading "log once" comment, a `calendar` period
being split to `present` instead of cycling correctly, and missing validation
on `event_means`. Three info items cover dead code, a duplicate constant
label, and a fragile test pattern.

## Critical Issues

### CR-01: Unguarded `fromisoformat()` on calendar event data crashes `async_evaluate`

**File:** `custom_components/climate_manager/schedule.py:169-170`

**Issue:** `_parse_calendar_dt()` calls `datetime.datetime.fromisoformat(s)`
and `datetime.date.fromisoformat(s)` with no `try/except`. These raise
`ValueError` if the calendar service returns a malformed `start` or `end`
string (e.g. `"Invalid date"`, a missing key default, or an unexpected
third-party calendar format). The exception propagates through
`resolve_calendar_presence()` → `_compute_present_persons()` or
`_apply_presence_overrides()` → `async_evaluate()` with no wrapping guard.
The net effect is that the entire minute evaluation tick is aborted for all
rooms, not just the person with the bad event. Although the `async_track_time_interval`
scheduler survives (the task failure is logged by asyncio and the next tick
still fires), every occurrence of a malformed event causes a full-minute
evaluation blackout, during which TRVs receive no temperature updates.

**Fix:**
```python
def _parse_calendar_dt(
    s: str,
    start_of_local_day,
) -> datetime.datetime:
    try:
        if "T" in s:
            return datetime.datetime.fromisoformat(s)
        d = datetime.date.fromisoformat(s)
        return start_of_local_day(d)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Unparseable calendar datetime {s!r}") from exc
```

Then in `resolve_calendar_presence()` wrap the per-event parse:
```python
    for event in events:
        start_s = event.get("start", "")
        end_s = event.get("end", "")
        if not start_s or not end_s:
            continue
        try:
            event_start = _parse_calendar_dt(start_s, _sol)
            event_end = _parse_calendar_dt(end_s, _sol)
        except ValueError:
            _LOGGER.warning(
                "Skipping calendar event with unparseable datetime: %r",
                event,
            )
            continue
        ...
```

This keeps the crash local to the malformed event rather than aborting the
entire evaluation cycle.

---

### CR-02: Silent loss of `event_means` change when no calendar entity is selected

**File:** `frontend/src/components/person-card.ts:488-502`

**Issue:** `_onEventMeansChange` reads `currentEntityId` from
`this.config?.calendar_config?.entity_id ?? ""`. When the user has not yet
selected a calendar entity (entity_id is `""`), the handler sends a
`set_person_config` payload of
`{ calendar_config: { entity_id: "", event_means: <new_value> } }`.
The backend's T-11-06 guard in `websocket.py:511-512` then pops the entire
`calendar_config` key from `incoming` because `""` does not start with
`"calendar."`. The `.update(incoming)` call at line 522 receives no
`calendar_config` key and leaves the stored record unchanged. The backend
returns `success: true`, but the `event_means` selection the user just made
is silently discarded. No toast error is shown.

The same issue exists in `_onPeriodCalendarConfigChange` (line 1056) when
`currentEntityId` is `""`.

**Fix:** Guard before sending to avoid the silent drop:
```typescript
private async _onEventMeansChange(e: Event) {
  const means = (e.target as HTMLSelectElement).value as "absent" | "present";
  const currentEntityId = this.config?.calendar_config?.entity_id ?? "";
  // Cannot save event_means without a calendar entity selected.
  if (!currentEntityId) {
    this.panel.showToast(
      "Select a calendar entity first before changing event meaning.",
      true,
    );
    return;
  }
  // ... existing save logic ...
}
```

Apply the same guard in `_onPeriodCalendarConfigChange` at the top of the
method when `currentEntityId` is `""` for the `event_means` branch.

---

## Warnings

### WR-01: "Log once" comment is wrong — WARNING fires every minute on calendar unavailability

**File:** `custom_components/climate_manager/coordinator.py:207,260`

**Issue:** The docstring says `"D-04: HomeAssistantError → single WARNING +
empty-list fallback"` and the inline comment reads `"# D-04: log once at
WARNING"`. In reality, `_calendar_cache` is reset to `{}` at the top of
every `async_evaluate` cycle (line 157), so every cycle with an unavailable
calendar entity triggers a fresh `_fetch_one` call, a new
`HomeAssistantError`, and a new `WARNING` log line. With a 1-minute poll
interval this produces one WARNING per minute indefinitely. There is no
"log once" throttle mechanism anywhere in the code.

**Fix:** Either implement actual throttling (track last-warned time per
entity_id on the coordinator) or correct the comment to accurately describe
the current behavior:
```python
# D-04: WARNING per cycle on calendar entity unavailability;
# empty-list fallback keeps the person as absent.
_LOGGER.warning(
    "Calendar entity %s unavailable — falling back to absent",
    eid,
)
```

If true one-time logging is desired:
```python
if eid not in self._calendar_warn_issued:
    _LOGGER.warning(
        "Calendar entity %s unavailable — falling back to absent "
        "(further failures for this entity will be suppressed)",
        eid,
    )
    self._calendar_warn_issued.add(eid)
```

Clear `_calendar_warn_issued` on successful fetch so the warning re-fires
after recovery.

---

### WR-02: Splitting a `calendar` period state produces incorrect `present` half

**File:** `frontend/src/components/time-bar.ts:697-698`

**Issue:** `PRESENCE_CYCLE = ["present", "absent"]` does not include
`"calendar"`. When the user opens the "Split period" action on a segment
with `state="calendar"`, `cycle.indexOf("calendar")` returns `-1`. Then:
```
nextType = cycle[(-1 + 1) % 2] = cycle[0] = "present"
```
The split creates a `{ state: "present" }` second half. The `"calendar"` type
is effectively demoted to `"present"` silently on split, losing the calendar
configuration for that half. A user expecting both halves to remain `calendar`
(or get a logical next type) will see incorrect behavior.

**Fix:** Handle `"calendar"` as a special case before the cycle lookup:
```typescript
const currentIdx = cycle.indexOf(currentType);
// "calendar" is not in PRESENCE_CYCLE; split produces "absent" as the
// next half — calendar config cannot be cloned automatically.
const nextType =
  currentIdx === -1 ? "absent" : cycle[(currentIdx + 1) % cycle.length];
```

Returning `"absent"` for an unknown type is explicit and safe; the user can
then use "Change mode" on the new half to set it to `"calendar"` and
configure its entity.

---

### WR-03: `event_means` is not validated in `set_person_config`

**File:** `custom_components/climate_manager/websocket.py:504-512`

**Issue:** The T-11-06 guard validates `entity_id` but does not validate
`event_means`. Any string value can be stored. In
`schedule.py:resolve_calendar_presence` the logic is:
```python
if event_means == "absent":
    ...
else:  # implicitly "present" or anything else
    ...
```
A stored `event_means` of `"foo"` would be silently treated as `"present"`,
causing the person's presence state to invert.

**Fix:** Add a `vol.In` check when extracting `calendar_config` in
`set_person_config`:
```python
if "calendar_config" in incoming:
    cal_cfg = incoming["calendar_config"]
    eid = (
        cal_cfg.get("entity_id", "")
        if isinstance(cal_cfg, dict)
        else ""
    )
    event_means = (
        cal_cfg.get("event_means", "absent")
        if isinstance(cal_cfg, dict)
        else "absent"
    )
    if not (isinstance(eid, str) and eid.startswith("calendar.")):
        incoming.pop("calendar_config")
    elif event_means not in ("absent", "present"):
        incoming.pop("calendar_config")
```

---

### WR-04: Selecting the `"— Select a calendar —"` placeholder silently erases an existing calendar association

**File:** `frontend/src/components/person-card.ts:826-831`

**Issue:** When calendar entities exist, the `<select>` includes a
non-disabled placeholder option `value=""` (line 827). Selecting it fires
`_onCalendarEntityChange` with `entityId=""`, which sends
`{ calendar_config: { entity_id: "", event_means: <current> } }` to the
backend. The backend's T-11-06 pops the entire `calendar_config` block,
returning `success: true`. This erases a previously configured
`calendar_config` silently. The user sees "Saved" in the toast, but the
calendar source is gone.

Compare line 822 where the "no calendars" fallback option IS `disabled` but
the placeholder when calendars exist is not.

**Fix:** Add `disabled` to the placeholder option, or handle the `""` value
explicitly in `_onCalendarEntityChange`:
```typescript
<option value="" disabled ?selected=${!this.config?.calendar_config?.entity_id}>
  — Select a calendar —
</option>
```

Alternatively, return early in `_onCalendarEntityChange` when `entityId` is
`""` rather than propagating the erase to the backend.

---

### WR-05: Test at line 581 uses HA private internal API `hass.services._services`

**File:** `tests/test_calendar.py:581`

**Issue:** The test directly pops the `"calendar"` key from
`hass.services._services` (a private attribute) to swap the mock service
between evaluation cycles. This is flagged with `# noqa: SLF001` acknowledging
it is a private access. The HA test framework may change the internal
structure of the service registry across versions, breaking this test silently
(it would appear to pass because the second `async_mock_service` call would
register against an empty registry, but the coordinator might then not call
`get_events` at all, causing the assertion to pass vacuously).

**Fix:** Use the standard HA test pattern of replacing the mock before the
second evaluate call by letting `async_mock_service` overwrite the existing
handler:
```python
# Instead of popping _services, just re-register with the same domain/service.
# HA's async_mock_service replaces the existing handler for the same key.
hass.services.async_remove("calendar", "get_events")
async_mock_service(
    hass,
    "calendar",
    "get_events",
    response={cal_id: {"events": []}},
    supports_response=SupportsResponse.ONLY,
)
```

If `async_remove` is not available in the test harness version, use the
`patch` mechanism from `unittest.mock` to swap the handler instead of
reaching into private state.

---

## Info

### IN-01: `PERIOD_LABELS` constant is exported but never used

**File:** `frontend/src/types.ts:197-205`

**Issue:** `PERIOD_LABELS` (single-character labels F/R/N/C, P/A, C) is
exported from `types.ts` but never imported anywhere in the frontend source.
It is dead code.

**Fix:** Remove the export, or add the missing `import { PERIOD_LABELS }` in
the component that would use it (e.g. for accessibility `aria-label`
generation in `time-bar.ts`).

---

### IN-02: `PERIOD_LABELS` has duplicate `"C"` for both `comfort` and `calendar`

**File:** `frontend/src/types.ts:201,204`

**Issue:** Both `comfort` and `calendar` map to `"C"` in `PERIOD_LABELS`.
Any code using this map for display would silently produce the same character
for two distinct period types. The value for `calendar` should be `"Cal"` or
some other disambiguating label.

**Fix:**
```typescript
export const PERIOD_LABELS: Record<string, string> = {
  frost_protection: "F",
  reduced: "R",
  normal: "N",
  comfort: "C",
  present: "P",
  absent: "A",
  calendar: "Cal", // Phase 11 — distinguish from "comfort"
};
```

---

### IN-03: D-04 "no log spam" test only verifies a single cycle

**File:** `tests/test_calendar.py:477-520`

**Issue:** `test_calendar_fallback_on_error` asserts exactly one WARNING in a
single `async_evaluate` call. It does not verify that a second cycle also
produces exactly one WARNING (i.e., that the log-spam concern is actually
tested). Given that WR-01 shows the code does log every cycle, the test
does not exercise the stated requirement (`D-04: no log spam`).

**Fix:** Add a second `async_evaluate` call and assert total WARNING count
is 2 (one per cycle), or explicitly document that "no log spam" means the
test is aspirational / a separate deduplication mechanism needs to be built.
If WR-01 is fixed (throttled logging), update this test to assert count == 1
across both cycles.

---

_Reviewed: 2026-06-02T10:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
