"""Climate Manager TRV control helper.

Implements the two-call TRV service sequence required by INFRA-04:
  1. climate.set_hvac_mode with hvac_mode="heat" (blocking)
  2. climate.set_temperature with the target temperature (blocking)

Design decisions (from RESEARCH.md / CLAUDE.md):
- Pattern 5: Two-call TRV service sequence
- INFRA-04: Heat mode ALWAYS set first; hvac_mode "heat" is the only value used
- ROOM-03: Unavailable or missing TRVs are silently skipped
- T-01-07: hvac_mode is hardcoded "heat"
- T-01-08: Guard on hass.states.get returning None or "unavailable"
"""
from homeassistant.core import HomeAssistant

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
    if state is None or state.state == "unavailable":
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
