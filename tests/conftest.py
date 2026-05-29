"""Shared pytest fixtures for Climate Manager tests."""

import sys
import threading
import types
from pathlib import Path
from unittest.mock import patch

import pytest

# pytest-homeassistant-custom-component provides `hass` and
# `enable_custom_integrations` fixtures automatically via its plugin.


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for all tests in this package.

    Without this autouse fixture, HA's test harness blocks loading integrations
    from custom_components/ and tests fail with 'Integration not found'.
    """


@pytest.fixture(autouse=True)
def mock_hass_frontend():
    """Mock hass_frontend package for tests.

    The test venv does not install hass-frontend (the built web UI package).
    The homeassistant.components.frontend module imports hass_frontend at setup
    time; without this mock the 'frontend' dependency in manifest.json causes
    the integration to fail to load in tests.

    This mock provides the minimal interface (where()) that frontend/__init__.py
    requires so that the dependency chain
    climate_manager → panel_custom → frontend → hass_frontend
    can complete without the actual frontend bundle being present.
    """
    hass_frontend_mock = types.ModuleType("hass_frontend")
    # frontend/__init__.py calls hass_frontend.where() to locate static files.
    # Must return a Path object (frontend code does root_path / subpath).
    # Return the tests/ directory as a stand-in — it exists and has no HA frontend files.
    hass_frontend_mock.where = lambda: Path(__file__).parent
    with patch.dict(sys.modules, {"hass_frontend": hass_frontend_mock}):
        yield


@pytest.fixture(autouse=True)
def filter_aiohttp_shutdown_threads(monkeypatch):
    """Filter aiohttp _run_safe_shutdown_loop threads from verify_cleanup.

    When hass_ws_client is used, it starts the aiohttp HTTP server which spawns a
    daemon thread named '_run_safe_shutdown_loop' for graceful shutdown handling.
    This thread may still be alive when pytest-homeassistant-custom-component's
    verify_cleanup fixture checks for lingering threads, causing a spurious test failure.

    This fixture patches threading.enumerate() to exclude _run_safe_shutdown_loop
    daemon threads, allowing verify_cleanup to pass without false positives.
    """
    original_enumerate = threading.enumerate

    def _filtered_enumerate():
        return [
            t
            for t in original_enumerate()
            if not (t.daemon and "_run_safe_shutdown_loop" in t.name)
        ]

    monkeypatch.setattr(threading, "enumerate", _filtered_enumerate)
