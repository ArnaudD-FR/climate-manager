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
- Boost: valve wide open until released at the learned anticipation
  (minutes before the target at the current heating speed), tuned by the
  overshoot after the release

The boost is off (plain pre-heat target) unless a test requests the
with_boost fixture.
"""

import logging
from datetime import datetime, timedelta, timezone

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
    PERIOD_COMFORT,
    PERIOD_NORMAL,
    PERIOD_PREHEAT,
    PERIOD_REDUCED,
)
from custom_components.climate_manager import room as room_module
from custom_components.climate_manager.preheat import (
    PREHEAT_STORE_KEY,
    PreheatStore,
    add_reading,
    heating_slope,
    tune_anticipation,
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
):
    """Room "a" pre-heats MORNING_PROGRAM."""
    rooms = rooms or {"a": {}}
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


@pytest.fixture
def with_boost():
    """Request it to keep the pre-heat boost in a test."""


@pytest.fixture(autouse=True)
def _boost_off(request, monkeypatch):
    """No boost (cap 0) unless the test requests with_boost."""
    if "with_boost" not in request.fixturenames:
        monkeypatch.setattr(room_module, "PREHEAT_BOOST_MAX", 0.0)


async def _setup(hass, config: dict):
    """Set up the integration with `config`."""
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
    rooms = entry.runtime_data.preheat_data.setdefault("rooms", {})
    rooms.setdefault("a", {})["samples"] = [
        {"rate": rate, "censored": False} for _ in range(count)
    ]


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
    await _tick(hass, freezer, coordinator, calls, "13:00", 19.0)
    assert coordinator.rooms["a"]._preheat_in_progress["measuring"]

    await _tick(hass, freezer, coordinator, calls, "14:01", 19.0)
    stored = entry.runtime_data.preheat_data["rooms"]["a"]
    assert len(stored["samples"]) == 1
    sample = stored["samples"][0]
    assert sample["censored"] is True
    assert (
        sample["duration_minutes"] == 2 * DEFAULT_PREHEAT_MAX_LEAD_MINUTES + 1
    )
    assert sample["rate"] == pytest.approx(481 / 3, abs=0.01)
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


def _sensor_config() -> dict:
    """Room "a" read from SENSOR (set before each tick, see _tick_room)."""
    return _config(rooms={"a": {"temperature_sensor": SENSOR}})


def _set_room(hass, temp: float) -> None:
    hass.states.async_set(
        TRV, "heat", {"temperature": REDUCED, "current_temperature": temp}
    )
    hass.states.async_set(SENSOR, str(temp), {"device_class": "temperature"})


async def _tick_room(hass, freezer, coordinator, calls, local, room_temp):
    """One evaluation at `local` with the room sensor at room_temp."""
    hass.states.async_set(
        SENSOR, str(room_temp), {"device_class": "temperature"}
    )
    return await _tick(hass, freezer, coordinator, calls, local, room_temp)


def _status(coordinator) -> dict:
    payload = coordinator._build_status_payload()
    return next(r for r in payload["rooms_status"] if r["area_id"] == "a")


async def test_full_boost_until_release(hass, freezer, caplog, with_boost):
    """+3 °C until the target is 10 min away at the current speed; the
    boost is not re-applied after a dip."""
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    freezer.move_to(_utc("06:00"))
    _set_room(hass, 17.0)
    entry, coordinator, calls = await _setup(hass, _sensor_config())
    stored = entry.runtime_data.preheat_data["rooms"]

    assert await _tick_room(
        hass, freezer, coordinator, calls, "06:00", 17.0
    ) == (NORMAL + 3.0)
    room = coordinator.rooms["a"]
    assert room._last_setpoint == NORMAL
    assert room.preheat_boosting
    assert _status(coordinator)["preheat_boost"] == 3.0

    # 0.05 °C/min, 2.5 °C left → 50 min: keep the valve open.
    for local, temp in (("06:10", 17.5), ("06:20", 18.0), ("06:30", 19.0)):
        assert await _tick_room(
            hass, freezer, coordinator, calls, local, temp
        ) == (NORMAL + 3.0)
    assert not stored["a"].get("observe")

    # 2.1 °C over the last 30 min, 0.4 °C left → 6 min ≤ 10: released.
    assert await _tick_room(
        hass, freezer, coordinator, calls, "06:40", 19.6
    ) == (NORMAL)
    assert not room.preheat_boosting
    assert room._preheat_in_progress["released"]
    assert not room._preheat_in_progress["converged"]
    assert room._preheat_boost_applied is None
    assert room.current_period == PERIOD_PREHEAT
    assert stored["a"]["observe"]["peak"] == 19.6
    assert stored["a"]["run"]["released"] is True
    assert any(
        "released left=6min slope=0.070°C/min" in m for m in caplog.messages
    )

    await _tick_room(hass, freezer, coordinator, calls, "06:50", 19.9)
    assert room._preheat_in_progress["converged"]
    assert len(stored["a"]["samples"]) == 1
    assert (
        await _tick_room(hass, freezer, coordinator, calls, "06:55", 19.5)
        == NORMAL
    )


async def test_release_without_slope_near_the_target(hass, freezer, with_boost):
    """Under 10 min of readings and no learned rate: released within the
    convergence threshold."""
    freezer.move_to(_utc("06:00"))
    _set_room(hass, 17.0)
    _, coordinator, calls = await _setup(hass, _sensor_config())

    await _tick_room(hass, freezer, coordinator, calls, "06:00", 17.0)
    assert await _tick_room(
        hass, freezer, coordinator, calls, "06:05", 19.5
    ) == (NORMAL + 3.0)
    assert await _tick_room(
        hass, freezer, coordinator, calls, "06:06", 19.8
    ) == (NORMAL)
    assert coordinator.rooms["a"]._preheat_in_progress["released"]


async def test_within_anticipation_at_start_no_boost(hass, freezer, with_boost):
    """Learned 2 min/°C, 1 °C short: 2 min left ≤ 10 → never boosted,
    nothing to tune."""
    freezer.move_to(_utc("06:50"))
    _set_room(hass, 19.0)
    entry, coordinator, calls = await _setup(hass, _sensor_config())
    _seed_rate(entry, 2.0)

    assert await _tick_room(
        hass, freezer, coordinator, calls, "06:50", 19.0
    ) == (NORMAL)
    room = coordinator.rooms["a"]
    assert room._preheat_active
    assert room._preheat_in_progress["released"]
    assert not room._preheat_in_progress["boosted"]
    stored = entry.runtime_data.preheat_data["rooms"]["a"]
    assert not stored.get("observe")


async def test_boost_continues_while_measuring(hass, freezer, with_boost):
    """Not reached at 07:00: Normal gets the boost until released."""
    freezer.move_to(_utc("06:00"))
    _set_room(hass, 17.0)
    _, coordinator, calls = await _setup(hass, _sensor_config())

    await _tick_room(hass, freezer, coordinator, calls, "06:00", 17.0)
    room = coordinator.rooms["a"]
    assert await _tick_room(
        hass, freezer, coordinator, calls, "07:00", 18.0
    ) == (NORMAL + 3.0)
    assert room._preheat_in_progress["measuring"]
    assert room.current_period == PERIOD_NORMAL

    # Released and converged in the same tick: the measuring run ends.
    assert await _tick_room(
        hass, freezer, coordinator, calls, "07:10", 19.9
    ) == (NORMAL)
    assert not room._preheat_in_progress


async def test_boost_bounded_by_trv_max_temp(hass, freezer, with_boost):
    """A TRV capped at 21.5 °C never gets more."""
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
    _, coordinator, calls = await _setup(hass, _config())

    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    assert calls[-1].data["temperature"] == 21.5


async def test_no_boost_without_room_temperature(hass, freezer, with_boost):
    """No room reading → the plain target."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(TRV, "heat", {"temperature": REDUCED})
    _, coordinator, calls = await _setup(hass, _config())

    await coordinator.async_evaluate()
    await hass.async_block_till_done()
    assert coordinator.rooms["a"]._preheat_active
    assert calls[-1].data["temperature"] == NORMAL


# ---------------------------------------------------------------------------
# Heating speed and anticipation
# ---------------------------------------------------------------------------


def test_heating_slope_window():
    """Slope over the last 30 min (plus the reading at its start); unknown
    under 10 min of readings or when the room is not warming."""
    t0 = datetime(2026, 1, 5, 14, 0, tzinfo=timezone.utc)
    run = {"start_time": t0}

    def read(minutes: int, temp: float) -> None:
        add_reading(run, t0 + timedelta(minutes=minutes), temp)

    read(0, 17.0)
    assert heating_slope(run) is None
    read(5, 17.5)
    assert heating_slope(run) is None
    read(10, 17.5)
    assert heating_slope(run) == pytest.approx(0.05)
    for minutes, temp in ((20, 18.0), (40, 19.0), (50, 19.0)):
        read(minutes, temp)
    assert [r[0] for r in run["readings"]] == [20, 40, 50]
    assert heating_slope(run) == pytest.approx(1 / 30)
    read(60, 17.5)
    assert heating_slope(run) is None


@pytest.mark.parametrize(
    ("anticipation", "overshoot", "expected"),
    [
        (10, 0.5, 15),  # released too late → anticipate more
        (10, 0.2, 10),  # within tolerance → keep
        (10, -0.1, 10),
        (10, -0.3, 5),  # released too early → anticipate less
        (0, -1.0, 0),  # bounded low
        (60, 1.0, 60),  # bounded high
    ],
)
def test_tune_anticipation(anticipation, overshoot, expected):
    assert tune_anticipation(anticipation, overshoot) == expected


async def _release_at_0630(hass, freezer, config):
    """Boosted run released at 06:30 at 19.6 °C (4.6 min left)."""
    freezer.move_to(_utc("06:00"))
    _set_room(hass, 17.0)
    entry, coordinator, calls = await _setup(hass, config)
    for local, temp in (
        ("06:00", 17.0),
        ("06:10", 17.5),
        ("06:20", 18.5),
        ("06:30", 19.6),
    ):
        await _tick_room(hass, freezer, coordinator, calls, local, temp)
    assert coordinator.rooms["a"]._preheat_in_progress["released"]
    return entry, coordinator, calls


async def test_anticipation_raised_by_overshoot(
    hass, freezer, caplog, with_boost
):
    """Peaks 0.6 °C above within the hour after the release → 10 → 15."""
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    entry, coordinator, calls = await _release_at_0630(
        hass, freezer, _sensor_config()
    )
    stored = entry.runtime_data.preheat_data["rooms"]

    await _tick_room(hass, freezer, coordinator, calls, "06:45", NORMAL + 0.6)
    await _tick_room(hass, freezer, coordinator, calls, "07:10", NORMAL + 0.2)
    assert stored["a"]["observe"]["peak"] == NORMAL + 0.6
    assert "anticipation" not in stored["a"]

    await _tick_room(hass, freezer, coordinator, calls, "07:31", NORMAL + 0.2)
    assert stored["a"]["anticipation"] == 15
    assert stored["a"]["observe"] is None
    assert coordinator.rooms["a"].anticipation() == 15
    assert any(
        "anticipation=10→15min overshoot=+0.6°C" in m for m in caplog.messages
    )
    assert _status(coordinator)["preheat_anticipation"] == 15


async def test_anticipation_lowered_when_short(hass, freezer, with_boost):
    """Stalls 0.4 °C short of the target after the release → 10 → 5."""
    entry, coordinator, calls = await _release_at_0630(
        hass, freezer, _sensor_config()
    )

    await _tick_room(hass, freezer, coordinator, calls, "07:00", 19.6)
    await _tick_room(hass, freezer, coordinator, calls, "07:31", 19.6)
    assert entry.runtime_data.preheat_data["rooms"]["a"]["anticipation"] == 5


async def test_warmer_period_drops_the_overshoot_watch(
    hass, freezer, with_boost
):
    """A Comfort period during the window: the rise is not overshoot."""
    config = _sensor_config()
    for day in _DAYS:
        config["default_zone"]["time_program"][day] = [
            *MORNING_PROGRAM[day],
            {"start": "07:15", "mode": PERIOD_COMFORT},
        ]
    entry, coordinator, calls = await _release_at_0630(hass, freezer, config)
    stored = entry.runtime_data.preheat_data["rooms"]
    assert stored["a"]["observe"]

    await _tick_room(hass, freezer, coordinator, calls, "07:16", 21.5)
    await _tick_room(hass, freezer, coordinator, calls, "07:17", 21.5)

    assert stored["a"]["observe"] is None
    assert "anticipation" not in stored["a"]
