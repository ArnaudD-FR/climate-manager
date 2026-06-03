"""Smoke tests for Climate Manager integration entry point.

Tests:
- Integration loads to "loaded" state under pytest hass fixture
- entry.runtime_data is populated with ClimateManagerData
- Unloading the entry succeeds
- hass.data[DOMAIN] is NOT used (state lives on runtime_data)
- Phase 2: coordinator and cancel_scheduler are wired on setup (D-01, INFRA-03)
- Quick oo1: _async_auto_detect_matter_mappings auto-trigger on startup / rediscovery
"""

import copy
from unittest.mock import patch

from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.climate_manager.const import DEFAULT_CONFIG, DOMAIN
from custom_components.climate_manager import (
    ClimateManagerData,
    ClimateManagerCoordinator,
)


async def test_setup_entry_reaches_loaded_state(hass):
    """Integration loads without errors and reaches 'loaded' state.

    Phase 1 primary success criterion (INFRA-01).
    """
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state.value == "loaded"


async def test_setup_entry_runtime_data_populated(hass):
    """entry.runtime_data is a ClimateManagerData with all expected fields.

    Verifies store, runtime_config, rooms, and persons are present.
    """
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data is not None
    assert isinstance(entry.runtime_data, ClimateManagerData)
    assert hasattr(entry.runtime_data, "store")
    assert hasattr(entry.runtime_data, "runtime_config")
    assert hasattr(entry.runtime_data, "rooms")
    assert hasattr(entry.runtime_data, "persons")


async def test_setup_entry_runtime_config_is_default_on_fresh_install(hass):
    """runtime_config equals DEFAULT_CONFIG on fresh install (no prior storage)."""
    from custom_components.climate_manager.const import DEFAULT_CONFIG

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.runtime_config == DEFAULT_CONFIG


async def test_unload_entry_succeeds(hass):
    """Unloading the entry returns True and does not raise (Pitfall 1)."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(entry.entry_id)
    assert result is True


async def test_hass_data_domain_not_used(hass):
    """State lives on entry.runtime_data, not hass.data[DOMAIN] (T-01-11)."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # hass.data[DOMAIN] must not be set by the integration
    assert DOMAIN not in hass.data


async def test_setup_entry_coordinator_and_scheduler_wired(hass):
    """Phase 2: coordinator and cancel_scheduler are set after setup (D-01, INFRA-03).

    Verifies that async_setup_entry wires both the coordinator instance and
    the scheduler cancel callback into entry.runtime_data as required by Phase 2.
    """
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Coordinator must be an instance of ClimateManagerCoordinator (D-01)
    assert entry.runtime_data.coordinator is not None
    assert isinstance(entry.runtime_data.coordinator, ClimateManagerCoordinator)

    # cancel_scheduler must be set and callable (Pitfall 1 — stored for clean unload)
    assert entry.runtime_data.cancel_scheduler is not None
    assert callable(entry.runtime_data.cancel_scheduler)


# ---------------------------------------------------------------------------
# Tests: _async_auto_detect_matter_mappings auto-trigger (quick oo1)
# ---------------------------------------------------------------------------


def _setup_tado_matter_registry(hass, serial):
    """Register a matched Tado X + Matter device/entity pair.

    Returns the tado climate entity registry entry.
    """
    tado_entry = MockConfigEntry(domain="tado_x", data={})
    tado_entry.add_to_hass(hass)
    matter_entry = MockConfigEntry(domain="matter", data={})
    matter_entry.add_to_hass(hass)

    device_reg = dr.async_get(hass)
    entity_reg = er.async_get(hass)

    zone_device = device_reg.async_get_or_create(
        config_entry_id=tado_entry.entry_id,
        identifiers={("tado_x", "zone_" + serial)},
    )
    valve_device = device_reg.async_get_or_create(
        config_entry_id=tado_entry.entry_id,
        identifiers={("tado_x", serial)},
    )
    device_reg.async_update_device(
        valve_device.id, via_device_id=zone_device.id
    )
    matter_device = device_reg.async_get_or_create(
        config_entry_id=matter_entry.entry_id,
        identifiers={("matter", "serial_" + serial)},
    )
    tado_climate = entity_reg.async_get_or_create(
        domain="climate",
        platform="tado_x",
        unique_id="tado_climate_" + serial,
        config_entry=tado_entry,
        device_id=zone_device.id,
    )
    entity_reg.async_get_or_create(  # matter climate — exists for registry lookup
        domain="climate",
        platform="matter",
        unique_id="matter_climate_" + serial,
        config_entry=matter_entry,
        device_id=matter_device.id,
    )
    return tado_climate


async def test_auto_detect_on_startup_when_empty(hass):
    """On fresh entry (no matter_mappings), auto-detect populates mappings."""
    tado_climate = _setup_tado_matter_registry(hass, "VA1111111111")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    mappings = entry.runtime_data.runtime_config.get("matter_mappings", {})
    assert mappings, "matter_mappings must be non-empty after auto-detect"
    assert tado_climate.entity_id in mappings


async def test_auto_detect_skipped_on_startup_when_already_set(hass):
    """Pre-seeded matter_mappings must not be overwritten on startup."""
    manual_mappings = {"climate.tado_x_zone": ["climate.matter_x"]}
    pre_seeded = copy.deepcopy(DEFAULT_CONFIG)
    pre_seeded["matter_mappings"] = manual_mappings
    _setup_tado_matter_registry(hass, "VA2222222222")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.climate_manager.storage"
        ".ClimateManagerStore.async_load",
        return_value=pre_seeded,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    mappings = entry.runtime_data.runtime_config.get("matter_mappings", {})
    assert mappings == manual_mappings


async def test_auto_detect_on_registry_change_additive(hass):
    """Registry-change rediscovery adds new mappings without removing manual ones."""
    tado_climate = _setup_tado_matter_registry(hass, "VA3333333333")

    manual_mappings = {"climate.existing": ["climate.manual"]}
    pre_seeded = copy.deepcopy(DEFAULT_CONFIG)
    pre_seeded["matter_mappings"] = manual_mappings

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)

    with patch(
        "custom_components.climate_manager.storage"
        ".ClimateManagerStore.async_load",
        return_value=pre_seeded,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    hass.bus.async_fire(
        EVENT_ENTITY_REGISTRY_UPDATED,
        {"action": "create", "entity_id": tado_climate.entity_id},
    )
    await hass.async_block_till_done()

    mappings = entry.runtime_data.runtime_config.get("matter_mappings", {})
    assert "climate.existing" in mappings
    assert mappings["climate.existing"] == ["climate.manual"]
    assert tado_climate.entity_id in mappings
