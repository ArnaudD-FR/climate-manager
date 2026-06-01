# Phase 11: Calendar Presence Backend - Context

**Gathered:** 2026-06-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a "Calendar" presence mode to the integration backed by HA's native
calendar entities (`calendar.*`). When a person is set to Calendar mode,
their presence is determined by whether a calendar event is active at the
current time. Calendar presence is also available as a period state within
the existing Scheduled mode, allowing mixed schedules (e.g., "weekdays 8h–18h
→ defer to calendar; rest → present").

**In scope:**

- New `"calendar"` presence mode for persons (top-level mode alongside
  `"scheduled"`, `"force_present"`, `"force_absent"`, `"ha"`)
- New `"calendar"` period state within Scheduled mode — individual periods in
  a person's schedule can have state `"calendar"` instead of
  `"present"`/`"absent"`; resolved at evaluate time via the linked calendar entity
- `calendar_config` per person (and per calendar-state period): stores
  `entity_id` (the `calendar.*` HA entity) and `event_means`
  (`"absent"` default | `"present"`)
- Configurable pre-heat lead time per person: start heating X minutes before
  a calendar-driven absence ends (person returns home); default 1h,
  user-configurable
- `resolve_presence()` extended to handle `"calendar"` mode by calling
  `hass.services.async_call("calendar", "get_events", ...)` and checking
  whether any event is active at `now`
- Coordinator: per-cycle cache of `get_events` results keyed by
  `calendar_entity_id` — one call per entity per `async_evaluate` cycle
  regardless of how many persons share the entity
- Frontend: person card gains Calendar mode UI — entity picker + `event_means`
  toggle (inline, below mode select); period editor in Scheduled mode gains
  `"Calendar"` as a period state option with the same inline config
- Frontend: scheduling/presence section moves ABOVE the associated rooms list
  in the person card
- `set_person_config` WS command extended (or new command) to persist
  `calendar_config` and `preheat_lead_minutes` per person

**Out of scope:**

- Direct Pronote API integration (`pronotepy`) — not needed; HA's Pronote
  integration exposes a `calendar.*` entity that Climate Manager reads
- Direct iCal URL fetching (`icalendar`, `recurring-ical-events`) — same
  reason; HA's calendar integration owns fetching and caching
- Credential storage for external calendar services — handled by HA
- Per-zone or per-room pre-heat lead time (single per-person value only)
- Predictive inertia learning (Phase 12)
- REQUIREMENTS.md CAL-01..04 as written are superseded by this HA-native
  design; planner must update REQUIREMENTS.md to reflect the new approach

</domain>

<decisions>
## Implementation Decisions

### Architecture — HA-native Calendar Sources

- **D-01:** Climate Manager does NOT fetch calendar data from external sources.
  Both school timetables (Pronote) and personal calendars (iCal, Google
  Calendar, etc.) are accessed as standard HA `calendar.*` entities via
  `hass.services.async_call("calendar", "get_events", ...)`. HA's calendar
  integrations own fetching, caching, RRULE expansion, and credentials.
- **D-02:** No new PyPI dependencies. `pronotepy`, `icalendar`, and
  `recurring-ical-events` are all out of scope. `manifest.json`
  `"requirements"` stays empty.

### Presence Mode Extension

- **D-03:** New presence mode value: `"calendar"`. Added alongside existing
  `"scheduled"`, `"force_present"`, `"force_absent"`, `"ha"` in `const.py`.
  `PRESENCE_CALENDAR = "calendar"` constant.
- **D-04:** `resolve_presence()` in `schedule.py` gains a new dispatch branch
  for `mode == "calendar"`: call `get_events` on the configured
  `calendar_entity_id`, check if any event covers `now`. If the calendar
  entity is unavailable or returns an error, fall back to `False` (absent)
  and log once at WARNING — no log spam on repeated failures.
- **D-05:** `resolve_presence()` must become `async` (or a new async helper
  is added) since `get_events` is an async HA service call. The coordinator's
  existing `_compute_present_persons` call chain must be updated accordingly.

### Per-Period Calendar State in Scheduled Mode

- **D-06:** Period state `"calendar"` is added alongside `"present"` /
  `"absent"` in the schedule period schema. When a period has
  `state: "calendar"`, `resolve_presence()` evaluates the calendar config
  attached to that period (same `calendar_config` shape as the person-level
  config) at the current time.
- **D-07:** Calendar period state is only available in Scheduled mode
  (`schedule_type: "single"` or `"even_odd"`). It is NOT a recursive dispatch
  (a calendar state inside a calendar mode is not supported).

### Calendar Config Schema

- **D-08:** New nested object `calendar_config` on the person config (and
  inline on periods with `state: "calendar"`):
  ```json
  {
    "entity_id": "calendar.pronote_jean",
    "event_means": "absent"
  }
  ```
  `entity_id`: the `calendar.*` HA entity ID.
  `event_means`: `"absent"` (default — active event → person absent) or
  `"present"` (active event → person present).
- **D-09:** Additive schema — `calendar_config` is absent on persons not using
  Calendar mode. No migration needed for existing persons.

### Pre-Heat Lead Time

- **D-10:** New per-person config key `preheat_lead_minutes` (integer, default
  `60`). When a person is in Calendar mode, the coordinator starts heating
  their associated rooms `preheat_lead_minutes` before the active calendar
  event is scheduled to end (i.e., before the person returns home).
- **D-11:** Lead time is per-person (not global, not per-room). Displayed and
  edited in the person card UI as a number input (minutes), visible when
  Calendar mode is selected.
- **D-12:** `preheat_lead_minutes` is independent of Phase 12's inertia
  learning — it is a simple fixed offset. Phase 12 may replace or augment
  this with adaptive lead times; Phase 11 ships the fixed version only.

### Evaluate Cycle Cache

- **D-13:** The coordinator maintains a `_calendar_cache: dict[str, list]`
  per `async_evaluate` cycle. Before the presence pass, for each unique
  `calendar_entity_id` referenced by any person or period, one
  `get_events` call is issued covering `[now, now + 24h]`. Results are stored
  in `_calendar_cache` and reused for all persons sharing that entity within
  the same cycle. Cache is reset at the start of each `async_evaluate` call.

### Frontend — Person Card Layout

- **D-14:** Scheduling / presence configuration section moves ABOVE the
  associated rooms list in the person card. New order:
  1. Person name / mode picker
  2. Calendar config (entity picker + event_means toggle + lead time input)
     — visible only when Calendar mode is selected
  3. Schedule editor (periods) — visible only when Scheduled mode is selected
  4. Associated rooms list (moved below scheduling, same as before otherwise)
- **D-15:** Calendar entity picker in the person card: a native `<select>`
  populated from `hass.states` filtered to `domain === "calendar"`. Entity
  friendly name shown; entity_id stored. Same `<select>` pattern used for
  TRV entity pickers in room cards.
- **D-16:** `event_means` toggle: native `<select>` with two options —
  "Absent during events" (value `"absent"`, default) and "Present during
  events" (value `"present"`).
- **D-17:** In the Scheduled mode period editor, period state options extend
  from `["present", "absent"]` to `["present", "absent", "calendar"]`. When
  `"calendar"` is selected for a period, the inline calendar config block
  (entity picker + event_means) appears below the period row.

### Folded Todos

- **Pronote scheduling source (2026-05-27):** Core intent folded — presence
  from school timetable. Implementation changed from direct pronotepy to HA
  calendar entity. Pronote credential management is out of scope.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements

- `.planning/REQUIREMENTS.md` §Calendar Presence Sources — CAL-01..04 are
  superseded; planner must rewrite these requirements to reflect the HA-native
  calendar entity approach before writing plans
- `.planning/ROADMAP.md` §Phase 11 — phase boundaries and success criteria
  (also note the success criteria reference `schedule_type = "pronote"` which
  is superseded — use the decisions above)

### Key Source Files — Backend

- `custom_components/climate_manager/schedule.py` — `resolve_presence()`
  is the central function to extend; read fully before modifying (current
  mode dispatch, even/odd week logic, period walk)
- `custom_components/climate_manager/coordinator.py` — `async_evaluate()`,
  `_compute_present_persons()`, `_apply_presence_overrides()` — understand
  the full evaluation flow before adding the calendar cache and async changes
- `custom_components/climate_manager/const.py` — `DEFAULT_CONFIG`, presence
  mode constants (`PRESENCE_AUTOMATIC`, `PRESENCE_HA`, etc.) — where new
  `PRESENCE_CALENDAR` constant and `preheat_lead_minutes` default go
- `custom_components/climate_manager/websocket.py` — existing
  `set_person_config` pattern (or `_make_ws_set_person_config`) — extend to
  accept `calendar_config` and `preheat_lead_minutes`

### Key Source Files — Frontend

- `frontend/src/components/person-card.ts` — mode picker (add "Calendar"
  option), existing schedule period editor (add "Calendar" period state),
  layout reorder (scheduling above rooms); read fully before editing
- `frontend/src/components/persons-tab.ts` — where `hass.states` is available
  for computing the `calendar.*` entity list
- `frontend/src/types.ts` §ClimateConfig / person config shape — where
  `calendar_config` and `preheat_lead_minutes` types are added

### Established Patterns (prior phases)

- Phase 7 CONTEXT.md — additive schema pattern (`schedule_type`/`schedule_even`/
  `schedule_odd`); `calendar_config` follows the same absent-field-is-default
  approach
- Phase 9 CONTEXT.md D-12 — auto-save on change, no Save button; apply to
  entity picker and event_means toggle
- Phase 10 CONTEXT.md D-04 — native `<select>` for dropdowns (not `ha-select`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `schedule.py:resolve_presence()` lines 123–179 — add `"calendar"` branch
  after the `"ha"` mode check in `_compute_present_persons()`; the function
  needs to become async or a new async wrapper is needed
- `coordinator.py:_compute_present_persons()` lines 596–635 — already handles
  `"ha"` mode as a special case outside `resolve_presence()`; calendar mode
  may follow the same pattern (async lookup in coordinator, result passed in)
- `person-card.ts` — existing `<select>` for presence mode (lines ~503–529);
  add `<option value="calendar">Calendar</option>`; existing `schedule-hint`
  hint paragraph pattern for contextual inline config blocks

### Established Patterns

- **Async coordinator pattern:** `asyncio.gather()` over all rooms / persons
  in `async_evaluate`; calendar `get_events` calls should be gathered upfront
  (D-13 cache) then results consumed synchronously in the presence pass
- **Sparse config keys:** absent = default; `calendar_config` absent means
  person is not using Calendar mode
- **Silent fallback:** on calendar entity unavailable → log once at WARNING,
  fall back to `False` (absent) — consistent with PERSON-05 default
- **Native `<select>`:** all dropdowns use native `<select>`; entity picker
  is populated by filtering `Object.keys(hass.states)` on `domain === "calendar"`

### Integration Points

- `coordinator.py:async_evaluate()` — add `await self._prefetch_calendars(config)`
  before the presence pass to populate `_calendar_cache`
- `coordinator.py:_compute_present_persons()` — calendar lookup uses cached
  results from `_calendar_cache`; pass cache dict into `resolve_presence`
  or handle inline
- `schedule.py:resolve_presence()` — new `"calendar"` dispatch; receives
  cached events list (not the raw async call) to keep it synchronous
- `websocket.py` — extend person config WS command to accept and persist
  `calendar_config` dict and `preheat_lead_minutes` int
- `person-card.ts:render()` — new conditional calendar config block rendered
  when `mode === "calendar"`; reorder: scheduling section moves before rooms

</code_context>

<specifics>
## Specific Ideas

- Default `event_means` is `"absent"` — a calendar event = person is away.
  This covers the most common use cases (school, work, holiday).
- Pre-heat lead time default is 60 minutes. Displayed in person card as a
  number input labeled something like "Start heating X min before return"
  — only visible when Calendar mode is selected.
- Period state `"calendar"` in the schedule editor should show the calendar
  entity name (friendly name from `hass.states`) rather than the entity ID
  in the period summary for readability.
- Scheduling / presence section order in person card: mode picker → calendar
  config OR schedule editor → rooms. The layout reorder (scheduling above
  rooms) is a simple CSS/template change, not a data-model change.

</specifics>

<deferred>
## Deferred Ideas

- **Adaptive pre-heat lead time (inertia learning)** — Phase 12 (PREHEAT)
  will replace or augment the fixed `preheat_lead_minutes` with a learned
  inertia factor. Phase 11 ships the fixed value only.
- **Direct Pronote API via pronotepy** — superseded by HA calendar entity
  approach; if a Pronote HA integration is unavailable the user installs
  one separately, not our concern.
- **Per-room or per-zone lead time** — D-10 specifies per-person only;
  per-room granularity deferred to Phase 12 pre-heat engine.
- **Multiple calendar sources per person** — Phase 11 supports one
  `calendar_entity_id` per person (or per period). Multiple sources
  (logical OR/AND) deferred to a future phase.

### Reviewed Todos (not folded)

- **Even/odd week presence scheduling (score 0.6)** — already shipped in
  Phase 7–8; not relevant here.
- **Rename "ha" mode (score 0.9)** — shipped in Phase 10 as "Live tracking."
- **Hide HA presence mode when no trackers (score 0.9)** — shipped in
  Phase 10.
- **Multi-language support (score 0.5)** — deferred to v2 in REQUIREMENTS.md.

</deferred>

---

*Phase: 11-calendar-presence-backend*
*Context gathered: 2026-06-01*
