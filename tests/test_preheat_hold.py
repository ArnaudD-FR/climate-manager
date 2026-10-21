"""Multi-cycle pre-heat tests through the coordinator.

Tests:
- The pre-heat setpoint is held on every tick until the occupied time
  (the zone schedule no longer undoes it one minute later)
- The room period sensor reports "preheat" while it holds
- Convergence records a lead-time sample but keeps holding until the
  occupied time
- The room temperature sensor (not the TRV) decides convergence / warmth
- No pre-heat in a zone that is off
- A config rebuild keeps a running pre-heat
- Not reached at the occupied time → measuring continues (real duration),
  or ends censored after 2 × max lead
- A learned rate scales the lead with the gap (colder room starts earlier)
- A restart resumes the persisted run (hold + original start time)
- Store v1 → v2 migration
"""

import logging

import pytest

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    PERIOD_NORMAL,
    PERIOD_PREHEAT,
    PERIOD_REDUCED,
)
from custom_components.climate_manager.preheat import (
    PREHEAT_STORE_KEY,
    PreheatStore,
)

_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Reduced until 07:00, then Normal.
MORNING_PROGRAM: dict = {
    day: [
        {"start": "00:00", "mode": PERIOD_REDUCED},
        {"start": "07:00", "mode": PERIOD_NORMAL},
    ]
    for day in _DAYS
}

NORMAL = DEFAULT_PERIOD_TEMPERATURES[PERIOD_NORMAL]
REDUCED = DEFAULT_PERIOD_TEMPERATURES[PERIOD_REDUCED]

TRV = "climate.a_trv"
SENSOR = "sensor.a_temperature"


def _utc(local_hhmm: str) -> str:
    """Monday 2026-01-05 local (US/Pacific test TZ, UTC-8) → UTC string."""
    hh, mm = (int(x) for x in local_hhmm.split(":"))
    return f"2026-01-05 {hh + 8:02d}:{mm:02d}:00"


def _config(
    zone_mode: str = MODE_TIME_PROGRAM,
    rooms: dict | None = None,
    boost: float = 0,
):
    """Room "a" pre-heats MORNING_PROGRAM; boost 0 keeps the plain target."""
    rooms = {
        area_id: {"preheat_boost_factor": boost, **room}
        for area_id, room in (rooms or {"a": {}}).items()
    }
    return {
        "version": 2,
        "default_zone": {
            "name": "Home",
            "mode": zone_mode,
            "time_program": MORNING_PROGRAM,
            "preheat_enabled": True,
        },
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "rooms": rooms,
        "persons": {},
        "zones": {},
    }


async def _setup(hass, config: dict):
    async_mock_service(hass, "climate", "set_hvac_mode")
    calls = async_mock_service(hass, "climate", "set_temperature")
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entry.runtime_data.runtime_config = config
    entry.runtime_data.rooms = {"a": [TRV]}
    return entry, entry.runtime_data.coordinator, calls


async def _tick(hass, freezer, coordinator, calls, local: str, room_temp):
    """Run one evaluation at `local`; the TRV then reports what it got."""
    freezer.move_to(_utc(local))
    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    setpoint = calls[-1].data["temperature"] if calls else None
    hass.states.async_set(
        TRV,
        "heat",
        {"temperature": setpoint, "current_temperature": room_temp},
    )
    await hass.async_block_till_done()
    return setpoint


async def test_preheat_setpoint_held_until_occupied_time(hass, freezer, caplog):
    """06:00 trigger → 20 °C held every tick → Normal takes over at 07:00."""
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    _, coordinator, calls = await _setup(hass, _config())

    assert await _tick(hass, freezer, coordinator, calls, "06:00", 17.0) == (
        NORMAL
    )
    room = coordinator.rooms["a"]
    assert room._preheat_active
    assert hass.states.get("sensor.a_period").state == PERIOD_PREHEAT
    assert any(m.startswith("preheat | room=a") for m in caplog.messages)

    pushes_after_trigger = len(calls)
    for local in ("06:01", "06:02", "06:30", "06:59"):
        assert (
            await _tick(hass, freezer, coordinator, calls, local, 17.5)
            == NORMAL
        )
        assert hass.states.get("sensor.a_period").state == PERIOD_PREHEAT
    assert len(calls) == pushes_after_trigger, "no 18 °C push in between"

    await _tick(hass, freezer, coordinator, calls, "07:00", 18.0)
    assert not room._preheat_active
    # Not reached yet: the run keeps measuring, without holding.
    assert room._preheat_in_progress["measuring"]
    assert room.current_period == PERIOD_NORMAL
    assert hass.states.get("sensor.a_period").state == PERIOD_NORMAL


async def test_convergence_records_sample_and_keeps_holding(hass, freezer):
    """Target reached after 06:20 → seen at 06:21; held until 07:00."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    entry, coordinator, calls = await _setup(hass, _config())

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    await _tick(hass, freezer, coordinator, calls, "06:10", 18.5)
    await _tick(hass, freezer, coordinator, calls, "06:20", NORMAL)
    await _tick(hass, freezer, coordinator, calls, "06:21", NORMAL)

    samples = entry.runtime_data.preheat_data["rooms"]["a"]["samples"]
    # The room reports 20 °C after the 06:20 tick; seen at 06:21.
    assert [s["duration_minutes"] for s in samples] == [21]
    assert samples[0]["rate"] == 7.0  # 21 min for 17 → 20 °C

    # Still holding the pre-heat setpoint after convergence.
    room = coordinator.rooms["a"]
    assert room._preheat_active
    assert room.current_period == PERIOD_PREHEAT
    assert calls[-1].data["temperature"] == NORMAL
    assert all(c.data["temperature"] != REDUCED for c in calls[1:])

    await _tick(hass, freezer, coordinator, calls, "07:00", NORMAL)
    assert room.current_period == PERIOD_NORMAL
    assert len(samples) == 1


async def test_room_sensor_decides_warmth(hass, freezer):
    """Room sensor at 20 °C (TRV reads 17 °C) → room already warm."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    hass.states.async_set(SENSOR, str(NORMAL), {"device_class": "temperature"})
    _, coordinator, calls = await _setup(
        hass, _config(rooms={"a": {"temperature_sensor": SENSOR}})
    )

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    assert not coordinator.rooms["a"]._preheat_active
    assert all(c.data["temperature"] == REDUCED for c in calls)


async def test_no_preheat_when_zone_off(hass, freezer):
    """A zone that is off never pre-heats its rooms."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV,
        "heat",
        {"temperature": REDUCED, "current_temperature": 17.0},
    )
    _, coordinator, calls = await _setup(hass, _config(zone_mode=MODE_OFF))

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    assert not coordinator.rooms["a"]._preheat_active
    assert all(c.data["temperature"] != NORMAL for c in calls)


async def test_rebuild_keeps_running_preheat(hass, freezer):
    """A config edit during pre-heat keeps the run and its start time."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    entry, coordinator, calls = await _setup(hass, _config())

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    start = coordinator.rooms["a"]._preheat_in_progress["start_time"]

    entry.runtime_data.runtime_config["default_zone"]["name"] = "Renamed"
    await _tick(hass, freezer, coordinator, calls, "06:05", 17.5)

    room = coordinator.rooms["a"]
    assert room._preheat_in_progress["start_time"] == start
    assert room.current_period == PERIOD_PREHEAT
    assert calls[-1].data["temperature"] == NORMAL


def _seed_rate(entry, rate: float, count: int = 3) -> None:
    """Pretend the room already learned `rate` min/°C."""
    entry.runtime_data.preheat_data = {
        "rooms": {
            "a": {
                "samples": [
                    {"rate": rate, "censored": False} for _ in range(count)
                ],
                "run": None,
            }
        }
    }


async def test_measuring_past_occupied_time_records_real_duration(
    hass, freezer
):
    """Target reached after 07:30 (seen 07:40) → 100 min sample, run ends."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    entry, coordinator, calls = await _setup(hass, _config())

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    await _tick(hass, freezer, coordinator, calls, "07:00", 18.5)
    room = coordinator.rooms["a"]
    assert room._preheat_in_progress["measuring"]
    assert not entry.runtime_data.preheat_data["rooms"]["a"]["samples"]

    await _tick(hass, freezer, coordinator, calls, "07:30", NORMAL)
    await _tick(hass, freezer, coordinator, calls, "07:40", NORMAL)

    stored = entry.runtime_data.preheat_data["rooms"]["a"]
    assert [s["duration_minutes"] for s in stored["samples"]] == [100]
    assert stored["samples"][0]["censored"] is False
    assert stored["run"] is None
    assert not room._preheat_in_progress


async def test_never_reached_records_censored_sample(hass, freezer):
    """Still short of the target after 2 × max lead → censored sample."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    entry, coordinator, calls = await _setup(hass, _config())

    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    await _tick(hass, freezer, coordinator, calls, "07:00", 18.0)
    await _tick(hass, freezer, coordinator, calls, "09:00", 19.0)
    assert coordinator.rooms["a"]._preheat_in_progress["measuring"]

    await _tick(hass, freezer, coordinator, calls, "10:01", 19.0)
    stored = entry.runtime_data.preheat_data["rooms"]["a"]
    assert len(stored["samples"]) == 1
    sample = stored["samples"][0]
    assert sample["censored"] is True
    assert (
        sample["duration_minutes"] == 2 * DEFAULT_PREHEAT_MAX_LEAD_MINUTES + 1
    )
    assert sample["rate"] == pytest.approx(241 / 3, abs=0.01)
    assert stored["run"] is None


@pytest.mark.parametrize(
    ("room_temp", "first_trigger"),
    [(17.0, "06:27"), (15.0, "06:05")],
)
async def test_learned_rate_scales_lead_with_gap(
    hass, freezer, room_temp, first_trigger
):
    """10 min/°C learned: 3 °C gap → 33 min lead; 5 °C → 55 min."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV,
        "heat",
        {"temperature": REDUCED, "current_temperature": room_temp},
    )
    entry, coordinator, calls = await _setup(hass, _config())
    _seed_rate(entry, 10.0)

    hh, mm = (int(x) for x in first_trigger.split(":"))
    before = f"{hh:02d}:{mm - 1:02d}"
    await _tick(hass, freezer, coordinator, calls, before, room_temp)
    room = coordinator.rooms["a"]
    assert not room._preheat_active
    assert calls[-1].data["temperature"] == REDUCED

    await _tick(hass, freezer, coordinator, calls, first_trigger, room_temp)
    assert room._preheat_active
    assert calls[-1].data["temperature"] == NORMAL
    assert room.learned_rate() == 10.0

    payload = coordinator._build_status_payload()
    status = next(r for r in payload["rooms_status"] if r["area_id"] == "a")
    assert status["preheat_rate"] == 10.0
    assert status["preheat_samples"] == 3
    expected_lead = 10.0 * (NORMAL - room_temp) * 1.1
    assert status["preheat_lead"] == round(expected_lead)


async def test_restart_resumes_running_preheat(hass, freezer):
    """A restart at 06:20 keeps the hold and the 06:00 start time."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    entry, coordinator, calls = await _setup(hass, _config())
    await _tick(hass, freezer, coordinator, calls, "06:00", 17.0)
    config = entry.runtime_data.runtime_config
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # "Reboot": a fresh entry loads the run from the pre-heat store.
    freezer.move_to(_utc("06:20"))
    entry2, coordinator2, calls2 = await _setup(hass, config)
    await _tick(hass, freezer, coordinator2, calls2, "06:20", 18.5)
    room = coordinator2.rooms["a"]
    assert room._preheat_active
    assert room.current_period == PERIOD_PREHEAT
    assert calls2[-1].data["temperature"] == NORMAL
    assert room._preheat_in_progress["start_time"].hour == 6
    assert room._preheat_in_progress["start_time"].minute == 0

    await _tick(hass, freezer, coordinator2, calls2, "06:40", NORMAL)
    await _tick(hass, freezer, coordinator2, calls2, "06:41", NORMAL)
    samples = entry2.runtime_data.preheat_data["rooms"]["a"]["samples"]
    assert [s["duration_minutes"] for s in samples] == [41]


async def test_store_v1_migrates_to_empty_v2(hass, hass_storage):
    """v1 samples (no start temperature) cannot give a rate: dropped."""
    hass_storage[PREHEAT_STORE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": PREHEAT_STORE_KEY,
        "data": {"a": [{"duration_minutes": 30, "timestamp": "t"}]},
    }
    assert await PreheatStore(hass).async_load() == {"rooms": {}}


async def test_boost_follows_room_gap_then_drops_on_convergence(hass, freezer):
    """Factor 2: 3 °C gap → +3 (cap); 0.5 °C → +1; reached → plain 20."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    _, coordinator, calls = await _setup(hass, _config(boost=2))

    assert await _tick(hass, freezer, coordinator, calls, "06:00", 19.5) == (
        NORMAL + 3.0
    )
    room = coordinator.rooms["a"]
    assert room._last_setpoint == NORMAL
    payload = coordinator._build_status_payload()
    status = next(r for r in payload["rooms_status"] if r["area_id"] == "a")
    assert status["preheat_boost"] == 3.0

    # The room is 0.5 °C short: 2 × 0.5 = +1.
    assert await _tick(hass, freezer, coordinator, calls, "06:30", 20.0) == (
        NORMAL + 1.0
    )

    # Target reached: the plain setpoint is re-pushed in the same tick.
    assert await _tick(hass, freezer, coordinator, calls, "06:40", 20.0) == (
        NORMAL
    )
    assert room._preheat_in_progress["converged"]
    assert room._preheat_boost_applied is None
    assert room.current_period == PERIOD_PREHEAT


async def test_boost_continues_while_measuring(hass, freezer):
    """Not reached at 07:00: Normal gets the boost until the room is warm."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 17.0}
    )
    _, coordinator, calls = await _setup(hass, _config(boost=2))

    await _tick(hass, freezer, coordinator, calls, "06:00", 19.0)
    room = coordinator.rooms["a"]
    assert await _tick(hass, freezer, coordinator, calls, "07:00", 19.5) == (
        NORMAL + 2.0
    )
    assert room._preheat_in_progress["measuring"]
    assert room.current_period == PERIOD_NORMAL

    assert await _tick(hass, freezer, coordinator, calls, "07:10", 20.0) == (
        NORMAL + 1.0
    )
    assert await _tick(hass, freezer, coordinator, calls, "07:20", 20.0) == (
        NORMAL
    )
    assert not room._preheat_in_progress


async def test_boost_bounded_by_trv_max_temp(hass, freezer):
    """A TRV capped at 21.5 °C never gets more, whatever the gap."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV,
        "heat",
        {
            "temperature": REDUCED,
            "current_temperature": 17.0,
            "max_temp": 21.5,
        },
    )
    _, coordinator, calls = await _setup(hass, _config(boost=2))

    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    assert calls[-1].data["temperature"] == 21.5


async def test_boost_factor_defaults_when_room_has_no_setting(hass, freezer):
    """No preheat_boost_factor → DEFAULT_PREHEAT_BOOST_FACTOR (2)."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": 19.5}
    )
    config = _config()
    config["rooms"] = {}
    _, coordinator, calls = await _setup(hass, config)

    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    assert calls[-1].data["temperature"] == NORMAL + 1.0


async def test_no_boost_without_room_temperature(hass, freezer):
    """No room reading → the plain target, as before."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(TRV, "heat", {"temperature": REDUCED})
    _, coordinator, calls = await _setup(hass, _config(boost=2))

    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    assert coordinator.rooms["a"]._preheat_active
    assert calls[-1].data["temperature"] == NORMAL
