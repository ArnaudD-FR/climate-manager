"""Tests for vendors/vicare.py and the boiler readings helper."""

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.climate_manager.vendors import (
    BoilerReadings,
    boiler_readings,
    boiler_vendor,
)

BOILER = "climate.vitodens_heating"
PREFIX = "7724_7956"


def _vicare(hass, *, circuit_flow=True):
    """A ViCare boiler: heating circuit climate + device sensors."""
    entry = MockConfigEntry(domain="vicare", data={})
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("vicare", PREFIX)}
    )
    reg = er.async_get(hass)

    def register(domain, key, unique_id, entity_id, state):
        reg.async_get_or_create(
            domain,
            "vicare",
            f"{PREFIX}-{unique_id}",
            config_entry=entry,
            device_id=device.id,
            translation_key=key,
            suggested_object_id=entity_id.split(".", 1)[1],
        )
        if state is not None:
            hass.states.async_set(entity_id, state)

    register("climate", "heating", "heating-0", BOILER, None)
    hass.states.async_set(
        BOILER,
        "auto",
        {
            "heating_curve_slope": 1.4,
            "heating_curve_shift": 6,
            "active_vicare_program": "normal",
        },
    )
    register(
        "sensor",
        "outside_temperature",
        "outside_temperature",
        "sensor.vitodens_outside",
        "11.5",
    )
    register(
        "sensor",
        "boiler_supply_temperature",
        "boiler_supply_temperature",
        "sensor.vitodens_boiler_supply",
        "60.0",
    )
    if circuit_flow:
        register(
            "sensor",
            "supply_temperature",
            "supply_temperature-1",
            "sensor.vitodens_supply_1",
            "35.0",
        )
        register(
            "sensor",
            "supply_temperature",
            "supply_temperature-0",
            "sensor.vitodens_supply_0",
            "51.4",
        )


async def test_vicare_readings(hass):
    """Curve and program from the climate, sensors of the same circuit."""
    _vicare(hass)
    assert boiler_vendor(hass, BOILER).label == "ViCare"
    assert boiler_readings(hass, {"entity_id": BOILER}) == BoilerReadings(
        outdoor_temp=11.5,
        flow_temp=51.4,
        curve_slope=1.4,
        curve_shift=6.0,
        program="normal",
    )


async def test_vicare_boiler_level_flow_fallback(hass):
    _vicare(hass, circuit_flow=False)
    assert boiler_readings(hass, {"entity_id": BOILER}).flow_temp == 60.0


async def test_other_boiler_and_sensor_overrides(hass):
    """No vendor: empty readings; the config sensors fill or override."""
    hass.states.async_set("switch.boiler", "on")
    hass.states.async_set("sensor.outdoor", "4.5")
    hass.states.async_set("sensor.flow", "unavailable")
    assert boiler_vendor(hass, "switch.boiler") is None
    assert boiler_readings(hass, None) == BoilerReadings()
    assert (
        boiler_readings(hass, {"entity_id": "switch.boiler"})
        == BoilerReadings()
    )
    assert boiler_readings(
        hass,
        {
            "entity_id": "switch.boiler",
            "outdoor_temperature_entity_id": "sensor.outdoor",
            "flow_temperature_entity_id": "sensor.flow",
        },
    ) == BoilerReadings(outdoor_temp=4.5)

    _vicare(hass)
    readings = boiler_readings(
        hass,
        {
            "entity_id": BOILER,
            "outdoor_temperature_entity_id": "sensor.outdoor",
        },
    )
    assert (readings.outdoor_temp, readings.flow_temp) == (4.5, 51.4)
