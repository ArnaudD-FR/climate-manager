# Feature Landscape

**Project:** Climate Manager — v1.3 Calendar Presence & Pre-heat
**Researched:** 2026-05-31
**Confidence:** HIGH (codebase internals), MEDIUM (external library behaviour),
LOW (pronotepy long-term stability)

---

## Context

This document covers the five new features targeted for v1.3. All v1.0–v1.2
features (global mode, time programs, zones, even/odd presence, TRV calibration)
are already shipped and are dependencies, not in-scope work. References to
existing code use actual source filenames.

**Core theme:** Replace manual presence entry with calendar-driven sources, make
rooms reach temperature _before_ the occupied period begins, and make Tado X
calibration sub-minute via direct Matter sensor subscription.

---

## Table Stakes

Features users expect from v1.3 as stated in PROJECT.md. Missing = milestone
does not deliver on its goal.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Pronote presence source — school timetable maps to absent/present | Parents with Pronote-enrolled children expect school hours to drive child presence automatically; manual weekly re-entry is the current pain | High | External PyPI dep `pronotepy`; reverse-engineered protocol; first mandatory credential storage in person config; fallback to manual on fetch failure required |
| iCal presence source — ICS calendar maps to absent/present | Work calendars (Google, Outlook, Nextcloud) are the dominant adult scheduling tool; typing a work schedule manually is inferior when a URL feed exists | Medium | External PyPI deps `icalendar` + `recurring-ical-events`; ICS URL fetch + TTL cache; RRULE expansion critical for recurring "work" events |
| Predictive pre-heat — room reaches target temp _at_ period start not _after_ | Users who set a 7:00 normal period expect 20°C at 7:00; the current system only begins heating at 7:00 | High | Inertia learning loop; pre-heat cap; convergence tracking; "Pre-heating" status in UI; mode-compatibility guard for live-presence sources |
| Matter→Tado X sensor mapping — sub-minute calibration refresh | Calibration currently stale for 45 min on Tado X free tier; users with Matter TRVs in the same room can get real-time reads | Medium | Room-level mapping table in UI; `state_changed` subscription lifecycle; fall back to existing zone entity when no mapping |
| Hide HA presence mode when person has no device trackers | Showing a broken option silently corrupts heating logic; users expect the UI to show only what works | Low | Frontend filter on `hass.states[personId]?.attributes?.device_trackers`; or backend flag in `get_status` persons payload |

---

## Differentiators

Features that make v1.3 stand out beyond "calendar sync in HA".

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Adaptive inertia learning per room | Lead time is automatically tuned to the room's actual thermal behaviour rather than a fixed guess; converges after 3–5 cycles | High | Normalised to reference flow temp; `did_not_converge` samples excluded from model; convergence flag reduces safety margin |
| Pre-heat cap + "could not reach target" warning | Prevents runaway pre-heat in poorly insulated rooms; surfaces a diagnostic the user can act on | Low | `preheat_max_duration` configurable per room; warning shown in room card when cap was hit |
| Graceful Pronote fallback to manual schedule | Library maintenance risk (Pronote changes protocol ~annually) is isolated behind a fallback; heating continues correctly | Low | Log warning on failure; `last_fetch_error` surfaced in person card |
| ICS recurring event support (RRULE) | Work calendars heavily use RRULE for daily/weekly recurrence; ignoring RRULE silently misses most events | Medium | Requires `recurring-ical-events`; expand occurrences in a ±7-day window at fetch time |
| Pre-heat status label in room card | "Pre-heating (→ 20.0°C)" replaces generic period label; user immediately sees the system is working ahead of schedule | Low | Coordinator exposes `preheat_active: bool` + `preheat_target: float` per room in status payload |

---

## Anti-Features

Explicitly out of scope for v1.3.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Boiler entity integration for flow temp | Adds a whole new entity-type dependency; not all users have a HA-connected boiler | Use per-zone `preheat_flow_temp_ref` fixed assumption (default 60°C); real boiler read deferred to v2 |
| Live/reactive GPS presence pre-heat | No future transition time to target — pre-heat cannot compute a lead time | Detect live-source rooms, suppress pre-heat, show "Pre-heat disabled — presence cannot be scheduled." |
| Outdoor temperature entity for heat curve normalisation | Adds another optional dependency; heat curve lookup table is v2 scope | Treat inertia_factor as learned at average conditions; accept ±10% seasonal variation |
| Pronote teacher/vie-scolaire accounts | pronotepy support is limited and unmaintained for non-student accounts | Student account only in v1.3; teacher accounts deferred |
| iCal write-back (creating events from heating data) | Out-of-scope scope creep; HA calendar write is a different API surface | Read-only ICS fetch only |
| Presence source priority / fallback chain between Pronote and iCal | A person can have at most one schedule source; multi-source merging adds ambiguity | One `schedule_source` field per person: "manual" \| "pronote" \| "ical"; no blending |
| Custom credential vault / secret manager | HA already encrypts ConfigEntry data at rest; no extra layer needed | Store Pronote credentials in person config via existing Store helper; same pattern as other sensitive config |

---

## Feature Dependencies

```
v1.3 features depend on (all already shipped in v1.0–v1.2):
  └─→ schedule.py resolve_presence() — additive: new "pronote"/"ical" sources plug in
  └─→ const.py PRESENCE_* constants — add PRESENCE_PRONOTE / PRESENCE_ICAL
  └─→ coordinator.py _compute_present_persons() — call new source resolvers
  └─→ storage.py person schema — additive fields: schedule_source, pronote_*, ical_*
  └─→ websocket.py set_person_config — carry new person config fields

Feature 1 — Pronote presence source
  └─→ NEW external dep: pronotepy (PyPI); declared in manifest.json requirements[]
  └─→ Timetable fetch: async executor wrapper (pronotepy is sync — run_in_executor)
  └─→ Cache: per-person TTL cache (default 1h); keyed by person_id
  └─→ schedule.py: resolve_presence() gains "pronote" branch; calls cached timetable
  └─→ Person config additions: schedule_source, pronote_url, pronote_username,
      pronote_password (encrypted-at-rest by HA Store)
  └─→ UI: person card gains schedule_source selector; pronote credential fields
      appear when source=pronote
  └─→ Fallback: on any pronotepy exception, fall through to manual schedule
  └─→ Status payload: persons entry gains fetch_error / last_fetched fields

Feature 2 — iCal presence source
  └─→ NEW external deps: icalendar + recurring-ical-events (PyPI)
  └─→ ICS fetch: aiohttp (already in HA) or urllib; TTL cache (default 1h)
  └─→ RRULE expansion: recurring-ical-events.between(now-7d, now+7d) at fetch time
  └─→ Mapping: work-type events → absent; holiday events → present
      (configurable via keyword list on the person config)
  └─→ schedule.py: resolve_presence() gains "ical" branch; queries expanded event list
  └─→ Person config additions: schedule_source, ical_url, ical_absent_keywords,
      ical_present_keywords
  └─→ UI: person card gains ical_url field + keyword config when source=ical

Feature 3 — Predictive pre-heat
  └─→ Pre-heat is additive to existing coordinator evaluation passes
  └─→ coordinator.py: new pre-heat pass BEFORE _compute_desired_temps(); if a room
      is in its pre-heat window, override desired_temp with the upcoming period's temp
  └─→ schedule.py: new helper next_period_transition(daily_program, now) →
      (next_mode, transition_datetime)
  └─→ Room config additions: preheat_enabled, preheat_max_duration,
      inertia_factor, inertia_samples
  └─→ Zone config additions: preheat_flow_temp_ref (default 60.0°C)
  └─→ Observation loop: runs after push pass; records actual_time for rooms that
      reached target since last pre-heat start; updates inertia_factor
  └─→ Status payload: rooms entry gains preheat_active, preheat_target
  └─→ UI: room card shows "Pre-heating (→ XX.X°C)" label when preheat_active
  └─→ Compatibility guard: if person has live/reactive presence source (ha mode),
      preheat_enabled is ignored for rooms linked to that person

Feature 4 — Matter→Tado X sensor mapping
  └─→ coordinator.py _async_calibrate(): already routes to _async_calibrate_tado_device
      for rooms with Tado X Radiator Valve X devices
  └─→ NEW: subscribe state_changed for mapped Matter entities on integration setup;
      cancel subscription on unload (Pitfall 1 pattern — store cancel callback on runtime_data)
  └─→ On state_changed: extract new_state.attributes.current_temperature;
      immediately call _async_calibrate_tado_device for the mapped room
  └─→ Matter entity subscription replaces zone entity as temperature source for
      calibration — only for rooms with an explicit mapping configured
  └─→ Config additions: per-room matter_calibration_entity (entity_id string or null)
  └─→ UI: Global Settings calibration section → mapping table (room name → Matter entity picker)
  └─→ Fall back to existing zone entity temperature when no mapping present (no regression)
  └─→ HA helper: homeassistant.helpers.event.async_track_state_change_event

Feature 5 — Hide HA presence mode when no device trackers
  └─→ person entity attributes: hass.states['person.X'].attributes
      contains 'device_trackers' (list of entity_ids) when device trackers are
      linked; absent or empty list means no tracking configured
  └─→ Preferred approach: Approach 1 (frontend-only) — check
      hass.states[personId]?.attributes?.device_trackers?.length > 0 before
      rendering the "HA" option in the mode picker; zero backend changes
  └─→ Fallback: Approach 2 (backend flag) if the 'device_trackers' attribute
      proves unreliable — add has_device_tracker: bool to get_status persons payload
  └─→ websocket.py: no change needed for Approach 1; for Approach 2, add lookup
      in _build_status_payload() using hass.states.get(person_entity_id)
  └─→ No storage changes required for either approach
```

---

## Expected Behaviours and Edge Cases

### Feature 1 — Pronote presence source

**Normal operation:** On each coordinator tick (or on demand), the cached
timetable is queried. If the current time falls within a lesson slot, the person
is absent; otherwise present. Lesson objects expose `start`, `end`,
`is_cancelled` — cancelled lessons must be treated as free time (present).

**Fetch failure:** pronotepy raises on network error, expired session, or
Pronote protocol change. Fallback to manual schedule; log warning with
`last_fetch_error` in status payload. Do not let a single failed fetch freeze
presence — heating must continue.

**Session expiry:** Pronote sessions expire (typically ~12h). The library
provides `session_check()`. Reconnect transparently on expiry.

**Synchronous blocking:** pronotepy is sync. All calls must be wrapped in
`hass.async_add_executor_job()` to avoid blocking the event loop.

**New school year / empty timetable:** Between school years, timetable may be
empty. Empty timetable → person considered present (conservative: do not
deprive of heat when data is absent).

**Long weekend / holiday:** When all slots on a day are cancelled or the day
has no lessons, person is present for the full day.

### Feature 2 — iCal presence source

**Keyword matching:** Work event detection must be keyword-based (summary
contains "work", "bureau", etc.) since ICS files have no standard "work" flag.
Default absent keywords: ["work", "bureau", "réunion", "meeting"]; default
present keywords: ["holiday", "vacances", "congé"]. Configurable per person.

**All-day events:** ICS all-day events use DATE (not DATETIME) values; they
cover the full day. A "holiday" all-day event means present for the day.

**RRULE expansion:** Must expand to the ±7-day window at fetch time.
`recurring-ical-events.between()` handles this. Without expansion, weekly
recurring "work" events are invisible to the evaluator.

**Timezone handling:** ICS events may have TZID; all comparisons must use
tz-aware datetimes. `icalendar` + `zoneinfo` handles this correctly.

**Fetch TTL:** Default 1h prevents hammering the ICS endpoint. URL may be a
private Google/Outlook/Nextcloud link — treat as opaque.

**Conflict: work event and holiday event on same day:** Present (holiday) wins
over absent (work). Holiday is the conservative choice for heating.

### Feature 3 — Predictive pre-heat

**Lead time computation:** `lead_time = (ΔT / effective_rate) × safety_margin`,
where `effective_rate = inertia_factor × (flow_temp_now / T_flow_ref)`. With no
boiler entity, `flow_temp_now = preheat_flow_temp_ref` (fixed assumption). The
simplification produces ±15–20% error vs a real heat curve, which is acceptable
for comfort-level control.

**Cold start (inertia not yet learned):** Use fixed 60-minute default, capped by
`preheat_max_duration`. After the first successful convergence cycle, replace
with learned value.

**Pre-heat cap overflow:** If `lead_time > preheat_max_duration`, clamp to cap
and record observation as `did_not_converge=True`. Exclude from inertia model.
Surface warning: "Room X could not reach target before period start."

**Room already at target:** Skip pre-heat entirely. Delta ≤ threshold (matches
calibration threshold logic).

**Pre-heat window overlaps a frost/reduced period:** Start pre-heat from the
period boundary — do not drop below the frost protection temperature during the
ramp. Coordinator treats the pre-heat window as a synthetic "comfort/normal"
sub-period for the affected room.

**Live-presence mode incompatibility:** Rooms whose heating depends on a person
with `mode=ha` (live device tracker) cannot schedule a future transition. Guard:
if any room-linked person uses `mode=ha`, set `preheat_enabled_effective=False`
for that room and surface the warning in UI. Rooms linked to pronote/ical/manual
persons are unaffected.

**Multiple persons linked to a room:** Pre-heat is triggered by the earliest
upcoming transition among all linked persons. If person A becomes present at
7:00 and person B at 8:00, pre-heat targets 7:00.

**Convergence detection:** Track last 5 inertia_samples. Convergence when
variance of last 3 non-`did_not_converge` samples is < 10% of mean. Once
converged, safety_margin reduces from 1.3 → 1.0 over 2 additional cycles.

### Feature 4 — Matter→Tado X sensor mapping

**Subscription lifecycle:** `async_track_state_change_event` must be called
after HA is fully started. Cancel callback stored on `runtime_data` and invoked
in `async_unload_entry` (mirrors existing minute-ticker cancel pattern).

**Missing Matter entity:** If the configured `matter_calibration_entity` does
not exist in `hass.states`, log a warning at startup and skip subscription.
Do not raise — graceful degradation to existing 45-min calibration.

**Multiple TRV devices per room:** The Matter entity maps to the _room_, not to
individual TRV devices. On `state_changed`, calibrate all Tado X devices in
the room, same as the periodic pass.

**current_temperature attribute absent:** The Matter TRV may fire `state_changed`
without a `current_temperature` attribute (mode-only changes). Guard: check
`new_state.attributes.get('current_temperature')` before triggering calibration.

**Calibration throttle:** Back-to-back Matter state changes (sub-second) must
not hammer the Tado X cloud API. Apply a per-room minimum interval (e.g. 30s)
between calibration writes triggered by Matter events. Periodic pass (1 min) is
unaffected.

**Coexistence with periodic pass:** Matter-event-triggered calibration and the
1-minute periodic calibration pass both write `_calibration_last_offset`. They
must use the same dictionary and the same delta threshold to avoid race conditions.
The periodic pass checks `abs(delta) > threshold` — if Matter already corrected
to within threshold, the periodic pass silently skips.

### Feature 5 — Hide HA presence mode when no device trackers

**Attribute name:** HA `person.*` entities expose `device_trackers` as a list
of entity_id strings in their state attributes when device trackers are
configured. Empty list or absent attribute = no tracking configured.

**Frontend guard:** `hass.states[personId]?.attributes?.device_trackers?.length > 0`
is the simplest check. If the person entity itself is absent from hass.states
(not a recognised HA person), fall back to hiding the HA option entirely.

**Edge case — HA person entity not in hass.states:** Person IDs in Climate
Manager are stored as `person.<name>` entity IDs. If the user renames or
deletes a HA person, the entity ID may become stale. The existing coordinator
code already handles this gracefully (missing persons yield no presence result).
The UI guard should also handle the missing-entity case without throwing.

**Rename HA mode label:** Related quick task (noted in todo). Label should read
"HA device tracker" instead of "HA" to be self-explanatory. Zero backend change;
purely a frontend string update.

---

## MVP Recommendation

Ship in this priority order within v1.3:

1. **Hide HA presence mode when no device trackers** — lowest risk, zero
   backend change, prevents silent breakage for new users who try the HA option.
2. **Matter→Tado X sensor mapping** — no new PyPI deps; extends existing
   calibration infrastructure; delivers immediate value for existing Tado X users.
3. **iCal presence source** — cleaner integration risk profile than Pronote
   (standard protocol, stable libs); useful for the majority of working adults.
4. **Pronote presence source** — introduces first external dep + credential
   storage; higher protocol risk; very high value for French households with
   school-age children.
5. **Predictive pre-heat** — highest complexity; requires new coordinator pass,
   inertia learning loop, schema changes, UI status labels; build after presence
   sources are stable so pre-heat can target calendar-driven transitions.

Defer to v1.4 or quick tasks post-v1.3:

- Outdoor temperature entity for heat curve correction (pre-heat accuracy)
- Boiler entity integration for real flow temp (pre-heat accuracy)
- Pronote teacher/vie-scolaire account support
- Keyword-configuration UI for iCal event classification

---

## Sources

- pronotepy GitHub (maintenance mode statement, sync-only API):
  https://github.com/bain3/pronotepy
- pronotepy PyPI: https://pypi.org/project/pronotepy/
- pronotepy stable docs (clients/lessons API):
  https://pronotepy.readthedocs.io/en/stable/api/clients.html
- icalendar PyPI (RFC 5545 parser): https://pypi.org/project/icalendar/
- recurring-ical-events PyPI (RRULE expansion):
  https://pypi.org/project/recurring-ical-events/
- HA Person integration docs (device_trackers attribute):
  https://www.home-assistant.io/integrations/person/
- HA Developer Docs — entity event setup (async_track_state_change_event):
  https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/entity-event-setup/
- Adaptive HVAC Preheat HA community thread (convergence patterns):
  https://community.home-assistant.io/t/adaptive-hvac-preheat-for-home-assistant-learns-your-system-hits-comfort-time/997235
- Existing codebase: const.py, coordinator.py, schedule.py, trv.py, storage.py,
  websocket.py
