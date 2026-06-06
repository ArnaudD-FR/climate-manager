# SPDX-License-Identifier: MIT
"""Generate use-case screenshot data from the real coordinator.

This is not a test in the assertion sense — it is a data generator that reuses
the Home Assistant test harness (the `hass` fixture + custom-integration
plugin). For every ``docs/use-cases/<slug>/scenario.py`` it:

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
docs/use-cases/generate.py``).
"""

from __future__ import annotations

import copy
import datetime
import importlib.util
import json
import pathlib

from freezegun import freeze_time
from homeassistant.components import frontend
from homeassistant.core import SupportsResponse
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_manager.const import DOMAIN

_USE_CASES_DIR = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = _USE_CASES_DIR.parents[1]


def _load_scenarios() -> list[dict]:
    """Load every ``docs/use-cases/<slug>/scenario.py`` SCENARIO dict."""
    scenarios: list[dict] = []
    for path in sorted(_USE_CASES_DIR.glob("*/scenario.py")):
        mod_name = f"scenario_{path.parent.name.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(mod_name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "SCENARIO"):
            scenarios.append(module.SCENARIO)
    return scenarios


def _variants(scenario: dict) -> list[dict]:
    """Return the scenario's variants.

    A scenario may declare ``variants`` — a list of ``{id, now, caption,
    states}`` showing the same configuration at different moments / world
    states (e.g. a person present vs. away). Legacy single-moment scenarios
    (no ``variants`` key) yield one variant with ``id=None`` written to the
    old ``scenario.json`` filename for back-compat.
    """
    if "variants" in scenario:
        return scenario["variants"]
    return [{"id": None, "now": scenario["now"]}]


def _merge_states(base: dict, overrides: dict) -> dict:
    """Deep-merge per-variant state overrides onto the base world states."""
    merged = copy.deepcopy(base)
    for entity_id, override in overrides.items():
        if entity_id in merged:
            if "state" in override:
                merged[entity_id]["state"] = override["state"]
            if "attributes" in override:
                merged[entity_id].setdefault("attributes", {}).update(
                    override["attributes"]
                )
        else:
            merged[entity_id] = copy.deepcopy(override)
    return merged


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


async def _generate_variant(
    hass, scenario: dict, variant: dict
) -> pathlib.Path:
    """Generate one variant's scenario.json with a fresh integration setup.

    Each variant gets its own setup → evaluate → teardown so no coordinator
    state (cached calendar presence, pre-heat baselines) can leak between a
    use case's present/away moments.
    """
    world = scenario["hass"]
    areas = world.get("areas", {})
    humidity = scenario.get("humidity", {})
    now_dt = datetime.datetime.fromisoformat(variant["now"])
    states = _merge_states(world["states"], variant.get("states", {}))

    # Seed the HA world for this variant (TRVs, persons, trackers).
    for entity_id, state in states.items():
        hass.states.async_set(
            entity_id, state["state"], state.get("attributes", {})
        )

    # Mock the climate services the evaluation issues, plus calendar events.
    # These handlers are stateless; re-registering per variant just overwrites.
    # A variant may override the calendar event set (e.g. a canceled class) via
    # its own "calendars"; otherwise the scenario-level calendars are used.
    async_mock_service(hass, "climate", "set_temperature")
    async_mock_service(hass, "climate", "set_hvac_mode")
    _register_calendar(
        hass, variant.get("calendars", scenario.get("calendars", {}))
    )

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
    for room in status["rooms_status"]:
        area_id = room["area_id"]
        if area_id in areas:
            room["name"] = areas[area_id]["name"]
        if area_id in humidity:
            room["humidity"] = humidity[area_id]

    variant_world = dict(world)
    variant_world["states"] = states
    out = {
        "now": variant["now"],
        "variant": variant["id"],
        "caption": variant.get("caption", ""),
        "config": scenario["config"],
        "status": status,
        "hass": variant_world,
    }
    folder = _USE_CASES_DIR / scenario["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    name = (
        "scenario.json"
        if variant["id"] is None
        else f"scenario.{variant['id']}.json"
    )
    out_path = folder / name
    out_path.write_text(
        json.dumps(out, indent=2, default=str, ensure_ascii=False) + "\n"
    )

    # Tear down so the next variant / scenario starts fresh. The integration
    # registers a sidebar panel on setup but does not remove it on unload, so
    # drop it here to avoid an "Overwriting panel" error on the next setup.
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    frontend.async_remove_panel(hass, DOMAIN)
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    return out_path


async def _generate_one(hass, scenario: dict) -> list[pathlib.Path]:
    return [
        await _generate_variant(hass, scenario, variant)
        for variant in _variants(scenario)
    ]


async def test_generate_use_cases(hass) -> None:
    """Generate scenario.json for every use case (data generator, not a test)."""
    scenarios = _load_scenarios()
    assert scenarios, "no docs/use-cases/<slug>/scenario.py files found"
    for scenario in scenarios:
        paths = await _generate_one(hass, scenario)
        for path in paths:
            print(f"  wrote {path.relative_to(_REPO_ROOT)}")
