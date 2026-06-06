# SPDX-License-Identifier: MIT
"""Pytest fixtures for the use-case data generator (docs/use-cases/generate.py).

The generator is a docs tool, not a test, but it reuses the Home Assistant test
harness to drive the real coordinator. The `hass` fixture comes from the
``pytest-homeassistant-custom-component`` plugin (available everywhere); the
autouse fixtures that let a custom integration load are defined in
``tests/conftest.py`` and re-exported here so they apply to this directory too.
"""

from tests.conftest import (  # noqa: F401
    auto_enable_custom_integrations,
    filter_aiohttp_shutdown_threads,
    mock_hass_frontend,
)
