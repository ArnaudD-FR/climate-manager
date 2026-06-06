# SPDX-License-Identifier: MIT
"""Generate use-case screenshot data from the real coordinator.

This is not a test in the assertion sense — it is a data generator that reuses
the Home Assistant test harness (the `hass` fixture + custom-integration
plugin). For every scenario under ``docs/use-cases/_scenarios/`` it:

1. sets the integration's runtime config to the scenario's user-authored config,
2. seeds the surrounding HA world (TRV temperatures, person entities, calendar
   events) exactly as the scenario declares it,
3. pins the clock to the scenario's moment and runs the real coordinator
   evaluation,
4. records ``coordinator._build_status_payload()`` — the genuine present-persons,
   per-room and per-zone periods, and pre-heat state — into
   ``docs/use-cases/<slug>/scenario.json``.

The browser harness (``docs/use-cases/_harness.html``) then renders the panel
from that JSON, and ``docs/screenshot.js`` pins the browser clock to the same
moment, so the screenshots are coherent by construction. No status values are
hand-written. See ``docs/use-cases/AGENT.md``.

Run via: ``make use-case-data`` (``.venv/bin/python -m pytest
tests/generate_use_cases.py``).
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import pathlib

from freezegun import freeze_time
from homeassistant.core import SupportsResponse
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.const import DOMAIN

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
_USE_CASES_DIR = _REPO_ROOT / "docs" / "use-cases"
_SCEN_DIR = _USE_CASES_DIR / "_scenarios"


def _load_scenarios() -> list[dict]:
    scenarios: list[dict] = []
    for path in sorted(_SCEN_DIR.glob("*.py")):
        if path.name.startswith("__"):
            continue
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "SCENARIO"):
            scenarios.append(module.SCENARIO)
    return scenarios


def _register_calendar(hass, calendars: dict) -> None:
    """Register a calendar.get_events handler returning scenario events."""

    async def _get_events(call):
        targets = call.data.get("entity_id") or []
        if isinstance(targets, str):
            targets = [targets]
        return {
            eid: {"events": calendars.get(eid, {}).get("events", [])}
            for eid in targets
        }

    hass.services.async_register(
        "calendar",
        "get_events",
        _get_events,
        supports_response=SupportsResponse.ONLY,
    )


async def _generate_one(hass, scenario: dict) -> pathlib.Path:
    now_dt = datetime.datetime.fromisoformat(scenario["now"])
    world = scenario["hass"]

    # Seed HA world: entity states (TRVs, persons, calendars).
    for entity_id, state in world["states"].items():
        hass.states.async_set(
            entity_id, state["state"], state.get("attributes", {})
        )

    # Mock the climate services the evaluation issues, plus calendar events.
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    _register_calendar(hass, scenario.get("calendars", {}))

    # Stand up the integration and inject the scenario config + discovery map.
    # Pin HA's timezone to UTC so schedule "HH:MM" values are interpreted in
    # UTC — the same clock the browser harness is pinned to (no tz drift).
    await hass.config.async_set_time_zone("UTC")

    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.runtime_config = scenario["config"]
    entry.runtime_data.rooms = scenario["rooms"]

    coord = entry.runtime_data.coordinator
    coord._build_domain_objects(scenario["config"])

    # Pin the clock and run the real evaluation.
    with freeze_time(now_dt):
        await coord.async_evaluate(now_dt)
        status = coord._build_status_payload()

    # Inject cosmetic, non-engine fields (display names, humidity).
    areas = world.get("areas", {})
    humidity = scenario.get("humidity", {})
    for room in status["rooms_status"]:
        area_id = room["area_id"]
        if area_id in areas:
            room["name"] = areas[area_id]["name"]
        if area_id in humidity:
            room["humidity"] = humidity[area_id]

    out = {
        "now": scenario["now"],
        "config": scenario["config"],
        "status": status,
        "hass": world,
    }
    folder = _USE_CASES_DIR / scenario["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    out_path = folder / "scenario.json"
    out_path.write_text(
        json.dumps(out, indent=2, default=str, ensure_ascii=False) + "\n"
    )

    # Clean up so the next scenario starts from a fresh entry.
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    return out_path


async def test_generate_use_cases(hass) -> None:
    """Generate scenario.json for every use case (data generator, not a test)."""
    scenarios = _load_scenarios()
    assert scenarios, "no scenarios found under docs/use-cases/_scenarios/"
    for scenario in scenarios:
        path = await _generate_one(hass, scenario)
        print(f"  wrote {path.relative_to(_REPO_ROOT)}")
