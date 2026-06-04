# SPDX-License-Identifier: MIT
"""Climate Manager zone domain model.

Defines the ZoneMode state machine (plain base class, assert-False overloads,
no ABC) and the Zone class that owns period evaluation, INFO log emission on
(period, mode_name) change (OBS-01/D-03), and first-tick suppression.

Design decisions:
- D-03: zone log state encodes both period AND mode:
  state=<old_period>[<old_mode>]->new_period>[<new_mode>]
- D-04: Zone owns ZoneMode; ZoneMode reads zone state through weakref at
  call time — no config on the mode object.
- D-09: reason field distinguishes schedule-driven vs user-driven changes.
- D-10: anti-spam is driven by Zone._current_period/_current_mode_name — no
  separate log-state dict. Log fires only when (period, mode_name) changes.
- D-01: zone name in log is short-stripped (zone_main -> zone=main).
- Open Question 1: first-tick log is suppressed (avoid None[None]->...).
"""

from __future__ import annotations

import logging
import weakref
from typing import TYPE_CHECKING

from .const import (
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
)
from .schedule import compute_occupied_temp, evaluate_schedule

if TYPE_CHECKING:
    from .eval_context import EvalContext
    from .room import Room

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Short-name helper (D-01)
# ---------------------------------------------------------------------------


def _short_name(entity_id: str) -> str:
    """Strip domain/prefix for log display (D-01).

    Examples:
        zone_main   -> main
        zone_living -> living
        area_kitchen -> kitchen
    """
    if "." in entity_id:
        return entity_id.split(".", 1)[1]
    for prefix in ("area_", "zone_"):
        if entity_id.startswith(prefix):
            return entity_id[len(prefix) :]
    return entity_id


# ---------------------------------------------------------------------------
# ZoneMode base class + three concrete subclasses
# ---------------------------------------------------------------------------


class ZoneMode:
    """Plain base class for zone operation modes (D-04).

    Holds a weakref back-link to the owning Zone; reads zone.time_program
    and zone.rooms at call time — no config parameters on evaluate().

    The base evaluate() uses assert False (not NotImplementedError, not
    @abstractmethod) per D-04.
    """

    mode_name: str = ""

    def __init__(self, zone: "Zone") -> None:
        self._zone_ref: weakref.ref[Zone] = weakref.ref(zone)

    @property
    def zone(self) -> "Zone":
        """Dereference the weakref; assert not garbage-collected."""
        z = self._zone_ref()
        assert z is not None, "Zone has been garbage-collected"
        return z

    async def evaluate(self, ctx: "EvalContext") -> tuple[str, str]:
        """Evaluate this mode; return (period, mode_name).

        Subclasses override this. Base raises assert False.
        """
        assert False, f"{type(self).__name__}.evaluate() not implemented"


class ZoneModeOff(ZoneMode):
    """Zone mode: OFF — all rooms frost-locked (EVAL-01).

    Iterates zone.rooms and calls room.apply_setpoint(PERIOD_FROST_PROTECTION,
    frost_temp, ctx) for each room.
    """

    mode_name: str = "off"

    async def evaluate(self, ctx: "EvalContext") -> tuple[str, str]:
        """Frost-lock all rooms in the zone."""
        zone = self.zone
        frost_temp: float = ctx.period_temperatures[PERIOD_FROST_PROTECTION]
        for room in zone.rooms:
            await room.apply_setpoint(PERIOD_FROST_PROTECTION, frost_temp, ctx)
        return PERIOD_FROST_PROTECTION, self.mode_name


class ZoneModeTimeProgram(ZoneMode):
    """Zone mode: TIME_PROGRAM — rooms follow the zone schedule (EVAL-02).

    Evaluates evaluate_schedule(zone.time_program, ctx.now) to resolve the
    active period, then pushes the corresponding temperature to all rooms.
    """

    mode_name: str = "time_program"

    async def evaluate(self, ctx: "EvalContext") -> tuple[str, str]:
        """Apply schedule-based setpoint to all rooms."""
        zone = self.zone
        period: str = evaluate_schedule(zone.time_program, ctx.now)
        temp: float | None = ctx.period_temperatures.get(period)
        if temp is None:
            _LOGGER.warning(
                "Unknown period %r in zone %s — skipping setpoint",
                period,
                zone.zone_id,
            )
            return period, self.mode_name
        for room in zone.rooms:
            await room.apply_setpoint(period, temp, ctx)
        return period, self.mode_name


class ZoneModeProgramPresences(ZoneMode):
    """Zone mode: TIME_PROGRAM_PRESENCES — presence overrides baseline (EVAL-03).

    Computes the baseline period from the schedule, then per-room iterates
    room.assigned_persons calling await person.evaluate(ctx) (cached in ctx),
    passes any_present to compute_occupied_temp, and applies the resolved
    setpoint via room.apply_setpoint.
    """

    mode_name: str = "time_program_presences"

    async def evaluate(self, ctx: "EvalContext") -> tuple[str, str]:
        """Apply presence-aware setpoint to all rooms."""
        zone = self.zone

        # Baseline period from the zone time program
        baseline_period: str = evaluate_schedule(zone.time_program, ctx.now)

        last_period = baseline_period
        for room in zone.rooms:
            # Evaluate presence for all assigned persons (cached in ctx)
            any_present = False
            for person in room.assigned_persons:
                is_home = await person.evaluate(ctx)
                if is_home:
                    any_present = True

            # compute_occupied_temp applies PERSON-07/08/09 rules
            occupied_temp, occupied_period = compute_occupied_temp(
                zone.time_program,
                ctx.now,
                any_present,
                ctx.period_temperatures,
            )

            await room.apply_setpoint(occupied_period, occupied_temp, ctx)
            last_period = occupied_period

        # Return the last resolved period (or baseline if no rooms)
        return last_period, self.mode_name


# ---------------------------------------------------------------------------
# Mode factory
# ---------------------------------------------------------------------------

_MODE_FACTORY: dict[str, type[ZoneMode]] = {
    MODE_OFF: ZoneModeOff,
    MODE_TIME_PROGRAM: ZoneModeTimeProgram,
    MODE_TIME_PROGRAM_PRESENCES: ZoneModeProgramPresences,
}


# ---------------------------------------------------------------------------
# Zone class
# ---------------------------------------------------------------------------


class Zone:
    """Zone domain class — state machine owning a ZoneMode and a room list.

    One Zone instance is created per zone ID that the coordinator manages.
    The coordinator populates _rooms and _time_program at setup time.

    Design decisions:
    - D-04: Zone.evaluate delegates to self._mode.evaluate(ctx).
    - D-10: anti-spam via _current_period/_current_mode_name scalars on Zone.
    - D-03: log state encodes period[mode] format.
    - D-09: reason field in log distinguishes trigger type.
    - Open Question 1: first-tick log is suppressed.
    - D-01: short-stripped zone name in log (zone_main -> zone=main).
    """

    def __init__(
        self,
        zone_id: str,
        hass=None,
        initial_mode: str = MODE_TIME_PROGRAM,
        time_program: dict | None = None,
        preheat_enabled: bool = False,
    ) -> None:
        self.zone_id = zone_id
        self._hass = hass
        self._rooms: list[Room] = []
        self._time_program: dict = time_program or {}
        self._preheat_enabled: bool = preheat_enabled

        # D-10 anti-spam state — no separate log-state dict
        self._current_period: str | None = None
        self._current_mode_name: str | None = None

        # Build the initial mode object
        mode_cls = _MODE_FACTORY.get(initial_mode, ZoneModeTimeProgram)
        self._mode: ZoneMode = mode_cls(self)

    # ------------------------------------------------------------------
    # Properties read by ZoneMode subclasses through the weakref
    # ------------------------------------------------------------------

    @property
    def rooms(self) -> list:
        """List of Room objects assigned to this zone."""
        return self._rooms

    @property
    def time_program(self) -> dict:
        """Zone time program (per-day schedule dict)."""
        return self._time_program

    @property
    def preheat_enabled(self) -> bool:
        """Whether preheat is enabled for this zone."""
        return self._preheat_enabled

    # ------------------------------------------------------------------
    # Core evaluate
    # ------------------------------------------------------------------

    async def evaluate(self, ctx: "EvalContext") -> None:
        """Evaluate the zone: delegate to mode, then log if state changed.

        First-tick suppression (Open Question 1): when _current_period is
        None, store state without emitting any log record.
        """
        period, mode_name = await self._mode.evaluate(ctx)

        if self._current_period is None:
            # First tick — store state, suppress log (avoid None[None]->...)
            self._current_period = period
            self._current_mode_name = mode_name
            return

        if (period, mode_name) != (
            self._current_period,
            self._current_mode_name,
        ):
            # Build D-09 schedule reason for time-program-driven changes
            reason = f"time_program:{period}"
            self._log_period_change(
                old_period=self._current_period,
                old_mode=self._current_mode_name,
                new_period=period,
                new_mode=mode_name,
                reason=reason,
            )
            self._current_period = period
            self._current_mode_name = mode_name

    # ------------------------------------------------------------------
    # Log helper (D-03 format — called directly by tests)
    # ------------------------------------------------------------------

    def _log_period_change(
        self,
        old_period: str,
        old_mode: str,
        new_period: str,
        new_mode: str,
        reason: str,
    ) -> None:
        """Emit the zone INFO log record in D-03 format.

        Format: zone | zone=<short> state=<old_period>[<old_mode>]
                ->new_period>[<new_mode>] reason=<why>
        """
        old_state = f"{old_period}[{old_mode}]"
        new_state = f"{new_period}[{new_mode}]"
        _LOGGER.info(
            "zone | zone=%s state=%s→%s reason=%s",
            _short_name(self.zone_id),
            old_state,
            new_state,
            reason,
        )

    # ------------------------------------------------------------------
    # Mode mutation (WS handler API)
    # ------------------------------------------------------------------

    def change_mode(self, new_mode: str, reason: str = "") -> None:
        """Swap _mode and log the transition (user-driven, D-09 reason).

        Emits: reason=user:<old_mode>-><new_mode>
        """
        old_mode_name = self._mode.mode_name
        mode_cls = _MODE_FACTORY.get(new_mode)
        if mode_cls is None:
            _LOGGER.warning(
                "Unknown mode %r for zone %s — ignoring change_mode",
                new_mode,
                self.zone_id,
            )
            return
        self._mode = mode_cls(self)
        new_mode_name = self._mode.mode_name

        # Log the mode change if state was initialized
        if self._current_period is not None:
            transition_reason = f"user:{old_mode_name}→{new_mode_name}"
            self._log_period_change(
                old_period=self._current_period,
                old_mode=old_mode_name,
                new_period=self._current_period,
                new_mode=new_mode_name,
                reason=transition_reason,
            )
            self._current_mode_name = new_mode_name

    # ------------------------------------------------------------------
    # Config update (plain setter — NO log, D-10 anti-pattern)
    # ------------------------------------------------------------------

    def update_config(self, time_program: dict) -> None:
        """Update the zone time program. Emits NO log record."""
        self._time_program = time_program
