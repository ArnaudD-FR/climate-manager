"""Shared pytest fixtures for Climate Manager tests."""
import pytest

# pytest-homeassistant-custom-component provides `hass` and
# `enable_custom_integrations` fixtures automatically via its plugin.


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests in this package.

    Without this autouse fixture, HA's test harness blocks loading integrations
    from custom_components/ and tests fail with 'Integration not found'.
    """
