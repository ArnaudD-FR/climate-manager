# SPDX-License-Identifier: MIT
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
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


async def discover_rooms(hass: HomeAssistant) -> dict[str, list[str]]:
    """Return {area_id: [climate_entity_ids]} for areas with >= 1 climate entity.

    Areas with no climate entities are silently excluded (ROOM-02).
    The list value supports multiple TRVs per room (ROOM-03 storage model).
    Keys are HA area_ids (D-13).

    Covers both assignment paths:
    - Direct entity → area (entity.area_id is set)
    - Device → area (device.area_id is set; entity.area_id is None and inherits)
    Most HA users assign areas at the device level, so the second path is critical.
    """
    area_reg = ar.async_get(hass)
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    # Pre-seed an entry for every known area (empty list = excluded later)
    known_area_ids: set[str] = {area.id for area in area_reg.async_list_areas()}
    rooms: dict[str, list[str]] = {area_id: [] for area_id in known_area_ids}
    seen: set[str] = set()

    # Pass 1: direct entity-level area assignment
    for entry in entity_reg.entities.values():
        if (
            entry.entity_id.split(".")[0] == "climate"
            and entry.area_id in known_area_ids
            and not entry.disabled_by
        ):
            rooms[entry.area_id].append(entry.entity_id)  # type: ignore[index]
            seen.add(entry.entity_id)

    # Pass 2: device-level area assignment (entity.area_id is None → inherit from device)
    for entry in entity_reg.entities.values():
        eid = entry.entity_id
        if (
            eid.split(".")[0] == "climate"
            and eid not in seen
            and not entry.disabled_by
            and entry.area_id is None
            and entry.device_id is not None
        ):
            device = device_reg.devices.get(entry.device_id)
            if device and device.area_id in known_area_ids:
                rooms[device.area_id].append(eid)  # type: ignore[index]
                seen.add(eid)

    # Exclude areas with no climate entities (ROOM-02)
    return {area_id: ids for area_id, ids in rooms.items() if ids}


async def discover_room_sensors(
    hass: HomeAssistant,
) -> dict[str, dict[str, str]]:
    """Return {area_id: {temperature: entity_id, humidity: entity_id}} for auto-discovered sensors.

    Finds the first sensor entity per area with device_class "temperature" or "humidity".
    Covers both direct entity → area and device → area assignment paths (same logic as discover_rooms).
    Used as a middle-tier fallback: configured override > auto-discovered > TRV built-in.
    """
    area_reg = ar.async_get(hass)
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    known_area_ids: set[str] = {area.id for area in area_reg.async_list_areas()}
    area_sensors: dict[str, list[str]] = {
        area_id: [] for area_id in known_area_ids
    }
    seen: set[str] = set()

    # Pass 1: direct entity-level area assignment
    for entry in entity_reg.entities.values():
        if (
            entry.entity_id.split(".")[0] == "sensor"
            and entry.area_id in known_area_ids
        ):
            area_sensors[entry.area_id].append(  # type: ignore[index]
                entry.entity_id
            )
            seen.add(entry.entity_id)

    # Pass 2: device-level area assignment
    for entry in entity_reg.entities.values():
        eid = entry.entity_id
        if (
            eid.split(".")[0] == "sensor"
            and eid not in seen
            and entry.area_id is None
            and entry.device_id is not None
        ):
            device = device_reg.devices.get(entry.device_id)
            if device and device.area_id in known_area_ids:
                area_sensors[device.area_id].append(eid)  # type: ignore[index]
                seen.add(eid)

    result: dict[str, dict[str, str]] = {}
    for area_id, sensor_ids in area_sensors.items():
        sensors: dict[str, str] = {}
        for eid in sensor_ids:
            state = hass.states.get(eid)
            if state is None:
                continue
            dc = state.attributes.get("device_class")
            if dc == "temperature" and "temperature" not in sensors:
                sensors["temperature"] = eid
            elif dc == "humidity" and "humidity" not in sensors:
                sensors["humidity"] = eid
            if len(sensors) == 2:
                break
        if sensors:
            result[area_id] = sensors

    return result


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


async def suggest_matter_mappings(
    hass: HomeAssistant,
) -> dict[str, list[str]]:
    """Return {tado_x_entity_id: [matter_entity_id, ...]} by matching
    Tado X valve serial numbers to Matter device identifiers.

    Algorithm:
    Step 1: Build serial → matter_entity_id lookup from Matter climate
            entities whose device has an identifier ("matter", "serial_*").
    Step 2: For each tado_x climate entity, find valve sub-devices via
            via_device_id, extract their tado_x identifiers as serials,
            and map to Matter entity_ids via the Step 1 lookup.
    """
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)

    # Step 1 — build serial → matter_entity_id lookup
    matter_serial_to_entity: dict[str, str] = {}
    for entry in entity_reg.entities.values():
        if (
            entry.entity_id.split(".")[0] != "climate"
            or entry.platform != "matter"
        ):
            continue
        device = (
            device_reg.async_get(entry.device_id) if entry.device_id else None
        )
        if device is None:
            continue
        for identifier in device.identifiers:
            if identifier[0] == "matter" and identifier[1].startswith(
                "serial_"
            ):
                serial = identifier[1][7:]  # strip "serial_" prefix
                matter_serial_to_entity[serial] = entry.entity_id

    # Step 2 — for each tado_x zone, find valve devices and map serials
    mappings: dict[str, list[str]] = {}
    for entry in entity_reg.entities.values():
        if (
            entry.entity_id.split(".")[0] != "climate"
            or entry.platform != "tado_x"
        ):
            continue
        zone_device_id = entry.device_id
        valve_devices = [
            d
            for d in device_reg.devices.values()
            if d.via_device_id == zone_device_id
        ]
        matter_eids: list[str] = []
        for valve in valve_devices:
            for identifier in valve.identifiers:
                if identifier[0] == "tado_x":
                    serial = identifier[1]
                    matter_eid = matter_serial_to_entity.get(serial)
                    if matter_eid:
                        matter_eids.append(matter_eid)
        if matter_eids:
            mappings[entry.entity_id] = matter_eids
    return mappings
