# SPDX-License-Identifier: MIT
"""Tests for person.py — Person/PersonMode presence evaluation + log emission.

Scenarios:
- Person.evaluate(ctx) emits one INFO record matching
  `presence | person=%s home=%s reason=%s` on a _last_home flip (OBS-01, D-05).
- No log emitted on repeated same value (anti-spam via _last_home, D-10).
- reason field is the mode name only per D-08:
  scheduled / ha / calendar / force_present / force_absent.
- Short-name strip (D-01): person.alice → person=alice in log output.
- Second evaluate() call on the same cycle returns the cached value from
  ctx._presence_cache without re-running the mode (D-02, D-05).
"""

import logging


from custom_components.climate_manager.person import (
    Person,
    PersonModeForceAbsent,
    PersonModeForcePresent,
)


PERSON_LOGGER = "custom_components.climate_manager.person"


def test_person_evaluate_emits_info_on_home_flip(caplog):
    """Person.evaluate emits one INFO record on _last_home flip (OBS-01).
    Format: `presence | person=<name> home=<bool> reason=<source>`
    """
    person = Person(person_id="person.alice")
    # _last_home starts None — first evaluate always logs.

    # Set up a ForcePresent mode (always returns True).
    mode = PersonModeForcePresent(person)
    person._mode = mode

    import datetime
    from unittest.mock import MagicMock

    ctx = MagicMock()
    ctx._presence_cache = {}
    ctx.now = datetime.datetime.now()

    with caplog.at_level(logging.INFO, logger=PERSON_LOGGER):
        person.evaluate_sync(ctx)

    records = [r for r in caplog.records if r.name == PERSON_LOGGER]
    assert len(records) == 1, (
        f"Expected exactly one INFO record on first evaluate, "
        f"got {len(records)}: {[r.getMessage() for r in records]}"
    )
    msg = records[0].getMessage()
    assert "presence | person=" in msg
    assert "home=" in msg
    assert "reason=" in msg
    # D-01: person.alice → alice
    assert "person=alice" in msg
    assert "home=True" in msg
    # D-08: reason is mode name only
    assert "reason=force_present" in msg


def test_person_no_log_on_same_home_value(caplog):
    """Anti-spam (D-10): repeated evaluate with same _last_home value emits
    no additional INFO record.
    """
    person = Person(person_id="person.bob")
    person._last_home = True  # already logged as home=True

    mode = PersonModeForcePresent(person)
    person._mode = mode

    import datetime
    from unittest.mock import MagicMock

    ctx = MagicMock()
    ctx._presence_cache = {}
    ctx.now = datetime.datetime.now()

    with caplog.at_level(logging.INFO, logger=PERSON_LOGGER):
        person.evaluate_sync(ctx)

    records = [r for r in caplog.records if r.name == PERSON_LOGGER]
    assert len(records) == 0, (
        f"Expected no log on repeated same value, got: "
        f"{[r.getMessage() for r in records]}"
    )


def test_person_name_strip_d01(caplog):
    """D-01: person.alice logs as person=alice, not person=person.alice."""
    person = Person(person_id="person.alice")
    mode = PersonModeForceAbsent(person)
    person._mode = mode

    import datetime
    from unittest.mock import MagicMock

    ctx = MagicMock()
    ctx._presence_cache = {}
    ctx.now = datetime.datetime.now()

    with caplog.at_level(logging.INFO, logger=PERSON_LOGGER):
        person.evaluate_sync(ctx)

    records = [r for r in caplog.records if r.name == PERSON_LOGGER]
    assert records, "Expected at least one INFO record"
    msg = records[0].getMessage()
    assert "person=alice" in msg, (
        f"Expected D-01 short name 'person=alice', got: {msg!r}"
    )
    assert "person=person.alice" not in msg


def test_person_reason_is_mode_name_only(caplog):
    """D-08: reason field is the mode name only — no extra detail.
    Accepted values: scheduled / ha / calendar / force_present / force_absent.
    """
    for mode_cls, expected_reason in [
        (PersonModeForcePresent, "force_present"),
        (PersonModeForceAbsent, "force_absent"),
    ]:
        person = Person(person_id="person.charlie")
        person._mode = mode_cls(person)

        import datetime
        from unittest.mock import MagicMock

        ctx = MagicMock()
        ctx._presence_cache = {}
        ctx.now = datetime.datetime.now()

        caplog.clear()
        with caplog.at_level(logging.INFO, logger=PERSON_LOGGER):
            person.evaluate_sync(ctx)

        records = [r for r in caplog.records if r.name == PERSON_LOGGER]
        if records:
            msg = records[0].getMessage()
            assert f"reason={expected_reason}" in msg, (
                f"Expected 'reason={expected_reason}' in {msg!r}"
            )


def test_person_presence_cache_dedup(caplog):
    """Person.evaluate returns cached value from ctx._presence_cache on second
    call without re-running the mode (D-02 / D-05 invariant).
    """
    person = Person(person_id="person.dana")
    mode = PersonModeForcePresent(person)
    person._mode = mode

    import datetime
    from unittest.mock import MagicMock

    ctx = MagicMock()
    ctx._presence_cache = {}
    ctx.now = datetime.datetime.now()

    # First call: populates the cache.
    result1 = person.evaluate_sync(ctx)
    assert result1 is True
    assert "person.dana" in ctx._presence_cache

    # Patch mode.is_present to a sentinel that should NOT be called on cache hit.
    call_count = 0

    def counting_is_present(c):
        nonlocal call_count
        call_count += 1
        return True

    mode.is_present = counting_is_present  # type: ignore[method-assign]

    # Second call: must return cached value without calling is_present.
    result2 = person.evaluate_sync(ctx)
    assert result2 is True
    assert call_count == 0, (
        f"Expected mode.is_present NOT to be called on cache hit, "
        f"called {call_count} times"
    )
