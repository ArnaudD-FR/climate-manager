"""Tests for alignment.py: the brand-neutral SensorAligner.

A fake vendor stands in for a brand: the SensorAligner must work through the
TRVVendor interface only.
"""

import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from custom_components.climate_manager import vendors
from custom_components.climate_manager.alignment import SensorAligner
from custom_components.climate_manager.vendors import (
    AlignmentTarget,
    TRVVendor,
)

TRV = "climate.fake_trv"
SENSOR = "sensor.room"
STEADY = timedelta(minutes=90)
_START = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)


class FakeVendor(TRVVendor):
    """Aligns every room entity; remembers the offsets written."""

    label = "Fake"

    def __init__(self, reported=None):
        self.reported = reported
        self.writes = []

    def alignment_targets(self, hass, area_id, entity_ids, mappings):
        return [
            AlignmentTarget(self, f"dev_{e}", e, e, entity_id=e)
            for e in entity_ids
        ]

    def read_offset(self, hass, target):
        return self.reported

    async def write_offset(self, hass, target, offset):
        self.writes.append((target.key, offset))


@pytest.fixture
def fake(monkeypatch):
    vendor = FakeVendor()
    monkeypatch.setattr(vendors, "VENDORS", (vendor,))
    return vendor


def _aligner(hass, rooms=dict):
    config = {
        "alignment_enabled": True,
        "alignment_threshold": 0.5,
        "rooms": {"office": {"temperature_sensor": SENSOR}},
    }
    data = SimpleNamespace(rooms={"office": [TRV]}, runtime_config=config)
    return SensorAligner(hass, data, rooms), config


def _set(hass, trv_temp, sensor_temp):
    hass.states.async_set(TRV, "heat", {"current_temperature": trv_temp})
    hass.states.async_set(SENSOR, str(sensor_temp))


async def _steady(aligner, config, freezer):
    """Two passes 90 min apart: steady readings, settled setpoint."""
    await aligner.align_room(config, "office")
    freezer.tick(STEADY)
    await aligner.align_room(config, "office")


async def test_offset_written_logged_and_remembered(
    hass, fake, freezer, caplog
):
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    aligner, config = _aligner(hass)
    _set(hass, 20.0, 19.2)

    await _steady(aligner, config, freezer)

    assert fake.writes == [(f"dev_{TRV}", -0.8)]
    assert aligner.last_offset == {f"dev_{TRV}": -0.8}
    assert aligner.last_delta == {f"dev_{TRV}": -0.8}
    assert f"dev_{TRV}" in aligner.last_changed
    assert any(
        m.startswith("align | room=office trv=climate.fake_trv")
        for m in caplog.messages
    )


async def test_within_threshold_nothing_written(hass, fake, freezer):
    aligner, config = _aligner(hass)
    _set(hass, 20.0, 19.6)

    await _steady(aligner, config, freezer)

    assert fake.writes == []


async def test_disabled_nothing_written(hass, fake, freezer):
    aligner, config = _aligner(hass)
    config["alignment_enabled"] = False
    _set(hass, 20.0, 18.0)

    await aligner.align_all(config)
    freezer.tick(STEADY)
    await aligner.align_all(config)

    assert fake.writes == []


async def test_waits_for_steady_readings(hass, fake, freezer):
    """No write before both readings were observed over the window."""
    aligner, config = _aligner(hass)
    _set(hass, 20.0, 19.0)

    await aligner.align_room(config, "office")
    freezer.tick(STEADY - timedelta(minutes=1))
    await aligner.align_room(config, "office")
    assert fake.writes == []

    freezer.tick(timedelta(minutes=1))
    await aligner.align_room(config, "office")
    assert fake.writes == [(f"dev_{TRV}", -1.0)]


async def test_no_alignment_while_preheating(hass, fake, freezer):
    """A pre-heat run (boost held at one setpoint, then released) is
    skipped as a whole.

    Readings are not recorded meanwhile: the window starts after it.
    """
    room = SimpleNamespace(preheat_running=True)
    aligner, config = _aligner(hass, lambda: {"office": room})
    _set(hass, 21.9, 20.5)

    await _steady(aligner, config, freezer)
    assert fake.writes == []

    room.preheat_running = False
    await aligner.align_room(config, "office")
    assert fake.writes == []
    freezer.tick(STEADY)
    await aligner.align_room(config, "office")
    assert fake.writes == [(f"dev_{TRV}", -1.4)]


@pytest.mark.parametrize(
    ("trv_temps", "sensor_temps"),
    [
        # TRV warming next to the radiator (0.8 °C/h).
        ((20.0, 20.6, 21.2), (19.6, 19.6, 19.6)),
        # Room sensor warming in the sun.
        ((19.0, 19.0, 19.0), (19.6, 20.2, 20.8)),
    ],
)
async def test_moving_reading_nothing_written(
    hass, fake, freezer, trv_temps, sensor_temps
):
    aligner, config = _aligner(hass)
    for trv_temp, sensor_temp in zip(trv_temps, sensor_temps, strict=True):
        _set(hass, trv_temp, sensor_temp)
        await aligner.align_room(config, "office")
        freezer.tick(STEADY / 2)

    assert fake.writes == []


async def test_regulation_cycles_averaged(hass, fake, freezer):
    """A TRV regulating at its setpoint swings with its valve cycles
    (20.0 ↔ 21.0 every 15 min): the mean gap is corrected."""
    aligner, config = _aligner(hass)
    for minute in range(0, 91, 15):
        _set(hass, 20.0 if minute % 30 == 0 else 21.0, 19.6)
        await aligner.align_room(config, "office")
        if minute < 90:
            freezer.tick(timedelta(minutes=15))

    assert fake.writes == [(f"dev_{TRV}", -0.9)]


@pytest.mark.freeze_time(_START)
async def test_extra_readings_do_not_weigh_more(hass, fake, freezer):
    """Event-driven passes add readings: the mean is time-weighted.

    5 min at 21.0 in each half-hour, seen by 5 passes, against 25 min at
    20.0 seen by one: mean 20.17, gap -0.57 (counted per reading, the
    mean would be 20.7).
    """
    aligner, config = _aligner(hass)
    _set(hass, 20.0, 19.6)
    await aligner.align_room(config, "office")
    for burst in (40, 70):
        freezer.move_to(_START + timedelta(minutes=burst))
        _set(hass, 21.0, 19.6)
        for _ in range(5):
            await aligner.align_room(config, "office")
            freezer.tick(timedelta(minutes=1))
        _set(hass, 20.0, 19.6)
        await aligner.align_room(config, "office")
    freezer.move_to(_START + timedelta(minutes=90))
    await aligner.align_room(config, "office")

    assert fake.writes == [(f"dev_{TRV}", -0.6)]


async def test_waits_after_setpoint_change(hass, fake, freezer):
    """A radiator keeps warming its TRV after closing: the flat top of
    that hump is not a steady state."""
    aligner, config = _aligner(hass)
    _set(hass, 20.0, 19.0)
    await aligner.align_room(config, "office")
    freezer.tick(timedelta(minutes=30))
    hass.states.async_set(
        TRV, "heat", {"current_temperature": 20.0, "temperature": 18.0}
    )
    await aligner.align_room(config, "office")

    # Readings flat for 90 min, setpoint changed 60 min ago.
    freezer.tick(timedelta(minutes=60))
    await aligner.align_room(config, "office")
    assert fake.writes == []

    freezer.tick(timedelta(minutes=30))
    await aligner.align_room(config, "office")
    assert fake.writes == [(f"dev_{TRV}", -1.0)]


async def test_waits_for_trv_to_settle_after_write(hass, fake, freezer):
    """A write starts the TRV readings over: no windup on a stale gap."""
    aligner, config = _aligner(hass)
    _set(hass, 20.0, 19.0)
    await _steady(aligner, config, freezer)

    # Same stale reading 6 min later: not corrected again.
    freezer.tick(timedelta(minutes=6))
    await aligner.align_room(config, "office")
    assert fake.writes == [(f"dev_{TRV}", -1.0)]

    # Settled on a still too high reading: accumulates on -1.0.
    _set(hass, 19.6, 19.0)
    await _steady(aligner, config, freezer)
    assert fake.writes[-1] == (f"dev_{TRV}", -1.6)


async def test_starts_from_reported_offset_then_clamps(hass, fake, freezer):
    fake.reported = 4.0
    aligner, config = _aligner(hass)
    _set(hass, 18.0, 20.0)

    await _steady(aligner, config, freezer)

    assert fake.writes == [(f"dev_{TRV}", 5.0)]


async def test_unchanged_offset_not_written(hass, fake, freezer):
    """At the clamp the offset cannot move: no API call."""
    fake.reported = -5.0
    aligner, config = _aligner(hass)
    _set(hass, 21.0, 20.0)

    await _steady(aligner, config, freezer)

    assert fake.writes == []


async def test_watched_entities_are_temperature_sources(hass, fake):
    aligner, _ = _aligner(hass)

    assert aligner.watched_entities() == {TRV: "office"}


async def test_no_vendor_no_target(hass, monkeypatch):
    monkeypatch.setattr(vendors, "VENDORS", ())
    aligner, _ = _aligner(hass)

    assert aligner.targets("office") == []


async def test_failed_write_waits_min_interval(hass, fake, freezer, caplog):
    """A failed write is not retried before the min interval (API quota)."""
    attempts = []

    async def failing_write(hass, target, offset):
        attempts.append(offset)
        raise ValueError("rejected")

    fake.write_offset = failing_write
    aligner, config = _aligner(hass)
    _set(hass, 20.0, 19.0)

    await _steady(aligner, config, freezer)
    freezer.tick(60)
    await aligner.align_room(config, "office")
    assert attempts == [-1.0]
    assert aligner.last_offset == {}
    assert "ValueError('rejected')" in caplog.text

    freezer.tick(241)
    await aligner.align_room(config, "office")
    assert attempts == [-1.0, -1.0]
