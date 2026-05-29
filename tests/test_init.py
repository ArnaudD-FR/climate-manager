"""Smoke tests for Climate Manager integration entry point.

Tests:
- Integration loads to "loaded" state under pytest hass fixture
- entry.runtime_data is populated with ClimateManagerData
- Unloading the entry succeeds
- hass.data[DOMAIN] is NOT used (state lives on runtime_data)
- Phase 2: coordinator and cancel_scheduler are wired on setup (D-01, INFRA-03)
"""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.climate_manager.const import DOMAIN
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
