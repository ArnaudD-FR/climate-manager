# Technology Stack

**Project:** Climate Manager — v1.3 Calendar Presence & Pre-heat
**Researched:** 2026-05-31
**Overall confidence:** MEDIUM — library versions from PyPI search results;
  integration patterns from HA developer docs.

---

## Verdict: Four New Additions, All Python-side

The v1.3 features require three new PyPI packages and one HA-internal pattern
change. The frontend stack is unchanged. No TypeScript or Vite changes needed.

---

## New Libraries

### Pronote Timetable Fetching

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pronotepy` | `==2.14.6` | Fetch school timetable from Pronote | Only Python library for Pronote protocol; reverse-engineers the internal API; supports student/parent accounts; actively maintained in bugfix mode |

**Dependencies pulled in by pronotepy:**
- `pycryptodome` — cryptographic operations (Pronote protocol uses AES); NOT
  the same as `pycrypto` (which is abandoned)
- `requests` — synchronous HTTP; note HA uses `aiohttp` for async I/O, but
  pronotepy uses synchronous requests — must be called via
  `hass.async_add_executor_job()` to avoid blocking the event loop

**HACS manifest entry:**
```json
"requirements": ["pronotepy==2.14.6"]
```
HA will pip-install this on first load. `pycryptodome` and `requests` are
transitive deps that pip resolves automatically.

**Confidence:** MEDIUM — version 2.14.6 confirmed from PyPI search results;
exact transitive dep list not machine-verified (WebFetch blocked). Pin the
version; Pronote frequently changes its protocol and pronotepy releases bugfixes
to match. Unpin = silent breakage on next HA restart after a pip upgrade.

**Risk flag:** pronotepy is in self-declared maintenance mode (bugfixes only,
no new features). The PRONOTE protocol is undocumented and reverse-engineered.
If Pronote pushes a breaking protocol change, the library may lag 1–4 weeks
before a fix lands. Build the fetch path with a hard timeout and an explicit
fallback to the manual schedule.

---

### iCal / ICS Calendar Parsing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `icalendar` | `>=6.3,<7` | Parse ICS feeds (work calendar, public holidays) | Established RFC 5545 parser; 6.x switched timezone handling to stdlib `zoneinfo`; no C extensions; pure Python |
| `recurring-ical-events` | `>=3,<4` | Expand RRULE recurrences to concrete event instances | `icalendar` parses the ICS structure but does NOT expand RRULE/EXDATE/RDATE into a concrete event list; this library does that reliably |

**Why not icalendar alone?** Recurring events (e.g. "every Monday, work")
require RRULE expansion. `icalendar` alone gives you the raw RRULE string.
Expanding it with `dateutil.rrule` manually is 50+ lines of edge-case handling.
`recurring-ical-events` is the canonical Python solution for "give me all events
in this date range." It builds on `icalendar` + `python-dateutil` and handles
EXDATE, RDATE, UNTIL, COUNT, and timezone-aware comparisons.

**Dependencies pulled in:**
- `python-dateutil` — `recurring-ical-events` uses it for RRULE expansion
- `tzdata` — icalendar 6.x requires it for `zoneinfo` on non-Linux environments
  (on HA OS / Debian, the system tzdata is present; listing it ensures portability)

**HACS manifest entry:**
```json
"requirements": [
  "pronotepy==2.14.6",
  "icalendar>=6.3,<7",
  "recurring-ical-events>=3,<4"
]
```

**Confidence:** MEDIUM — icalendar 6.3.2 confirmed as current stable from
readthedocs; recurring-ical-events version range estimated from PyPI search
results (latest series is v3.x); python-dateutil is a well-known transitive dep.

**iCal fetch pattern:** ICS URLs are fetched via `hass.components.http` session
or `aiohttp.ClientSession` (already bundled in HA). Do NOT add `aiohttp` to
`requirements` — it is already provided by HA's environment and re-declaring it
causes version conflicts.

---

## HA-Internal Pattern: state_changed Subscription

No new library. Uses existing HA event infrastructure.

| Pattern | API | Purpose |
|---------|-----|---------|
| Matter entity state subscription | `homeassistant.helpers.event.async_track_state_change_event` | Subscribe to `current_temperature` changes on mapped Matter entities; fires `_async_calibrate` immediately instead of waiting for the 1-minute poll |

**Why `async_track_state_change_event` not `async_track_state_change`:**
`async_track_state_change` is deprecated since HA 2024.x and removed in HA
2025.5. `async_track_state_change_event` is the current API and is more
efficient (entity-scoped listener, not a top-level EVENT_STATE_CHANGED fan-out).

**Lifecycle:** The cancel callback returned by `async_track_state_change_event`
must be stored on `runtime_data` and called in `async_unload_entry` — same
pattern as the existing `async_track_time_interval` cancel callback. If the
Matter→Tado X mapping changes (user edits the config), unsubscribe old listeners
and re-subscribe to the new entity set.

**Confidence:** HIGH — confirmed from HA developer blog post (2024-04-13) and
existing HA developer documentation.

---

## Unchanged Stack

Everything below is unchanged from v1.2. Listed for completeness.

### Python Backend

| Technology | Version | Status |
|------------|---------|--------|
| Python | 3.12+ | No change |
| `homeassistant.helpers.storage.Store` | HA 2026.x | Schema extension only — add `calendar_sources`, `preheat` config keys |
| `homeassistant.components.websocket_api` | HA 2026.x | Add new WS command handlers for calendar source CRUD |
| `homeassistant.helpers.event.async_track_time_interval` | HA 2026.x | No change — coordinator poll loop unchanged |
| `voluptuous` | HA-bundled | Add schema entries for new WS commands |

### Frontend Panel

| Technology | Version | Status |
|------------|---------|--------|
| Lit 3.x | ^3 | No change |
| TypeScript 5.x | ^5 | Extend types for calendar source config, pre-heat status |
| Vite 5.x | ^5 | No change |
| `home-assistant-js-websocket` | latest | No change |

### Tooling

| Technology | Status |
|------------|--------|
| `uv` / `pytest-homeassistant-custom-component` | No change |
| GitHub Actions | No change |

---

## Storage Schema Extensions

### New top-level keys in `DEFAULT_CONFIG` (const.py)

```python
# v1.3 calendar presence
"calendar_sources": {},   # keyed by person_id → {type, url/credentials, ttl, cache}

# v1.3 pre-heat
"preheat_enabled_global": False,  # global on/off (mirrors calibration_enabled pattern)
"outdoor_temp_entity": None,      # str | None — global outdoor temp sensor
```

### Person schema extension

```python
"schedule_source": "manual",  # "manual" | "pronote" | "ical"
# When schedule_source == "pronote":
"pronote_url": str,
"pronote_username": str,
"pronote_password": str,   # stored in HA Store (encrypted at rest by HA)
"pronote_cache": dict,     # {fetched_at, lessons: [...]}
# When schedule_source == "ical":
"ical_url": str,           # HTTP/HTTPS ICS URL
"ical_ttl": int,           # seconds, default 3600
"ical_cache": dict,        # {fetched_at, raw_ics: str}
```

### Room schema extension (pre-heat)

```python
"preheat_enabled": False,
"preheat_max_duration": 120,      # minutes
"inertia_factor": None,           # float | None
"inertia_samples": [],            # list of sample dicts (last N)
```

### Zone schema extension (pre-heat boiler)

```python
"boiler_entity": None,            # str | None
"preheat_flow_temp_ref": 60.0,    # normalisation reference °C
```

Storage version bump: `STORAGE_VERSION` 2 → 3 (calendar/preheat fields).
Migration: add all new keys with defaults to loaded config; existing data
unaffected.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| iCal parsing | `icalendar + recurring-ical-events` | `ics.py` | ics.py 0.7.x is semi-abandoned; 0.8.0.dev still in pre-release; uncertain maintenance |
| iCal parsing | `icalendar + recurring-ical-events` | `ical` (rfc2445) | Less popular, less battle-tested; icalendar is the collective/Plone-maintained standard |
| RRULE expansion | `recurring-ical-events` | `icalendar` alone + `dateutil.rrule` | 50+ lines of edge-case handling for EXDATE/RDATE/UNTIL/COUNT/timezone combinations; not worth re-implementing |
| Pronote fetch | `pronotepy` | Direct HTTP scraping | Pronote uses obfuscated JS-computed request signatures; pronotepy implements the full handshake |
| Pronote execution | `async_add_executor_job` wrapper | asyncio native | pronotepy is synchronous (uses `requests`); must be run in executor to avoid blocking HA event loop |
| Matter state events | `async_track_state_change_event` | Polling via `async_track_time_interval` | Current 1-min poll is too coarse for sub-minute calibration; event-driven fires immediately on temperature change |
| Credentials storage | HA `Store` helper | `ConfigEntry.options` | Pronote password is sensitive; Store data is stored in `.storage/` which HA encrypts at rest; ConfigEntry options are less suitable for secrets |

---

## What NOT to Add

- Do NOT add `aiohttp` to `requirements` — HA already provides it; declaring
  it causes pip version conflicts.
- Do NOT add `requests` to `requirements` — it is a transitive dep of
  `pronotepy`; pip resolves it automatically.
- Do NOT add `python-dateutil` to `requirements` — transitive dep of
  `recurring-ical-events`; no explicit declaration needed.
- Do NOT add any boiler integration library — the todo specifies a fixed
  flow temperature fallback when no boiler entity exists; boiler entity reads
  use the standard `hass.states.get()` pattern on whatever climate/sensor entity
  the user declares — no new library needed.
- Do NOT add a separate async HTTP library for iCal fetching — use
  `aiohttp.ClientSession` from HA's bundled aiohttp.
- Do NOT use `git+https://` URLs in `requirements` — HA 2023+ silently ignores
  or rejects VCS requirements in manifest.json. Pin to a released PyPI version.

---

## Installation Summary

```json
"requirements": [
  "pronotepy==2.14.6",
  "icalendar>=6.3,<7",
  "recurring-ical-events>=3,<4"
]
```

Three new entries in `manifest.json`. HA pip-installs on first load.
No changes to `frontend/package.json`.

---

## Sources

- [pronotepy PyPI](https://pypi.org/project/pronotepy/) — latest version 2.14.6
- [bain3/pronotepy GitHub](https://github.com/bain3/pronotepy) — maintenance status, dependencies
- [icalendar PyPI](https://pypi.org/project/icalendar/) — version 6.3.2 current stable
- [icalendar 6.3 docs](https://icalendar.readthedocs.io/en/stable/index.html) — zoneinfo, python-dateutil deps
- [recurring-ical-events PyPI](https://pypi.org/project/recurring-ical-events/) — RRULE expansion
- [Deprecating async_track_state_change | HA Developer Blog](https://developers.home-assistant.io/blog/2024/04/13/deprecate_async_track_state_change/) — async_track_state_change_event confirmed current API
- [HA manifest requirements](https://developers.home-assistant.io/docs/creating_integration_manifest/) — PyPI pinning requirements
