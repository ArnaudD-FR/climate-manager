"""Tests for calendar presence resolution — pure Python unit tests.

Tests for:
- Calendar constants (PRESENCE_CALENDAR, DEFAULT_PREHEAT_LEAD_MINUTES)
- resolve_calendar_presence() helper logic
- Period state "calendar" inside resolve_presence()

No hass fixture needed for Tasks 1-3 (pure logic). The dt_util import
is from homeassistant.util.dt which is a pure utility (no HA runtime).
"""

from freezegun import freeze_time
from homeassistant.util import dt as dt_util

from custom_components.climate_manager.const import (
    DEFAULT_PREHEAT_LEAD_MINUTES,
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
def test_preheat_triggers_at_boundary():
    """Active event ends exactly 60 min from now → present (pre-heat).

    Now = UTC 14:00. Event ends 15:00 UTC. lead=60 min.
    event_end (15:00) <= now+lead (15:00) → True (pre-heat triggered).
    """
    now = dt_util.now()
    events = [
        _timed_event(
            "2026-06-01T08:00:00+00:00",
            "2026-06-01T15:00:00+00:00",  # ends 60 min from now (UTC 14:00)
        )
    ]
    result = resolve_calendar_presence(
        events,
        "absent",
        now,
        preheat_lead_minutes=60,
        start_of_local_day=dt_util.start_of_local_day,
    )
    assert result is True


@freeze_time("2026-06-01 14:00:00 UTC")
def test_preheat_no_trigger_before_boundary():
    """Active event ends 61 min from now → still absent (False).

    Now = UTC 14:00. Event ends 15:01 UTC. lead=60 min.
    event_end (15:01) > now+lead (15:00) → False (not yet pre-heat time).
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
