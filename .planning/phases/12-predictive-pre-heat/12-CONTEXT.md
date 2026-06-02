# Phase 12: Predictive Pre-heat - Context

**Gathered:** 2026-06-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a per-room predictive pre-heat engine to the coordinator. When a room
opts in, the coordinator computes the next time the room will become occupied,
subtracts a learned lead time, and starts heating early. The lead time is
learned from observed convergence samples (how long the room takes to reach
target temperature). The panel shows live pre-heat status on the room card.

**In scope:**

- Per-room `preheat_enabled` toggle and `preheat_max_lead_minutes` cap stored
  in room config (Rooms tab in panel)
- New `next_occupied_at()` helper in `schedule.py` that returns the next
  datetime a person will be present (or `None` for HA mode / no schedule)
- Coordinator pre-heat pass: for each enabled room, compute earliest
  `next_occupied_at` across all assigned persons, subtract learned lead time,
  and start heating at the upcoming period's setpoint when `now >=
  next_transition - learned_lead_minutes`
- Inertia learning: per-room heating samples stored in a separate
  `climate_manager_preheat.json` Store file; average of last 5 valid samples
  is the learned lead time; initial default is 60 min until 3+ samples exist;
  samples where target was not reached within `preheat_max_lead_minutes` are
  excluded
- New `preheat_active` and `preheat_target` attributes on the room state
  returned by the existing `get_state` / `state_updated` WS response; room
  card shows "Pre-heating (→ XX.X°C)" when `preheat_active` is true; shows
  "Pre-heat disabled — presence cannot be scheduled" when HA-mode persons
  prevent next-transition computation
- Pre-heat config UI inline in the room card below the TRV list: enable
  toggle + max lead time input (auto-save on change)
- Rename per-person `preheat_lead_minutes` → `wakeup_advance_minutes`
  (Phase 11 concept: start heating X min before a calendar-mode person returns
  home — distinct from per-room inertia pre-heat)

**Out of scope:**

- Per-person or per-zone pre-heat lead time (per-room only)
- EWMA or median learning models (simple average of last 5 valid samples)
- Ambient temperature correction for samples
- Pre-heat for rooms with no deterministic next transition (HA mode → suppress,
  show warning)
- Configurable number of samples before learning kicks in (fixed: 3 minimum,
  5 max stored)

</domain>

<decisions>
## Implementation Decisions

### Pre-heat Config — Per-room Schema

- **D-01:** Pre-heat config lives on the room (not the person). New sparse
  keys on each room object in the Store:
  ```json
  {
    "preheat_enabled": true,
    "preheat_max_lead_minutes": 120
  }
  ```
  Absent = not enabled (sparse — no migration needed for existing rooms).
  Default max lead: 120 min per PREHEAT-01.

- **D-02:** Rename per-person `preheat_lead_minutes` →
  `wakeup_advance_minutes` (distinct concept: time before a calendar-mode
  person returns home). The rename is a schema migration — existing stored
  values must be read under both keys during a transition window, or a
  one-time migration run at `async_setup_entry`.

### Next-transition Computation

- **D-03:** New pure function `next_occupied_at(person_config, now, ...)` in
  `schedule.py`. Returns the next `datetime` when the person will be
  considered present, or `None` if not determinable.
  - `"scheduled"` (single / even_odd): walk the daily program for the
    upcoming 7 days, return the start of the first `"present"` period after
    `now`.
  - `"calendar"` mode or period: use the `_calendar_cache` events list;
    return the `end` datetime of the currently-active event (person returns
    home when the event ends), or the `start` of the next event if
    `event_means = "present"`.
  - `"ha"` mode: return `None` (live tracker — no deterministic next
    transition; pre-heat is suppressed).
  - `"force_present"` / `"force_absent"`: return `None` (forced — no
    schedule-driven next transition).

- **D-04:** Coordinator iterates all persons assigned to a room, calls
  `next_occupied_at()` for each, takes the **earliest non-None** result as
  the room's `next_occupied_at`. If all persons return `None`, pre-heat is
  suppressed for that room.

- **D-05:** Pre-heat trigger condition per room, checked each
  `async_evaluate` cycle:
  ```
  now >= next_occupied_at - learned_lead_minutes
  AND now < next_occupied_at
  AND room is not already at target (current_temp < setpoint - threshold)
  ```
  When triggered, the coordinator calls `set_temperature` on the room's TRVs
  at the upcoming period's setpoint (not a special pre-heat setpoint).

### Inertia Learning Model

- **D-06:** Per-room samples stored in a separate Store:
  `Store(hass, "climate_manager_preheat")`. Key: `{area_id}` → list of
  sample dicts:
  ```json
  {
    "duration_minutes": 42,
    "timestamp": "2026-06-02T06:00:00Z"
  }
  ```
  Only `duration_minutes` and `timestamp` — no ambient correction.

- **D-07:** A valid sample = pre-heat started, TRV's `current_temperature`
  reached the target setpoint within `preheat_max_lead_minutes`. Samples
  where the target was not reached in time are discarded (not stored).

- **D-08:** Learned lead time = simple average of the last 5 valid samples,
  capped at `preheat_max_lead_minutes`. Until 3 valid samples exist, use the
  initial default of 60 min.

- **D-09:** Sample recording: coordinator tracks in-memory
  `_preheat_in_progress: dict[area_id, {start_time, target_temp}]`. Each
  `async_evaluate` cycle checks if a tracked room has reached its target
  (current_temp >= target - 0.2°C tolerance). When convergence detected:
  compute duration, store sample, clear in-progress entry, persist to Store.
  If `async_evaluate` fires while `now >= next_occupied_at` (period started)
  and target still not reached: discard the in-progress entry without storing
  a sample.

### Pre-heat Status — WS Communication

- **D-10:** Room state returned by `get_state` / `state_updated` gains two
  new optional fields:
  ```json
  {
    "preheat_active": true,
    "preheat_target": 21.5,
    "preheat_suppressed": false
  }
  ```
  `preheat_active`: true when the coordinator is pre-heating this room right
  now.
  `preheat_target`: the setpoint being targeted during pre-heat (upcoming
  period's normal/comfort temp).
  `preheat_suppressed`: true when `preheat_enabled` is true but
  `next_occupied_at` returned `None` for all persons (HA mode blocks
  scheduling). Frontend shows the "Pre-heat disabled — presence cannot be
  scheduled" warning when this is `true`.

### Pre-heat UI in Room Card

- **D-11:** Pre-heat config appears inline in the room card below the TRV
  list. Auto-saves on change (no Save button). Components:
  - Toggle: `<input type="checkbox">` labeled "Pre-heat this room"
  - Max lead time input: `<input type="number">` labeled "Max lead time (min)"
    — visible only when toggle is enabled
  - Status line: "Pre-heating (→ XX.X°C)" when `preheat_active` is true;
    "Pre-heat disabled — presence cannot be scheduled" when
    `preheat_suppressed` is true; otherwise nothing shown.
  Pattern: same auto-save-on-change approach as Phase 9 calibration toggle
  (D-09 Phase 9).

### Folded Todos

- **Adaptive pre-heat with dynamic room inertia learning (2026-05-27):**
  Core intent folded — Phase 12 implements the adaptive inertia model with
  learned lead time per room. The learning algorithm is simple average of
  last 5 valid samples (per D-08).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements

- `.planning/REQUIREMENTS.md` §Predictive Pre-heat — PREHEAT-01..05 define
  the acceptance criteria for this phase
- `.planning/ROADMAP.md` §Phase 12 — phase boundaries and success criteria

### Key Source Files — Backend

- `custom_components/climate_manager/schedule.py` — add `next_occupied_at()`
  helper alongside `resolve_presence()` / `resolve_calendar_presence()`; read
  the full even/odd week and calendar dispatch logic before implementing
- `custom_components/climate_manager/coordinator.py` — `async_evaluate()`,
  `_compute_present_persons()`, `_apply_presence_overrides()`,
  `_async_calibrate()` — understand the full evaluate cycle before adding the
  pre-heat pass; `_calendar_cache` is already built per-cycle and available
  to `next_occupied_at()`
- `custom_components/climate_manager/const.py` — `DEFAULT_CONFIG`, room
  config schema — where `preheat_enabled` / `preheat_max_lead_minutes`
  defaults go; also where `wakeup_advance_minutes` rename lands
- `custom_components/climate_manager/storage.py` — Store usage pattern;
  adding a second `Store` instance (`climate_manager_preheat`) follows the
  same pattern as the main store

### Key Source Files — Frontend

- `frontend/src/components/room-card.ts` (or equivalent room component) —
  add pre-heat config block below TRV list; render `preheat_active` /
  `preheat_suppressed` status
- `frontend/src/types.ts` — extend room config type with `preheat_enabled`,
  `preheat_max_lead_minutes`; extend room state type with `preheat_active`,
  `preheat_target`, `preheat_suppressed`
- `frontend/src/ws-client.ts` — add `setRoomPreheatConfig(area_id, config)`
  method (mirrors existing set-room-config pattern)

### Established Patterns (prior phases)

- Phase 9 CONTEXT.md D-01..D-04 — calibration pass in `async_evaluate()`;
  same structure for the pre-heat pass (private method, asyncio.gather over
  rooms, called from end of `async_evaluate`)
- Phase 9 CONTEXT.md D-09 — auto-save on change, no Save button; apply to
  pre-heat toggle and max lead input
- Phase 11 CONTEXT.md D-13 — per-cycle `_calendar_cache`; `next_occupied_at()`
  receives the cache dict (already built) to resolve calendar next transitions
- Phase 10 CONTEXT.md D-04 — native `<input>` elements (not `ha-*` web
  components) for all form controls

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `schedule.py:resolve_calendar_presence()` — same event list / event_means
  logic applies to `next_occupied_at()` for calendar mode; the function
  already knows how to find the next event boundary
- `coordinator.py:_async_calibrate()` — template for the pre-heat pass:
  private method, `asyncio.gather()` over rooms, called at end of
  `async_evaluate()`
- `coordinator.py:_calendar_cache` — already populated per-cycle before the
  presence pass; pass it into `next_occupied_at()` for calendar lookups
- `storage.py:Store` — instantiate a second `Store(hass,
  "climate_manager_preheat")` for sample persistence; same `async_load` /
  `async_save` pattern

### Established Patterns

- **Sparse config keys:** absent = default; `preheat_enabled` absent means
  room is not opted in — no migration needed for existing rooms
- **Async coordinator pattern:** `asyncio.gather()` over all rooms in the
  pre-heat pass; per-room logic in a private helper
  `_async_preheat_room(area_id, ...)`
- **Calendar cache:** `_calendar_cache` dict keyed by `calendar_entity_id`;
  `next_occupied_at()` receives the cache as a parameter (already present in
  `resolve_calendar_presence()` call chain)

### Integration Points

- `coordinator.py:async_evaluate()` — add `await self._async_preheat()` call
  after the calibration pass; pre-heat runs last in the cycle
- `coordinator.py` — add `_preheat_in_progress: dict[str, dict]` instance
  variable for in-flight sample tracking; initialized in `__init__`
- `schedule.py` — new public `next_occupied_at(person_config, now,
  calendar_cache, ...)` function; mirrors `resolve_presence()` signature
- `websocket.py` — extend `get_state` response serializer and `state_updated`
  push to include `preheat_active`, `preheat_target`, `preheat_suppressed`
  on each room; extend person config WS command to handle
  `wakeup_advance_minutes` rename

</code_context>

<specifics>
## Specific Ideas

- `wakeup_advance_minutes` is the correct name for the per-person Phase 11
  concept (start heating before a calendar-mode person returns home). The
  planner must rename `preheat_lead_minutes` everywhere and handle the
  migration at `async_setup_entry` (read old key if new key absent).
- Pre-heat status line in the room card should be subtle — not a warning
  badge, just a small text line below the temperature display (same register
  as the calibration status).
- `preheat_suppressed` is only shown when `preheat_enabled` is true AND
  suppression applies — not shown for rooms where pre-heat is simply
  disabled.
- Sample timestamps are stored to allow future pruning (e.g., discard samples
  older than 30 days) in a later phase — but pruning is out of scope for
  Phase 12.

</specifics>

<deferred>
## Deferred Ideas

- **EWMA or ambient-corrected learning** — simple average is sufficient for
  Phase 12; smarter algorithms deferred to v2.
- **Per-room sample pruning by age** — timestamps stored but pruning logic
  is out of scope.
- **Pre-heat for force_present / force_absent persons** — returns `None`
  from `next_occupied_at()`; deferred to a future enhancement.
- **Pre-heat with boiler demand control** — the boiler demand control todo
  (2026-05-27) is out of scope for Phase 12.

### Reviewed Todos (not folded)

- **Rename "ha" mode (0.9)** — already shipped in Phase 10.
- **Hide HA presence mode when no trackers (0.9)** — shipped in Phase 10.
- **Remove room custom scheduling (0.9)** — separate UI refactor; not
  relevant to pre-heat engine.
- **Multi-language support (0.9)** — deferred to v2 per REQUIREMENTS.md.
- **Multi-zone heating / boiler demand / boiler declaration** — larger
  architectural features; out of scope for Phase 12.
- **Exclude panel.js from git (tooling)** — unrelated to pre-heat.
- **Add log traces (general)** — good idea but separate work item.
- **Document use cases with screenshots (docs)** — separate docs task.

</deferred>

---

*Phase: 12-predictive-pre-heat*
*Context gathered: 2026-06-02*
