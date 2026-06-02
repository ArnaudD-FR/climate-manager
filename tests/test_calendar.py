"""Tests for calendar presence resolution.

Tests for:
- Calendar constants (PRESENCE_CALENDAR, DEFAULT_PREHEAT_LEAD_MINUTES)
- resolve_calendar_presence() helper logic
- Period state "calendar" inside resolve_presence()
- _prefetch_calendars() cache deduplication, reset, and fallback
- Calendar-mode persons and calendar period states in coordinator
- set_person_config: calendar_config + preheat_lead_minutes persistence
  (ws_ prefix tests — Plan 03)

Pure unit tests (Tasks 1-3): no hass fixture needed.
Integration tests (Tasks 4-5): use hass fixture, MockConfigEntry,
async_mock_service.
WS persistence tests (Plan 03): use hass fixture + hass_ws_client.
"""

import datetime
import logging

import pytest
from freezegun import freeze_time
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DEFAULT_PREHEAT_LEAD_MINUTES,
    DOMAIN,
    MODE_TIME_PROGRAM_PRESENCES,
    PRESENCE_CALENDAR,
)
from custom_components.climate_manager.schedule import (
    resolve_calendar_presence,
    resolve_presence,
)

# ---------------------------------------------------------------------------
# Helper: build a timed event dict (ISO datetime with offset)
# ---------------------------------------------------------------------------


def _timed_event(start: str, end: str, summary: str = "Event") -> dict:
    """Build a calendar event dict with timed start/end ISO strings."""
    return {"start": start, "end": end, "summary": summary}


def _allday_event(
    start_date: str, end_date: str, summary: str = "Event"
) -> dict:
    """Build a calendar event dict with date-only (all-day) strings."""
    return {"start": start_date, "end": end_date, "summary": summary}


# ---------------------------------------------------------------------------
# Task 1 — constants
# ---------------------------------------------------------------------------


def test_constants():
    """PRESENCE_CALENDAR == 'calendar' and DEFAULT_PREHEAT_LEAD_MINUTES == 60."""
    assert PRESENCE_CALENDAR == "calendar"
    assert DEFAULT_PREHEAT_LEAD_MINUTES == 60


# ---------------------------------------------------------------------------
# Task 2 — resolve_calendar_presence() helper
# ---------------------------------------------------------------------------


@freeze_time("2026-06-01 10:00:00 UTC")
def test_calendar_mode_absent_during_event():
    """Active event, event_means=absent, preheat=60 → absent (False).

    Event 08:00–17:00 +02:00 (UTC 06:00–15:00). Frozen now is UTC 10:00
    (inside the event). Event ends at UTC 15:00, 300 min from now — beyond
    the 60-min lead → still absent.
    """
    now = dt_util.now()
    events = [
        _timed_event(
            "2026-06-01T08:00:00+02:00",
            "2026-06-01T17:00:00+02:00",
        )
    ]
    result = resolve_calendar_presence(
        events,
        "absent",
        now,
        preheat_lead_minutes=60,
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result is False


@freeze_time("2026-06-01 12:00:00 UTC")
def test_calendar_mode_present_no_event():
    """No active events, event_means=absent → present (True).

    No event = person is not absent → present.
    """
    now = dt_util.now()
    result = resolve_calendar_presence(
        [],
        "absent",
        now,
        preheat_lead_minutes=60,
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result is True


@freeze_time("2026-06-01 12:00:00 UTC")
def test_calendar_mode_present_during_event_when_means_present():
    """Active event, event_means=present → present (True)."""
    now = dt_util.now()
    events = [
        _timed_event(
            "2026-06-01T08:00:00+00:00",
            "2026-06-01T17:00:00+00:00",
        )
    ]
    result = resolve_calendar_presence(
        events,
        "present",
        now,
        preheat_lead_minutes=60,
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result is True


@freeze_time("2026-06-01 12:00:00 UTC")
def test_calendar_mode_absent_no_event_when_means_present():
    """No active events, event_means=present → absent (False).

    No event = person is not present when event_means=present.
    """
    now = dt_util.now()
    result = resolve_calendar_presence(
        [],
        "present",
        now,
        preheat_lead_minutes=60,
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result is False


@freeze_time("2026-06-01 14:00:00 UTC")
def test_absent_for_full_event_duration():
    """Active event → absent for its entire duration, no arrival pre-heat.

    Now = UTC 14:00. Event ends 15:00 UTC.
    Person is absent until 15:00 regardless of preheat_lead_minutes.
    """
    now = dt_util.now()
    events = [
        _timed_event(
            "2026-06-01T08:00:00+00:00",
            "2026-06-01T15:00:00+00:00",
        )
    ]
    result = resolve_calendar_presence(
        events,
        "absent",
        now,
        preheat_lead_minutes=60,
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result is False


@freeze_time("2026-06-01 14:00:00 UTC")
def test_preheat_no_trigger_before_boundary():
    """Active event ends 61 min from now → still absent (False).

    Now = UTC 14:00. Event ends 15:01 UTC. lead=60 min.
    Active event with 61 min remaining → absent (no arrival pre-heat).
    """
    now = dt_util.now()
    events = [
        _timed_event(
            "2026-06-01T08:00:00+00:00",
            "2026-06-01T15:01:00+00:00",  # ends 61 min from now
        )
    ]
    result = resolve_calendar_presence(
        events,
        "absent",
        now,
        preheat_lead_minutes=60,
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result is False


@freeze_time("2026-06-01 12:00:00 UTC")
def test_allday_event_handling():
    """All-day event with DATE-only strings: no TypeError, returns False.

    All-day event for 2026-06-01. Now = UTC 12:00.
    event_means=absent → person is absent during the event (False).
    Must not raise TypeError on naive/aware comparison.
    """
    now = dt_util.now()
    events = [_allday_event("2026-06-01", "2026-06-02")]
    result = resolve_calendar_presence(
        events,
        "absent",
        now,
        preheat_lead_minutes=60,
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result is False  # active all-day event, event_means=absent


# ---------------------------------------------------------------------------
# Task 3 — period state "calendar" inside resolve_presence()
# ---------------------------------------------------------------------------


def _make_calendar_schedule(entity_id: str, event_means: str) -> dict:
    """Build a 7-day person schedule with one period per day: state='calendar'."""
    day_periods = [
        {
            "start": "00:00",
            "state": "calendar",
            "calendar_config": {
                "entity_id": entity_id,
                "event_means": event_means,
            },
        }
    ]
    return {
        day: list(day_periods)
        for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }


@freeze_time("2026-06-01 12:00:00 UTC")  # 2026-06-01 is a Monday
def test_calendar_period_state_resolves():
    """Period state 'calendar' resolves via calendar_cache.

    Active event in cache → absent (False).
    Empty cache for entity → present (True).
    """
    now = dt_util.now()
    entity_id = "calendar.x"
    active_event = _timed_event(
        "2026-06-01T08:00:00+00:00",
        "2026-06-01T17:00:00+00:00",
    )
    person_config = {
        "mode": "scheduled",
        "schedule": _make_calendar_schedule(entity_id, "absent"),
    }

    # With active event → person is absent
    result_absent = resolve_presence(
        person_config,
        now,
        calendar_cache={entity_id: [active_event]},
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result_absent is False

    # With empty events → person is present (no event = not absent)
    result_present = resolve_presence(
        person_config,
        now,
        calendar_cache={entity_id: []},
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result_present is True


@freeze_time("2026-06-01 12:00:00 UTC")
def test_calendar_period_state_missing_cache_defaults_absent():
    """Period state 'calendar' with entity_id not in cache → treats as no events.

    event_means=absent, no events → present. No exception raised.
    """
    now = dt_util.now()
    entity_id = "calendar.x"
    person_config = {
        "mode": "scheduled",
        "schedule": _make_calendar_schedule(entity_id, "absent"),
    }
    # entity_id not in calendar_cache (empty dict)
    result = resolve_presence(
        person_config,
        now,
        calendar_cache={},
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result is True  # no events → not absent → present


@freeze_time("2026-06-01 12:00:00 UTC")
def test_present_absent_periods_unchanged():
    """Regression: present/absent period states still work without calendar_cache."""
    now = dt_util.now()
    person_present = {
        "mode": "scheduled",
        "schedule": {
            day: [{"start": "00:00", "state": "present"}]
            for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        },
    }
    person_absent = {
        "mode": "scheduled",
        "schedule": {
            day: [{"start": "00:00", "state": "absent"}]
            for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        },
    }

    # Without calendar_cache (default None) — must not raise
    assert resolve_presence(person_present, now) is True
    assert resolve_presence(person_absent, now) is False

    # With calendar_cache (should not affect non-calendar periods)
    assert resolve_presence(person_present, now, calendar_cache={}) is True
    assert resolve_presence(person_absent, now, calendar_cache={}) is False


# ---------------------------------------------------------------------------
# Helper for integration tests — minimal runtime config with persons
# ---------------------------------------------------------------------------


ALL_DAYS_NORMAL_PROGRAM: dict = {
    day: [{"start": "00:00", "mode": "normal"}]
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
}


def _make_calendar_runtime_config(persons_config: dict) -> dict:
    """Build a minimal runtime_config with calendar-mode persons."""
    return {
        "version": 2,
        "global_mode": MODE_TIME_PROGRAM_PRESENCES,
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "global_time_program": ALL_DAYS_NORMAL_PROGRAM,
        "rooms": {},
        "persons": persons_config,
        "zones": {},
        "default_zone_name": "Home",
    }


def _calendar_person_config(
    entity_id: str,
    event_means: str = "absent",
    room_ids: list | None = None,
) -> dict:
    """Build a calendar-mode person configuration dict."""
    return {
        "mode": PRESENCE_CALENDAR,
        "room_ids": room_ids or [],
        "calendar_config": {
            "entity_id": entity_id,
            "event_means": event_means,
        },
        "preheat_lead_minutes": DEFAULT_PREHEAT_LEAD_MINUTES,
    }


# ---------------------------------------------------------------------------
# Task 4 — _prefetch_calendars: cache deduplication and reset
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-06-01 12:00:00 UTC")
async def test_calendar_cache_deduplication(hass):
    """Two calendar-mode persons sharing the same calendar entity → one get_events.

    D-13: per-cycle cache. One get_events call per unique entity_id.
    The coordinator must issue exactly one ServiceCall even when two persons
    both reference 'calendar.shared'.
    """
    shared_cal = "calendar.shared"
    mock_events = [
        {
            "start": "2026-06-01T08:00:00+00:00",
            "end": "2026-06-01T17:00:00+00:00",
            "summary": "School",
        }
    ]

    calendar_calls = async_mock_service(
        hass,
        "calendar",
        "get_events",
        response={shared_cal: {"events": mock_events}},
        supports_response=SupportsResponse.ONLY,
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Two persons both referencing the same calendar entity
    persons_config = {
        "person.alice": _calendar_person_config(shared_cal),
        "person.bob": _calendar_person_config(shared_cal),
    }
    entry.runtime_data.runtime_config = _make_calendar_runtime_config(
        persons_config
    )

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    # D-13: exactly one get_events call for the shared entity (dedup)
    assert len(calendar_calls) == 1


@pytest.mark.freeze_time("2026-06-01 12:00:00 UTC")
async def test_calendar_cache_reset_per_cycle(hass):
    """Cache is repopulated each cycle — no stale entries carried forward.

    Two async_evaluate calls → 2 total get_events calls (one per cycle).
    D-13: _calendar_cache reset at start of every cycle.
    """
    cal_id = "calendar.person_a"
    mock_events = [
        {
            "start": "2026-06-01T08:00:00+00:00",
            "end": "2026-06-01T17:00:00+00:00",
            "summary": "Work",
        }
    ]

    calendar_calls = async_mock_service(
        hass,
        "calendar",
        "get_events",
        response={cal_id: {"events": mock_events}},
        supports_response=SupportsResponse.ONLY,
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    persons_config = {
        "person.alice": _calendar_person_config(cal_id),
    }
    entry.runtime_data.runtime_config = _make_calendar_runtime_config(
        persons_config
    )

    # First evaluate cycle
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    # Second evaluate cycle
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    # Two cycles → 2 total get_events calls (cache resets each cycle)
    assert len(calendar_calls) == 2


@pytest.mark.freeze_time("2026-06-01 12:00:00 UTC")
async def test_calendar_fallback_on_error(hass, caplog):
    """HomeAssistantError from get_events → empty list in cache + one WARNING.

    D-04: fallback to absent on calendar entity error; no log spam.
    """
    cal_id = "calendar.missing"

    async_mock_service(
        hass,
        "calendar",
        "get_events",
        raise_exception=HomeAssistantError("No entities matched"),
        supports_response=SupportsResponse.ONLY,
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    persons_config = {
        "person.alice": _calendar_person_config(cal_id),
    }
    entry.runtime_data.runtime_config = _make_calendar_runtime_config(
        persons_config
    )

    with caplog.at_level(logging.WARNING):
        await entry.runtime_data.coordinator.async_evaluate()
        await hass.async_block_till_done()

    # D-04: _calendar_cache[eid] == [] on error (fallback to absent)
    assert entry.runtime_data.coordinator._calendar_cache[cal_id] == []

    # D-04: exactly one WARNING for the failing calendar entity
    warning_records = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and cal_id in r.message
    ]
    assert len(warning_records) == 1


# ---------------------------------------------------------------------------
# Task 5 — calendar mode and period states in coordinator presence methods
# ---------------------------------------------------------------------------


@pytest.mark.freeze_time("2026-06-01 12:00:00 UTC")
async def test_calendar_mode_person_present_in_evaluate(hass):
    """Calendar-mode person: event active → absent; no event → present.

    Two async_evaluate calls on the same coordinator with different mock
    responses confirm cache-driven presence resolution each cycle.

    Cycle 1: event active (event_means=absent) → person NOT in present list.
    Cycle 2: no events (event_means=absent) → person IS in present list.
    """
    cal_id = "calendar.person_cal"
    active_event = {
        "start": "2026-06-01T08:00:00+00:00",
        "end": "2026-06-01T17:00:00+00:00",
        "summary": "Away",
    }

    # Cycle 1: mocked response has one active event → person absent
    calendar_calls = async_mock_service(
        hass,
        "calendar",
        "get_events",
        response={cal_id: {"events": [active_event]}},
        supports_response=SupportsResponse.ONLY,
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    persons_config = {
        "person.alice": _calendar_person_config(cal_id, event_means="absent"),
    }
    entry.runtime_data.runtime_config = _make_calendar_runtime_config(
        persons_config
    )

    # Cycle 1: active event → person is absent
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    assert (
        "person.alice"
        not in entry.runtime_data.coordinator._last_present_persons
    ), "Active absent-event → person must NOT be in present list"

    # Cycle 2: swap the mock to return no events → person becomes present
    # Re-register the service with an empty event list. Remove the existing
    # handler first via the public API, then register the new one.
    calendar_calls.clear()
    hass.services.async_remove("calendar", "get_events")
    async_mock_service(
        hass,
        "calendar",
        "get_events",
        response={cal_id: {"events": []}},
        supports_response=SupportsResponse.ONLY,
    )

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    # No events → event_means=absent → not absent → person IS present
    assert (
        "person.alice" in entry.runtime_data.coordinator._last_present_persons
    ), "No events + event_means=absent → person must be present"


@pytest.mark.freeze_time("2026-06-01 12:00:00 UTC")
async def test_calendar_period_overrides_rooms(hass):
    """Calendar period state in a scheduled-mode person drives room temp via cache.

    Person has a scheduled mode, but the active period state is "calendar".
    The calendar entity returns an event → person is absent for the period →
    room is heated at reduced temperature.
    With empty events → person is present → room at Normal temperature.
    (Only tests that _apply_presence_overrides consumed the cache, not stale data.)
    """
    cal_id = "calendar.schedule_cal"
    active_event = {
        "start": "2026-06-01T08:00:00+00:00",
        "end": "2026-06-01T17:00:00+00:00",
        "summary": "Away",
    }

    # Schedule: all day is a "calendar" period state
    calendar_period_schedule = {
        day: [
            {
                "start": "00:00",
                "state": "calendar",
                "calendar_config": {
                    "entity_id": cal_id,
                    "event_means": "absent",
                },
            }
        ]
        for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }

    # Seed a climate entity in HA state for room "bedroom"
    hass.states.async_set("climate.bedroom_trv", "heat", {"temperature": 15.0})

    calendar_calls = async_mock_service(
        hass,
        "calendar",
        "get_events",
        response={cal_id: {"events": [active_event]}},
        supports_response=SupportsResponse.ONLY,
    )
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Person in scheduled mode with calendar period state, associated with bedroom
    persons_config = {
        "person.alice": {
            "mode": "scheduled",
            "room_ids": ["bedroom"],
            "schedule": calendar_period_schedule,
            "preheat_lead_minutes": DEFAULT_PREHEAT_LEAD_MINUTES,
        }
    }
    runtime_config = _make_calendar_runtime_config(persons_config)
    entry.runtime_data.runtime_config = runtime_config
    entry.runtime_data.rooms = {"bedroom": ["climate.bedroom_trv"]}

    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    # D-13: get_events was called (cache was used — not stale)
    assert len(calendar_calls) >= 1

    # Person should be absent (active event, event_means=absent)
    assert (
        "person.alice"
        not in entry.runtime_data.coordinator._last_present_persons
    )


# ---------------------------------------------------------------------------
# Plan 03 — WS persistence tests (set_person_config calendar fields)
# ---------------------------------------------------------------------------


async def _setup_ws_entry(hass) -> MockConfigEntry:
    """Set up the integration and return the config entry (no mocked services).

    Mirrors _setup_entry in test_websocket.py for WS-level tests.
    """
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_ws_persists_calendar_config(hass, hass_ws_client):
    """set_person_config with calendar_config persists entity_id + event_means.

    D-08: set_person_config persists calendar_config {entity_id, event_means}.
    D-09: additive sparse-merge — absent for non-Calendar persons.
    Send calendar_config with mode=calendar; assert persisted to runtime_config.
    """
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(
        hass,
        "calendar",
        "get_events",
        response={},
        supports_response=SupportsResponse.ONLY,
    )

    entry = await _setup_ws_entry(hass)
    pid = "person.alice"

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": pid,
            "config": {
                "mode": "calendar",
                "calendar_config": {
                    "entity_id": "calendar.x",
                    "event_means": "present",
                },
            },
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    persisted = entry.runtime_data.runtime_config.get("persons", {}).get(
        pid, {}
    )
    assert persisted.get("calendar_config") == {
        "entity_id": "calendar.x",
        "event_means": "present",
    }


async def test_ws_persists_preheat_lead_minutes(hass, hass_ws_client):
    """set_person_config with legacy preheat_lead_minutes=90 is mapped to
    wakeup_advance_minutes (D-02 rename, backward-compat legacy key).

    D-02: preheat_lead_minutes is renamed to wakeup_advance_minutes at the
    WS handler level; sending the old key persists the value under the new key.
    """
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = await _setup_ws_entry(hass)
    pid = "person.bob"

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": pid,
            "config": {"preheat_lead_minutes": 90},
        }
    )
    msg = await client.receive_json()

    assert msg["success"] is True
    persisted = entry.runtime_data.runtime_config.get("persons", {}).get(
        pid, {}
    )
    # D-02: legacy key is mapped → wakeup_advance_minutes stored, old key absent
    assert persisted.get("wakeup_advance_minutes") == 90
    assert "preheat_lead_minutes" not in persisted


async def test_ws_rejects_non_calendar_entity_id(hass, hass_ws_client):
    """set_person_config with calendar_config.entity_id='light.*' not persisted.

    T-11-06 (ASVS V5): entity_id not starting with 'calendar.' is rejected
    before persistence. The invalid calendar_config must not appear in
    runtime_config.persons; the person's calendar_config must remain absent
    or unchanged.
    """
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    entry = await _setup_ws_entry(hass)
    pid = "person.alice"

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_person_config",
            "person_id": pid,
            "config": {
                "calendar_config": {
                    "entity_id": "light.kitchen",
                    "event_means": "absent",
                },
            },
        }
    )
    # Consume the WS response (success or error — either is acceptable).
    await client.receive_json()

    # Command may succeed (dropping the invalid key) or return an error;
    # the critical assertion is that light.kitchen is not persisted.
    persisted = entry.runtime_data.runtime_config.get("persons", {}).get(
        pid, {}
    )
    cal_cfg = persisted.get("calendar_config", {})
    bad_entity = cal_cfg.get("entity_id", "")
    assert not bad_entity.startswith("light."), (
        f"Invalid entity_id 'light.kitchen' was persisted: {cal_cfg!r}"
    )


# ---------------------------------------------------------------------------
# Gap handling mode tests
# ---------------------------------------------------------------------------

_TZ = "+02:00"


def _ev(start: str, end: str) -> dict:
    """Build a timed event with the test timezone offset."""
    return {"start": f"{start}{_TZ}", "end": f"{end}{_TZ}"}


def _now(ts: str) -> datetime.datetime:
    """Return an aware datetime for the given ISO timestamp."""
    return datetime.datetime.fromisoformat(f"{ts}{_TZ}")


def test_gap_exact_present_in_gap():
    """gap_handling='exact': gap between events → person is present."""
    events = [
        _ev("2026-06-02T09:00:00", "2026-06-02T10:00:00"),
        _ev("2026-06-02T11:00:00", "2026-06-02T13:00:00"),
    ]
    now = _now("2026-06-02T10:30:00")
    result = resolve_calendar_presence(
        events, "absent", now, gap_handling="exact"
    )
    assert result is True, "exact: gap should be treated as present"


def test_gap_day_span_absent_in_gap():
    """gap_handling='day_span': gap between events → person stays absent."""
    events = [
        _ev("2026-06-02T09:00:00", "2026-06-02T10:00:00"),
        _ev("2026-06-02T11:00:00", "2026-06-02T13:00:00"),
    ]
    now = _now("2026-06-02T10:30:00")
    result = resolve_calendar_presence(
        events, "absent", now, gap_handling="day_span"
    )
    assert result is False, "day_span: gap should be treated as absent"


def test_gap_day_span_present_before_first_event():
    """gap_handling='day_span': before first event → person is present."""
    events = [
        _ev("2026-06-02T09:00:00", "2026-06-02T10:00:00"),
        _ev("2026-06-02T11:00:00", "2026-06-02T13:00:00"),
    ]
    now = _now("2026-06-02T08:00:00")
    result = resolve_calendar_presence(
        events, "absent", now, gap_handling="day_span"
    )
    assert result is True, "day_span: before first event → present"


def test_gap_day_span_present_after_last_event():
    """gap_handling='day_span': after last event → person is present."""
    events = [
        _ev("2026-06-02T09:00:00", "2026-06-02T10:00:00"),
        _ev("2026-06-02T11:00:00", "2026-06-02T13:00:00"),
    ]
    now = _now("2026-06-02T14:00:00")
    result = resolve_calendar_presence(
        events, "absent", now, gap_handling="day_span"
    )
    assert result is True, "day_span: after last event → present"


def test_gap_threshold_absent_short_gap():
    """gap_handling='threshold': gap shorter than threshold → person stays absent."""
    events = [
        _ev("2026-06-02T09:00:00", "2026-06-02T10:00:00"),
        _ev("2026-06-02T10:20:00", "2026-06-02T12:00:00"),
    ]
    now = _now("2026-06-02T10:10:00")  # 10-min gap, threshold=30
    result = resolve_calendar_presence(
        events,
        "absent",
        now,
        gap_handling="threshold",
        gap_threshold_minutes=30,
    )
    assert result is False, "threshold: short gap (10 min < 30) → absent"


def test_gap_threshold_present_long_gap():
    """gap_handling='threshold': gap longer than threshold → person returns home."""
    events = [
        _ev("2026-06-02T09:00:00", "2026-06-02T10:00:00"),
        _ev("2026-06-02T11:30:00", "2026-06-02T13:00:00"),
    ]
    now = _now("2026-06-02T10:45:00")  # 90-min gap, threshold=30
    result = resolve_calendar_presence(
        events,
        "absent",
        now,
        gap_handling="threshold",
        gap_threshold_minutes=30,
    )
    assert result is True, "threshold: long gap (90 min > 30) → present"


def test_gap_threshold_in_event_always_absent():
    """gap_handling='threshold': inside an active event → always absent."""
    events = [
        _ev("2026-06-02T09:00:00", "2026-06-02T10:00:00"),
    ]
    now = _now("2026-06-02T09:30:00")
    result = resolve_calendar_presence(
        events,
        "absent",
        now,
        gap_handling="threshold",
        gap_threshold_minutes=0,
    )
    assert result is False, "threshold: inside event → absent"
