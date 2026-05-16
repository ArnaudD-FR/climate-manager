"""Climate Manager auto-discovery helpers.

Provides discover_rooms and discover_persons using HA area and entity
registries — never the deprecated async_get_registry() (Pitfall 4).

Design decisions (from RESEARCH.md):
- Pattern 4: Area + Entity Registry Discovery
- D-12: Rooms auto-discovered from climate entities in HA areas
- D-13: Room ID = area.id from area registry
- D-14/D-15: Persons auto-discovered as all person.* entity_ids
- D-16: No explicit opt-in — all discovered entities are managed
- ROOM-02: Areas with no climate entity are silently excluded
- ROOM-03: Multiple TRVs per area supported (returns list of entity_ids)
- Open Question 3: Use entity_id.split(".")[0] == "climate" as safe primary
  filter (entity_id prefix always works; .domain may vary by HA version)
"""
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er


async def discover_rooms(hass: HomeAssistant) -> dict[str, list[str]]:
    """Return {area_id: [climate_entity_ids]} for areas with >= 1 climate entity.

    Areas with no climate entities are silently excluded (ROOM-02).
    The list value supports multiple TRVs per room (ROOM-03 storage model).
    Keys are HA area_ids (D-13).
    """
    area_reg = ar.async_get(hass)
    entity_reg = er.async_get(hass)

    rooms: dict[str, list[str]] = {}
    for area in area_reg.async_list_areas():
        # get_entries_for_area_id returns all registry entries for the area
        climate_entity_ids = [
            entry.entity_id
            for entry in entity_reg.entities.get_entries_for_area_id(area.id)
            # Safe primary filter: entity_id prefix is always reliable (Open Question 3 / A1)
            if entry.entity_id.split(".")[0] == "climate"
        ]
        if climate_entity_ids:
            # Only include areas that have >= 1 climate entity (ROOM-02)
            rooms[area.id] = climate_entity_ids

    return rooms


async def discover_persons(hass: HomeAssistant) -> list[str]:
    """Return a list of all person.* entity_ids from the entity registry.

    Uses entity_id prefix matching (D-14, D-15).
    No other entity domains are included.
    """
    entity_reg = er.async_get(hass)
    return [
        entry.entity_id
        for entry in entity_reg.entities.values()
        if entry.entity_id.split(".")[0] == "person"
    ]
