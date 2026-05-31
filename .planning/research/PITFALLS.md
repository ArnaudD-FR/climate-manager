# Domain Pitfalls — v1.3 Calendar Presence & Pre-heat

**Project:** Climate Manager
**Milestone:** v1.3 Calendar Presence, iCal, Pre-heat, Matter Sensor Mapping
**Researched:** 2026-05-31
**Overall confidence:** HIGH (integration patterns from HA docs + confirmed
  issues from pronotepy issue tracker + icalendar RFC + HA core source)

---

## Critical Pitfalls

Mistakes that cause silent failures, IP bans, corrupted learning models,
or ghost listeners that survive integration reload.

---

### CRIT-01: pronotepy IP suspension from over-frequent login

**What goes wrong:** Pronote servers ban the integration's IP address when
it logs in too frequently. The error is
`PronoteAPIError: Your IP address is suspended` (error code 25: "Exceeded
max authorisation requests"). Confirmed in the pronotepy issue tracker (#291)
and the hass-pronote project.

**Why it happens:** pronotepy creates a fresh session per `Client()` call.
If the integration creates a new `Client` on every coordinator tick (every
minute) to fetch the timetable, it hammers the Pronote login endpoint at
60 logins/hour — well above the threshold.

**Consequences:** The IP of the HA instance is suspended for an unspecified
period. All Pronote-sourced persons fall back to manual schedule silently.
The user may not notice until they realise presence detection stopped updating.

**Prevention:**
- Cache the `Client` object; reconnect only on `PronoteAPIError` or
  `ExpiredObject`.
- Use `client.session_check()` to renew the session cheaply without a full
  re-login.
- Fetch the timetable at most once per day at a random morning offset (school
  timetables change at semester boundaries, not minute by minute). Store the
  fetched timetable in-memory with a TTL of at least 6 hours.
- On `PronoteAPIError` (login failure), back off exponentially; do not retry
  within the same minute.

**Detection:** `PronoteAPIError: Your IP address is suspended` in HA logs.
Monitor login frequency in the coordinator — log every login attempt at
DEBUG level.

**Phase:** Pronote source implementation phase.

---

### CRIT-02: pronotepy API breakage from Pronote server updates

**What goes wrong:** Pronote regularly updates their internal (undocumented)
protocol. pronotepy reverse-engineers this protocol and each Pronote server
update can silently break authentication or timetable parsing. The library
entered maintenance-only mode (bug fixes, no new features). A 2025 update
broke QR-code login and required a pronotepy patch release (v2.14.5).

**Why it happens:** pronotepy has no stable contract with Pronote — it
reverse-engineers encrypted API calls. When Pronote updates their crypto
or session flow, all existing integrations fail simultaneously.

**Consequences:** All Pronote-sourced persons silently fall back to manual
schedule. If fallback is not implemented, persons show wrong presence state.

**Prevention:**
- Always wrap `Client()` and all `.lessons()` / `.timetable()` calls in
  `try/except (PronoteAPIError, CryptoError, Exception)` — the exception
  surface from a reverse-engineered protocol is wide.
- Implement the fallback-to-manual-schedule explicitly: if timetable fetch
  fails, `schedule_source` degrades to `"manual"` until the next successful
  fetch. Log at `_LOGGER.warning` level, not DEBUG.
- Pin pronotepy to a minor version in `manifest.json` (e.g.
  `pronotepy>=2.14,<3`) to avoid automatically pulling a breaking major.
- Document the maintenance risk in the UI tooltip for the Pronote config.

**Detection:** Any exception from pronotepy in logs. Absence of timetable
updates over 24+ hours when school is in session.

**Phase:** Pronote source implementation phase.

---

### CRIT-03: iCal DTSTART DATE vs DATETIME type collision

**What goes wrong:** All-day events use `DTSTART;VALUE=DATE:20260601`
(a `datetime.date` object) while timed events use
`DTSTART;TZID=Europe/Paris:20260601T090000` (a `datetime.datetime`). Code
that compares `event.start >= now` crashes with
`TypeError: can't compare datetime.datetime to datetime.date` unless both
sides are normalised first.

**Why it happens:** RFC 5545 allows both value types. Calendar exports from
Google Calendar, Outlook, and Apple Calendar mix both types in the same feed.
The Python `icalendar` library faithfully returns the raw type without
coercion.

**Consequences:** An `AttributeError` or `TypeError` inside the timetable
evaluation function causes the entire person's presence to fail, typically
raising an unhandled exception in `async_evaluate` that silently aborts the
calibration pass too.

**Prevention:**
- Normalize at parse time: if `isinstance(event.start, datetime.date) and
  not isinstance(event.start, datetime.datetime)`, convert to
  `datetime.datetime(d.year, d.month, d.day, tzinfo=<local_tz>)`.
- Use a helper function `_to_aware_datetime(val, local_tz)` called on every
  event start/end before any comparison.
- Unit-test with a fixture ICS file that contains both all-day and timed
  events in the same feed.

**Detection:** `TypeError: can't compare datetime.datetime to datetime.date`
in HA logs during presence evaluation.

**Phase:** iCal source implementation phase.

---

### CRIT-04: iCal timezone-naive datetime vs aware datetime comparison

**What goes wrong:** Some ICS producers emit `DTSTART:20260601T090000`
(no `Z`, no `TZID`) — a timezone-naive datetime. Comparing this to
`dt_util.now()` (which is always timezone-aware) raises
`TypeError: can't compare offset-naive and offset-aware datetimes`.

**Why it happens:** RFC 5545 §3.3.5 calls a DTSTART without TZID or Z suffix
"floating time" — intended to mean "local time, whatever the locale". Many
real-world ICS feeds (especially from French platforms like ENT portals)
emit floating times. The `icalendar` library returns them as naive
`datetime.datetime` objects.

**Consequences:** Same as CRIT-03 — exception terminates presence evaluation.

**Prevention:**
- In `_to_aware_datetime`, also handle the naive case: if
  `event_dt.tzinfo is None`, attach the HA-configured timezone by calling
  `dt_util.as_local(naive_dt)` (never use `dt.replace(tzinfo=...)` which
  ignores DST transitions).
- Test with a fixture ICS file from a French ENT portal that emits floating
  times.

**Detection:** `TypeError: can't compare offset-naive and offset-aware` in
HA logs.

**Phase:** iCal source implementation phase.

---

### CRIT-05: RRULE recurring event expansion producing unbounded results

**What goes wrong:** Expanding RRULE recurring events with no UNTIL or COUNT
clause (e.g. `RRULE:FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR`) generates an
infinite sequence. Calling `list(rruleset)` on such an event hangs the event
loop or consumes all memory.

**Why it happens:** A work calendar "every weekday forever" is a valid and
common pattern. Naive RRULE expansion code does not bound the query window.

**Consequences:** HA event loop blocked; integration appears frozen; watchdog
may restart HA.

**Prevention:**
- Use `recurring-ical-events` library (PyPI: `recurring-ical-events`), which
  takes an explicit `(start, end)` window and only materialises events in that
  range. Query a 7-day rolling window around `now`.
- Never call `rrule.between()` without explicit `dtstart`/`until` bounds.
- Add `recurring-ical-events` and `icalendar` to `manifest.json` requirements.

**Detection:** Integration becomes unresponsive during iCal timetable parsing.

**Phase:** iCal source implementation phase.

---

### CRIT-06: PyPI requirements not installed on first boot (Docker / venv)

**What goes wrong:** `pronotepy`, `icalendar`, and `recurring-ical-events`
are declared in `manifest.json` requirements. On a fresh Docker-based HA
install, HA attempts pip installation during `async_setup_entry`. If the
container network is slow or pip fails (SSL, mirror outage), the integration
fails to load with `ModuleNotFoundError` at import time.

**Why it happens:** HA installs requirements asynchronously before calling
`async_setup_entry`, but import of the requirement happens at module import
time (top-level `import pronotepy`) — before the install attempt completes
in some edge cases. There is also a confirmed HA 2026.3 regression where
custom integration requirements fail after the Python 3.14 upgrade.

**Consequences:** Integration silently fails to load. User sees "Failed to
set up Climate Manager" in the UI. No climate control.

**Prevention:**
- Import optional dependencies inside the function that uses them
  (`from pronotepy import ...` inside the async coroutine, not at module top
  level). This converts an import-time crash into a graceful runtime error.
- Catch `ImportError` around these deferred imports and raise
  `ConfigEntryNotReady` so HA retries setup after a delay.
- Test in a Docker environment before shipping — do not rely on venv-only
  testing.
- Add a user-facing warning if pronotepy is unavailable: "Pronote source
  requires the pronotepy package. Ensure HA can reach PyPI on startup."

**Detection:** `ModuleNotFoundError: No module named 'pronotepy'` in logs.
Integration shows "Failed to set up" in the UI.

**Phase:** First phase to introduce any external PyPI dependency.

---

### CRIT-07: Inertia learning model corruption from atypical heating samples

**What goes wrong:** A window-open day, a maintenance visit (door open for
hours), or a guest-heavy day produces a much faster heat-up than normal
(extra heat sources, different thermal mass). The `inertia_factor` is updated
with this outlier and the model permanently over-estimates heating speed,
causing the room to pre-heat too late on subsequent normal days.

**Why it happens:** The learning algorithm has no mechanism to distinguish
atypical from typical samples. A single outlier in a small sample set (3-5
samples) has disproportionate influence.

**Consequences:** Rooms miss their target temperature at period start. The
model degrades silently — users see pre-heat failing but do not know why.

**Prevention:**
- Implement `did_not_converge` flag (already specified in the todo) — but
  also implement an outlier flag for the opposite case: if actual heat-up
  time was more than 2x faster than the running mean of prior samples, mark
  the sample as `is_outlier = true` and exclude it from `inertia_factor`
  computation.
- Use a rolling median (not mean) over the last N valid samples to reduce
  outlier sensitivity.
- Cap the maximum per-cycle adjustment to the `inertia_factor` (e.g. ±30%)
  to prevent a single sample from drastically shifting the model.
- Expose `inertia_samples` count and `inertia_factor` in the status payload
  so the panel can show "Learning (3/5 samples)" for user observability.

**Detection:** `inertia_factor` shifting by >50% between two consecutive
samples; actual room heat-up time deviating greatly from predicted.

**Phase:** Pre-heat implementation phase.

---

### CRIT-08: Pre-heat target overwritten by frost/reduced pass

**What goes wrong:** A pre-heat window computed backward from a period start
may overlap with a frost or reduced period. If the pre-heat starts during a
frost period (e.g. 05:30 frost, 07:00 normal — pre-heat starts at 06:00),
the coordinator's `_compute_desired_temps` pushes frost temperature at 06:00
instead of the pre-heat target, cancelling the pre-heat silently.

**Why it happens:** Pre-heat is a separate pass from the main schedule
evaluation. If pre-heat target injection is not applied after the main
desired-temp resolution, the main pass overwrites it.

**Consequences:** Pre-heat never works in the most common case (heating up
from overnight frost). Inertia samples always show `did_not_converge = true`.

**Prevention:**
- Inject pre-heat targets as a final pass after `_compute_desired_temps` and
  `_apply_presence_overrides`. Pre-heat targets must override frost/reduced
  — they are the intentional early-start.
- The todo already specifies "pre-heat window extends into frost/reduced
  period: start from the boundary" — implement this as: if the backward
  window from period start reaches into a frost period, clamp pre-heat start
  to the frost→normal boundary. The window shortens but does not start inside
  a frost period.
- Write a unit test: 05:30 frost, 07:00 normal, 60 min default lead time →
  pre-heat starts at 06:00 (clamped from 05:30 boundary), target is Normal
  temperature, not frost.

**Detection:** Pre-heat never reaches target; `did_not_converge` always true
for rooms whose schedule starts after an overnight frost period.

**Phase:** Pre-heat implementation phase.

---

## Moderate Pitfalls

---

### MOD-01: Matter entity not in state machine at subscription time

**What goes wrong:** `async_track_state_change_event` is registered for a
Matter TRV entity during `async_setup_entry`. If the Matter integration loads
after Climate Manager (common — HA loads integrations in parallel), the entity
does not yet exist in `hass.states`. The subscription itself succeeds (it is
event-bus-based), but any synchronous read of
`hass.states.get(matter_entity_id)` at setup time returns `None`.

**Why it happens:** HA's integration loading is concurrent. Climate Manager
subscribes to state changes before Matter registers its entities.

**Consequences:** Coordinator startup calibration pass logs "state is None,
skipping" for every Matter entity. The initial calibration baseline is missing.

**Prevention:**
- Always guard with `hass.states.get(entity_id)` returning `None` before
  processing a `state_changed` callback — this is already the pattern in
  the existing calibration code.
- Do not read entity state synchronously in `async_setup_entry`. Let the
  `state_changed` subscription drive calibration triggers.
- Consider registering the subscription only after `EVENT_HOMEASSISTANT_STARTED`
  fires if sub-minute calibration responsiveness is not needed at boot.

**Detection:** `state is None` log warnings for Matter entities on startup.

**Phase:** Matter sensor mapping phase.

---

### MOD-02: state_changed subscription not cancelled on integration unload

**What goes wrong:** `async_track_state_change_event` returns an unsubscribe
callable. If it is not stored and called in `async_unload_entry`, the
subscription survives integration reload. After reload, a second subscription
is registered, resulting in double-firing of the calibration trigger for
every Matter temperature change.

**Why it happens:** The existing code in `__init__.py` correctly stores
`cancel_scheduler` and `cancel_registry_listeners`, but a new Matter
subscription list must be added to `ClimateManagerData` if Matter subscriptions
are registered at setup time.

**Consequences:** After each reload, one more calibration call fires per
Matter state change. After 5 reloads, 5 calibration calls fire per update.
Tado X API rate limit hit; offset oscillates.

**Prevention:**
- Append Matter subscription cancel callbacks to
  `entry.runtime_data.cancel_registry_listeners` (the existing list) or
  create a new `cancel_matter_subscriptions` field on `ClimateManagerData`.
- Call all cancel callbacks in `async_unload_entry` before returning.
- Pattern already established: follow the same structure as
  `cancel_registry_listeners` in `__init__.py`.

**Detection:** Duplicate `_async_calibrate_tado_device` log entries on the
same tick after integration reload.

**Phase:** Matter sensor mapping phase.

---

### MOD-03: iCal URL returning stale content due to HTTP caching

**What goes wrong:** Some calendar servers (Google Calendar, Nextcloud) set
aggressive HTTP cache headers (`Cache-Control: max-age=3600`). If the iCal
fetcher uses `aiohttp` without explicit cache-busting, the same stale ICS
content is returned for hours, and event changes (cancelled lesson, new
holiday) are not reflected.

**Why it happens:** Python `aiohttp` respects HTTP `Cache-Control` headers by
default when using a connector with connection reuse. Some proxies also cache
ICS responses.

**Prevention:**
- Use `headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}` on the
  aiohttp request.
- Use `hass.helpers.aiohttp_client.async_get_clientsession(hass)` to get the
  shared HA aiohttp session (correct pattern for HA integrations).
- Fetch at most once per hour regardless — store the last-fetched ICS body
  in-memory with a TTL.

**Detection:** Calendar changes not reflected after 24h; timetable shows old
events.

**Phase:** iCal source implementation phase.

---

### MOD-04: Credentials stored in Store helper as plain text

**What goes wrong:** Pronote credentials (URL, username, password) and iCal
URLs with embedded auth tokens stored in `ClimateManagerStore` are plain-text
JSON in `.storage/`. If the HA config directory is exposed (backup,
misconfiguration), all credentials are leaked.

**Why it happens:** `Store` is the correct HA pattern for structured data but
provides no encryption. `ConfigEntry.data` is also plain text. HA has no
built-in secret encryption for third-party integrations.

**Consequences:** Pronote credentials leaked. Attacker can impersonate the
student's account on the school platform.

**Prevention:**
- Store Pronote credentials in `ConfigEntry.data` via `ConfigFlow` — this is
  the HA-recommended location for credentials because the HA reauth flow is
  designed around it.
- Document clearly in the UI: "Credentials are stored in the HA configuration
  directory. Secure your HA instance and backups."
- For iCal URLs with embedded tokens (Google private ICS URLs), treat the URL
  itself as a secret — same guidance applies.
- Never log credentials at any level, including DEBUG.

**Detection:** `.storage/core.config_entries` readable on filesystem.

**Phase:** Pronote/iCal config flow implementation.

---

### MOD-05: Pre-heat cap exceeded silently without user notification

**What goes wrong:** The `preheat_max_duration` cap is applied and the room
does not reach target before the period starts. The `did_not_converge` sample
is excluded from learning (correct). But if this happens every day (undersized
radiator, very cold room), the inertia model never converges and the default
60-minute lead time is used forever — the user never knows why pre-heat
appears to be doing nothing.

**Why it happens:** The todo specifies a warning should be surfaced, but the
warning is easy to miss if only written to the coordinator log. The panel UI
may not have a clear path to display it.

**Prevention:**
- Expose `preheat_status: "ok" | "did_not_converge" | "cap_exceeded"` in the
  room status payload (WebSocket `get_status` / `subscribe_status`).
- The panel should show a visible warning badge on the room card when
  `cap_exceeded` has been true for 3+ consecutive cycles.
- Log at `_LOGGER.warning` (not debug) when `did_not_converge = true`.

**Detection:** `inertia_samples` list filled entirely with
`did_not_converge: true` entries.

**Phase:** Pre-heat implementation phase.

---

### MOD-06: Tado X serial number matching ambiguity in device registry

**What goes wrong:** The Matter→Tado X mapping uses "Matter entity → Tado X
device serial" as described in the todo. If two rooms contain the same Tado X
model, matching by model name alone hits multiple devices. Serial number
lookup in the device registry requires reading `device.identifiers` — which
is not guaranteed to be present across all firmware versions.

**Why it happens:** `get_tado_valve_devices` currently matches by
`device.model == "Radiator Valve X"` and `device.area_id`. Serial number
matching requires reading from `device.identifiers` (a set of
`(domain, identifier)` tuples).

**Prevention:**
- Use `device.identifiers` to build the serial→device mapping. For Tado X,
  the identifier is the serial number from the `tado_x` domain.
- Fall back to matching by area and model only if `device.identifiers` is
  missing; log a warning if multiple matches exist with no serial to
  disambiguate.
- Unit-test the matching logic with a fixture device registry containing two
  Tado X devices in the same area.

**Detection:** Calibration applied to wrong TRV; offset diverges between two
TRVs in the same room.

**Phase:** Matter sensor mapping phase.

---

### MOD-07: iCal EXDATE and modified-occurrence events ignored

**What goes wrong:** When a recurring event has a cancellation
(`EXDATE:20260610T090000Z`) or a moved instance (`VEVENT` with
`RECURRENCE-ID`), naive RRULE expansion ignores these overrides. A cancelled
lesson still appears as "at school" on the cancelled day.

**Why it happens:** The Python `icalendar` library's raw RRULE expansion does
not handle `EXDATE` or `RECURRENCE-ID` overrides. These require post-processing
to remove cancelled instances and substitute modified ones.

**Prevention:**
- Use `recurring-ical-events` library which handles `EXDATE`, `EXRULE`, and
  `RECURRENCE-ID` correctly per RFC 5545 §3.8.5.
- Do not implement RRULE expansion manually.

**Detection:** Child present on school holiday / cancelled lesson days.

**Phase:** iCal source implementation phase.

---

### MOD-08: Hide HA presence mode — empty vs absent device_trackers attribute

**What goes wrong:** The feature "hide HA presence mode when person has no
tracked device" infers tracker availability from the `device_trackers`
attribute of the `person.*` entity. The `person` integration always emits
`device_trackers` as a list (possibly empty). Checking
`if attributes.get("device_trackers") is None` misses the empty list case —
HA mode option remains visible for persons with no trackers assigned.

**Why it happens:** `dict.get("device_trackers")` returns `None` only when
the key is absent, not when the value is `[]`. Both cases mean "no trackers
configured" but require different checks.

**Prevention:**
- Use `not attributes.get("device_trackers", [])` — evaluates to `True` when
  the attribute is absent, `None`, or an empty list.
- Unit-test with a fixture person entity with `device_trackers: []` and with
  `device_trackers: ["device_tracker.phone"]`.

**Detection:** HA presence mode option visible in UI for persons who have no
device trackers configured.

**Phase:** Hide HA presence mode feature phase.

---

## Minor Pitfalls

---

### MIN-01: iCal URL auth token expiry returns 403 silently

**What goes wrong:** Google Calendar and similar providers rotate the private
token in the ICS URL when the user revokes or regenerates calendar access.
After rotation, the ICS fetch returns 403 or an empty calendar, and all events
disappear from the timetable, showing the person as permanently absent.

**Prevention:** Detect 403 / empty-calendar responses explicitly; surface a
user-facing error in the panel ("iCal URL may have expired — please update
it"). Do not silently fall back to an empty presence schedule.

**Phase:** iCal source implementation phase.

---

### MIN-02: pronotepy ExpiredObject on cached lesson references

**What goes wrong:** `pronotepy` raises `ExpiredObject` (error 22) when code
holds a reference to a lesson object across a session renewal. The Pronote
server invalidates all object IDs each session.

**Prevention:** Never cache individual `Lesson` objects. Cache only the raw
timetable data (start/end times, subject name) derived from them. Re-fetch
and re-derive on each session renewal.

**Phase:** Pronote source implementation phase.

---

### MIN-03: Boiler entity unavailable degrades to fallback silently

**What goes wrong:** If `boiler_entity` is configured for a zone but the
boiler integration is unavailable (boiler off, integration error), the pre-heat
calculation falls back to `preheat_flow_temp_ref`. This is correct per the
todo spec, but if not logged the user cannot distinguish "no boiler
configured" from "boiler unavailable".

**Prevention:** Log at DEBUG when falling back from a configured but unavailable
boiler entity. Surface `flow_temp_source: "actual" | "fallback"` in the
pre-heat status payload.

**Phase:** Pre-heat implementation phase.

---

### MIN-04: Using deprecated async_track_state_change (without _event suffix)

**What goes wrong:** The older `async_track_state_change` (without `_event`
suffix) was deprecated in HA 2024.4 because it creates a top-level
`EVENT_STATE_CHANGED` listener that fires for every state change in HA,
causing performance issues at scale.

**Prevention:** Always use `async_track_state_change_event` (with `_event`
suffix). This is already the project's established practice — apply the same
pattern to the new Matter sensor subscriptions.

**Phase:** Matter sensor mapping phase.

---

### MIN-05: requirements version pinning too tight vs too loose

**What goes wrong:** Pinning `pronotepy==2.14.5` blocks security fixes.
Pinning `pronotepy>=2` allows a future breaking major version. The `icalendar`
library is on v6.x with a v7 in progress — a `>=6` pin would pull v7 if it
introduces breaking API changes.

**Prevention:**
- Use compatible-release or upper-bounded pins. Recommended:
  `pronotepy>=2.14,<3`, `icalendar>=6.0,<7`, `recurring-ical-events>=3.0,<4`.
- Revisit pins at each HA version bump.

**Phase:** First phase to introduce external PyPI dependencies.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Pronote source | CRIT-01 IP ban from over-polling | Cache Client; fetch timetable once per 6h max |
| Pronote source | CRIT-02 pronotepy API breakage | Broad exception handling; fallback to manual |
| Pronote source | MOD-04 credentials in plain text | Use ConfigEntry.data; document security |
| Pronote source | MIN-02 ExpiredObject on lesson refs | Cache derived data, not Lesson objects |
| iCal source | CRIT-03 DATE vs DATETIME collision | `_to_aware_datetime()` helper with unit tests |
| iCal source | CRIT-04 naive vs aware comparison | `dt_util.as_local()` for floating times |
| iCal source | CRIT-05 unbounded RRULE expansion | Use `recurring-ical-events` with windowed query |
| iCal source | MOD-03 stale HTTP cache | `Cache-Control: no-cache` header; in-memory TTL |
| iCal source | MOD-07 EXDATE/RECURRENCE-ID ignored | Use `recurring-ical-events`, not raw rrule |
| iCal source | MIN-01 token rotation gives 403 | Detect 403, surface user error, no silent empty |
| External deps (first) | CRIT-06 requirements not installed | Deferred import; ConfigEntryNotReady; Docker test |
| External deps (first) | MIN-05 version pin strategy | Compatible-release pins; revisit on HA bump |
| Pre-heat algorithm | CRIT-07 inertia model pollution | Outlier detection; rolling median; per-cycle cap |
| Pre-heat algorithm | CRIT-08 pre-heat overwritten by frost pass | Clamp window to frost boundary; inject as final pass |
| Pre-heat algorithm | MOD-05 cap exceeded silently | preheat_status in WS payload; panel warning badge |
| Pre-heat algorithm | MIN-03 boiler unavailable silent fallback | Log at DEBUG; surface flow_temp_source in payload |
| Matter sensor mapping | MOD-01 entity missing at subscription time | Null-guard in place; no synchronous startup read |
| Matter sensor mapping | MOD-02 subscription not cancelled on unload | Extend cancel_registry_listeners; call in unload |
| Matter sensor mapping | MOD-06 serial number matching ambiguity | Use device.identifiers; warn on multiple matches |
| Matter sensor mapping | MIN-04 deprecated state_change API | Use async_track_state_change_event (project standard) |
| Hide HA presence mode | MOD-08 empty vs absent device_trackers | `not attributes.get("device_trackers", [])` |

---

## Sources

- [pronotepy GitHub issues — IP suspension (#291)](https://github.com/bain3/pronotepy/issues/291)
- [pronotepy exceptions documentation](https://pronotepy.readthedocs.io/en/v2.12.1/api/exceptions.html)
- [hass-pronote IP suspension issue (#128)](https://github.com/delphiki/hass-pronote/issues/128)
- [HA manifest.json — requirements](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [HA custom integration requirements not installed after 2026.3 (#166255)](https://github.com/home-assistant/core/issues/166255)
- [HA handling setup failures](https://developers.home-assistant.io/docs/integration_setup_failures/)
- [HA entity event subscription lifecycle rules](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/entity-event-setup/)
- [async_track_state_change deprecation (2024-04-13)](https://developers.home-assistant.io/blog/2024/04/13/deprecate_async_track_state_change/)
- [recurring-ical-events PyPI](https://pypi.org/project/recurring-ical-events/)
- [RFC 5545 — RRULE](https://icalendar.org/iCalendar-RFC-5545/3-8-5-3-recurrence-rule.html)
- [icalendar Python library documentation](https://icalendar.readthedocs.io/en/stable/usage.html)
- [Nylas — The Deceptively Complex World of Calendar Events and RRULEs](https://www.nylas.com/blog/calendar-events-rrules/)
- [HA Person integration documentation](https://www.home-assistant.io/integrations/person/)
- [async_register_static_paths migration (HA 2025.7)](https://developers.home-assistant.io/blog/2024/06/18/async_register_static_paths/)
