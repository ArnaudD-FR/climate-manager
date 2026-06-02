---
phase: 12-predictive-pre-heat
reviewed: 2026-06-02T10:30:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - custom_components/climate_manager/__init__.py
  - custom_components/climate_manager/coordinator.py
  - custom_components/climate_manager/schedule.py
  - custom_components/climate_manager/storage.py
  - custom_components/climate_manager/websocket.py
  - frontend/src/components/person-card.ts
  - frontend/src/components/room-card.ts
  - frontend/src/types.ts
  - tests/test_calendar.py
  - tests/test_preheat.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-06-02T10:30:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 12 adds predictive pre-heat: `next_occupied_at()` in `schedule.py`, a
pre-heat pass in `coordinator.py`, per-room preheat config storage, and
corresponding frontend controls in `room-card.ts` and `person-card.ts`. The
storage migration renames `preheat_lead_minutes` to `wakeup_advance_minutes`.

Two blockers were found. First, `schedule.py` still reads the old
`preheat_lead_minutes` key that is renamed in production — the user-configured
wakeup advance is silently ignored for scheduled-mode persons whose active
period has state `"calendar"`. Second, `_async_preheat_room` always evaluates
the zone's time program to determine the upcoming setpoint, even for rooms in
`room_mode=custom`; this produces the wrong target temperature whenever the
custom program differs from the zone program at the next-occupied time.

Five warnings and three info items cover: a deferred `import statistics` inside
a hot async path, a TypeScript type lie on `zone_id=null`, duplicate
accessibility labels, boolean-passes-int-check for numeric config fields,
zero-duration samples biasing learned lead, and dead code.

---

## Critical Issues

### CR-01: `schedule.py` reads stale `preheat_lead_minutes` key — wakeup advance always ignored

**File:** `custom_components/climate_manager/schedule.py:355`

**Issue:** `resolve_presence()` reads `preheat_lead_minutes` directly from
`person_config` to pass to `resolve_calendar_presence()`. Storage migration
(`storage.py:148-154`) and the WebSocket handler (`websocket.py:570-573`) both
rename this key to `wakeup_advance_minutes` before persisting. In production,
any person config loaded from storage will have `wakeup_advance_minutes` and
**no** `preheat_lead_minutes` key, so the `dict.get("preheat_lead_minutes", 60)`
call at line 355 always returns the hardcoded fallback `60` regardless of what
the user configured. The user-visible "Wake-up advance" setting in the panel is
completely ignored for the calendar-period-state path in `resolve_presence()`.

The coordinator (`coordinator.py:444-450` and `1007-1013`) already has the
correct dual-key fallback chain; `schedule.py` does not.

**Fix:**

```python
# schedule.py line 355 — replace:
preheat = person_config.get("preheat_lead_minutes", 60)

# with the same fallback chain used by coordinator.py:
preheat = person_config.get(
    "wakeup_advance_minutes",
    person_config.get("preheat_lead_minutes", 60),
)
```

---

### CR-02: Pre-heat trigger uses zone time program for `room_mode=custom` rooms — wrong setpoint

**File:** `custom_components/climate_manager/coordinator.py:714-720`

**Issue:** `_async_preheat_room()` calls `self._resolve_zone_config(area_id,
config)` to obtain the time program for setpoint calculation (line 714). This
always returns the **zone's** time program. When a room has `room_mode=custom`,
its own `time_program` (set by the user in the panel) is the actual schedule
that `_compute_desired_temps()` uses for the normal push pass. If the two
programs assign different period modes at `next_occupied` time, the pre-heat
fires at the **zone's** setpoint, but the main push immediately overrides to
the room's own setpoint one minute later. The pre-heat target recorded in
`_preheat_target[area_id]` and displayed in the panel is also wrong.

**Fix:**

```python
# coordinator.py — before line 714, resolve using room's own program when custom:
room_config_ph = (config.get("rooms") or {}).get(area_id, {})
if room_config_ph.get("room_mode") == ROOM_MODE_CUSTOM:
    zone_time_program = (
        room_config_ph.get("time_program")
        or config.get("global_time_program", {})
    )
else:
    _zone_mode, zone_time_program = self._resolve_zone_config(area_id, config)
upcoming_period = evaluate_schedule(zone_time_program, next_occupied)
```

---

## Warnings

### WR-01: Deferred `import statistics` inside hot async path

**File:** `custom_components/climate_manager/coordinator.py:697`

**Issue:** `import statistics` is placed inside the body of
`_async_preheat_room()`, inside a conditional branch that fires every minute
once a room accumulates `>= 3` samples. `statistics` is a standard-library
module so it will never fail, but Python must search `sys.modules` on every
call until the module is cached there. More importantly, the `# noqa: PLC0415`
suppression hides a linter rule that exists for this reason. Move the import to
the top of `coordinator.py` with the other stdlib imports.

**Fix:** Add `import statistics` at line ~45 in the top-level imports block and
remove the inline import and the `# noqa` comment.

---

### WR-02: `isinstance(val, int)` accepts `bool` — `True`/`False` bypasses validation

**File:** `custom_components/climate_manager/websocket.py:446,577`

**Issue:** Python's `bool` is a subclass of `int`, so `isinstance(True, int)`
evaluates to `True`. Both `preheat_max_lead_minutes` (line 446) and
`wakeup_advance_minutes` (line 577) are validated with `isinstance(val, int)`.
A WebSocket message containing `{"preheat_max_lead_minutes": true}` passes
validation, stores `True` (which is `1` numerically), and then the coordinator
uses it as a `1`-minute maximum lead. This is unlikely from the frontend (which
uses `parseInt`), but a crafted message can break preheat behavior silently.

**Fix:**

```python
# Both sites — replace the isinstance check:
if not (isinstance(val, int) and not isinstance(val, bool) and 0 <= val <= 480):
    incoming_config.pop("preheat_max_lead_minutes")
```

---

### WR-03: Zero-duration preheat samples corrupt learned-lead average

**File:** `custom_components/climate_manager/coordinator.py:619-626`

**Issue:** `duration_min` is computed as
`int((now - start_time).total_seconds() / 60)`. If convergence is detected on
the same tick that triggered preheat (e.g. room is already warm, but
`current_temp` was `None` on the trigger tick so the warm-guard was bypassed),
`start_time == now` gives `duration_min = 0`. A zero-minute sample is recorded
and persisted, and subsequent calls to `statistics.mean()` will bias the
learned lead toward zero, eventually causing the trigger window to shrink to
near-zero minutes and making pre-heat ineffective. There is no minimum-sample
guard.

**Fix:** Add a minimum guard before appending:

```python
duration_min = int((now - start_time).total_seconds() / 60)
if duration_min < 1:
    # Convergence on same tick — invalid sample, discard silently
    del self._preheat_in_progress[area_id]
    self._preheat_active[area_id] = False
    return
samples = self._data.preheat_samples.setdefault(area_id, [])
```

---

### WR-04: `zone_id: null as unknown as string | undefined` bypasses TypeScript type safety

**File:** `frontend/src/components/room-card.ts:425`

**Issue:** When a user clears a room's zone assignment, the frontend sends
`{ zone_id: null }` via this cast: `{ zone_id: null as unknown as string |
undefined }`. The `as unknown as` double-cast is a TypeScript type lie that
suppresses a legitimate type error rather than fixing it. If the `RoomConfig`
interface or downstream WS call signature ever changes (e.g. to validate that
`zone_id` is `string | undefined`), this cast silently sends `null` past the
compiler. The backend does handle `null` correctly (websocket.py line 437), but
the frontend lies to the type system to do it.

**Fix:** Update `RoomConfig.zone_id` in `types.ts` to allow `null` explicitly
for the clear-assignment case, or use a separate field / omit the key:

```typescript
// types.ts — update zone_id to accept null for clearing:
zone_id?: string | null;

// room-card.ts line 423-425:
const patch: Partial<RoomConfig> = newZoneId
  ? { zone_id: newZoneId }
  : { zone_id: null };
```

---

### WR-05: Test helper `_calendar_person_config` injects deprecated `preheat_lead_minutes` key — masks CR-01

**File:** `tests/test_calendar.py:358-373`

**Issue:** `_calendar_person_config()` builds person config dicts with
`"preheat_lead_minutes"` key (line 371). These are injected directly into
`runtime_data.runtime_config`, bypassing the storage migration that renames the
key to `wakeup_advance_minutes`. As a result, `schedule.py:355`'s `dict.get(
"preheat_lead_minutes", 60)` **succeeds** in tests (finds the key), masking the
production bug documented in CR-01. The same issue applies to
`test_calendar_period_overrides_rooms` (line 656).

**Fix:** Replace the deprecated key in the helper and test data:

```python
# test_calendar.py line 371:
"wakeup_advance_minutes": DEFAULT_PREHEAT_LEAD_MINUTES,
# (and same at line 656)
```

---

## Info

### IN-01: `PERIOD_LABELS` has duplicate value `"C"` for `comfort` and `calendar`

**File:** `frontend/src/types.ts:235,238`

**Issue:** `PERIOD_LABELS` maps both `comfort` and `calendar` to `"C"`. These
single-character labels are described as "for accessibility." If a consumer
iterates labels or uses them as identifiers, the collision will produce
ambiguous output. Current usage in the time-bar appears visual-only, but the
duplicate is a latent correctness hazard.

**Fix:**

```typescript
export const PERIOD_LABELS: Record<string, string> = {
  // ...
  comfort: "C",
  calendar: "K",  // distinguish from Comfort
};
```

---

### IN-02: Redundant `end > now` condition in `_next_occupied_calendar`

**File:** `custom_components/climate_manager/schedule.py:446`

**Issue:** The condition `if start <= now < end and end > now:` is logically
equivalent to `if start <= now < end:` because `now < end` already implies
`end > now`. The second clause is dead code. Not a bug, but leaves misleading
defensive intent in a public function.

**Fix:**

```python
# schedule.py line 446:
for start, end in events:
    if start <= now < end:
        return end
```

---

### IN-03: `ClimateConfig.calibration_threshold` carries a `TODO` comment for a missing mutation path

**File:** `frontend/src/types.ts:122-124`

**Issue:** The `calibration_threshold` field has an inline TODO noting that no
mutation path exists yet: `TODO(phase-10): no mutation path exists yet —
backend const only. Remove this field or add a setCalibrationThreshold WS
command in the phase that exposes threshold configuration to the user.` Phase
10 has shipped; this is now stale dead configuration surface.

**Fix:** Either add the `set_calibration_threshold` WS command in the current
or next phase, or remove the `calibration_threshold` field from `ClimateConfig`
until it is implemented. Remove the TODO comment in either case.

---

_Reviewed: 2026-06-02T10:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
