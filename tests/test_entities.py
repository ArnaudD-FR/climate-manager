# SPDX-License-Identifier: MIT
"""Tests for the Climate Manager HA entities (select + sensor platforms).

Scenarios:
- Setup creates a zone device with a mode select and a period sensor for
  the Default Zone.
- select.select_option persists the zone mode and updates the entities.
- A mode change from the panel (set_zone_mode WS) updates the select.
- Zone lifecycle via WS: create adds entities, rename updates the device
  name, delete removes the device and its entities.
- Room period sensors: in time_program_presences mode each room reports
  its presence-resolved period while the zone reports the schedule period.
- Unloading the entry makes the entities unavailable.
"""

import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.const import (
    DOMAIN,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
    PERIOD_NORMAL,
    PERIOD_REDUCED,
)

# Monday 16:30 UTC = 08:30 US/Pacific (test harness TZ). The default
# weekday program is Reduced from 08:00 to 17:00.
MONDAY_0830 = "2026-01-05 16:30:00"

# Reduced 00:00-07:00, Normal 07:00-22:00, Reduced 22:00+ — every day.
_DAY = [
    {"start": "00:00", "mode": PERIOD_REDUCED},
    {"start": "07:00", "mode": PERIOD_NORMAL},
    {"start": "22:00", "mode": PERIOD_REDUCED},
]
NORMAL_DAYTIME_PROGRAM = {
    day: list(_DAY) for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
}


async def _setup_entry(hass) -> MockConfigEntry:
    """Set up the integration entry and return it."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _entity_id(hass, platform: str, entry, suffix: str) -> str | None:
    """Resolve an entity_id from its unique_id suffix."""
    return er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{suffix}"
    )


def _device(hass, entry, identifier: str):
    return dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, identifier), entry.entry_id
    )


@pytest.mark.freeze_time(MONDAY_0830)
async def test_default_zone_entities_created(hass):
    """Default Zone gets a device with a mode select and a period sensor."""
    entry = await _setup_entry(hass)

    select_id = _entity_id(hass, "select", entry, "zone_default_mode")
    sensor_id = _entity_id(hass, "sensor", entry, "zone_default_period")
    assert select_id == "select.home_mode"
    assert sensor_id == "sensor.home_period"

    select_state = hass.states.get(select_id)
    assert select_state.state == MODE_TIME_PROGRAM
    assert select_state.attributes["options"] == [
        MODE_OFF,
        MODE_TIME_PROGRAM,
        MODE_TIME_PROGRAM_PRESENCES,
    ]
    sensor_state = hass.states.get(sensor_id)
    assert sensor_state.state == PERIOD_REDUCED
    assert sensor_state.attributes["device_class"] == "enum"

    device = _device(hass, entry, "zone_default")
    assert device is not None
    assert device.name == "Home"
    assert device.model == "Heating zone"


@pytest.mark.freeze_time(MONDAY_0830)
async def test_select_option_sets_zone_mode(hass):
    """select.select_option persists the mode and re-evaluates the zone."""
    entry = await _setup_entry(hass)
    entry.runtime_data.store.async_save = _async_noop

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": "select.home_mode", "option": MODE_OFF},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.runtime_config["default_zone"]["mode"] == MODE_OFF
    assert hass.states.get("select.home_mode").state == MODE_OFF
    assert hass.states.get("sensor.home_period").state == (
        PERIOD_FROST_PROTECTION
    )


@pytest.mark.freeze_time(MONDAY_0830)
async def test_select_option_save_failure_raises(hass):
    """A store failure surfaces as HomeAssistantError and rolls back."""
    from homeassistant.exceptions import HomeAssistantError

    entry = await _setup_entry(hass)

    async def _fail(_config):
        raise OSError("disk full")

    entry.runtime_data.store.async_save = _fail

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.home_mode", "option": MODE_OFF},
            blocking=True,
        )
    config = entry.runtime_data.runtime_config
    assert config["default_zone"]["mode"] == MODE_TIME_PROGRAM
    assert hass.states.get("select.home_mode").state == MODE_TIME_PROGRAM


@pytest.mark.freeze_time(MONDAY_0830)
async def test_ws_set_zone_mode_updates_select(hass, hass_ws_client):
    """A mode change from the panel is reflected by the select entity."""
    await _setup_entry(hass)
    client = await hass_ws_client()

    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/set_zone_mode",
            "zone_id": "default",
            "mode": MODE_TIME_PROGRAM_PRESENCES,
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    await hass.async_block_till_done()

    assert hass.states.get("select.home_mode").state == (
        MODE_TIME_PROGRAM_PRESENCES
    )


@pytest.mark.freeze_time(MONDAY_0830)
async def test_zone_lifecycle_create_rename_delete(hass, hass_ws_client):
    """Zone entities follow create / rename / delete from the panel."""
    entry = await _setup_entry(hass)
    client = await hass_ws_client()

    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/create_zone", "name": "Upstairs"}
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    zone_id = msg["result"]["zone_id"]
    await hass.async_block_till_done()

    select_id = _entity_id(hass, "select", entry, f"zone_{zone_id}_mode")
    sensor_id = _entity_id(hass, "sensor", entry, f"zone_{zone_id}_period")
    assert select_id == "select.upstairs_mode"
    assert sensor_id == "sensor.upstairs_period"
    assert hass.states.get(select_id).state == MODE_TIME_PROGRAM
    assert hass.states.get(sensor_id).state == PERIOD_REDUCED
    assert _device(hass, entry, f"zone_{zone_id}").name == "Upstairs"

    # Rename: device name follows; entity_id is stable.
    await client.send_json_auto_id(
        {
            "type": f"{DOMAIN}/rename_zone",
            "zone_id": zone_id,
            "name": "First floor",
        }
    )
    assert (await client.receive_json())["success"] is True
    await hass.async_block_till_done()
    assert _device(hass, entry, f"zone_{zone_id}").name == "First floor"
    assert hass.states.get(select_id).attributes["friendly_name"] == (
        "First floor Mode"
    )

    # Delete: device and entities are removed from the registries.
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/delete_zone", "zone_id": zone_id}
    )
    assert (await client.receive_json())["success"] is True
    await hass.async_block_till_done()

    assert _device(hass, entry, f"zone_{zone_id}") is None
    assert _entity_id(hass, "select", entry, f"zone_{zone_id}_mode") is None
    assert _entity_id(hass, "sensor", entry, f"zone_{zone_id}_period") is None
    assert hass.states.get(select_id) is None
    assert hass.states.get(sensor_id) is None
    # Default Zone entities are untouched.
    assert hass.states.get("select.home_mode").state == MODE_TIME_PROGRAM


@pytest.mark.freeze_time(MONDAY_0830)
async def test_room_period_sensors_in_presence_mode(hass):
    """Rooms report presence-resolved periods; zone reports the schedule."""
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    area_reg = ar.async_get(hass)
    entity_reg = er.async_get(hass)
    for name in ("Lounge", "Bedroom"):
        area = area_reg.async_create(name)
        slug = name.lower()
        reg_entry = entity_reg.async_get_or_create(
            "climate", "test", f"{slug}_trv", suggested_object_id=f"{slug}_trv"
        )
        entity_reg.async_update_entity(reg_entry.entity_id, area_id=area.id)
        hass.states.async_set(
            reg_entry.entity_id, "heat", {"temperature": 15.0}
        )

    entry = await _setup_entry(hass)
    assert set(entry.runtime_data.rooms) == {"lounge", "bedroom"}

    config = entry.runtime_data.runtime_config
    config["default_zone"]["mode"] = MODE_TIME_PROGRAM_PRESENCES
    config["default_zone"]["time_program"] = NORMAL_DAYTIME_PROGRAM
    config["persons"] = {
        "person.alice": {
            "mode": "force_present",
            "room_ids": ["lounge"],
            "schedule": {},
        },
    }
    await entry.runtime_data.coordinator.async_evaluate()
    await hass.async_block_till_done()

    lounge_id = _entity_id(hass, "sensor", entry, "room_lounge_period")
    bedroom_id = _entity_id(hass, "sensor", entry, "room_bedroom_period")
    assert lounge_id == "sensor.lounge_period"
    assert bedroom_id == "sensor.bedroom_period"
    # Present person → Normal; empty room → Reduced (PERSON-09).
    assert hass.states.get(lounge_id).state == PERIOD_NORMAL
    assert hass.states.get(bedroom_id).state == PERIOD_REDUCED
    # Zone period is the schedule baseline, independent of room order.
    assert hass.states.get("sensor.home_period").state == PERIOD_NORMAL

    # Room devices are placed in their HA area.
    device = _device(hass, entry, "room_lounge")
    assert device is not None
    assert device.name == "Lounge"
    assert device.area_id == "lounge"
    assert hass.states.get(lounge_id).attributes["friendly_name"] == (
        "Lounge Period"
    )


@pytest.mark.freeze_time(MONDAY_0830)
async def test_unload_makes_entities_unavailable(hass):
    """Unloading the entry unloads the select/sensor platforms."""
    entry = await _setup_entry(hass)
    assert hass.states.get("select.home_mode").state == MODE_TIME_PROGRAM

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("select.home_mode").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.home_period").state == STATE_UNAVAILABLE


@pytest.mark.freeze_time(MONDAY_0830)
async def test_status_exposes_entity_ids(hass, hass_ws_client):
    """get_status resolves entity_ids from the registry for the panel."""
    async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    area = ar.async_get(hass).async_create("Lounge")
    entity_reg = er.async_get(hass)
    trv = entity_reg.async_get_or_create(
        "climate", "test", "lounge_trv", suggested_object_id="lounge_trv"
    )
    entity_reg.async_update_entity(trv.entity_id, area_id=area.id)
    hass.states.async_set(trv.entity_id, "heat", {"temperature": 15.0})

    entry = await _setup_entry(hass)
    client = await hass_ws_client()

    async def _get_status() -> dict:
        await client.send_json_auto_id({"type": f"{DOMAIN}/get_status"})
        msg = await client.receive_json()
        assert msg["success"] is True
        return msg["result"]

    status = await _get_status()
    assert status["zones"]["default"]["mode_entity_id"] == "select.home_mode"
    assert status["zones"]["default"]["period_entity_id"] == (
        "sensor.home_period"
    )
    lounge = next(r for r in status["rooms_status"] if r["area_id"] == "lounge")
    assert lounge["period_entity_id"] == "sensor.lounge_period"

    # A user-renamed entity_id is followed (never guessed by the panel).
    entity_reg.async_update_entity(
        "sensor.home_period", new_entity_id="sensor.house_period"
    )
    await hass.async_block_till_done()
    status = await _get_status()
    assert status["zones"]["default"]["period_entity_id"] == (
        "sensor.house_period"
    )

    # A new zone exposes its entity_ids once its entities are added.
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/create_zone", "name": "Upstairs"}
    )
    zone_id = (await client.receive_json())["result"]["zone_id"]
    await hass.async_block_till_done()
    status = await _get_status()
    assert status["zones"][zone_id]["mode_entity_id"] == (
        "select.upstairs_mode"
    )
    assert status["zones"][zone_id]["period_entity_id"] == (
        "sensor.upstairs_period"
    )
    assert entry.runtime_data.entry_id == entry.entry_id


async def _async_noop(_config) -> None:
    """Stand-in for store.async_save."""
