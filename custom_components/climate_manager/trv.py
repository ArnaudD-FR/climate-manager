# SPDX-License-Identifier: MIT
"""Climate Manager TRV control helper.

Implements the two-call TRV service sequence required by INFRA-04:
  1. climate.set_hvac_mode with hvac_mode="heat" (blocking)
  2. climate.set_temperature with the target temperature (blocking)

Also implements off-capable TRV support (quick task 260526-ffr):
  - supports_hvac_off: checks if a TRV advertises HVACMode.OFF in its hvac_modes attribute
  - set_trv_off: issues a single climate.set_hvac_mode=off call for off-capable TRVs

Domain classes (plan 16-03, D-07/D-10/D-11):
  - TRV: owns entity_id, last_pushed, last_slot, platform; async
    push_temperature, push_off. Anti-flap guard, manual-override
    hold lifted on period change, INFO push log, per-call timeout.
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
- D-11: INFO push log fires only when a setpoint is actually sent; the
  first push (startup, rebuild of a new TRV, back online) is forced
- T-16-05: Exception-safe wrapper in push_temperature/push_off (never raises)
- T-16-06: Matter dedup via frozenset at TRVGroup assembly
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import TRV_COMMAND_TIMEOUT

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

    When the entity has no state yet (its integration is still loading at HA
    startup), max_temp is read from the entity registry capabilities so the
    TRV is not dropped from its room until the next domain rebuild.
    """
    state = hass.states.get(entity_id)
    if state is not None:
        max_t = state.attributes.get("max_temp")
    else:
        reg = er.async_get(hass).async_get(entity_id)
        if reg is None:
            return False
        max_t = (reg.capabilities or {}).get("max_temp")
    return max_t is None or float(max_t) <= _TRV_MAX_TEMP_THRESHOLD


async def set_trv_temperature(
    hass: HomeAssistant,
    entity_id: str,
    temperature: float,
    *,
    force: bool = False,
) -> None:
    """Issue the two-call sequence to set a TRV's target temperature.

    Step 1: set_hvac_mode to "heat" (Matter TRVs require explicit heat mode).
    Step 2: set_temperature to the target value.

    Both calls use blocking=True to ensure sequential execution.

    Redundant-call guards (skip-redundant-hvac-and-temp-calls): each call is
    skipped when the TRV is already in the desired state, halving cloud API
    writes on startup / period transitions.
    - set_hvac_mode is skipped when state.state is already "heat". It still
      fires for any other mode ("auto"/"off"/"cool") because some TRVs in
      auto mode ignore set_temperature until forced into heat mode (INFRA-04).
    - set_temperature is skipped when the reported "temperature" attribute
      already equals the desired value. When the attribute is absent we cannot
      prove the setpoint and so issue the call. force=True always issues it
      (first push after startup or back-online: the HA state may be stale).

    Silently skips the entity if its state is None or "unavailable" (ROOM-03).
    Never uses any hvac_mode other than "heat" (INFRA-04).
    """
    # Availability guard (ROOM-03, T-01-08): skip missing or unavailable TRVs
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unavailable", "unknown"):
        return

    # Step 1: Ensure heat mode (INFRA-04 — hvac_mode must be "heat").
    # Skip when already heating; fire for any non-heat mode (auto-mode
    # workaround — some TRVs ignore set_temperature unless in heat mode).
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
    if force or current_setpoint != temperature:
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

    Owns entity_id, platform, last_pushed and last_slot.  Encapsulates the
    anti-flap guard and D-03 manual-override hold that previously lived in
    coordinator _push_if_changed.  Emits an INFO push log on every setpoint
    sent (D-11) but never on repeated identical setpoints (D-10).

    All methods are exception-safe (T-16-05): they catch Exception, log a
    WARNING, and never propagate into the evaluation loop.  Every service
    call is bounded by TRV_COMMAND_TIMEOUT so an unresponsive valve cannot
    stall the other rooms.
    """

    def __init__(
        self, hass: HomeAssistant, entity_id: str, platform: str | None
    ) -> None:
        self._hass = hass
        self.entity_id = entity_id
        self.platform = platform
        self.last_pushed: float | str | None = None
        # Period (slot) of the last successful push. The D-03 hold and the
        # D-10 anti-spam only apply while the slot is unchanged.
        self.last_slot: str | None = None
        # True once the "hold" INFO log has been emitted for the current
        # manual override (one log per hold, not one per tick).
        self._holding = False

    def reset_push_state(self) -> None:
        """Forget the last push so the next one is forced (back online)."""
        self.last_pushed = None
        self.last_slot = None
        self._holding = False

    def carry_push_state(self, old: "TRV") -> None:
        """Copy push state from the TRV it replaces on a domain rebuild."""
        self.last_pushed = old.last_pushed
        self.last_slot = old.last_slot
        self._holding = old._holding

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

        Anti-flap guard (D-10): skip when the slot is unchanged and
        last_pushed == desired_temp.
        Manual-override hold (D-03): skip when the slot is unchanged and the
        TRV reports a temp different from last_pushed (user adjusted
        manually). A new slot (period change) lifts the hold.
        Startup push (D-11): last_pushed=None bypasses both guards and forces
        set_temperature even if the reported setpoint already matches — the
        HA state may be stale after a restart or reconnection.
        INFO log fires only when a push is about to happen (D-11).
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

            same_slot = last is not None and slot == self.last_slot

            # D-03: manual-override hold until the next period transition
            if same_slot:
                reported = state.attributes.get("temperature")
                if reported is not None and float(reported) != last:
                    if not self._holding:
                        self._holding = True
                        _LOGGER.info(
                            "hold | trv=%s reported=%s°C last=%s°C slot=%s",
                            _short_name(self.entity_id),
                            reported,
                            last,
                            slot,
                        )
                    return
                self._holding = False

            # D-10: anti-spam — skip if already pushed this setpoint
            if same_slot and last == desired_temp:
                return

            # All guards passed — emit INFO log then push (D-11)
            _LOGGER.info(
                "push | room=%s trv=%s temp=%s°C slot=%s zone=%s",
                _short_name(room_name),
                _short_name(self.entity_id),
                desired_temp,
                slot,
                _short_name(zone_name),
            )
            async with asyncio.timeout(TRV_COMMAND_TIMEOUT):
                await set_trv_temperature(
                    self._hass,
                    self.entity_id,
                    desired_temp,
                    force=self.last_pushed is None,
                )
            self.last_pushed = desired_temp
            self.last_slot = slot
            self._holding = False
        except TimeoutError:
            _LOGGER.warning(
                "timeout | trv=%s temp=%s°C after %ss",
                self.entity_id,
                desired_temp,
                TRV_COMMAND_TIMEOUT,
            )
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Failed to push temperature to %s", self.entity_id)

    async def push_off(self, frost_temp: float, ctx: object) -> None:
        """Pre-set frost setpoint then issue set_hvac_mode=off.

        Mirrors coordinator _push_off_safely.  Anti-flap: skips when
        last_pushed == "off" sentinel (D-10).  Never raises (T-16-05).

        Step 1: set_temperature(frost_temp) — so TRV resumes at frost on
                wake-up rather than its previous arbitrary setpoint.
        Step 2: set_hvac_mode=off — sentinel stored only on success.
        Each step is bounded by TRV_COMMAND_TIMEOUT.
        """
        try:
            state = self._hass.states.get(self.entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                return

            if self.last_pushed == "off":
                return  # Anti-flap: already pushed off

            _LOGGER.info(
                "push | trv=%s off (frost=%s°C)",
                _short_name(self.entity_id),
                frost_temp,
            )
            try:
                async with asyncio.timeout(TRV_COMMAND_TIMEOUT):
                    await set_trv_temperature(
                        self._hass,
                        self.entity_id,
                        frost_temp,
                        force=self.last_pushed is None,
                    )
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Failed to pre-set frost temp on %s before MODE_OFF",
                    self.entity_id,
                )

            try:
                async with asyncio.timeout(TRV_COMMAND_TIMEOUT):
                    await set_trv_off(self._hass, self.entity_id)
                self.last_pushed = "off"
                self.last_slot = "off"
                self._holding = False
            except TimeoutError:
                _LOGGER.warning(
                    "timeout | trv=%s off after %ss",
                    self.entity_id,
                    TRV_COMMAND_TIMEOUT,
                )
            except Exception:  # noqa: BLE001
                _LOGGER.warning(
                    "Failed to push OFF to %s in MODE_OFF", self.entity_id
                )
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Unexpected error in push_off for %s", self.entity_id
            )


class TRVGroup:
    """One logical push unit assembled at coordinator init (D-07).

    Contains one or more TRV instances resolved from matter_mappings at
    assembly time.  At push time there is no platform branching — the correct
    TRVs are already in the group.  Uses asyncio.gather for concurrent pushes.

    Assembly rules (Pitfall 4), brand-neutral:
      mapped entity     → its paired Matter entities only (a cloud entity
                          is replaced by the local valves it controls)
      pairing target    → skipped (already in the group through its key)
      any other entity  → standalone push target
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

        The paired frozenset (T-16-06) prevents double-pushing a Matter
        entity that is already covered by its paired entity.
        """
        from homeassistant.helpers import (  # noqa: PLC0415
            entity_registry as er,
        )

        entity_reg = er.async_get(hass)

        def _platform(entity_id: str) -> str | None:
            reg = entity_reg.async_get(entity_id)
            return reg.platform if reg is not None else None

        paired: frozenset[str] = frozenset(
            eid for eids in matter_mappings.values() for eid in eids
        )

        trvs: list[TRV] = []
        for entity_id in entity_ids:
            # Skip boiler/HVAC entities (max_temp > 45°C) so we never push a
            # room setpoint to a boiler. Matches the is_trv_entity filter the
            # coordinator applies on every other entity-iterating path.
            if not is_trv_entity(hass, entity_id):
                continue
            mapped = matter_mappings.get(entity_id)
            if mapped:
                for m_eid in mapped:
                    trvs.append(TRV(hass, m_eid, _platform(m_eid)))
            elif entity_id not in paired:
                trvs.append(TRV(hass, entity_id, _platform(entity_id)))

        return cls(trvs, room_name, zone_name)

    @property
    def trvs(self) -> list[TRV]:
        """TRV push targets of this group."""
        return self._trvs

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

    async def push_off(self, frost_temp: float, ctx: object) -> None:
        """Push MODE_OFF: push_off for off-capable TRVs, frost temp for others."""
        await asyncio.gather(
            *(
                (
                    trv.push_off(frost_temp, ctx)
                    if supports_hvac_off(trv._hass, trv.entity_id)
                    else trv.push_temperature(
                        frost_temp,
                        room_name=self._room_name,
                        zone_name=self._zone_name,
                        slot="off",
                        ctx=ctx,
                    )
                )
                for trv in self._trvs
            )
        )
