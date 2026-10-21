"""Tests for vendors/tado_x.py (Tado X valves, offsets, Matter pairing)."""

from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.vendors import (
    CalibrationTarget,
    accessory_models,
    cloud_polling,
    pairable_entities,
)
from custom_components.climate_manager.vendors.tado_x import TadoX

ZONE = "climate.tado_office"


def _register(hass, domain, platform, unique_id, device_id=None, entry=None):
    return er.async_get(hass).async_get_or_create(
        domain,
        platform,
        unique_id,
        config_entry=entry,
        device_id=device_id,
    )


def _valve(hass, entry, serial, area_id, name="Valve"):
    device_reg = dr.async_get(hass)
    device = device_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("tado_x", serial)},
        model="Radiator Valve X",
        name=name,
    )
    return device_reg.async_update_device(device.id, area_id=area_id)


def _matter_climate(hass, serial):
    entry = MockConfigEntry(domain="matter", data={})
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("matter", f"serial_{serial}")},
    )
    return _register(hass, "climate", "matter", f"m_{serial}", device.id)


def _setup_room(hass):
    """Office area with a tado_x zone entity and two valves."""
    area = ar.async_get(hass).async_create("Office")
    entry = MockConfigEntry(domain="tado_x", data={})
    entry.add_to_hass(hass)
    zone = _register(hass, "climate", "tado_x", "zone_office", entry=entry)
    hass.states.async_set(zone.entity_id, "heat", {"current_temperature": 21})
    v1 = _valve(hass, entry, "VA1", area.id, "Valve 1")
    v2 = _valve(hass, entry, "VA2", area.id, "Valve 2")
    return area, entry, zone.entity_id, v1, v2


# ---------------------------------------------------------------------------
# calibration_targets
# ---------------------------------------------------------------------------


async def test_targets_one_per_valve_read_on_zone_entity(hass):
    """Without Matter, every valve is compared with the zone entity."""
    area, _, zone, v1, v2 = _setup_room(hass)

    targets = TadoX().calibration_targets(hass, area.id, [zone], {})

    assert {(t.key, t.name, t.temp_entity_id) for t in targets} == {
        (v1.id, "Valve 1", zone),
        (v2.id, "Valve 2", zone),
    }
    assert all(t.device_id == t.key and t.entity_id == zone for t in targets)


async def test_targets_read_on_matter_entity_of_same_serial(hass):
    """A paired valve is read on its own Matter entity, the other one on
    the zone's first paired entity."""
    area, _, zone, v1, v2 = _setup_room(hass)
    m1 = _matter_climate(hass, "VA1").entity_id
    other = _matter_climate(hass, "VA9").entity_id
    for eid in (m1, other):
        hass.states.async_set(eid, "heat", {"current_temperature": 20})

    targets = TadoX().calibration_targets(
        hass, area.id, [zone], {zone: [other, m1]}
    )

    by_key = {t.key: t.temp_entity_id for t in targets}
    assert by_key == {v1.id: m1, v2.id: other}


async def test_targets_fall_back_to_zone_entity_without_valves(hass):
    """No valve device known: one entity-based target per zone entity."""
    entry = MockConfigEntry(domain="tado_x", data={})
    entry.add_to_hass(hass)
    zone = _register(hass, "climate", "tado_x", "zone_x", entry=entry)
    hass.states.async_set(zone.entity_id, "heat", {})

    targets = TadoX().calibration_targets(
        hass, "office", [zone.entity_id], {zone.entity_id: ["climate.m"]}
    )

    assert targets == [
        CalibrationTarget(
            vendor=targets[0].vendor,
            key=zone.entity_id,
            name=zone.entity_id.split(".", 1)[1],
            temp_entity_id="climate.m",
            entity_id=zone.entity_id,
        )
    ]


async def test_no_targets_for_other_brands(hass):
    """Entities of another integration are not Tado X targets."""
    other = _register(hass, "climate", "other", "trv_1")
    hass.states.async_set(other.entity_id, "heat", {"temperature_offset": 0})

    assert TadoX().calibration_targets(hass, "a", [other.entity_id], {}) == []


# ---------------------------------------------------------------------------
# read_offset / write_offset
# ---------------------------------------------------------------------------


async def test_read_offset_from_valve_sensor(hass):
    area, entry, _, v1, _ = _setup_room(hass)
    sensor = _register(
        hass, "sensor", "tado_x", "VA1_temperature_offset", v1.id, entry
    )
    hass.states.async_set(sensor.entity_id, "-1.2")
    target = CalibrationTarget(TadoX(), v1.id, "V", ZONE, device_id=v1.id)

    assert TadoX().read_offset(hass, target) == -1.2


async def test_read_offset_unknown_without_sensor(hass):
    _, _, _, v1, _ = _setup_room(hass)
    target = CalibrationTarget(TadoX(), v1.id, "V", ZONE, device_id=v1.id)

    assert TadoX().read_offset(hass, target) is None


async def test_read_offset_of_zone_entity_from_attribute(hass):
    hass.states.async_set(ZONE, "heat", {"temperature_offset": 0.5})
    target = CalibrationTarget(TadoX(), ZONE, "z", ZONE, entity_id=ZONE)

    assert TadoX().read_offset(hass, target) == 0.5


async def test_write_offset_by_device_rounds_to_one_decimal(hass):
    """The Tado X API rejects more than one decimal place."""
    calls = async_mock_service(hass, "tado_x", "set_temperature_offset")
    target = CalibrationTarget(TadoX(), "dev", "V", ZONE, device_id="dev")

    await TadoX().write_offset(hass, target, 0.15 + 0.07)

    assert [c.data for c in calls] == [{"device_id": "dev", "offset": 0.2}]


async def test_write_offset_by_zone_entity(hass):
    calls = async_mock_service(hass, "tado_x", "set_temperature_offset")
    hass.states.async_set(ZONE, "heat", {})
    target = CalibrationTarget(TadoX(), ZONE, "z", ZONE, entity_id=ZONE)

    await TadoX().write_offset(hass, target, 1.5)

    assert [c.data for c in calls] == [{"entity_id": ZONE, "offset": 1.5}]


async def test_write_offset_skips_unavailable_zone_entity(hass):
    calls = async_mock_service(hass, "tado_x", "set_temperature_offset")
    hass.states.async_set(ZONE, "unavailable", {})
    target = CalibrationTarget(TadoX(), ZONE, "z", ZONE, entity_id=ZONE)

    await TadoX().write_offset(hass, target, 1.0)

    assert calls == []


async def test_write_offset_without_service_is_silent(hass):
    target = CalibrationTarget(TadoX(), "dev", "V", ZONE, device_id="dev")

    await TadoX().write_offset(hass, target, 1.0)


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


async def test_valve_model_is_a_boiler_accessory(hass):
    assert "Radiator Valve X" in accessory_models()


async def test_pairable_entities_are_tado_x_climate_entities(hass):
    tado = _register(hass, "climate", "tado_x", "zone_p")
    other = _register(hass, "climate", "matter", "m_p")

    assert pairable_entities(hass, [tado.entity_id, other.entity_id]) == [
        tado.entity_id
    ]


async def test_cloud_polling_reads_tado_x_scan_interval(hass):
    entry = MockConfigEntry(domain="tado_x", data={})
    entry.add_to_hass(hass)

    class _Coordinator:
        _scan_interval = 2700

    hass.data["tado_x"] = {entry.entry_id: _Coordinator()}

    assert cloud_polling(hass) == [{"vendor": "Tado X", "interval": 2700}]


async def test_cloud_polling_empty_without_tado_x(hass):
    assert cloud_polling(hass) == []


# ---------------------------------------------------------------------------
# suggest_mappings: Matter pairing by valve serial
# ---------------------------------------------------------------------------


async def test_suggest_mappings_matches_by_serial(hass):
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

    result = TadoX().suggest_mappings(hass)

    assert tado_climate.entity_id in result
    assert matter_climate.entity_id in result[tado_climate.entity_id]


async def test_suggest_mappings_no_valve_subdevices(hass):
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

    result = TadoX().suggest_mappings(hass)

    assert result == {}


async def test_suggest_mappings_no_tado_x_entities(hass):
    """Test C: no tado_x climate entities in entity registry → returns {}."""
    entity_reg = er.async_get(hass)

    # Register only a non-tado_x climate entity
    entity_reg.async_get_or_create(
        domain="climate",
        platform="other_platform",
        unique_id="some_climate",
    )

    result = TadoX().suggest_mappings(hass)

    assert result == {}
