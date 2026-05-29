"""Tests for discovery.py (room + person registry discovery).

TDD RED phase: written before discovery.py exists.
Verifies Assumptions A1/A2 from RESEARCH.md:
  A1 - RegistryEntry has a .domain attribute usable for filtering
  A2 - AreaEntry has .id and .name attributes
"""

from homeassistant.helpers import area_registry as ar, entity_registry as er

from custom_components.climate_manager.discovery import (
    discover_persons,
    discover_rooms,
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
