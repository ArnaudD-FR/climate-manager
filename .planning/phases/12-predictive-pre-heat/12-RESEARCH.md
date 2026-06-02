# Phase 12: Predictive Pre-heat — Research

**Researched:** 2026-06-02
**Domain:** HA custom integration — coordinator pre-heat engine, adaptive
  inertia learning, Store persistence, frontend room card extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Per-room sparse keys `preheat_enabled` and
  `preheat_max_lead_minutes` (default 120) on room objects in the
  existing Store. Absent = not enabled.
- **D-02:** Rename per-person `preheat_lead_minutes` →
  `wakeup_advance_minutes` in schema. Migration: read old key if new
  key absent, at `async_setup_entry`.
- **D-03:** New pure function `next_occupied_at(person_config, now,
  calendar_cache, ...)` in `schedule.py`. Returns next occupied
  `datetime` or `None`. Mode dispatch: `"scheduled"` / `"even_odd"` →
  walk 7-day window; `"calendar"` → use `_calendar_cache` events;
  `"ha"` → `None`; `"force_present"` / `"force_absent"` → `None`.
- **D-04:** Coordinator takes earliest non-`None` across all persons
  assigned to a room.
- **D-05:** Pre-heat trigger: `now >= next_occupied_at - lead_minutes`
  AND `now < next_occupied_at` AND `current_temp < setpoint - threshold`.
- **D-06:** Separate Store `climate_manager_preheat`: key `{area_id}` →
  list of `{duration_minutes, timestamp}` samples.
- **D-07:** Valid sample: target reached within `preheat_max_lead_minutes`.
  Samples where target not reached are discarded.
- **D-08:** Learned lead = simple average of last 5 valid samples, capped
  at `preheat_max_lead_minutes`. Default 60 min until 3+ samples exist.
- **D-09:** In-memory `_preheat_in_progress: dict[area_id, {start_time,
  target_temp}]`. Convergence check each cycle: `current_temp >= target
  - 0.2`. On convergence: compute duration, store sample, persist. If
  cycle fires with `now >= next_occupied_at` and target not reached:
  discard in-progress entry.
- **D-10:** `get_state` / `state_updated` room payload gains
  `preheat_active: bool`, `preheat_target: float | null`,
  `preheat_suppressed: bool`.
- **D-11:** Pre-heat config UI inline in room card below TRV list:
  checkbox labeled "Pre-heat this room" + max-lead-time `<input
  type="number">` (hidden when disabled) + status line. Auto-save on
  change. Native HTML controls (not ha-* components).

### Claude's Discretion

None specified — all decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- EWMA or ambient-corrected learning
- Per-room sample pruning by age (timestamps stored, pruning deferred)
- Pre-heat for `force_present` / `force_absent` persons
- Pre-heat with boiler demand control
- Configurable sample window size (fixed 3 min / 5 max stored)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PREHEAT-01 | Per-room pre-heat toggle + configurable max lead time (default 120 min) in Rooms tab | D-01, D-11; `set_room_config` WS command carries the new sparse keys |
| PREHEAT-02 | Coordinator starts heating before next normal/comfort period using learned inertia; initial default 60 min | D-05, D-08; pre-heat pass runs after calibration pass in `async_evaluate` |
| PREHEAT-03 | Learns room thermal inertia from 3-5 complete cycles; samples that never reached target are excluded | D-06, D-07, D-08, D-09; separate `climate_manager_preheat` Store |
| PREHEAT-04 | Panel shows "Pre-heating (→ XX.X°C)" when active; "Pre-heat disabled…" when suppressed | D-10, D-11; `preheat_active` / `preheat_suppressed` fields on room status |
| PREHEAT-05 | Compatible with even/odd and calendar scheduling | D-03; `next_occupied_at()` handles `even_odd` and `calendar` modes |
</phase_requirements>

---

## Summary

Phase 12 adds a predictive pre-heat engine to the existing coordinator. All
architecture decisions are fully locked in CONTEXT.md; this research phase
confirms their implementation correctness against the existing codebase and
identifies every integration point.

The pre-heat engine is a new private `_async_preheat()` pass in
`coordinator.py`, structurally identical to the existing `_async_calibrate()`
pass (asyncio.gather over rooms, called at the end of `async_evaluate`). It
reads from a second `Store` instance (`climate_manager_preheat`) for sample
persistence. A new pure function `next_occupied_at()` in `schedule.py` computes
when a person will next be present, paralleling `resolve_presence()`. The
frontend extends `RoomConfig`, `RoomStatus`, and the room card with native HTML
controls following the established auto-save pattern.

The rename `preheat_lead_minutes` → `wakeup_advance_minutes` (D-02) is a
schema migration on the *person* config, not the room config. The backend must
read both keys during a transition window (old key fallback if new key absent).
The quick task `260602-wakeup-advance-rename` changed only the UI label, not the
storage key — the full schema rename (storage key + constant + migration) is
Phase 12 work.

**Primary recommendation:** Implement in 3 waves: (1) backend engine +
migration, (2) WS / status changes, (3) frontend room card UI.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `next_occupied_at()` computation | Backend (schedule.py) | — | Pure Python, no HA imports — same constraint as `resolve_presence()` |
| Pre-heat trigger evaluation | Backend (coordinator.py) | — | Needs access to TRV current_temperature via hass.states; I/O-bound |
| Sample recording + persistence | Backend (coordinator.py) | Store | In-memory tracking in coordinator; Store for durability |
| `wakeup_advance_minutes` migration | Backend (__init__.py/storage.py) | — | Runs at `async_setup_entry` time; same pattern as existing mode migrations |
| Pre-heat status in WS payload | Backend (coordinator.py, websocket.py) | — | Both `_build_status_payload()` and `ws_get_status` must include new fields |
| Pre-heat config UI | Frontend (room-card.ts) | ws-client.ts | Calls `setRoomConfig` with new sparse keys — existing WS command |
| Pre-heat status display | Frontend (room-card.ts) | — | Reads `preheat_active` / `preheat_suppressed` from `RoomStatus` |

---

## Standard Stack

### Core (no new packages — all existing)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `homeassistant.helpers.storage.Store` | HA 2025.x | Second Store instance for preheat samples | Established pattern; `ClimateManagerStore` already uses it [VERIFIED: existing codebase] |
| `asyncio.gather` | stdlib | Concurrent room pass | Established coordinator pattern [VERIFIED: existing codebase] |
| `datetime.datetime` / `datetime.timedelta` | stdlib | Time arithmetic for pre-heat window | Used throughout schedule.py [VERIFIED: existing codebase] |

No new Python or npm packages are required for this phase. [VERIFIED: existing
codebase]

### Package Legitimacy Audit

> No external packages are installed in this phase. Section omitted.

---

## Architecture Patterns

### System Architecture Diagram

```
async_evaluate() cycle (every 60s)
  │
  ├── _prefetch_calendars()       (populate _calendar_cache)
  ├── _compute_present_persons()  (presence list for status)
  ├── _check_ha_tracker_warnings()
  ├── _compute_desired_temps()    (PASS 1 baseline)
  ├── _apply_presence_overrides() (PASS 2 presence)
  ├── _push_temperatures()        (TRV service calls)
  ├── bus.async_fire()            (status push)
  ├── _async_calibrate()          (existing calibration pass)
  └── _async_preheat()            ← NEW (pre-heat pass)
        │
        ├── for each room with preheat_enabled:
        │     ├── _check_preheat_convergence()   ← NEW
        │     │     reads _preheat_in_progress
        │     │     if reached target → store sample → persist
        │     │     if now >= next_occupied_at → discard
        │     └── _compute_preheat_action()      ← NEW
        │           next_occupied_at() → earliest across persons
        │           if now in [next - lead, next) and not warm:
        │             set_temperature(upcoming_setpoint)
        │             _preheat_in_progress[area_id] = {start, target}
        │
        └── preheat_store.async_save()  (if any sample recorded)

next_occupied_at(person_config, now, calendar_cache, sol)
  │  in schedule.py — pure Python
  ├── mode="scheduled"/"even_odd" → walk 7 days, find first present start
  ├── mode="calendar" → calendar_cache events → next event boundary
  ├── mode="ha"            → None
  ├── mode="force_present" → None
  └── mode="force_absent"  → None
```

### Recommended Project Structure

```
custom_components/climate_manager/
├── schedule.py          # +next_occupied_at()
├── coordinator.py       # +_async_preheat(), +_preheat_in_progress,
│                        #  +preheat_store, +preheat fields on status
├── storage.py           # +wakeup_advance_minutes migration
├── const.py             # +PREHEAT_* constants
├── websocket.py         # +set_room_preheat_config or extend set_room_config
│                        #  +preheat_active/suppressed in get_status / _build_status
└── __init__.py          # +preheat_store init; +wakeup migration at load time
frontend/src/
├── types.ts             # +RoomConfig preheat_enabled/max_lead; +RoomStatus fields
├── ws-client.ts         # no new method needed (setRoomConfig already used)
└── components/
    └── room-card.ts     # +pre-heat config block + status line
tests/
└── test_preheat.py      # NEW
```

### Pattern 1: Second Store Instance (D-06)

**What:** Instantiate a separate `Store(hass, "climate_manager_preheat")` in
`async_setup_entry`, attach it to coordinator.

**When to use:** When phase-specific persisted data is too complex to embed in
the main Store (sample lists per room) and must survive restarts.

**Example:**

```python
# Source: existing storage.py ClimateManagerStore.__init__
preheat_store = Store(
    hass,
    version=1,
    key="climate_manager_preheat",
)
preheat_data = await preheat_store.async_load() or {}
```

The coordinator receives both store and preheat_data at construction (or via
a new field on `ClimateManagerData`). [VERIFIED: existing codebase pattern]

### Pattern 2: Pre-heat Pass Structure (mirrors `_async_calibrate`)

**What:** Private async method called at the end of `async_evaluate`, with
`asyncio.gather` over all rooms, guard on enabled flag.

**Example:**

```python
# Source: existing coordinator.py _async_calibrate (lines 501–560)
async def _async_preheat(self, config: dict) -> None:
    rooms = self._data.rooms
    tasks = [
        self._async_preheat_room(area_id, config)
        for area_id in rooms
    ]
    await asyncio.gather(*tasks)

async def _async_preheat_room(
    self, area_id: str, config: dict
) -> None:
    room_config = config.get("rooms", {}).get(area_id, {})
    if not room_config.get("preheat_enabled", False):
        return
    # ... convergence check, trigger logic
```

[VERIFIED: existing codebase — _async_calibrate at lines 501–560]

### Pattern 3: `next_occupied_at()` in schedule.py

**What:** Pure function, mirrors `resolve_presence()` signature but returns
`datetime | None`.

**Key implementation detail — 7-day lookahead for `"scheduled"` mode:**

Walk `now` forward up to 7 days (one day at a time), checking each day's
presence periods for the first `"present"` state boundary after `now`. This
covers the case where a person is currently absent all day but will be present
tomorrow.

```python
# Source: pattern derived from resolve_presence() lines 276–367
def next_occupied_at(
    person_config: dict,
    now: datetime.datetime,
    calendar_cache: dict | None = None,
    start_of_local_day=None,
) -> datetime.datetime | None:
    mode = person_config.get("mode", PRESENCE_AUTOMATIC)
    if mode in (PRESENCE_HA, PRESENCE_PRESENT, PRESENCE_ABSENT):
        return None  # D-03: no deterministic next transition
    # ... walk schedule for 7 days
```

**Calendar mode dispatch:** The `_calendar_cache` is already populated per-cycle
by `_prefetch_calendars()`. Pass it in as the `calendar_cache` argument (same
pattern as `resolve_presence()`). For `event_means="absent"`: person returns home
when the next event *ends*. For `event_means="present"`: person arrives when the
next event *starts*.

[VERIFIED: existing codebase — resolve_presence at lines 276–367]

### Pattern 4: Wakeup Advance Migration (D-02)

**What:** In `storage.py:async_load()`, after the main sparse-merge, scan all
person configs and migrate `preheat_lead_minutes` → `wakeup_advance_minutes`.

**Example:**

```python
# Source: existing storage.py migration block (lines 129–138)
for person_cfg in result.get("persons", {}).values():
    # D-02: rename preheat_lead_minutes → wakeup_advance_minutes
    if "preheat_lead_minutes" in person_cfg and \
            "wakeup_advance_minutes" not in person_cfg:
        person_cfg["wakeup_advance_minutes"] = \
            person_cfg.pop("preheat_lead_minutes")
```

**Coordination with websocket.py:** The `set_person_config` handler currently
validates/clamps `preheat_lead_minutes`. After migration, it must also accept
`wakeup_advance_minutes` (and clamp it). The old key should still be accepted
during a transition window (or rejected cleanly). [VERIFIED: existing codebase]

**Coordination with coordinator.py:** Three call sites currently read
`preheat_lead_minutes` from person_config (lines 414, 753 in coordinator.py;
line 353 in schedule.py). After migration, they must read
`wakeup_advance_minutes` (with fallback to `preheat_lead_minutes` during the
transition window, then remove the fallback in a subsequent cleanup).
[VERIFIED: existing codebase]

### Pattern 5: Status Payload Extension (D-10)

**What:** Both `_build_status_payload()` in coordinator.py and `ws_get_status`
in websocket.py build the `rooms_status` list. Both must be updated to include
the three new fields. The `subscribe_status` WS command forwards
`_build_status_payload()` output directly, so updating `_build_status_payload`
is sufficient for push; `ws_get_status` is a separate read path that must also
be updated.

```python
# Extend the room_entry dict (same location as present_person_count):
room_entry["preheat_active"] = coordinator._preheat_active.get(
    area_id, False
)
room_entry["preheat_target"] = coordinator._preheat_target.get(
    area_id, None
)
room_entry["preheat_suppressed"] = coordinator._preheat_suppressed.get(
    area_id, False
)
```

Store these in coordinator instance dicts (`_preheat_active`,
`_preheat_target`, `_preheat_suppressed`) so both payload builders can read
them without re-computation. [VERIFIED: existing codebase pattern — mirroring
`_last_room_periods` / `_calibration_last_changed`]

### Pattern 6: Auto-save Room Config (D-11)

**What:** The room card already uses `this.ws.setRoomConfig(roomId, payload)`
with no Save button for zone assignment changes. The pre-heat toggle and max-lead
input follow the exact same pattern.

```typescript
// Source: existing room-card.ts _onZoneChange (lines 421–433)
private async _onPreheatToggle(e: Event) {
  const enabled = (e.target as HTMLInputElement).checked;
  try {
    await this.ws.setRoomConfig(this.roomId, {
      preheat_enabled: enabled,
    });
    await this.panel.reloadConfig();
    this.panel.showToast("Saved", false);
  } catch {
    this.panel.showToast("Save failed — retrying...", true);
  }
}
```

No new WS command is needed — `setRoomConfig` passes arbitrary config dicts.
[VERIFIED: existing codebase — ws-client.ts setRoomConfig + set_room_config
handler in websocket.py accepts `dict` for config]

### Anti-Patterns to Avoid

- **Running next_occupied_at() in schedule.py with HA imports:** schedule.py
  must remain pure Python. The calendar cache is pre-built by the coordinator
  and passed in — no `hass` calls inside `next_occupied_at()`.
- **Updating only one of the two status builders:** Both
  `_build_status_payload()` and `ws_get_status` must be updated, otherwise
  initial page load (get_status) shows stale data and push events are correct.
- **Storing `preheat_enabled` in the preheat store:** Room config (toggle,
  max_lead) belongs in the main store's `rooms[area_id]` dict. The preheat
  store holds samples only.
- **Treating `force_present` as having a next transition:** It doesn't —
  `next_occupied_at()` returns `None` for forced modes. The person is always
  present; there is no *next* occupation event.
- **Persisting preheat store on every tick:** Only persist when a sample is
  added or removed. The Store's `async_save` is async and should not fire on
  every 60-second evaluation cycle unnecessarily.
- **Clamping learned lead to `preheat_max_lead_minutes` after computing
  average:** Cap must be applied after averaging to prevent the average from
  being contaminated by off-by-one errors. Valid samples are already capped by
  the discard rule (D-07); the cap on the learned lead (D-08) is a secondary
  safety bound.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Persistent sample storage | Custom file I/O or DB | `Store(hass, "climate_manager_preheat")` | HA-managed JSON store survives restart, handles async safely, is already in the codebase |
| Calendar next-event lookup | Custom calendar client | `_calendar_cache` already populated by `_prefetch_calendars()` | Already fetched per-cycle; re-use avoids redundant `calendar.get_events` calls |
| Concurrent room pass | Sequential for-loop | `asyncio.gather(*tasks)` | Established coordinator pattern; keeps evaluation time under 1 s even with many rooms |
| UI toggle + number input | Custom web components | Native `<input type="checkbox">` + `<input type="number">` | Project constraint (Phase 10 memory): ha-textfield and ha-select are broken in HA 2026.x |

**Key insight:** Every capability in this phase has an exact structural analog
in the existing codebase — no novel patterns are required.

---

## Runtime State Inventory

This phase includes a schema rename (`preheat_lead_minutes` →
`wakeup_advance_minutes`). The inventory answers where the old name is stored.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Main Store (`climate_manager`): `persons[*].preheat_lead_minutes` — written by `set_person_config` since Phase 11 | In-memory migration in `storage.py:async_load()` at startup; old key is read-and-renamed, new key is written on next save |
| Live service config | None — no external services store this field | None |
| OS-registered state | None | None |
| Secrets/env vars | None — field is a user config value, not a secret | None |
| Build artifacts | None — field name is not embedded in built `panel.js` path structure | Code changes to `person-card.ts` label and `types.ts` comment only (the quick task 260602-wakeup-advance-rename may already have done the UI label; the storage key rename is Phase 12) |

**Test files:** `tests/test_calendar.py` has 8+ references to
`preheat_lead_minutes` as a string key in test fixture dicts. These will need
updating to `wakeup_advance_minutes` after the migration lands.
[VERIFIED: grep of tests directory]

**Status of quick task 260602-wakeup-advance-rename:** Per git log and the
PLAN.md, this task changed only the UI label "Pre-heat lead time" → "Wake-up
advance" in `person-card.ts` (frontend display only). The storage key
`preheat_lead_minutes` is unchanged in the backend. The full rename (const +
storage migration + coordinator read sites + websocket validation + tests) is
Phase 12 work. [VERIFIED: grep results show `preheat_lead_minutes` still used
in coordinator.py, schedule.py, websocket.py, const.py, and test_calendar.py]

---

## Common Pitfalls

### Pitfall 1: Two Status Payload Builders
**What goes wrong:** `_build_status_payload()` is updated but `ws_get_status`
in websocket.py is not (or vice versa). Page load shows wrong/missing preheat
fields; push events show correct ones.
**Why it happens:** The coordinator builds payloads for push events; websocket.py
builds payloads for the initial `get_status` poll. They are separate code paths.
**How to avoid:** Always treat them as a pair — search for
`present_person_count` (a field added in both) as the anchor for adding new
room_entry fields.
**Warning signs:** `preheat_active` absent on initial page load but present
after the next 60s push.

### Pitfall 2: `next_occupied_at()` Midnight Boundary
**What goes wrong:** Walking forward day-by-day uses `now.date() + timedelta(days=n)`.
When computing the `datetime` for a period start on a future day, the code must
combine `target_date` with the period's "HH:MM" time and the correct timezone
(HA always uses aware datetimes via `dt_util.now()`).
**Why it happens:** Naive datetime + timezone-aware datetime comparison raises
`TypeError`. schedule.py already uses `_parse_time()` which returns a bare
`time` object.
**How to avoid:** Use `datetime.datetime.combine(target_date, _parse_time(period["start"])).replace(tzinfo=now.tzinfo)` or `dt_util.start_of_local_day(target_date) + timedelta(hours=h, minutes=m)`.
The `_parse_calendar_dt` helper already handles aware datetime parsing; reuse
that pattern.

### Pitfall 3: Pre-heat Fires After Occupied Period Starts
**What goes wrong:** If `async_evaluate` fires exactly when
`now == next_occupied_at`, the pre-heat trigger condition
`now < next_occupied_at` is false — no trigger. But the in-progress entry also
gets discarded ("period started, target not reached"). This is correct behavior
(the period has started; normal heating takes over) but must not be treated as
a convergence sample.
**Why it happens:** The discard condition and the trigger condition share the
same `next_occupied_at` boundary.
**How to avoid:** Check the discard condition before the trigger condition in
`_async_preheat_room`. The guard order in D-09 is: (1) check convergence, (2)
check discard, (3) evaluate trigger.

### Pitfall 4: `preheat_store` Not Attached to Data / Coordinator
**What goes wrong:** The second Store is instantiated but not stored on
`ClimateManagerData` or the coordinator — it gets garbage collected, and the
reference is lost on next tick.
**Why it happens:** `async_setup_entry` creates the Store but the coordinator
is constructed before it is passed a reference.
**How to avoid:** Add `preheat_store` and `preheat_data` fields to
`ClimateManagerData` (or pass them to the coordinator constructor). Use
`field(default=None)` to avoid mutable default in the dataclass.

### Pitfall 5: Convergence Check Reads Wrong Temperature
**What goes wrong:** D-09 checks "current_temp >= target - 0.2". The code reads
`hass.states.get(entity_id).attributes.get("current_temperature")` (the
sensor reading) not `.attributes.get("temperature")` (the setpoint — Pitfall 6
from coordinator.py comment). These are the same attribute key confusion that
exists in the push path.
**Why it happens:** The climate entity has both `current_temperature` (measured)
and `temperature` (setpoint). Convergence needs the *measured* temp.
**How to avoid:** Use `"current_temperature"` for convergence reads; use
`"temperature"` for detecting manual overrides. The existing coordinator.py
comment already documents Pitfall 6 — apply the same awareness here.

### Pitfall 6: Wakeup Advance Migration Applied to Wrong Store
**What goes wrong:** Migration is written against the preheat Store instead of
the main Store — or applied before the sparse-merge, causing the DEFAULT_CONFIG
to absorb the old key.
**Why it happens:** The migration must run *after* the sparse-merge in
`async_load()`, on the merged `result` dict.
**How to avoid:** Follow the existing migration block pattern at lines 129–138
of storage.py, which runs on `result` (post-merge). Confirm the block position
is after the `for key, value in stored.items()` loop.

### Pitfall 7: `even_odd` Week Parity in `next_occupied_at()`
**What goes wrong:** When computing the next present start for an `even_odd`
person, the parity of each future *day* must be computed from the ISO week of
that day — not from `now`'s week.
**Why it happens:** `now` may be in week N; the next present period may be in
week N+1 (opposite parity).
**How to avoid:** For each candidate day in the 7-day lookahead, compute
`target_date.isocalendar().week % 2` to select `schedule_even` or
`schedule_odd`. The existing `WR-03` note in schedule.py about week 53 applies
here too — accepted limitation.

---

## Code Examples

### next_occupied_at() Skeleton

```python
# Source: derived from resolve_presence() and existing schedule.py patterns
def next_occupied_at(
    person_config: dict,
    now: datetime.datetime,
    calendar_cache: dict | None = None,
    start_of_local_day=None,
) -> datetime.datetime | None:
    """Return the next datetime when this person will be present.

    Returns None if mode is ha/force_present/force_absent (no deterministic
    transition). Looks ahead up to 7 days for scheduled modes.
    """
    mode = person_config.get("mode", PRESENCE_AUTOMATIC)
    if mode in (PRESENCE_HA, PRESENCE_PRESENT, PRESENCE_ABSENT):
        return None

    _sol = start_of_local_day if start_of_local_day is not None \
        else _local_day_fallback

    if mode == PRESENCE_CALENDAR:
        # calendar mode: next event boundary from _calendar_cache
        cal_cfg = person_config.get("calendar_config") or {}
        eid = cal_cfg.get("entity_id", "")
        event_means = cal_cfg.get("event_means", "absent")
        events = (calendar_cache or {}).get(eid, [])
        return _next_calendar_occupied_at(events, event_means, now, _sol)

    # Scheduled mode (single or even_odd): 7-day lookahead
    schedule_type = person_config.get("schedule_type", "single")
    for day_offset in range(7):
        target_date = (now + timedelta(days=day_offset)).date()
        if schedule_type == "even_odd":
            parity = target_date.isocalendar().week % 2
            schedule_key = "schedule_even" if parity == 0 \
                else "schedule_odd"
            schedule = person_config.get(schedule_key, {})
        else:
            schedule = person_config.get("schedule", {})
        day_name = WEEKDAY_TO_DAY[target_date.weekday()]
        periods = schedule.get(day_name, [])
        result = _first_present_after(
            periods, now, target_date, _sol
        )
        if result is not None:
            return result
    return None
```

### Pre-heat Trigger Condition (D-05)

```python
# Source: decision D-05 from CONTEXT.md
def _should_preheat(
    now: datetime.datetime,
    next_occupied: datetime.datetime,
    learned_lead_minutes: float,
    current_temp: float | None,
    target_setpoint: float,
    convergence_threshold: float = 0.2,
) -> bool:
    lead = timedelta(minutes=learned_lead_minutes)
    if not (next_occupied - lead <= now < next_occupied):
        return False
    if current_temp is None:
        return True  # unknown — fire anyway (safe default)
    return current_temp < target_setpoint - convergence_threshold
```

### Room Card Pre-heat Block (D-11)

```typescript
// Source: derived from existing zone assignment block in room-card.ts
private _renderPreheatSection() {
  const enabled = this.config?.preheat_enabled ?? false;
  const preheatActive = this.roomStatus?.preheat_active ?? false;
  const preheatTarget = this.roomStatus?.preheat_target;
  const preheatSuppressed = this.roomStatus?.preheat_suppressed ?? false;

  return html`
    <div class="section-label">Pre-heat</div>
    <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
      <input
        type="checkbox"
        .checked=${enabled}
        @change=${this._onPreheatToggle}
      />
      Pre-heat this room
    </label>
    ${enabled ? html`
      <label style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        Max lead time (min)
        <input
          type="number"
          .value=${String(this.config?.preheat_max_lead_minutes ?? 120)}
          min="0" max="480" step="5"
          @change=${this._onPreheatMaxLeadChange}
          style="width:70px"
        />
      </label>
    ` : ''}
    ${preheatActive && preheatTarget != null ? html`
      <p class="schedule-hint">
        Pre-heating (→ ${preheatTarget.toFixed(1)}°C)
      </p>
    ` : ''}
    ${enabled && preheatSuppressed ? html`
      <p class="schedule-hint">
        Pre-heat disabled — presence cannot be scheduled
      </p>
    ` : ''}
  `;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `preheat_lead_minutes` on person (Phase 11 CAL-04) | `wakeup_advance_minutes` on person (Phase 12 D-02) | Phase 12 rename | Storage migration required; coordinator + schedule + WS handler must read new key |
| Fixed 60-min lead time (Phase 11) | Learned lead from samples (Phase 12) | Phase 12 | Per-room adaptive behavior; 60 min is only the initial default |

**Deprecated/outdated:**

- `preheat_lead_minutes` person config key: replaced by `wakeup_advance_minutes`.
  Old key must be migrated in `storage.py:async_load()` and all read sites
  (coordinator.py lines 414, 753; schedule.py line 353) must be updated.
  [VERIFIED: existing codebase]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The existing `set_room_config` WS handler passes arbitrary `dict` values through to `rooms[room_id]` — so no new WS command is needed for `preheat_enabled` / `preheat_max_lead_minutes` | Standard Stack, Don't Hand-Roll | If handler has a key allowlist, a new handler or handler extension is needed. Currently the handler uses `update(incoming_config)` on whatever dict is sent — no allowlist observed in code review. [VERIFIED: websocket.py lines 406–447 — no allowlist] |
| A2 | `preheat_suppressed` is computed each cycle from whether `next_occupied_at` returned `None` for all assigned persons — this information is available inside `_async_preheat_room` and can be stored on the coordinator before `_build_status_payload` runs | Architecture Patterns | If status payload is built before the pre-heat pass, the suppressed flag will lag one cycle. Confirmed: `_async_preheat` is called last in `async_evaluate`, before `bus.async_fire`. The fire event call is *before* calibrate/preheat in the current code — see coordinator.py line 197. This means the bus event fires BEFORE the pre-heat pass runs. **See Open Question 1.** |

---

## Open Questions

1. **Status push timing vs pre-heat pass order**
   - What we know: In `async_evaluate()`, `bus.async_fire()` fires the
     `_status_update` event at line 197, *before* `_async_calibrate()` (line
     202). The pre-heat pass runs after calibration. This means the push event
     sent to subscribed panel connections will contain stale pre-heat status
     (from the *previous* cycle).
   - What's unclear: Whether one cycle of lag is acceptable, or whether the
     bus fire should be moved to after the pre-heat pass.
   - Recommendation: Move `bus.async_fire()` to after `_async_preheat()` (last
     line of `async_evaluate`). This adds at most ~10ms to the cycle for a
     household with a few rooms. This is the same fix that would be needed for
     calibration status if it were surfaced in real-time. Confirm with user or
     make the call as Claude's discretion — the CONTEXT.md does not lock the
     ordering.

2. **`ClimateManagerData` vs coordinator for `preheat_store`**
   - What we know: The existing pattern is that `ClimateManagerData` holds the
     main `store`; the coordinator receives `data` (which includes `store`).
     The preheat store is write-only from the coordinator's perspective.
   - What's unclear: Whether to add `preheat_store` to `ClimateManagerData`
     (for consistency) or pass it directly to the coordinator constructor.
   - Recommendation: Add `preheat_store` and `preheat_samples` to
     `ClimateManagerData` — consistent with `store` / `runtime_config` pattern.
     The coordinator receives `data` already and can call
     `data.preheat_store.async_save(data.preheat_samples)`.

---

## Environment Availability

> Skip condition: no external CLI tools or services beyond the existing HA
> dev environment are required.

All dependencies are already present: Python 3.12+ (existing), HA test
harness (existing), `make test` via `pytest` (existing). [VERIFIED: Makefile,
pyproject.toml]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with pytest-homeassistant-custom-component |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/test_preheat.py -v` |
| Full suite command | `make test` (`.venv/bin/python -m pytest tests/ -v`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PREHEAT-01 | Room config sparse keys stored/loaded | unit | `pytest tests/test_preheat.py::test_room_preheat_config_stored -x` | Wave 0 |
| PREHEAT-02 | Coordinator triggers pre-heat at right time | unit | `pytest tests/test_preheat.py::test_preheat_trigger_fires -x` | Wave 0 |
| PREHEAT-02 | Pre-heat uses 60 min default before 3 samples | unit | `pytest tests/test_preheat.py::test_default_lead_time -x` | Wave 0 |
| PREHEAT-03 | Sample recorded on convergence; discarded if missed | unit | `pytest tests/test_preheat.py::test_sample_recorded_on_convergence -x` | Wave 0 |
| PREHEAT-03 | Learned lead = avg of last 5 valid samples | unit | `pytest tests/test_preheat.py::test_learned_lead_average -x` | Wave 0 |
| PREHEAT-04 | Status payload contains preheat_active/suppressed | unit | `pytest tests/test_preheat.py::test_status_payload_preheat_fields -x` | Wave 0 |
| PREHEAT-05 | next_occupied_at works for even_odd schedules | unit | `pytest tests/test_preheat.py::test_next_occupied_even_odd -x` | Wave 0 |
| PREHEAT-05 | next_occupied_at works for calendar mode | unit | `pytest tests/test_preheat.py::test_next_occupied_calendar -x` | Wave 0 |
| D-02 | Migration: preheat_lead_minutes → wakeup_advance_minutes | unit | `pytest tests/test_preheat.py::test_wakeup_advance_migration -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/bin/python -m pytest tests/test_preheat.py -v`
- **Per wave merge:** `make test` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- `tests/test_preheat.py` — all 9 test cases listed above; covers PREHEAT-01..05
  and the wakeup_advance migration
- `tests/conftest.py` already has shared fixtures — no new conftest needed

---

## Security Domain

> `security_enforcement` not explicitly set to false; treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | HA WebSocket auth gate handles this |
| V3 Session Management | no | N/A |
| V4 Access Control | no | Integration config is owner-only in HA |
| V5 Input Validation | yes | Clamp `preheat_max_lead_minutes` to 0–480 int; validate `preheat_enabled` bool; reject non-calendar entity IDs in existing pattern |
| V6 Cryptography | no | No cryptographic operations |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed room config payload (negative max_lead) | Tampering | Clamp `preheat_max_lead_minutes` to [0, 480] in `set_room_config` handler (mirrors existing `preheat_lead_minutes` clamp in `set_person_config`) |
| Preheat bypassing zone MODE_OFF | Elevation of Privilege | Pre-heat pass must check `frost_locked_rooms` before calling `set_temperature` — same guard as presence overrides |

---

## Sources

### Primary (HIGH confidence)

- Existing `coordinator.py` lines 501–560 (`_async_calibrate`) — template for
  pre-heat pass structure [VERIFIED: existing codebase]
- Existing `schedule.py` lines 276–367 (`resolve_presence`) — template for
  `next_occupied_at()` [VERIFIED: existing codebase]
- Existing `storage.py` lines 129–138 — template for schema migration at load
  time [VERIFIED: existing codebase]
- Existing `websocket.py` lines 394–447 (`set_room_config`) — confirmed no
  key allowlist, arbitrary dict update [VERIFIED: existing codebase]
- Existing `coordinator.py` lines 873–957 (`_build_status_payload`) + websocket.py
  lines 129–242 (`ws_get_status`) — both status builders confirmed [VERIFIED:
  existing codebase]
- `tests/test_calendar.py` — 8 references to `preheat_lead_minutes` confirmed
  requiring update after migration [VERIFIED: grep]
- `const.py` line 59: `DEFAULT_PREHEAT_LEAD_MINUTES: int = 60` — existing
  constant [VERIFIED: existing codebase]
- `.planning/REQUIREMENTS.md` §Predictive Pre-heat [VERIFIED: project file]
- `.planning/phases/12-predictive-pre-heat/12-CONTEXT.md` [VERIFIED: project
  file]

### Secondary (MEDIUM confidence)

- None required — all findings verified against codebase directly.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new packages; all patterns verified in codebase
- Architecture: HIGH — all integration points confirmed; one open question on
  status push timing (low risk)
- Pitfalls: HIGH — derived from confirmed codebase observations and the
  existing pitfall register in coordinator.py / schedule.py comments

**Research date:** 2026-06-02
**Valid until:** 2026-07-02 (stable HA integration patterns; no external
dependencies)
