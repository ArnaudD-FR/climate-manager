"""SensorAligner seeded from the recorder after a restart.

A module of its own: the recorder must be set up before hass, so the
package's autouse fixture is overridden here to request it first.
"""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from custom_components.climate_manager.alignment import ALIGNMENT_STORE_KEY
from tests import test_alignment
from tests.test_alignment import TRV, _START, _aligner, _set

fake = test_alignment.fake


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Recorder first, then the package's custom integrations."""


async def test_seeded_from_recorder_after_restart(hass, fake, freezer):
    """Readings and setpoint recorded before a restart: a new aligner
    corrects at its first pass instead of waiting for a new window."""
    freezer.move_to(_START)
    _set(hass, 20.0, 19.0)
    await async_wait_recording_done(hass)
    freezer.tick(timedelta(minutes=125))
    await hass.async_block_till_done()

    aligner, config = _aligner(hass)
    await aligner.align_room(config, "office")

    assert fake.writes == [(f"dev_{TRV}", -1.0)]


async def test_recorded_setpoint_change_still_settles(hass, fake, freezer):
    """A setpoint changed 60 min before the restart: still 60 min to go."""
    freezer.move_to(_START)
    _set(hass, 18.2, 17.2)
    await async_wait_recording_done(hass)
    freezer.tick(timedelta(minutes=125))
    hass.states.async_set(
        TRV, "heat", {"current_temperature": 18.2, "temperature": 18.0}
    )
    await async_wait_recording_done(hass)
    freezer.tick(timedelta(minutes=60))

    aligner, config = _aligner(hass)
    await aligner.align_room(config, "office")
    assert fake.writes == []

    freezer.tick(timedelta(minutes=60))
    await aligner.align_room(config, "office")
    assert fake.writes == [(f"dev_{TRV}", -1.0)]


async def test_recorded_trv_ramp_not_corrected(hass, fake, freezer):
    """A TRV reading is an attribute: its recorded ramp (warming next to
    the radiator) counts, not only its last value."""
    freezer.move_to(_START)
    for trv_temp in (19.0, 19.6, 20.2, 20.8):
        _set(hass, trv_temp, 19.0)
        await async_wait_recording_done(hass)
        freezer.tick(timedelta(minutes=30))

    aligner, config = _aligner(hass)
    await aligner.align_room(config, "office")

    assert fake.writes == []


async def test_not_seeded_across_a_preheat(hass, fake, freezer):
    """Restarted during a pre-heat: its recorded readings are not used
    once it ends."""
    freezer.move_to(_START)
    _set(hass, 20.0, 19.0)
    await async_wait_recording_done(hass)
    freezer.tick(timedelta(minutes=125))
    room = SimpleNamespace(preheat_boosting=True)
    aligner, config = _aligner(hass, lambda: {"office": room})
    await aligner.align_room(config, "office")

    room.preheat_boosting = False
    await aligner.align_room(config, "office")
    assert fake.writes == []
    freezer.tick(timedelta(minutes=125))
    await aligner.align_room(config, "office")
    assert fake.writes == [(f"dev_{TRV}", -1.0)]


async def test_not_seeded_before_last_write(hass, fake, freezer):
    """Parents' room, 2026-10-23: written at 14:32, restarted at 14:38,
    corrected again on the readings of before the write."""
    fake.offset_entity = "sensor.fake_offset"
    freezer.move_to(_START)
    _set(hass, 20.0, 19.0)
    hass.states.async_set("sensor.fake_offset", "0.0")
    await async_wait_recording_done(hass)
    freezer.tick(timedelta(minutes=125))
    hass.states.async_set("sensor.fake_offset", "-1.0")
    await async_wait_recording_done(hass)
    freezer.tick(timedelta(minutes=5))

    aligner, config = _aligner(hass)
    await aligner.align_room(config, "office")
    assert fake.writes == []

    freezer.tick(timedelta(minutes=120))
    await aligner.align_room(config, "office")
    assert fake.writes == [(f"dev_{TRV}", -1.0)]


async def test_not_seeded_before_persisted_write(
    hass, fake, freezer, hass_storage
):
    """Lucie's room, 2026-10-24: written at 11:14, restarted at 11:18
    while Tado X still reported the old offset; corrected twice."""
    freezer.move_to(_START)
    _set(hass, 20.0, 19.0)
    await async_wait_recording_done(hass)
    freezer.tick(timedelta(minutes=125))
    hass_storage[ALIGNMENT_STORE_KEY] = {
        "version": 1,
        "key": ALIGNMENT_STORE_KEY,
        "data": {
            "targets": {
                f"dev_{TRV}": {
                    "offset": -0.8,
                    "changed": dt_util.utcnow().isoformat(timespec="seconds"),
                    "delta": -0.6,
                }
            }
        },
    }
    freezer.tick(timedelta(minutes=4))

    aligner, config = _aligner(hass)
    await aligner.align_room(config, "office")
    assert fake.writes == []

    freezer.tick(timedelta(minutes=120))
    await aligner.align_room(config, "office")
    assert fake.writes == [(f"dev_{TRV}", -1.8)]
