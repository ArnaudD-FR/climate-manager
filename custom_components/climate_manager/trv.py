# SPDX-License-Identifier: MIT
"""Climate Manager TRV control helper.

Implements the two-call TRV service sequence required by INFRA-04:
  1. climate.set_hvac_mode with hvac_mode="heat" (blocking)
  2. climate.set_temperature with the target temperature (blocking)

Also implements off-capable TRV support (quick task 260526-ffr):
  - supports_hvac_off: checks if a TRV advertises HVACMode.OFF in its hvac_modes attribute
  - set_trv_off: issues a single climate.set_hvac_mode=off call for off-capable TRVs

Domain classes (plan 16-03, D-07/D-10/D-11):
  - TRV: owns entity_id, last_pushed, platform; async push_temperature,
    push_off, calibrate. Anti-flap guard and DEBUG heating log.
  - TRVGroup: assembled at init from matter_mappings; no platform branching
    at push time; uses asyncio.gather for concurrent TRV pushes.

Design decisions (from RESEARCH.md / CLAUDE.md):
- Pattern 5: Two-call TRV service sequence
- INFRA-04: Heat mode set first whenever the TRV is not already heating; the
  hvac_mode "heat" is the only value ever used
- ROOM-03: Unavailable or missing TRVs are silently skipped
- T-01-07: hvac_mode is hardcoded "heat"
- T-01-08: Guard on hass.states.get returning None or "unavailable"
- D-01: Name strip — area_/zone_ prefixes stripped for log display
- D-07: TRVGroup assembles push targets at init; push time is platform-agnostic
- D-10: Anti-spam via TRV.last_pushed (no separate guard dict)
- D-11: DEBUG log fires only when last_pushed != desired_temp
- T-16-05: Exception-safe wrapper in push_temperature/push_off (never raises)
- T-16-06: Matter dedup via frozenset at TRVGroup assembly
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

_LOGGER = logging.getLogger(__name__)

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

    Redundant-call guards (skip-redundant-hvac-and-temp-calls): each call is
    skipped when the TRV is already in the desired state, halving tado_x API
    writes on startup / period transitions.
    - set_hvac_mode is skipped when state.state is already "heat". It still
      fires for any other mode ("auto"/"off"/"cool") because Tado X TRVs in
      auto mode ignore set_temperature until forced into heat mode (INFRA-04).
    - set_temperature is skipped when the reported "temperature" attribute
      already equals the desired value. When the attribute is absent we cannot
      prove the setpoint and so issue the call.

    Silently skips the entity if its state is None or "unavailable" (ROOM-03).
    Never uses any hvac_mode other than "heat" (INFRA-04).
    """
    # Availability guard (ROOM-03, T-01-08): skip missing or unavailable TRVs
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unavailable", "unknown"):
        return

    # Step 1: Ensure heat mode (INFRA-04 — hvac_mode must be "heat").
    # Skip when already heating; fire for any non-heat mode (Tado X auto-mode
    # workaround — set_temperature is ignored unless the TRV is in heat mode).
    if state.state != HVACMode.HEAT.value:
        await hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": entity_id, "hvac_mode": "heat"},
            blocking=True,
        )

    # Step 2: Set target temperature. Skip when the reported setpoint already
    # matches the desired value (self-contained guard mirroring the
    # coordinator's D-02 _push_if_changed check). Missing attribute means we
    # cannot prove the setpoint, so issue the call.
    current_setpoint = state.attributes.get("temperature")
    if current_setpoint != temperature:
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
    return (
        "temperature_offset" in state.attributes
        or hass.services.has_service("tado_x", "set_temperature_offset")
    )


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
        # Tado X API requires exactly one decimal place (Issue 1):
        # round at the boundary so every caller is protected.
        {"device_id": device_id, "offset": round(offset, 1)},
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
        # Tado X API requires exactly one decimal place (Issue 1):
        # round at the boundary so every caller is protected.
        {"entity_id": entity_id, "offset": round(offset, 1)},
        blocking=True,
    )


# ---------------------------------------------------------------------------
# Domain classes (plan 16-03, D-07/D-10/D-11)
# ---------------------------------------------------------------------------


def _short_name(entity_id: str) -> str:
    """Strip domain/prefix for log display (D-01).

    Examples:
      person.alice   → alice
      area_kitchen   → kitchen  (strip area_ prefix)
      zone_main      → main     (strip zone_ prefix)
      climate.trv    → trv
      kitchen        → kitchen  (no change)
    """
    if "." in entity_id:
        return entity_id.split(".", 1)[1]
    for prefix in ("area_", "zone_"):
        if entity_id.startswith(prefix):
            return entity_id[len(prefix) :]
    return entity_id


class TRV:
    """One physical TRV push unit (D-07).

    Owns entity_id, platform, and last_pushed.  Encapsulates the anti-flap
    guard and D-03 manual-override hold that previously lived in coordinator
    _push_if_changed.  Emits a DEBUG heating log on every setpoint change
    (D-11) but never on repeated identical setpoints (D-10).

    All methods are exception-safe (T-16-05): they catch Exception, log a
    WARNING, and never propagate into the evaluation loop.
    """

    def __init__(
        self, hass: HomeAssistant, entity_id: str, platform: str | None
    ) -> None:
        self._hass = hass
        self.entity_id = entity_id
        self.platform = platform
        self.last_pushed: float | str | None = None

    async def push_temperature(
        self,
        desired_temp: float,
        *,
        room_name: str,
        zone_name: str,
        slot: str,
        ctx: object,
    ) -> None:
        """Push desired_temp to the TRV entity.

        Anti-flap guard (D-10): skip when last_pushed == desired_temp.
        Manual-override hold (D-03): skip when TRV reports a temp different
        from last_pushed (user adjusted manually).
        Startup push (D-11): last_pushed=None bypasses both guards so the
        first evaluation always pushes (intentional).
        DEBUG log fires only when a push is about to happen (D-11).
        Exception-safe: catches all exceptions and WARNING-logs (T-16-05).
        """
        try:
            state = self._hass.states.get(self.entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                return

            last = self.last_pushed

            # Clear stale MODE_OFF sentinel — "off" is a string not a float.
            # Leaving it as-is would make float(reported) != "off" always True,
            # causing the D-03 hold to fire on every tick after MODE_OFF exit.
            if isinstance(last, str):
                last = None

            # D-10: anti-spam — skip if already pushed this setpoint
            if last is not None and last == desired_temp:
                return

            # D-03: manual-override hold — only active when we have a prior push
            if last is not None:
                reported = state.attributes.get("temperature")
                if reported is not None and float(reported) != last:
                    # User adjusted manually — hold until next period transition
                    return

            # All guards passed — emit DEBUG log then push (D-11)
            _LOGGER.debug(
                "heating | room=%s temp=%s°C zone=%s slot=%s",
                _short_name(room_name),
                desired_temp,
                _short_name(zone_name),
                slot,
            )
            await set_trv_temperature(self._hass, self.entity_id, desired_temp)
            self.last_pushed = desired_temp
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Failed to push temperature to %s", self.entity_id)

    async def push_off(self, frost_temp: float, ctx: object) -> None:
        """Pre-set frost setpoint then issue set_hvac_mode=off.

        Mirrors coordinator _push_off_safely.  Anti-flap: skips when
        last_pushed == "off" sentinel (D-10).  Never raises (T-16-05).

        Step 1: set_temperature(frost_temp) — so TRV resumes at frost on
                wake-up rather than its previous arbitrary setpoint.
        Step 2: set_hvac_mode=off — sentinel stored only on success.
        """
        try:
            state = self._hass.states.get(self.entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                return

            if self.last_pushed == "off":
                return  # Anti-flap: already pushed off

            try:
                await set_trv_temperature(
                    self._hass, self.entity_id, frost_temp
                )
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Failed to pre-set frost temp on %s before MODE_OFF",
                    self.entity_id,
                )

            try:
                await set_trv_off(self._hass, self.entity_id)
                self.last_pushed = "off"
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Failed to push OFF to %s in MODE_OFF", self.entity_id
                )
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Unexpected error in push_off for %s", self.entity_id
            )

    async def calibrate(self, offset: float, ctx: object) -> None:
        """Apply temperature offset calibration to this TRV.

        Thin wrapper delegating to set_trv_offset.  Full calibration logic
        moves here in plan 16-04 (room).  Exception-safe (T-16-05).
        """
        try:
            await set_trv_offset(self._hass, self.entity_id, offset)
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to calibrate TRV %s with offset %s",
                self.entity_id,
                offset,
            )


class TRVGroup:
    """One logical push unit assembled at coordinator init (D-07).

    Contains one or more TRV instances resolved from matter_mappings at
    assembly time.  At push time there is no platform branching — the correct
    TRVs are already in the group.  Uses asyncio.gather for concurrent pushes.

    Assembly rules (from coordinator _push_temperatures / Pitfall 4):
      tado_x + mapped   → Matter entity_ids only (not the tado_x entity)
      tado_x + unmapped → tado_x entity itself
      matter + in dedup → skip (already covered by tado_x branch)
      matter + not dedup → standalone push target
      other platform    → standalone push target
    """

    def __init__(
        self,
        trvs: list[TRV],
        room_name: str,
        zone_name: str,
    ) -> None:
        self._trvs = trvs
        self._room_name = room_name
        self._zone_name = zone_name

    @classmethod
    def from_room_config(
        cls,
        hass: HomeAssistant,
        entity_ids: list[str],
        matter_mappings: dict[str, list[str]],
        room_name: str,
        zone_name: str,
    ) -> "TRVGroup":
        """Build a TRVGroup from a room's entity list and matter_mappings.

        The matter_entity_set frozenset (T-16-06) prevents double-pushing
        a Matter entity that is already covered by a tado_x mapping.
        """
        from homeassistant.helpers import (  # noqa: PLC0415
            entity_registry as er,
        )

        entity_reg = er.async_get(hass)

        # Frozenset of all Matter entity_ids referenced in any mapping value
        # (T-16-06: dedup guard — Pitfall 4)
        matter_entity_set: frozenset[str] = frozenset(
            eid for eids in matter_mappings.values() for eid in eids
        )

        trvs: list[TRV] = []
        for entity_id in entity_ids:
            reg = entity_reg.async_get(entity_id)
            platform = reg.platform if reg is not None else None
            if platform == "tado_x":
                mapped = matter_mappings.get(entity_id)
                if mapped:
                    # Mapped tado_x → use Matter entities only
                    for m_eid in mapped:
                        trvs.append(TRV(hass, m_eid, "matter"))
                else:
                    # Unmapped tado_x → use tado_x entity
                    trvs.append(TRV(hass, entity_id, "tado_x"))
            elif platform == "matter":
                if entity_id not in matter_entity_set:
                    # Standalone Matter entity — independent push target
                    trvs.append(TRV(hass, entity_id, "matter"))
                # else: skip — already in the group via tado_x mapping
            else:
                # Generic TRV entity
                trvs.append(TRV(hass, entity_id, platform))

        return cls(trvs, room_name, zone_name)

    async def push(self, temp: float, slot: str, ctx: object) -> None:
        """Push temp to all TRVs concurrently (asyncio.gather pattern).

        No platform branching — TRVs are already resolved at assembly time.
        """
        await asyncio.gather(
            *(
                trv.push_temperature(
                    temp,
                    room_name=self._room_name,
                    zone_name=self._zone_name,
                    slot=slot,
                    ctx=ctx,
                )
                for trv in self._trvs
            )
        )
