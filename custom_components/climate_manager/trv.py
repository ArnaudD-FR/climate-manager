# SPDX-License-Identifier: MIT
"""Climate Manager TRV control helper.

Implements the two-call TRV service sequence required by INFRA-04:
  1. climate.set_hvac_mode with hvac_mode="heat" (blocking)
  2. climate.set_temperature with the target temperature (blocking)

Also implements off-capable TRV support (quick task 260526-ffr):
  - supports_hvac_off: checks if a TRV advertises HVACMode.OFF in its hvac_modes attribute
  - set_trv_off: issues a single climate.set_hvac_mode=off call for off-capable TRVs

Design decisions (from RESEARCH.md / CLAUDE.md):
- Pattern 5: Two-call TRV service sequence
- INFRA-04: Heat mode ALWAYS set first; hvac_mode "heat" is the only value used
- ROOM-03: Unavailable or missing TRVs are silently skipped
- T-01-07: hvac_mode is hardcoded "heat"
- T-01-08: Guard on hass.states.get returning None or "unavailable"
"""

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

# TRV rooms control individual radiators; boilers/HVAC units have max_temp > 45°C.
_TRV_MAX_TEMP_THRESHOLD = 45.0


def is_trv_entity(hass: HomeAssistant, entity_id: str) -> bool:
    """Return True if entity_id is a room TRV (not a boiler or HVAC unit).

    Distinguishes TRVs (max_temp ~30°C) from boiler/HVAC entities like Viessmann
    vicare (max_temp=60°C). Falls back to True when max_temp is absent so that
    unknown climate entities are included rather than silently dropped.

    Only returns False when the entity state is unknown (None) or max_temp exceeds the
    TRV threshold. Missing current_temperature is not treated as a disqualifier — a TRV
    can be present but not yet reporting sensor data.
    """
    state = hass.states.get(entity_id)
    if state is None:
        return False
    max_t = state.attributes.get("max_temp")
    return max_t is None or float(max_t) <= _TRV_MAX_TEMP_THRESHOLD


async def set_trv_temperature(
    hass: HomeAssistant, entity_id: str, temperature: float
) -> None:
    """Issue the two-call sequence to set a TRV's target temperature.

    Step 1: set_hvac_mode to "heat" (Matter TRVs require explicit heat mode).
    Step 2: set_temperature to the target value.

    Both calls use blocking=True to ensure sequential execution.

    Silently skips the entity if its state is None or "unavailable" (ROOM-03).
    Always uses hvac_mode "heat" — never any other mode (INFRA-04).
    """
    # Availability guard (ROOM-03, T-01-08): skip missing or unavailable TRVs
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unavailable", "unknown"):
        return

    # Step 1: Ensure heat mode (INFRA-04 — hvac_mode must be "heat")
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": "heat"},
        blocking=True,
    )

    # Step 2: Set target temperature
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": entity_id, "temperature": temperature},
        blocking=True,
    )


def supports_hvac_off(hass: HomeAssistant, entity_id: str) -> bool:
    """Return True if the TRV entity advertises HVACMode.OFF in its hvac_modes attribute.

    Returns False when:
    - The entity state is missing (None) — ROOM-03 parity
    - The hvac_modes attribute is absent or None
    - HVACMode.OFF.value ("off") is not in the list

    Never raises — TRVs that don't expose the list are treated as not supporting off
    and fall back to the frost-protection path (T-01-07 / INFRA-04).
    """
    state = hass.states.get(entity_id)
    if state is None:
        return False
    return HVACMode.OFF.value in (state.attributes.get("hvac_modes") or [])


async def set_trv_off(hass: HomeAssistant, entity_id: str) -> None:
    """Issue a single climate.set_hvac_mode=off call to turn off an off-capable TRV.

    Unlike set_trv_temperature, this issues ONLY one service call (no set_temperature).
    The device must support HVACMode.OFF — verified by supports_hvac_off before calling
    this function. The coordinator calls this for off-capable TRVs in MODE_OFF.

    Silently skips the entity if its state is None or "unavailable" (ROOM-03 / T-01-08).
    """
    # Availability guard (ROOM-03, T-01-08): skip missing or unavailable TRVs
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unavailable", "unknown"):
        return

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": HVACMode.OFF.value},
        blocking=True,
    )


def supports_offset_calibration(hass: HomeAssistant, entity_id: str) -> bool:
    """Return True if the TRV entity supports temperature offset adjustment.

    Two detection paths (D-08):
    - Attribute check: entity exposes temperature_offset in its state.
    - Service check: tado_x.set_temperature_offset is registered.

    Returns True if either path matches. set_trv_offset routes to the tado_x
    service when it is present; if only the attribute path matched, the
    set_trv_offset call will return silently (no write path available yet).

    Returns False when the entity state is missing (None) — ROOM-03 parity.

    Never raises.
    """
    state = hass.states.get(entity_id)
    if state is None:
        return False
    has_attribute = "temperature_offset" in state.attributes
    has_service = hass.services.has_service("tado_x", "set_temperature_offset")
    return has_attribute or has_service


def get_tado_valve_devices(hass: HomeAssistant, area_id: str) -> list[dict]:
    """Return Radiator Valve X device info for the given area.

    Queries the HA device registry for physical Tado X TRV devices (model
    "Radiator Valve X") in the area. Used by both the coordinator (calibration
    loop) and the websocket handler (calibration status display) so that both
    paths agree on which devices exist.

    Returns a list of {"device_id": str, "name": str} dicts.
    Returns an empty list when tado_x is not configured or the area has none.
    """
    dev_reg = dr.async_get(hass)
    tado_x_entries = {
        e.entry_id for e in hass.config_entries.async_entries("tado_x")
    }
    if not tado_x_entries:
        return []
    result = []
    for device in dev_reg.devices.values():
        if device.area_id != area_id:
            continue
        if not any(ce in tado_x_entries for ce in device.config_entries):
            continue
        if device.model != "Radiator Valve X":
            continue
        result.append(
            {
                "device_id": device.id,
                "name": device.name_by_user or device.name or device.id,
            }
        )
    return result


async def set_trv_offset_by_device(
    hass: HomeAssistant, device_id: str, offset: float
) -> None:
    """Call tado_x.set_temperature_offset targeting a physical device by device_id.

    The tado_x service takes device_id (not entity_id) — this is the correct
    call path for Radiator Valve X devices. Returns silently when the service
    is absent.
    """
    if not hass.services.has_service("tado_x", "set_temperature_offset"):
        return

    await hass.services.async_call(
        "tado_x",
        "set_temperature_offset",
        {"device_id": device_id, "offset": offset},
        blocking=True,
    )


async def set_trv_offset(
    hass: HomeAssistant, entity_id: str, offset: float
) -> None:
    """Issue a single tado_x.set_temperature_offset call to apply a new offset.

    Caller (coordinator) is responsible for the capability guard before calling
    this function — use supports_offset_calibration to check first.

    Silently skips the entity if its state is None, "unavailable", or
    "unknown" (ROOM-03 parity / T-01-08), matching the set_trv_off /
    set_trv_temperature guard pattern.

    Only calls the tado_x service when it is registered; returns silently
    for TRVs where the service is absent (no write path available).
    """
    # Availability guard (ROOM-03, T-01-08): skip missing or unavailable TRVs
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unavailable", "unknown"):
        return

    # Route: only call tado_x service when it exists; attribute-only TRVs
    # have no write path yet — skip silently rather than raising ServiceNotFound.
    if not hass.services.has_service("tado_x", "set_temperature_offset"):
        return

    await hass.services.async_call(
        "tado_x",
        "set_temperature_offset",
        {"entity_id": entity_id, "offset": offset},
        blocking=True,
    )
