"""Tests for discovery.py (room + person registry discovery).

TDD RED phase: written before discovery.py exists.
Verifies Assumptions A1/A2 from RESEARCH.md:
  A1 - RegistryEntry has a .domain attribute usable for filtering
  A2 - AreaEntry has .id and .name attributes
"""

from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.climate_manager.discovery import (
    discover_persons,
    discover_rooms,
    suggest_matter_mappings,
)


async def test_discover_rooms_returns_climate_entities_by_area(hass):
    """Test 1: discover_rooms returns {area_id: [climate_entity_ids]} for areas
    that have >= 1 climate entity (ROOM-01).
    """
    area_reg = ar.async_get(hass)
    entity_reg = er.async_get(hass)

    # Create an area with one climate entity
    area = area_reg.async_create("Living Room")
    entity_entry = entity_reg.async_get_or_create(
        domain="climate",
        platform="test",
        unique_id="trv_living",
    )
    entity_reg.async_update_entity(entity_entry.entity_id, area_id=area.id)

    rooms = await discover_rooms(hass)

    assert area.id in rooms
    assert entity_entry.entity_id in rooms[area.id]


async def test_discover_rooms_excludes_area_with_no_climate_entity(hass):
    """Test 2: An area with no climate entity does NOT appear in results (ROOM-02)."""
    area_reg = ar.async_get(hass)
    entity_reg = er.async_get(hass)

    # Create an area with a non-climate entity only
    area = area_reg.async_create("Office")
    entity_entry = entity_reg.async_get_or_create(
        domain="light",
        platform="test",
        unique_id="office_light",
    )
    entity_reg.async_update_entity(entity_entry.entity_id, area_id=area.id)

    rooms = await discover_rooms(hass)

    assert area.id not in rooms


async def test_discover_rooms_supports_multiple_trvs_per_area(hass):
    """Test 3: An area with two climate entities returns both entity_ids (ROOM-03)."""
    area_reg = ar.async_get(hass)
    entity_reg = er.async_get(hass)

    area = area_reg.async_create("Bedroom")
    trv1 = entity_reg.async_get_or_create(
        domain="climate",
        platform="test",
        unique_id="trv_bedroom_1",
    )
    trv2 = entity_reg.async_get_or_create(
        domain="climate",
        platform="test",
        unique_id="trv_bedroom_2",
    )
    entity_reg.async_update_entity(trv1.entity_id, area_id=area.id)
    entity_reg.async_update_entity(trv2.entity_id, area_id=area.id)

    rooms = await discover_rooms(hass)

    assert area.id in rooms
    assert trv1.entity_id in rooms[area.id]
    assert trv2.entity_id in rooms[area.id]
    assert len(rooms[area.id]) == 2


async def test_discover_persons_returns_only_person_entity_ids(hass):
    """Test 4: discover_persons returns every person.* entity_id and excludes others."""
    entity_reg = er.async_get(hass)

    # Register a person entity
    person1 = entity_reg.async_get_or_create(
        domain="person",
        platform="test",
        unique_id="person_john",
    )
    # Register a non-person entity that should be excluded
    non_person = entity_reg.async_get_or_create(
        domain="light",
        platform="test",
        unique_id="kitchen_light",
    )

    persons = await discover_persons(hass)

    assert person1.entity_id in persons
    assert non_person.entity_id not in persons


# ---------------------------------------------------------------------------
# Tests: suggest_matter_mappings (Plan quick/260603-o8e)
# ---------------------------------------------------------------------------


async def test_suggest_matter_mappings_matches_by_serial(hass):
    """Test A: tado_x entity whose zone device has one valve sub-device with
    identifier ("tado_x", "VA3805450240"), and a matter entity whose device
    has identifier ("matter", "serial_VA3805450240") → returns
    {"climate.tado_zone": ["climate.matter_valve"]}.
    """
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    # Create mock config entries so device registry accepts config_entry_id
    tado_entry = MockConfigEntry(domain="tado_x", data={})
    tado_entry.add_to_hass(hass)
    matter_entry_cfg = MockConfigEntry(domain="matter", data={})
    matter_entry_cfg.add_to_hass(hass)

    # Create the tado_x zone device (parent)
    zone_device = device_reg.async_get_or_create(
        config_entry_id=tado_entry.entry_id,
        identifiers={("tado_x", "zone_1")},
        name="Living Room Zone",
    )

    # Create the valve sub-device (child via via_device_id)
    valve_device = device_reg.async_get_or_create(
        config_entry_id=tado_entry.entry_id,
        identifiers={("tado_x", "VA3805450240")},
        name="Valve 1",
    )
    device_reg.async_update_device(
        valve_device.id, via_device_id=zone_device.id
    )

    # Create the Matter device with the matching serial identifier
    matter_device = device_reg.async_get_or_create(
        config_entry_id=matter_entry_cfg.entry_id,
        identifiers={("matter", "serial_VA3805450240")},
        name="Matter Valve 1",
    )

    # Register tado_x climate entity on the zone device
    tado_climate = entity_reg.async_get_or_create(
        domain="climate",
        platform="tado_x",
        unique_id="tado_zone_lr",
    )
    entity_reg.async_update_entity(
        tado_climate.entity_id, device_id=zone_device.id
    )

    # Register matter climate entity on the matter device
    matter_climate = entity_reg.async_get_or_create(
        domain="climate",
        platform="matter",
        unique_id="matter_valve_lr",
    )
    entity_reg.async_update_entity(
        matter_climate.entity_id, device_id=matter_device.id
    )

    result = await suggest_matter_mappings(hass)

    assert tado_climate.entity_id in result
    assert matter_climate.entity_id in result[tado_climate.entity_id]


async def test_suggest_matter_mappings_no_valve_subdevices(hass):
    """Test B: tado_x entity whose zone device has no valve sub-devices
    (via_device_id does not match) → returns {}.
    """
    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    # Create a mock config entry for device registry
    tado_entry = MockConfigEntry(domain="tado_x", data={})
    tado_entry.add_to_hass(hass)

    # Create the tado_x zone device (no children)
    zone_device = device_reg.async_get_or_create(
        config_entry_id=tado_entry.entry_id,
        identifiers={("tado_x", "zone_2")},
        name="Bedroom Zone",
    )

    # Create a valve device that does NOT point to zone_device
    # (via_device_id left unset — not a child of zone_device)
    device_reg.async_get_or_create(
        config_entry_id=tado_entry.entry_id,
        identifiers={("tado_x", "VA9999999999")},
        name="Unrelated Valve",
    )

    # Register tado_x climate entity on the zone device
    tado_climate = entity_reg.async_get_or_create(
        domain="climate",
        platform="tado_x",
        unique_id="tado_zone_bedroom",
    )
    entity_reg.async_update_entity(
        tado_climate.entity_id, device_id=zone_device.id
    )

    result = await suggest_matter_mappings(hass)

    assert result == {}


async def test_suggest_matter_mappings_no_tado_x_entities(hass):
    """Test C: no tado_x climate entities in entity registry → returns {}."""
    entity_reg = er.async_get(hass)

    # Register only a non-tado_x climate entity
    entity_reg.async_get_or_create(
        domain="climate",
        platform="other_platform",
        unique_id="some_climate",
    )

    result = await suggest_matter_mappings(hass)

    assert result == {}
