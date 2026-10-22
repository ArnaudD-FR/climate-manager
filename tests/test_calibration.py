"""Tests for calibration.py: the brand-neutral Calibrator.

A fake vendor stands in for a brand: the Calibrator must work through the
TRVVendor interface only.
"""

import logging
from datetime import timedelta
from types import SimpleNamespace

import pytest

from custom_components.climate_manager import vendors
from custom_components.climate_manager.calibration import Calibrator
from custom_components.climate_manager.vendors import (
    CalibrationTarget,
    TRVVendor,
)

TRV = "climate.fake_trv"
SENSOR = "sensor.room"
STEADY = timedelta(minutes=30)


class FakeVendor(TRVVendor):
    """Calibrates every room entity; remembers the offsets written."""

    label = "Fake"

    def __init__(self, reported=None):
        self.reported = reported
        self.writes = []

    def calibration_targets(self, hass, area_id, entity_ids, mappings):
        return [
            CalibrationTarget(self, f"dev_{e}", e, e, entity_id=e)
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


def _calibrator(hass):
    config = {
        "calibration_enabled": True,
        "calibration_threshold": 0.5,
        "rooms": {"office": {"temperature_sensor": SENSOR}},
    }
    data = SimpleNamespace(rooms={"office": [TRV]}, runtime_config=config)
    return Calibrator(hass, data), config


def _set(hass, trv_temp, sensor_temp):
    hass.states.async_set(TRV, "heat", {"current_temperature": trv_temp})
    hass.states.async_set(SENSOR, str(sensor_temp))


async def _steady(calibrator, config, freezer):
    """Two passes 30 min apart: the readings look steady to the second."""
    await calibrator.calibrate_room(config, "office", None)
    freezer.tick(STEADY)
    await calibrator.calibrate_room(config, "office", None)


async def test_offset_written_logged_and_remembered(
    hass, fake, freezer, caplog
):
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.2)

    await _steady(calibrator, config, freezer)

    assert fake.writes == [(f"dev_{TRV}", -0.8)]
    assert calibrator.last_offset == {f"dev_{TRV}": -0.8}
    assert calibrator.last_delta == {f"dev_{TRV}": -0.8}
    assert f"dev_{TRV}" in calibrator.last_changed
    assert any(
        m.startswith("calibrate | room=office trv=climate.fake_trv")
        for m in caplog.messages
    )


async def test_within_threshold_nothing_written(hass, fake, freezer):
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.6)

    await _steady(calibrator, config, freezer)

    assert fake.writes == []


async def test_disabled_nothing_written(hass, fake, freezer):
    calibrator, config = _calibrator(hass)
    config["calibration_enabled"] = False
    _set(hass, 20.0, 18.0)

    await calibrator.calibrate_all(config, {})
    freezer.tick(STEADY)
    await calibrator.calibrate_all(config, {})

    assert fake.writes == []


async def test_waits_for_steady_readings(hass, fake, freezer):
    """No write before both readings were observed over the window."""
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.0)

    await calibrator.calibrate_room(config, "office", None)
    freezer.tick(STEADY - timedelta(minutes=1))
    await calibrator.calibrate_room(config, "office", None)
    assert fake.writes == []

    freezer.tick(timedelta(minutes=1))
    await calibrator.calibrate_room(config, "office", None)
    assert fake.writes == [(f"dev_{TRV}", -1.0)]


@pytest.mark.parametrize(
    ("trv_temps", "sensor_temps"),
    [
        # TRV warming next to the radiator (pre-heat, sun).
        ((20.0, 20.3, 20.6), (19.6, 19.6, 19.6)),
        # Room sensor warming in the sun.
        ((19.0, 19.0, 19.0), (19.6, 20.0, 20.4)),
    ],
)
async def test_moving_reading_nothing_written(
    hass, fake, freezer, trv_temps, sensor_temps
):
    calibrator, config = _calibrator(hass)
    for trv_temp, sensor_temp in zip(trv_temps, sensor_temps, strict=True):
        _set(hass, trv_temp, sensor_temp)
        await calibrator.calibrate_room(config, "office", None)
        freezer.tick(STEADY / 2)

    assert fake.writes == []


async def test_waits_for_trv_to_settle_after_write(hass, fake, freezer):
    """A write starts the TRV readings over: no windup on a stale gap."""
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.0)
    await _steady(calibrator, config, freezer)

    # Same stale reading 6 min later: not corrected again.
    freezer.tick(timedelta(minutes=6))
    await calibrator.calibrate_room(config, "office", None)
    assert fake.writes == [(f"dev_{TRV}", -1.0)]

    # Settled on a still too high reading: accumulates on -1.0.
    _set(hass, 19.6, 19.0)
    await _steady(calibrator, config, freezer)
    assert fake.writes[-1] == (f"dev_{TRV}", -1.6)


async def test_tighter_threshold_while_preheating(hass, fake, freezer):
    """A steady 0.3 °C gap: a TRV throttled before the room is warm."""
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.7)
    preheating = SimpleNamespace(preheat_boosting=True)

    await calibrator.calibrate_room(config, "office", preheating)
    freezer.tick(STEADY)
    await calibrator.calibrate_room(config, "office", preheating)

    assert fake.writes == [(f"dev_{TRV}", -0.3)]


async def test_starts_from_reported_offset_then_clamps(hass, fake, freezer):
    fake.reported = 4.0
    calibrator, config = _calibrator(hass)
    _set(hass, 18.0, 20.0)

    await _steady(calibrator, config, freezer)

    assert fake.writes == [(f"dev_{TRV}", 5.0)]


async def test_unchanged_offset_not_written(hass, fake, freezer):
    """At the clamp the offset cannot move: no API call."""
    fake.reported = -5.0
    calibrator, config = _calibrator(hass)
    _set(hass, 21.0, 20.0)

    await _steady(calibrator, config, freezer)

    assert fake.writes == []


async def test_watched_entities_are_temperature_sources(hass, fake):
    calibrator, _ = _calibrator(hass)

    assert calibrator.watched_entities() == {TRV: "office"}


async def test_no_vendor_no_target(hass, monkeypatch):
    monkeypatch.setattr(vendors, "VENDORS", ())
    calibrator, _ = _calibrator(hass)

    assert calibrator.targets("office") == []


async def test_failed_write_waits_min_interval(hass, fake, freezer, caplog):
    """A failed write is not retried before the min interval (API quota)."""
    attempts = []

    async def failing_write(hass, target, offset):
        attempts.append(offset)
        raise ValueError("rejected")

    fake.write_offset = failing_write
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.0)

    await _steady(calibrator, config, freezer)
    freezer.tick(60)
    await calibrator.calibrate_room(config, "office", None)
    assert attempts == [-1.0]
    assert calibrator.last_offset == {}
    assert "ValueError('rejected')" in caplog.text

    freezer.tick(241)
    await calibrator.calibrate_room(config, "office", None)
    assert attempts == [-1.0, -1.0]
