"""Boiler control: heat while at least one room needs heat.

Tests:
- Normal / Comfort / Pre-heat periods switch the boiler on; Reduced, an
  empty room (presence mode) and a zone that is off do not
- switch / input_boolean use turn_on / turn_off; climate uses the
  configured hvac modes and is never pushed as a valve
- Commands only on demand changes; resync when the boiler comes back
- Min on / off durations, also from the entity's last_changed at startup
- Status payload, demand binary sensor, set_boiler_config WS command
"""

import logging

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.const import (
    DEFAULT_PERIOD_TEMPERATURES,
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_COMFORT,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
)

_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

TRV = "climate.a_trv"
SWITCH = "switch.boiler"
CLIMATE_BOILER = "climate.boiler"
DEMAND = "binary_sensor.climate_manager_boiler_demand"


def _program(*slots: tuple[str, str]) -> dict:
    """Same day program every day: (start, period) slots."""
    return {
        day: [{"start": start, "mode": mode} for start, mode in slots]
        for day in _DAYS
    }


# Reduced, Normal 07:00–08:00, then Reduced.
MORNING = _program(
    ("00:00", PERIOD_REDUCED),
    ("07:00", PERIOD_NORMAL),
    ("08:00", PERIOD_REDUCED),
)


def _utc(local_hhmm: str) -> str:
    """Monday 2026-01-05 local (US/Pacific test TZ, UTC-8) → UTC string."""
    hh, mm = (int(x) for x in local_hhmm.split(":"))
    return f"2026-01-05 {hh + 8:02d}:{mm:02d}:00"


def _config(
    boiler: dict | None,
    *,
    program: dict = MORNING,
    zone_mode: str = MODE_TIME_PROGRAM,
    persons: dict | None = None,
    preheat: bool = False,
) -> dict:
    config = {
        "version": 2,
        "default_zone": {
            "name": "Home",
            "mode": zone_mode,
            "time_program": program,
            "preheat_enabled": preheat,
        },
        "period_temperatures": dict(DEFAULT_PERIOD_TEMPERATURES),
        "rooms": {},
        "persons": persons or {},
        "zones": {},
    }
    if boiler is not None:
        config["boiler"] = boiler
    return config


def _switch_boiler(min_on: int = 0, min_off: int = 0) -> dict:
    return {
        "entity_id": SWITCH,
        "min_on_minutes": min_on,
        "min_off_minutes": min_off,
    }


class _Calls:
    """Mocked boiler / TRV service calls."""

    def __init__(self, hass) -> None:
        self.hvac = async_mock_service(hass, "climate", "set_hvac_mode")
        self.temp = async_mock_service(hass, "climate", "set_temperature")
        self.on = async_mock_service(hass, "switch", "turn_on")
        self.off = async_mock_service(hass, "switch", "turn_off")

    def boiler_hvac(self) -> list[str]:
        return [
            c.data["hvac_mode"]
            for c in self.hvac
            if c.data["entity_id"] == CLIMATE_BOILER
        ]


async def _setup(hass, config: dict, rooms: dict | None = None):
    calls = _Calls(hass)
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entry.runtime_data.runtime_config = config
    entry.runtime_data.rooms = rooms or {"a": [TRV]}
    return entry, entry.runtime_data.coordinator, calls


async def _tick(hass, freezer, coordinator, local: str) -> None:
    freezer.move_to(_utc(local))
    await coordinator.async_evaluate()
    await hass.async_block_till_done()


def _trv(hass, current: float = 17.0) -> None:
    hass.states.async_set(
        TRV,
        "heat",
        {"temperature": 18.0, "current_temperature": current, "max_temp": 30},
    )


async def test_switch_follows_room_demand(hass, freezer, caplog):
    """Normal 07:00–08:00 → on at 07:00, off at 08:00, no repeat calls."""
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    freezer.move_to(_utc("06:00"))
    _trv(hass)
    hass.states.async_set(SWITCH, "off")
    _, coordinator, calls = await _setup(hass, _config(_switch_boiler()))

    await _tick(hass, freezer, coordinator, "06:00")
    assert not calls.on and not calls.off

    await _tick(hass, freezer, coordinator, "07:00")
    assert [c.data["entity_id"] for c in calls.on] == [SWITCH]
    assert "boiler | on rooms=a" in caplog.messages
    assert coordinator.boiler.is_on is True

    await _tick(hass, freezer, coordinator, "07:30")
    assert len(calls.on) == 1 and not calls.off

    await _tick(hass, freezer, coordinator, "08:00")
    assert len(calls.off) == 1
    assert "boiler | off" in caplog.messages


async def test_one_room_is_enough(hass, freezer):
    """Room b in Comfort keeps the boiler on while room a is Reduced."""
    freezer.move_to(_utc("06:00"))
    _trv(hass)
    hass.states.async_set("climate.b_trv", "heat", {"max_temp": 30})
    hass.states.async_set(SWITCH, "off")
    config = _config(_switch_boiler())
    config["zones"] = {
        "z": {
            "name": "Living",
            "mode": MODE_TIME_PROGRAM,
            "time_program": _program(("00:00", PERIOD_COMFORT)),
        }
    }
    config["rooms"] = {"b": {"zone_id": "z"}}
    _, coordinator, calls = await _setup(
        hass, config, rooms={"a": [TRV], "b": ["climate.b_trv"]}
    )

    await _tick(hass, freezer, coordinator, "06:00")
    assert len(calls.on) == 1
    assert coordinator.boiler.demand_rooms == ["b"]
    await _tick(hass, freezer, coordinator, "07:00")
    assert coordinator.boiler.demand_rooms == ["a", "b"]
    await _tick(hass, freezer, coordinator, "08:00")
    assert len(calls.on) == 1 and not calls.off


async def test_zone_off_and_empty_room_do_not_heat(hass, freezer):
    """Zone off (frost) or an empty room in presence mode: no demand."""
    freezer.move_to(_utc("07:00"))
    _trv(hass)
    hass.states.async_set(SWITCH, "off")
    _, coordinator, calls = await _setup(
        hass, _config(_switch_boiler(), zone_mode=MODE_OFF)
    )
    await _tick(hass, freezer, coordinator, "07:00")
    assert not calls.on

    persons = {"person.x": {"mode": "force_absent", "room_ids": ["a"]}}
    coordinator._data.runtime_config = _config(
        _switch_boiler(),
        zone_mode=MODE_TIME_PROGRAM_PRESENCES,
        persons=persons,
    )
    await _tick(hass, freezer, coordinator, "07:01")
    assert coordinator.rooms["a"].current_period == PERIOD_REDUCED
    assert not calls.on


async def test_climate_boiler_uses_hvac_modes(hass, freezer):
    """Climate boiler: configured hvac modes, never a valve setpoint."""
    freezer.move_to(_utc("06:00"))
    _trv(hass)
    hass.states.async_set(
        CLIMATE_BOILER,
        "off",
        {"hvac_modes": ["off", "auto", "heat"], "max_temp": 30},
    )
    boiler = {
        "entity_id": CLIMATE_BOILER,
        "on_hvac_mode": "auto",
        "off_hvac_mode": "off",
        "min_on_minutes": 0,
        "min_off_minutes": 0,
    }
    # The boiler sits in the room's area (and looks like a TRV: max 30 °C).
    _, coordinator, calls = await _setup(
        hass, _config(boiler), rooms={"a": [TRV, CLIMATE_BOILER]}
    )

    await _tick(hass, freezer, coordinator, "07:00")
    assert calls.boiler_hvac() == ["auto"]
    hass.states.async_set(CLIMATE_BOILER, "auto", {"hvac_modes": ["off"]})
    await _tick(hass, freezer, coordinator, "08:00")
    assert calls.boiler_hvac() == ["auto", "off"]
    assert all(c.data["entity_id"] != CLIMATE_BOILER for c in calls.temp)


async def test_min_on_delays_switch_off(hass, freezer, caplog):
    """On at 07:00, demand gone at 07:05 → off only at 07:10 (min on 10)."""
    caplog.set_level(logging.INFO, logger="custom_components.climate_manager")
    freezer.move_to(_utc("06:00"))
    _trv(hass)
    hass.states.async_set(SWITCH, "off")
    program = _program(
        ("00:00", PERIOD_REDUCED),
        ("07:00", PERIOD_NORMAL),
        ("07:05", PERIOD_REDUCED),
    )
    _, coordinator, calls = await _setup(
        hass, _config(_switch_boiler(min_on=10), program=program)
    )

    await _tick(hass, freezer, coordinator, "07:00")
    assert len(calls.on) == 1
    await _tick(hass, freezer, coordinator, "07:05")
    assert not calls.off
    assert coordinator.boiler.waiting_until is not None
    assert "boiler | waiting min_on 5min" in caplog.messages
    await _tick(hass, freezer, coordinator, "07:09")
    assert not calls.off
    await _tick(hass, freezer, coordinator, "07:10")
    assert len(calls.off) == 1
    assert coordinator.boiler.waiting_until is None


async def test_startup_uses_last_changed_for_min_off(hass, freezer):
    """Switched off at 06:58 before the restart → on only at 07:08."""
    freezer.move_to(_utc("06:58"))
    hass.states.async_set(SWITCH, "off")
    freezer.move_to(_utc("07:00"))
    _trv(hass)
    _, coordinator, calls = await _setup(
        hass, _config(_switch_boiler(min_off=10))
    )

    await _tick(hass, freezer, coordinator, "07:00")
    assert not calls.on
    await _tick(hass, freezer, coordinator, "07:08")
    assert len(calls.on) == 1


async def test_startup_aligns_and_back_online_resyncs(hass, freezer):
    """Already on at startup → no call; back online while off → turn_on."""
    freezer.move_to(_utc("06:00"))
    hass.states.async_set(SWITCH, "on")
    _trv(hass)
    _, coordinator, calls = await _setup(hass, _config(_switch_boiler()))

    await _tick(hass, freezer, coordinator, "07:00")
    assert not calls.on and not calls.off

    hass.states.async_set(SWITCH, "unavailable")
    await hass.async_block_till_done()
    hass.states.async_set(SWITCH, "off")
    await hass.async_block_till_done()
    assert len(calls.on) == 1


async def test_preheat_turns_boiler_on_same_tick(hass, freezer):
    """A pre-heat started at 06:00 asks for heat at once."""
    freezer.move_to(_utc("06:00"))
    _trv(hass, current=17.0)
    hass.states.async_set(SWITCH, "off")
    _, coordinator, calls = await _setup(
        hass, _config(_switch_boiler(), preheat=True)
    )

    await _tick(hass, freezer, coordinator, "06:00")
    assert coordinator.rooms["a"]._preheat_active
    assert len(calls.on) == 1
    assert coordinator.boiler.demand_rooms == ["a"]


async def test_status_and_demand_sensor(hass, freezer):
    """Status payload and binary sensor follow the demand."""
    freezer.move_to(_utc("07:00"))
    _trv(hass)
    hass.states.async_set(SWITCH, "off")
    _, coordinator, _calls = await _setup(hass, _config(_switch_boiler()))

    await _tick(hass, freezer, coordinator, "07:00")
    status = coordinator._build_status_payload()["boiler"]
    assert status == {
        "entity_id": SWITCH,
        "on": True,
        "demand_rooms": ["a"],
        "waiting_until": None,
    }
    state = hass.states.get(DEMAND)
    assert state.state == "on"
    assert state.attributes["rooms"] == ["a"]

    await _tick(hass, freezer, coordinator, "08:00")
    assert hass.states.get(DEMAND).state == "off"

    coordinator._data.runtime_config.pop("boiler")
    await _tick(hass, freezer, coordinator, "08:01")
    assert coordinator._build_status_payload()["boiler"] is None


async def test_ws_set_boiler_config(hass, hass_ws_client):
    """Validation, defaults, and clearing."""
    hass.states.async_set(SWITCH, "off")
    hass.states.async_set(
        CLIMATE_BOILER, "off", {"hvac_modes": ["off", "heat"]}
    )
    hass.states.async_set("light.x", "off")
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client()

    async def send(**payload):
        await client.send_json_auto_id(
            {"type": f"{DOMAIN}/set_boiler_config", **payload}
        )
        return await client.receive_json()

    for bad in (
        {"entity_id": "light.x"},
        {"entity_id": "switch.missing"},
        {"entity_id": CLIMATE_BOILER, "on_hvac_mode": "auto"},
        {"entity_id": SWITCH, "min_on_minutes": 61},
    ):
        assert not (await send(**bad))["success"], bad
    assert "boiler" not in entry.runtime_data.runtime_config

    assert (await send(entity_id=CLIMATE_BOILER))["success"]
    assert entry.runtime_data.runtime_config["boiler"] == {
        "entity_id": CLIMATE_BOILER,
        "on_hvac_mode": "heat",
        "off_hvac_mode": "off",
        "min_on_minutes": 10,
        "min_off_minutes": 10,
    }

    assert (await send(entity_id=SWITCH, min_off_minutes=5))["success"]
    assert entry.runtime_data.runtime_config["boiler"] == {
        "entity_id": SWITCH,
        "min_on_minutes": 10,
        "min_off_minutes": 5,
    }

    assert (await send(entity_id=None))["success"]
    assert "boiler" not in entry.runtime_data.runtime_config
