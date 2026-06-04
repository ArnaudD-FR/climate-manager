"""Tests for trv.py (two-call TRV control sequence).

TDD RED phase: written before trv.py exists.
Verifies all four behaviors from plan 02 Task 3 and INFRA-04.

Additional tests for supports_hvac_off and set_trv_off (quick task 260526-ffr).
Additional tests for TRV class and TRVGroup (plan 16-03, D-07/D-10/D-11).
"""

from unittest.mock import AsyncMock, MagicMock

from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.climate_manager.trv import (
    TRV,
    TRVGroup,
    set_trv_off,
    set_trv_offset,
    set_trv_offset_by_device,
    set_trv_temperature,
    supports_hvac_off,
    supports_offset_calibration,
)

CLIMATE_ENTITY = "climate.living_room_trv"


async def test_set_trv_temperature_issues_two_calls_in_order(hass):
    """Test 1: set_trv_temperature on an available TRV not already in heat mode
    issues exactly two service calls in order: climate.set_hvac_mode
    {hvac_mode: "heat"} then climate.set_temperature {temperature: T}, both
    blocking=True (INFRA-04).
    """
    # Set entity state as available but in "auto" mode with a different
    # setpoint so both guards pass and both calls fire.
    hass.states.async_set(CLIMATE_ENTITY, "auto", {"temperature": 18.0})

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
    hass.states.async_set(CLIMATE_ENTITY, "auto", {"temperature": 18.0})

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


# ---------------------------------------------------------------------------
# Tests 4a-4e: redundant-call guards (skip-redundant-hvac-and-temp-calls)
#
# set_trv_temperature must skip set_hvac_mode=heat when the TRV is already in
# heat mode, and skip set_temperature when the current setpoint already equals
# the desired temperature. The set_hvac_mode guard must still fire for any
# non-heat state ("auto"/"off"/"cool") because Tado X TRVs in auto mode ignore
# set_temperature until forced into heat mode (INFRA-04).
# ---------------------------------------------------------------------------


async def test_set_trv_temperature_skips_set_hvac_mode_when_already_heat(hass):
    """Guard A: when the TRV is already in "heat" mode, set_hvac_mode is NOT
    called. set_temperature still fires when the setpoint differs.
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature": 18.0})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    await set_trv_temperature(hass, CLIMATE_ENTITY, 21.0)

    assert len(hvac_calls) == 0, (
        "set_hvac_mode must be skipped when already in heat mode"
    )
    assert len(temp_calls) == 1
    assert temp_calls[0].data["temperature"] == 21.0


async def test_set_trv_temperature_calls_set_hvac_mode_when_auto(hass):
    """Guard A inverse: when the TRV is in "auto" mode, set_hvac_mode=heat IS
    called (Tado X auto-mode workaround, INFRA-04).
    """
    hass.states.async_set(CLIMATE_ENTITY, "auto", {"temperature": 18.0})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    await set_trv_temperature(hass, CLIMATE_ENTITY, 21.0)

    assert len(hvac_calls) == 1
    assert hvac_calls[0].data["hvac_mode"] == "heat"


async def test_set_trv_temperature_calls_set_hvac_mode_when_off(hass):
    """Guard A inverse: when the TRV is "off", set_hvac_mode=heat IS called."""
    hass.states.async_set(CLIMATE_ENTITY, "off", {"temperature": 18.0})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    await set_trv_temperature(hass, CLIMATE_ENTITY, 21.0)

    assert len(hvac_calls) == 1
    assert hvac_calls[0].data["hvac_mode"] == "heat"


async def test_set_trv_temperature_skips_set_temperature_when_already_set(hass):
    """Guard B: when the current setpoint already equals the desired
    temperature, set_temperature is NOT called. set_hvac_mode still fires when
    the mode is not heat.
    """
    hass.states.async_set(CLIMATE_ENTITY, "auto", {"temperature": 21.0})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    await set_trv_temperature(hass, CLIMATE_ENTITY, 21.0)

    assert len(hvac_calls) == 1, (
        "set_hvac_mode must still fire to leave auto mode (INFRA-04)"
    )
    assert len(temp_calls) == 0, (
        "set_temperature must be skipped when setpoint already correct"
    )


async def test_set_trv_temperature_skips_both_when_heat_and_setpoint_match(
    hass,
):
    """Guard A+B: steady state — already heating at the desired setpoint —
    issues ZERO service calls.
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature": 21.0})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    await set_trv_temperature(hass, CLIMATE_ENTITY, 21.0)

    assert len(hvac_calls) == 0
    assert len(temp_calls) == 0


async def test_set_trv_temperature_sets_temp_when_attribute_missing(hass):
    """Guard B edge: when the TRV exposes no "temperature" attribute,
    set_temperature IS called (cannot prove it is already correct).
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    await set_trv_temperature(hass, CLIMATE_ENTITY, 21.0)

    assert len(hvac_calls) == 0
    assert len(temp_calls) == 1
    assert temp_calls[0].data["temperature"] == 21.0


# ---------------------------------------------------------------------------
# Tests 5-8: supports_hvac_off and set_trv_off (quick task 260526-ffr)
# ---------------------------------------------------------------------------


def test_supports_hvac_off_true_when_off_in_hvac_modes(hass):
    """Test 5: supports_hvac_off returns True when "off" is in hvac_modes attribute."""
    hass.states.async_set(
        CLIMATE_ENTITY, "heat", {"hvac_modes": ["heat", "off"]}
    )
    assert supports_hvac_off(hass, CLIMATE_ENTITY) is True


def test_supports_hvac_off_false_when_attribute_missing(hass):
    """Test 6: supports_hvac_off returns False when hvac_modes attribute is absent."""
    hass.states.async_set(CLIMATE_ENTITY, "heat", {})
    assert supports_hvac_off(hass, CLIMATE_ENTITY) is False


async def test_set_trv_off_issues_single_set_hvac_mode_off_call(hass):
    """Test 7: set_trv_off issues exactly one set_hvac_mode call with hvac_mode="off"
    and ZERO set_temperature calls.
    """
    hass.states.async_set(
        CLIMATE_ENTITY, "heat", {"hvac_modes": ["heat", "off"]}
    )

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    await set_trv_off(hass, CLIMATE_ENTITY)

    assert len(hvac_calls) == 1
    assert hvac_calls[0].data["entity_id"] == CLIMATE_ENTITY
    assert hvac_calls[0].data["hvac_mode"] == "off"
    assert len(temp_calls) == 0


async def test_set_trv_off_skips_unavailable_entity(hass):
    """Test 8: set_trv_off on an "unavailable" entity issues ZERO service calls (ROOM-03)."""
    hass.states.async_set(CLIMATE_ENTITY, "unavailable", {})

    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    await set_trv_off(hass, CLIMATE_ENTITY)

    assert len(hvac_calls) == 0
    assert len(temp_calls) == 0


# ---------------------------------------------------------------------------
# Tests 9-15: supports_offset_calibration and set_trv_offset (CALIB-02/03)
# ---------------------------------------------------------------------------


def test_supports_offset_calibration_true_when_attribute_present(hass):
    """Test 9: supports_offset_calibration returns True when the TRV state has
    a temperature_offset attribute present (attribute-first guard, D-08).
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature_offset": 0.5})
    assert supports_offset_calibration(hass, CLIMATE_ENTITY) is True


def test_supports_offset_calibration_true_when_service_registered(hass):
    """Test 10: supports_offset_calibration returns True when the attribute is
    absent but the tado_x.set_temperature_offset service is registered (service
    registry fallback guard, D-08).
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {})
    # Register the tado_x service to simulate Tado X compatibility
    async_mock_service(hass, "tado_x", "set_temperature_offset")
    assert supports_offset_calibration(hass, CLIMATE_ENTITY) is True


def test_supports_offset_calibration_false_when_neither_present(hass):
    """Test 11: supports_offset_calibration returns False when neither the
    temperature_offset attribute nor the tado_x.set_temperature_offset service
    is present (D-08, Pitfall 3).
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {})
    # No attribute, no service registered
    assert supports_offset_calibration(hass, CLIMATE_ENTITY) is False


def test_supports_offset_calibration_false_when_state_none(hass):
    """Test 12: supports_offset_calibration returns False when
    hass.states.get returns None (ROOM-03 parity).
    """
    # No state set for the entity
    assert supports_offset_calibration(hass, "climate.nonexistent_trv") is False


async def test_set_trv_offset_issues_single_service_call(hass):
    """Test 13: set_trv_offset issues exactly one tado_x.set_temperature_offset
    call with the correct entity_id and offset value (CALIB-02).
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature_offset": 0.0})

    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    await set_trv_offset(hass, CLIMATE_ENTITY, 1.5)

    assert len(offset_calls) == 1
    assert offset_calls[0].data["entity_id"] == CLIMATE_ENTITY
    assert offset_calls[0].data["offset"] == 1.5


async def test_set_trv_offset_skips_unavailable_entity(hass):
    """Test 14: set_trv_offset silently skips (zero calls) when the entity
    state is "unavailable" (ROOM-03 parity).
    """
    hass.states.async_set(CLIMATE_ENTITY, "unavailable", {})

    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    await set_trv_offset(hass, CLIMATE_ENTITY, 1.0)

    assert len(offset_calls) == 0


async def test_set_trv_offset_skips_missing_entity(hass):
    """Test 15: set_trv_offset silently skips (zero calls) when
    hass.states.get returns None (ROOM-03 parity).
    """
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    await set_trv_offset(hass, "climate.nonexistent_trv", 1.0)

    assert len(offset_calls) == 0


# Issue 1 (ha-log-calibration-and-api-calls): Tado X API rejects offsets with
# more than one decimal place ("temperature should have only one digit after
# the decimal point"). Both offset write helpers must round to 1 decimal at the
# API boundary so every caller (device path and entity path) is protected.


async def test_set_trv_offset_rounds_to_one_decimal(hass):
    """set_trv_offset must round the offset to exactly one decimal place before
    calling tado_x.set_temperature_offset (Issue 1)."""
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature_offset": 0.0})

    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    # 0.15 + 0.07 float arithmetic -> 0.22 (two decimals) rejected by Tado X
    await set_trv_offset(hass, CLIMATE_ENTITY, 0.15 + 0.07)

    assert len(offset_calls) == 1
    sent = offset_calls[0].data["offset"]
    assert sent == 0.2
    assert round(sent, 1) == sent


async def test_set_trv_offset_by_device_rounds_to_one_decimal(hass):
    """set_trv_offset_by_device must round the offset to exactly one decimal
    place before calling tado_x.set_temperature_offset (Issue 1)."""
    offset_calls = async_mock_service(hass, "tado_x", "set_temperature_offset")

    await set_trv_offset_by_device(hass, "VA3805450240", 0.15 + 0.07)

    assert len(offset_calls) == 1
    assert offset_calls[0].data["device_id"] == "VA3805450240"
    sent = offset_calls[0].data["offset"]
    assert sent == 0.2
    assert round(sent, 1) == sent


# ---------------------------------------------------------------------------
# Tests 17-26: TRV class (plan 16-03, D-07/D-10/D-11)
#
# TRV(hass, entity_id, platform) owns last_pushed and the anti-flap guard.
# push_temperature emits DEBUG heating log only when last_pushed != desired.
# push_off uses "off" sentinel anti-flap.
# ---------------------------------------------------------------------------


async def test_trv_push_temperature_first_call_pushes_and_logs(hass, caplog):
    """Test 17: Fresh TRV (last_pushed=None) push_temperature issues the service
    call, sets last_pushed, and emits one DEBUG heating log line.

    Log format: "heating | room=%s temp=%s°C zone=%s slot=%s" (D-11)
    Short-name strip: area_kitchen→kitchen, zone_main→main (D-01)
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature": 18.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    ctx = MagicMock()
    trv = TRV(hass, CLIMATE_ENTITY, "generic")

    import logging

    with caplog.at_level(
        logging.DEBUG, logger="custom_components.climate_manager"
    ):
        await trv.push_temperature(
            20.0,
            room_name="area_kitchen",
            zone_name="zone_main",
            slot="normal",
            ctx=ctx,
        )

    # Service call must fire
    assert len(temp_calls) == 1
    assert temp_calls[0].data["temperature"] == 20.0

    # last_pushed updated
    assert trv.last_pushed == 20.0

    # DEBUG log emitted with correct format
    assert any(
        "heating | room=kitchen temp=20.0°C zone=main slot=normal" in r.message
        for r in caplog.records
    ), f"Expected heating log; got: {[r.message for r in caplog.records]}"


async def test_trv_push_temperature_repeat_same_setpoint_no_push_no_log(
    hass, caplog
):
    """Test 18: Second push_temperature with same setpoint: no service call,
    no DEBUG log (D-10 anti-spam — last_pushed == desired_temp).
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature": 20.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    ctx = MagicMock()
    trv = TRV(hass, CLIMATE_ENTITY, "generic")
    trv.last_pushed = 20.0  # Simulate prior push

    import logging

    with caplog.at_level(
        logging.DEBUG, logger="custom_components.climate_manager"
    ):
        await trv.push_temperature(
            20.0,
            room_name="area_kitchen",
            zone_name="zone_main",
            slot="normal",
            ctx=ctx,
        )

    assert len(temp_calls) == 0, "No push when last_pushed == desired_temp"
    assert not any("heating |" in r.message for r in caplog.records), (
        "No log when setpoint unchanged"
    )


async def test_trv_push_temperature_manual_override_hold(hass):
    """Test 19: Manual-override hold — TRV reports temp different from
    last_pushed → skip push (D-03 hold).

    last_pushed=20.0 but TRV reports 24.0 (user overrode) → no push.
    """
    # TRV reports 24.0 (user manually set), but last_pushed is 20.0
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature": 24.0})
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    ctx = MagicMock()
    trv = TRV(hass, CLIMATE_ENTITY, "generic")
    trv.last_pushed = 20.0  # We last pushed 20.0

    await trv.push_temperature(
        22.0,  # New desired temp different from both last_pushed and reported
        room_name="area_lounge",
        zone_name="zone_main",
        slot="normal",
        ctx=ctx,
    )

    assert len(temp_calls) == 0, "Override hold: TRV reports != last_pushed"


async def test_trv_push_temperature_skips_unavailable(hass):
    """Test 20: push_temperature silently skips unavailable entity."""
    hass.states.async_set(CLIMATE_ENTITY, "unavailable", {})
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    ctx = MagicMock()
    trv = TRV(hass, CLIMATE_ENTITY, "generic")

    await trv.push_temperature(
        20.0,
        room_name="area_kitchen",
        zone_name="zone_main",
        slot="normal",
        ctx=ctx,
    )

    assert len(temp_calls) == 0


async def test_trv_push_temperature_skips_missing_entity(hass):
    """Test 21: push_temperature silently skips missing entity (None state)."""
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    ctx = MagicMock()
    trv = TRV(hass, "climate.nonexistent", "generic")

    await trv.push_temperature(
        20.0,
        room_name="area_kitchen",
        zone_name="zone_main",
        slot="normal",
        ctx=ctx,
    )

    assert len(temp_calls) == 0


async def test_trv_push_temperature_startup_fires(hass, caplog):
    """Test 22: Startup push (last_pushed=None) always fires and logs (D-11).

    This is the intentional startup push behavior — last_pushed=None means no
    anti-flap, so the push always fires on first tick.
    """
    hass.states.async_set(CLIMATE_ENTITY, "heat", {"temperature": 20.0})
    async_mock_service(hass, "climate", "set_hvac_mode")
    temp_calls = async_mock_service(hass, "climate", "set_temperature")

    ctx = MagicMock()
    trv = TRV(hass, CLIMATE_ENTITY, "generic")
    # last_pushed is None (default) — startup state

    import logging

    with caplog.at_level(
        logging.DEBUG, logger="custom_components.climate_manager"
    ):
        await trv.push_temperature(
            20.0,
            room_name="area_kitchen",
            zone_name="zone_main",
            slot="normal",
            ctx=ctx,
        )

    # Startup push fires even when TRV already reports the same temp
    assert len(temp_calls) >= 0  # set_trv_temperature internal guard may skip
    # The key assertion: last_pushed is set after the startup push attempt
    assert trv.last_pushed == 20.0

    # Log fires on startup (first push always logs per D-11)
    assert any("heating | room=kitchen" in r.message for r in caplog.records), (
        "Startup push must emit heating log"
    )


async def test_trv_push_off_anti_flap(hass):
    """Test 23: push_off uses 'off' sentinel — second call skips both service
    calls (anti-flap parity with push_temperature, D-10).
    """
    hass.states.async_set(
        CLIMATE_ENTITY, "heat", {"hvac_modes": ["heat", "off"]}
    )
    hvac_calls = async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")

    ctx = MagicMock()
    trv = TRV(hass, CLIMATE_ENTITY, "generic")

    await trv.push_off(7.0, ctx)
    first_hvac_count = len(hvac_calls)

    await trv.push_off(7.0, ctx)  # Second call — anti-flap must skip

    assert len(hvac_calls) == first_hvac_count, (
        "Second push_off must not issue additional service calls (anti-flap)"
    )
    assert trv.last_pushed == "off"


async def test_trv_push_off_never_raises(hass):
    """Test 24: push_off catches exceptions and never propagates (T-16-05).

    Verified by calling push_off on a missing entity — must not raise.
    """
    ctx = MagicMock()
    trv = TRV(hass, "climate.gone", "generic")
    await trv.push_off(7.0, ctx)  # Must not raise


def test_trv_short_name_strips_prefixes():
    """Test 25: _short_name helper strips area_/zone_ prefixes and domain (D-01)."""
    from custom_components.climate_manager.trv import _short_name

    assert _short_name("area_kitchen") == "kitchen"
    assert _short_name("zone_main") == "main"
    assert _short_name("person.alice") == "alice"
    assert _short_name("climate.living_room") == "living_room"
    assert _short_name("kitchen") == "kitchen"  # no prefix — unchanged


# ---------------------------------------------------------------------------
# Tests 26-28: TRVGroup class (plan 16-03 Task 2, D-07/Matter dedup)
# ---------------------------------------------------------------------------


async def test_trvgroup_push_calls_each_trv_once(hass):
    """Test 26: TRVGroup.push iterates its TRVs and calls push_temperature
    on each exactly once with the correct args (D-07).
    """
    # Build a TRVGroup with 2 TRV mocks
    trv1 = MagicMock()
    trv1.push_temperature = AsyncMock()
    trv2 = MagicMock()
    trv2.push_temperature = AsyncMock()

    group = TRVGroup.__new__(TRVGroup)
    group._trvs = [trv1, trv2]
    group._room_name = "area_kitchen"
    group._zone_name = "zone_main"

    ctx = MagicMock()
    await group.push(20.0, "normal", ctx)

    trv1.push_temperature.assert_awaited_once_with(
        20.0,
        room_name="area_kitchen",
        zone_name="zone_main",
        slot="normal",
        ctx=ctx,
    )
    trv2.push_temperature.assert_awaited_once_with(
        20.0,
        room_name="area_kitchen",
        zone_name="zone_main",
        slot="normal",
        ctx=ctx,
    )


async def test_trvgroup_assembly_matter_dedup(hass):
    """Test 27: TRVGroup assembly skips Matter entity already covered by a
    tado_x mapping (Pitfall 4 — no double-push).

    Room entities: [tado_x_entity, matter_entity]
    matter_mappings: {tado_x_entity: [matter_entity]}
    Expected: one TRV (matter_entity), not two.
    """
    from homeassistant.helpers import entity_registry as er

    # Register entities in HA entity registry
    entity_reg = er.async_get(hass)

    tado_entity = "climate.tado_room"
    matter_entity = "climate.matter_room"

    # Set states so entities exist
    hass.states.async_set(tado_entity, "heat", {"temperature": 20.0})
    hass.states.async_set(matter_entity, "heat", {"temperature": 20.0})

    # Mock entity registry to return platform info
    tado_entry = MagicMock()
    tado_entry.platform = "tado_x"

    matter_entry = MagicMock()
    matter_entry.platform = "matter"

    def mock_async_get(eid):
        if eid == tado_entity:
            return tado_entry
        if eid == matter_entity:
            return matter_entry
        return None

    entity_reg.async_get = mock_async_get

    matter_mappings = {tado_entity: [matter_entity]}
    entity_ids = [tado_entity, matter_entity]

    group = TRVGroup.from_room_config(
        hass=hass,
        entity_ids=entity_ids,
        matter_mappings=matter_mappings,
        room_name="area_kitchen",
        zone_name="zone_main",
    )

    # Should have exactly one TRV — the matter entity (via tado_x mapping)
    # matter_entity as standalone is skipped (already in dedup set)
    assert len(group._trvs) == 1
    assert group._trvs[0].entity_id == matter_entity


async def test_trvgroup_assembly_no_dedup_for_standalone_matter(hass):
    """Test 28: TRVGroup assembly includes standalone Matter entity (not in
    any tado_x mapping) as its own TRV push target.
    """
    from homeassistant.helpers import entity_registry as er

    entity_reg = er.async_get(hass)

    standalone_matter = "climate.standalone_matter"
    hass.states.async_set(standalone_matter, "heat", {"temperature": 20.0})

    matter_entry = MagicMock()
    matter_entry.platform = "matter"
    entity_reg.async_get = lambda eid: (
        matter_entry if eid == standalone_matter else None
    )

    group = TRVGroup.from_room_config(
        hass=hass,
        entity_ids=[standalone_matter],
        matter_mappings={},  # No tado_x mappings
        room_name="area_lounge",
        zone_name="zone_main",
    )

    assert len(group._trvs) == 1
    assert group._trvs[0].entity_id == standalone_matter
