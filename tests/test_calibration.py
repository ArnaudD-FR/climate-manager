"""Tests for calibration.py: the brand-neutral Calibrator.

A fake vendor stands in for a brand: the Calibrator must work through the
TRVVendor interface only.
"""

import logging
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


async def test_offset_written_logged_and_remembered(hass, fake, caplog):
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.2)

    await calibrator.calibrate_room(config, "office", None)

    assert fake.writes == [(f"dev_{TRV}", -0.8)]
    assert calibrator.last_offset == {f"dev_{TRV}": -0.8}
    assert calibrator.last_delta == {f"dev_{TRV}": -0.8}
    assert f"dev_{TRV}" in calibrator.last_changed
    assert any(
        m.startswith("calibrate | room=office trv=climate.fake_trv")
        for m in caplog.messages
    )


async def test_within_threshold_nothing_written(hass, fake):
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.6)

    await calibrator.calibrate_room(config, "office", None)

    assert fake.writes == []


async def test_disabled_nothing_written(hass, fake):
    calibrator, config = _calibrator(hass)
    config["calibration_enabled"] = False
    _set(hass, 20.0, 18.0)

    await calibrator.calibrate_all(config, {})

    assert fake.writes == []


async def test_min_interval_between_two_writes(hass, fake, freezer):
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.0)
    await calibrator.calibrate_room(config, "office", None)

    _set(hass, 20.0, 18.0)
    freezer.tick(240)
    await calibrator.calibrate_room(config, "office", None)
    assert len(fake.writes) == 1

    freezer.tick(61)
    await calibrator.calibrate_room(config, "office", None)
    # Accumulates on the offset written first (-1.0), not on 0.
    assert fake.writes[-1] == (f"dev_{TRV}", -3.0)


async def test_starts_from_reported_offset_then_clamps(hass, fake):
    fake.reported = 4.0
    calibrator, config = _calibrator(hass)
    _set(hass, 18.0, 20.0)

    await calibrator.calibrate_room(config, "office", None)

    assert fake.writes == [(f"dev_{TRV}", 5.0)]


async def test_tighter_threshold_while_preheating(hass, fake):
    calibrator, config = _calibrator(hass)
    _set(hass, 20.0, 19.7)

    await calibrator.calibrate_room(
        config, "office", SimpleNamespace(preheat_boosting=True)
    )

    assert fake.writes == [(f"dev_{TRV}", -0.3)]


async def test_watched_entities_are_temperature_sources(hass, fake):
    calibrator, _ = _calibrator(hass)

    assert calibrator.watched_entities() == {TRV: "office"}


async def test_no_vendor_no_target(hass, monkeypatch):
    monkeypatch.setattr(vendors, "VENDORS", ())
    calibrator, _ = _calibrator(hass)

    assert calibrator.targets("office") == []
