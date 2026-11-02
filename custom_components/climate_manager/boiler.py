# SPDX-License-Identifier: MIT
"""Boiler control: heat while at least one room needs heat.

A room with at least one available TRV (a room without a valve, or whose
valves are offline, cannot use the heat) needs heat when:

- period: its effective period (schedule, presence and pre-heat resolved
  — Room.current_period) is one of BOILER_HEATING_PERIODS;
- else valve: one of its climate entities reports hvac_action with a
  state younger than BOILER_VALVE_MAX_AGE_MINUTES — then the valves
  decide: "heating" asks for heat, anything else for nothing (a closed
  valve cannot use the heat). "off" is no report: a valve we switched
  off (Off zone) says nothing about the room. Tado X reports it from the
  cloud only, at each poll; Matter has none;
- else below_setpoint: without a fresh valve report, its temperature is
  BOILER_START_GAP below its current setpoint, whatever the period (Frost
  protection in an Off zone); it asks until back at the setpoint
  (hysteresis kept per room).

The boiler is a climate entity (its hvac_mode toggles between the
configured on/off modes) or a switch / input_boolean (turn_on/turn_off).

Like the TRVs, a command is sent only when the demand changes: a manual
change on the boiler stays until the next demand change. The first tick
(startup, rebuild with a new entity) and a return online read the real
entity state instead, and align it. A minimum on / off duration, measured
from the last switch, guards the boiler against short cycles. The entity's
last_changed only counts as a switch when it predates this Boiler: after a
restart or a return online it is just when the state appeared (ViCare
loading: 2026-11-02, demand on at 20:35, boiler on only at 20:46).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    BOILER_DOMAINS,
    BOILER_HEATING_PERIODS,
    BOILER_START_GAP,
    BOILER_VALVE_MAX_AGE_MINUTES,
    DEFAULT_BOILER_MIN_OFF_MINUTES,
    DEFAULT_BOILER_MIN_ON_MINUTES,
    DEFAULT_BOILER_OFF_HVAC_MODE,
    DEFAULT_BOILER_ON_HVAC_MODE,
    DOMAIN,
    TRV_COMMAND_TIMEOUT,
)
from .trv import is_trv_entity
from .vendors import accessory_models, boiler_vendor

if TYPE_CHECKING:
    from .room import Room

_LOGGER = logging.getLogger(__name__)

_OFFLINE_STATES = ("unavailable", "unknown")

REASON_PERIOD = "period"
REASON_VALVE = "valve"
REASON_BELOW_SETPOINT = "below_setpoint"


def boiler_candidates(hass: HomeAssistant) -> list[str]:
    """Entities that can plausibly drive a boiler, sorted.

    - climate: heating devices only (not a TRV per is_trv_entity);
    - switch / input_boolean: user-facing (no config/diagnostic category,
      not hidden or disabled, not Climate Manager's own), and not an
      accessory of a radiator valve or room thermostat: on a device that
      has a climate entity (open window…) or a known valve model (child
      lock…).
    """
    entity_reg = er.async_get(hass)
    device_reg = dr.async_get(hass)
    climate_devices = {
        e.device_id
        for e in entity_reg.entities.values()
        if e.domain == "climate" and e.device_id
    }
    # Valve devices whose switches (child lock…) have no climate entity of
    # their own: their room climate entity sits on another device.
    valve_models = accessory_models()
    result = []
    for state in hass.states.async_all(BOILER_DOMAINS):
        entity_id = state.entity_id
        reg = entity_reg.async_get(entity_id)
        if reg is not None and (
            reg.entity_category is not None
            or reg.hidden_by is not None
            or reg.disabled_by is not None
            or reg.platform == DOMAIN
        ):
            continue
        if state.domain == "climate":
            if not is_trv_entity(hass, entity_id):
                result.append(entity_id)
            continue
        device_id = reg.device_id if reg is not None else None
        if device_id is not None:
            if device_id in climate_devices:
                continue
            device = device_reg.async_get(device_id)
            if device is not None and device.model in valve_models:
                continue
        result.append(entity_id)
    return sorted(result)


class Boiler:
    """The boiler driven by the rooms' demand."""

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self._hass = hass
        self.entity_id: str = config["entity_id"]
        self.domain: str = self.entity_id.split(".", 1)[0]
        self.on_mode: str = config.get(
            "on_hvac_mode", DEFAULT_BOILER_ON_HVAC_MODE
        )
        self.off_mode: str = config.get(
            "off_hvac_mode", DEFAULT_BOILER_OFF_HVAC_MODE
        )
        self.min_on = timedelta(
            minutes=config.get("min_on_minutes", DEFAULT_BOILER_MIN_ON_MINUTES)
        )
        self.min_off = timedelta(
            minutes=config.get(
                "min_off_minutes", DEFAULT_BOILER_MIN_OFF_MINUTES
            )
        )
        # Last known state (commanded, or read while syncing); None unknown.
        self._on: bool | None = None
        # When the boiler last switched (min on/off reference).
        self._since: datetime | None = None
        # False until the real entity state has been read and aligned.
        self._synced = False
        # A state change after this (startup loading) or before a return
        # online is not a switch: no min on / off from it.
        self._created = dt_util.utcnow()
        self._back_online = False
        # Rooms needing heat at the last evaluation (sorted area_ids), and
        # why: {area_id: [REASON_*]}.
        self.demand_rooms: list[str] = []
        self.demand_reasons: dict[str, list[str]] = {}
        # Rooms below their setpoint (hysteresis: in from setpoint -
        # BOILER_START_GAP, out once back at the setpoint).
        self._cold: set[str] = set()
        # Set while a switch waits for the min on/off duration.
        self.waiting_until: datetime | None = None

    @property
    def is_on(self) -> bool | None:
        """Last known boiler state (None until known)."""
        return self._on

    def same_target(self, other: Boiler) -> bool:
        """True when `other` drives the same entity the same way."""
        return (self.entity_id, self.on_mode, self.off_mode) == (
            other.entity_id,
            other.on_mode,
            other.off_mode,
        )

    def carry_state(self, old: Boiler) -> None:
        """Keep the switch state of the Boiler this one replaces."""
        if self.same_target(old):
            self._on = old._on
            self._since = old._since
            self._synced = old._synced
            self._created = old._created
            self._back_online = old._back_online
            self.demand_rooms = old.demand_rooms
            self.demand_reasons = old.demand_reasons
            self._cold = old._cold
            self.waiting_until = old.waiting_until

    def resync(self) -> None:
        """Re-read and align the entity state at the next evaluation.

        Called when the entity comes back online: its last_changed is that
        return, not a switch.
        """
        self._synced = False
        self._back_online = True

    def status(self) -> dict:
        """Status payload entry for the panel."""
        vendor = boiler_vendor(self._hass, self.entity_id)
        return {
            "entity_id": self.entity_id,
            "on": self._on,
            "demand_rooms": list(self.demand_rooms),
            "demand_reasons": {
                area_id: list(reasons)
                for area_id, reasons in self.demand_reasons.items()
            },
            "waiting_until": (
                self.waiting_until.isoformat() if self.waiting_until else None
            ),
            # Brand reporting flow / outdoor temperatures and heating curve.
            "vendor": vendor.label if vendor is not None else None,
        }

    def _read_state(self) -> tuple[bool | None, datetime] | None:
        """(on/off/None for another mode, last_changed); None if offline."""
        state = self._hass.states.get(self.entity_id)
        if state is None or state.state in _OFFLINE_STATES:
            return None
        if self.domain == "climate":
            on_value, off_value = self.on_mode, self.off_mode
        else:
            on_value, off_value = "on", "off"
        if state.state == on_value:
            current: bool | None = True
        elif state.state == off_value:
            current = False
        else:
            current = None
        return current, state.last_changed

    def _valve_demand(self, now: datetime, room: Room) -> bool | None:
        """The fresh valves' demand: True / False, None without one."""
        oldest = now - timedelta(minutes=BOILER_VALVE_MAX_AGE_MINUTES)
        fresh = False
        for entity_id in room.valve_entity_ids:
            if entity_id == self.entity_id:
                continue
            state = self._hass.states.get(entity_id)
            if state is None or state.state in _OFFLINE_STATES:
                continue
            action = state.attributes.get("hvac_action")
            # "off": switched off by an Off zone, not a demand answer.
            if action in (None, "off") or state.last_reported < oldest:
                continue
            if action == "heating":
                return True
            fresh = True
        return False if fresh else None

    def _below_setpoint(self, room: Room) -> bool:
        """Update and return the room's below-setpoint hysteresis."""
        area_id = room.area_id
        temp = room.room_temperature()
        setpoint = room.current_setpoint
        if temp is None or setpoint is None:
            self._cold.discard(area_id)
        elif temp >= setpoint:
            self._cold.discard(area_id)
        elif temp <= setpoint - BOILER_START_GAP:
            self._cold.add(area_id)
        return area_id in self._cold

    def _reasons(self, now: datetime, room: Room) -> list[str]:
        """Why the room needs heat (empty: it does not)."""
        cold = self._below_setpoint(room)
        if not room.has_available_trv:
            return []
        reasons = []
        if room.current_period in BOILER_HEATING_PERIODS:
            reasons.append(REASON_PERIOD)
        valve = self._valve_demand(now, room)
        if valve:
            reasons.append(REASON_VALVE)
        elif valve is None and cold:
            reasons.append(REASON_BELOW_SETPOINT)
        return reasons

    async def evaluate(self, now: datetime, rooms: dict[str, Room]) -> None:
        """Switch the boiler to follow the rooms' demand."""
        self._cold &= set(rooms)
        reasons = {
            area_id: self._reasons(now, room)
            for area_id, room in sorted(rooms.items())
        }
        self.demand_reasons = {a: r for a, r in reasons.items() if r}
        self.demand_rooms = list(self.demand_reasons)
        wanted = bool(self.demand_rooms)

        if not self._synced:
            read = self._read_state()
            if read is None:
                return  # offline — aligned when it comes back
            current, last_changed = read
            self._synced = True
            self._on = current
            # Another mode (e.g. auto), a state that appeared at startup or
            # on a return online: switch at once, no min duration.
            switched = (
                current is not None
                and not self._back_online
                and last_changed < self._created
            )
            self._since = last_changed if switched else None
            self._back_online = False

        if wanted == self._on:
            self.waiting_until = None
            return

        if self._on is not None and self._since is not None:
            min_duration = self.min_on if self._on else self.min_off
            ready_at = self._since + min_duration
            if now < ready_at:
                if self.waiting_until != ready_at:
                    self.waiting_until = ready_at
                    _LOGGER.info(
                        "boiler | waiting %s %smin",
                        "min_on" if self._on else "min_off",
                        max(1, round((ready_at - now).total_seconds() / 60)),
                    )
                return
        self.waiting_until = None

        if await self._command(wanted):
            self._on = wanted
            self._since = now
            if wanted:
                _LOGGER.info(
                    "boiler | on rooms=%s",
                    ",".join(
                        f"{area_id}({'+'.join(reasons)})"
                        for area_id, reasons in self.demand_reasons.items()
                    ),
                )
            else:
                _LOGGER.info("boiler | off")

    async def _command(self, on: bool) -> bool:
        """Send the on/off command; True on success."""
        if self.domain == "climate":
            service = "set_hvac_mode"
            data = {
                "entity_id": self.entity_id,
                "hvac_mode": self.on_mode if on else self.off_mode,
            }
        else:
            service = "turn_on" if on else "turn_off"
            data = {"entity_id": self.entity_id}
        try:
            async with asyncio.timeout(TRV_COMMAND_TIMEOUT):
                await self._hass.services.async_call(
                    self.domain, service, data, blocking=True
                )
        except TimeoutError:
            _LOGGER.warning(
                "timeout | boiler=%s %s after %ss",
                self.entity_id,
                "on" if on else "off",
                TRV_COMMAND_TIMEOUT,
            )
            return False
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to switch boiler %s %s",
                self.entity_id,
                "on" if on else "off",
            )
            return False
        return True
