# SPDX-License-Identifier: MIT
"""Boiler control: heat while at least one room needs heat.

A room needs heat when its effective period (schedule, presence and
pre-heat resolved — Room.current_period) is one of BOILER_HEATING_PERIODS.
Room temperatures and valve openings are not considered (v1).

The boiler is a climate entity (its hvac_mode toggles between the
configured on/off modes) or a switch / input_boolean (turn_on/turn_off).

Like the TRVs, a command is sent only when the demand changes: a manual
change on the boiler stays until the next demand change. The first tick
(startup, rebuild with a new entity) and a return online read the real
entity state instead, and align it. A minimum on / off duration, measured
from the last switch (the entity's last_changed after a restart), guards
the boiler against short cycles.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from .const import (
    BOILER_HEATING_PERIODS,
    DEFAULT_BOILER_MIN_OFF_MINUTES,
    DEFAULT_BOILER_MIN_ON_MINUTES,
    DEFAULT_BOILER_OFF_HVAC_MODE,
    DEFAULT_BOILER_ON_HVAC_MODE,
    TRV_COMMAND_TIMEOUT,
)

if TYPE_CHECKING:
    from .room import Room

_LOGGER = logging.getLogger(__name__)

_OFFLINE_STATES = ("unavailable", "unknown")


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
        # Rooms needing heat at the last evaluation (sorted area_ids).
        self.demand_rooms: list[str] = []
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
            self.demand_rooms = old.demand_rooms
            self.waiting_until = old.waiting_until

    def resync(self) -> None:
        """Re-read and align the entity state at the next evaluation."""
        self._synced = False

    def status(self) -> dict:
        """Status payload entry for the panel."""
        return {
            "entity_id": self.entity_id,
            "on": self._on,
            "demand_rooms": list(self.demand_rooms),
            "waiting_until": (
                self.waiting_until.isoformat() if self.waiting_until else None
            ),
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

    async def evaluate(self, now: datetime, rooms: dict[str, Room]) -> None:
        """Switch the boiler to follow the rooms' demand."""
        self.demand_rooms = sorted(
            area_id
            for area_id, room in rooms.items()
            if room.current_period in BOILER_HEATING_PERIODS
        )
        wanted = bool(self.demand_rooms)

        if not self._synced:
            read = self._read_state()
            if read is None:
                return  # offline — aligned when it comes back
            current, last_changed = read
            self._synced = True
            self._on = current
            # Another mode (e.g. auto): switch at once, no min duration.
            self._since = last_changed if current is not None else None

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
                    "boiler | on rooms=%s", ",".join(self.demand_rooms)
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
