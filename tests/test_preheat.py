# SPDX-License-Identifier: MIT
"""Unit tests for predictive pre-heat foundation (Phase 12, Plan 01).

Tests cover:
- next_occupied_at() for single-schedule, even_odd, calendar, ha, force modes
- wakeup_advance_minutes migration in storage.async_load

All next_occupied_at tests are pure Python (no hass fixture).
Migration tests use a mocked Store pattern mirroring test_storage.py.
"""

import datetime


from custom_components.climate_manager.schedule import next_occupied_at


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

TZ = datetime.timezone.utc


def _dt(year, month, day, hour, minute, tz=TZ):
    """Build a timezone-aware datetime."""
    return datetime.datetime(year, month, day, hour, minute, tzinfo=tz)


def _schedule(state_by_day: dict[str, list[dict]]) -> dict:
    """Build a schedule dict for a single person with given day states.

    Produces a full 7-day schedule; days not listed default to absent.
    """
    base = {
        "mon": [],
        "tue": [],
        "wed": [],
        "thu": [],
        "fri": [],
        "sat": [],
        "sun": [],
    }
    base.update(state_by_day)
    return base


# ---------------------------------------------------------------------------
# Task 2: next_occupied_at() tests
# ---------------------------------------------------------------------------


def test_next_occupied_scheduled_single():
    """Single-schedule person absent now, present at 07:00.

    now = Monday 2026-06-01 06:00 UTC (before 07:00 present period).
    Expected: today's 07:00 UTC as aware datetime strictly > now.
    """
    now = _dt(2026, 6, 1, 6, 0)  # Monday
    person = {
        "mode": "scheduled",
        "schedule_type": "single",
        "schedule": _schedule(
            {
                "mon": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "07:00", "state": "present"},
                    {"start": "22:00", "state": "absent"},
                ]
            }
        ),
    }
    result = next_occupied_at(person, now)
    assert result is not None
    assert result.tzinfo is not None
    assert result > now
    assert result.hour == 7
    assert result.minute == 0


def test_next_occupied_even_odd():
    """even_odd person: schedule_even for even weeks, schedule_odd for odd.

    now = Wednesday 2026-06-03 23:00 UTC (week 23, odd).
    Thursday 2026-06-04 is also week 23 (odd) — uses schedule_odd (present 08:00).
    Even schedule_even would return 09:00 on even weeks.
    Verify: result is 08:00 on Thursday 2026-06-04 (week 23, odd → schedule_odd).
    """
    # 2026-06-03 is ISO week 23 (odd → parity=1 → schedule_odd)
    # 2026-06-04 is ISO week 23 (odd → parity=1 → schedule_odd)
    now = _dt(2026, 6, 3, 23, 0)  # Wednesday 23:00
    person = {
        "mode": "scheduled",
        "schedule_type": "even_odd",
        "schedule_even": _schedule(
            {
                "thu": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "09:00", "state": "present"},
                ]
            }
        ),
        "schedule_odd": _schedule(
            {
                "thu": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "08:00", "state": "present"},
                ]
            }
        ),
    }
    result = next_occupied_at(person, now)
    assert result is not None
    assert result.tzinfo is not None
    assert result > now
    # 2026-06-04 (Thursday) — ISO week 23 is odd → schedule_odd → 08:00
    assert result.year == 2026
    assert result.month == 6
    assert result.day == 4
    assert result.hour == 8
    assert result.minute == 0


def test_next_occupied_even_odd_crosses_week_boundary():
    """even_odd: week boundary correctly selects schedule by TARGET day's week.

    now = Sunday 2026-06-07 23:30 UTC (ISO week 23, odd).
    Monday 2026-06-08 is ISO week 24 (even) → should use schedule_even.
    """
    now = _dt(2026, 6, 7, 23, 30)  # Sunday 23:30, week 23 (odd)
    person = {
        "mode": "scheduled",
        "schedule_type": "even_odd",
        "schedule_even": _schedule(
            {
                "mon": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "07:00", "state": "present"},
                ]
            }
        ),
        "schedule_odd": _schedule(
            {
                "mon": [
                    {"start": "00:00", "state": "absent"},
                    {"start": "09:00", "state": "present"},
                ]
            }
        ),
    }
    result = next_occupied_at(person, now)
    assert result is not None
    # 2026-06-08 (Monday) is ISO week 24 (even) → schedule_even → 07:00
    assert result.day == 8
    assert result.hour == 7


def test_next_occupied_calendar_absent():
    """Calendar mode, event_means=absent, currently inside an event.

    Returns the event's end datetime (person returns home when event ends).
    Event: 08:00–17:00 UTC. now = 10:00 UTC (inside event).
    Expected: event end = 17:00 UTC.
    """
    now = _dt(2026, 6, 1, 10, 0)
    event_end = "2026-06-01T17:00:00+00:00"
    person = {
        "mode": "calendar",
        "calendar_config": {
            "entity_id": "calendar.work",
            "event_means": "absent",
        },
    }
    calendar_cache = {
        "calendar.work": [
            {
                "start": "2026-06-01T08:00:00+00:00",
                "end": event_end,
                "summary": "Work",
            }
        ]
    }
    result = next_occupied_at(person, now, calendar_cache=calendar_cache)
    assert result is not None
    assert result.tzinfo is not None
    assert result > now
    assert result.hour == 17
    assert result.minute == 0


def test_next_occupied_calendar_present():
    """Calendar mode, event_means=present.

    Returns the start of the next event.
    now = 06:00 UTC. Event starts 09:00 UTC.
    Expected: event start = 09:00 UTC.
    """
    now = _dt(2026, 6, 1, 6, 0)
    person = {
        "mode": "calendar",
        "calendar_config": {
            "entity_id": "calendar.gym",
            "event_means": "present",
        },
    }
    calendar_cache = {
        "calendar.gym": [
            {
                "start": "2026-06-01T09:00:00+00:00",
                "end": "2026-06-01T10:00:00+00:00",
                "summary": "Gym",
            }
        ]
    }
    result = next_occupied_at(person, now, calendar_cache=calendar_cache)
    assert result is not None
    assert result.tzinfo is not None
    assert result > now
    assert result.hour == 9
    assert result.minute == 0


def test_next_occupied_ha_returns_none():
    """Mode 'ha' → next_occupied_at returns None."""
    now = _dt(2026, 6, 1, 10, 0)
    person = {"mode": "ha"}
    result = next_occupied_at(person, now)
    assert result is None


def test_next_occupied_force_modes_return_none():
    """force_present and force_absent → next_occupied_at returns None."""
    now = _dt(2026, 6, 1, 10, 0)
    for mode in ("force_present", "force_absent"):
        result = next_occupied_at({"mode": mode}, now)
        assert result is None, f"Expected None for mode={mode}"


def test_next_occupied_no_present_period_returns_none():
    """Scheduled person never present in the next 7 days → None."""
    now = _dt(2026, 6, 1, 10, 0)  # Monday
    # All periods are absent for all 7 days
    person = {
        "mode": "scheduled",
        "schedule_type": "single",
        "schedule": _schedule(
            {
                "mon": [{"start": "00:00", "state": "absent"}],
                "tue": [{"start": "00:00", "state": "absent"}],
                "wed": [{"start": "00:00", "state": "absent"}],
                "thu": [{"start": "00:00", "state": "absent"}],
                "fri": [{"start": "00:00", "state": "absent"}],
                "sat": [{"start": "00:00", "state": "absent"}],
                "sun": [{"start": "00:00", "state": "absent"}],
            }
        ),
    }
    result = next_occupied_at(person, now)
    assert result is None


# ---------------------------------------------------------------------------
# Task 3: wakeup_advance_minutes migration tests
# ---------------------------------------------------------------------------


async def test_wakeup_advance_migration(hass):
    """Stored preheat_lead_minutes=90 and no wakeup_advance_minutes.

    After async_load: wakeup_advance_minutes=90, preheat_lead_minutes absent.
    """
    from custom_components.climate_manager.storage import ClimateManagerStore

    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "persons": {
                "person.alice": {
                    "mode": "scheduled",
                    "preheat_lead_minutes": 90,
                }
            }
        }
    )
    result = await store.async_load()
    alice = result["persons"]["person.alice"]
    assert alice.get("wakeup_advance_minutes") == 90
    assert "preheat_lead_minutes" not in alice


async def test_wakeup_advance_migration_noop_when_new_key_present(hass):
    """Both keys present: wakeup_advance_minutes kept, preheat_lead_minutes removed.

    The existing wakeup_advance_minutes value must NOT be overwritten.
    """
    from custom_components.climate_manager.storage import ClimateManagerStore

    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "persons": {
                "person.bob": {
                    "mode": "scheduled",
                    "wakeup_advance_minutes": 45,
                    "preheat_lead_minutes": 90,
                }
            }
        }
    )
    result = await store.async_load()
    bob = result["persons"]["person.bob"]
    assert bob.get("wakeup_advance_minutes") == 45
    assert "preheat_lead_minutes" not in bob


async def test_wakeup_advance_migration_absent_key(hass):
    """Neither key present: no wakeup_advance_minutes added."""
    from custom_components.climate_manager.storage import ClimateManagerStore

    store = ClimateManagerStore(hass)
    await store._store.async_save(
        {
            "persons": {
                "person.carol": {
                    "mode": "scheduled",
                }
            }
        }
    )
    result = await store.async_load()
    carol = result["persons"]["person.carol"]
    assert "wakeup_advance_minutes" not in carol
    assert "preheat_lead_minutes" not in carol
