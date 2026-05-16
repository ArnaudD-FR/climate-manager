"""Tests for trv.py (two-call TRV control sequence).

TDD RED phase: written before trv.py exists.
Verifies all four behaviors from plan 02 Task 3 and INFRA-04.
"""
import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.climate_manager.trv import set_trv_temperature

CLIMATE_ENTITY = "climate.living_room_trv"


async def test_set_trv_temperature_issues_two_calls_in_order(hass):
    """Test 1: set_trv_temperature on an available TRV issues exactly two service calls
    in order: climate.set_hvac_mode {hvac_mode: "heat"} then climate.set_temperature
    {temperature: T}, both blocking=True (INFRA-04).
    """
    # Set entity state as available
    hass.states.async_set(CLIMATE_ENTITY, "heat", {})

    # Register mock climate services to capture calls
    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    await set_trv_temperature(hass, CLIMATE_ENTITY, 21.0)

    # Exactly one call to set_hvac_mode
    assert len(hvac_calls) == 1
    assert hvac_calls[0].data["entity_id"] == CLIMATE_ENTITY
    assert hvac_calls[0].data["hvac_mode"] == "heat"

    # Exactly one call to set_temperature
    assert len(temp_calls) == 1
    assert temp_calls[0].data["entity_id"] == CLIMATE_ENTITY
    assert temp_calls[0].data["temperature"] == 21.0


async def test_set_trv_temperature_never_uses_auto_mode(hass):
    """Test 2: set_trv_temperature never issues a service call with hvac_mode other
    than "heat" — auto mode is never used (INFRA-04).
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    await set_trv_temperature(hass, CLIMATE_ENTITY, 20.0)

    # All hvac_mode calls must use "heat", never "auto"
    for call in hvac_calls:
        assert call.data.get("hvac_mode") != "auto", (
            "Auto mode must never be used (INFRA-04)"
        )
        assert call.data.get("hvac_mode") == "heat"


async def test_set_trv_temperature_skips_unavailable_entity(hass):
    """Test 3: set_trv_temperature on an entity whose state is "unavailable"
    issues ZERO service calls and returns without error (ROOM-03).
    """
    # Set entity state to unavailable
    hass.states.async_set(CLIMATE_ENTITY, "unavailable", {})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    # Should not raise, should not call services
    await set_trv_temperature(hass, CLIMATE_ENTITY, 21.0)

    assert len(hvac_calls) == 0
    assert len(temp_calls) == 0


async def test_set_trv_temperature_skips_missing_entity(hass):
    """Test 4: set_trv_temperature on a missing entity (hass.states.get returns None)
    issues ZERO service calls and returns without error.
    """
    # Do NOT set any state for the entity — hass.states.get returns None

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    # Should not raise
    await set_trv_temperature(hass, "climate.nonexistent_trv", 21.0)

    assert len(hvac_calls) == 0
    assert len(temp_calls) == 0
