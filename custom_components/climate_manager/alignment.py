# SPDX-License-Identifier: MIT
"""Offset alignment: keep each TRV reading aligned on its room sensor.

The vendors say what can be aligned in a room (AlignmentTarget: which
offset, compared with which climate entity) and how to read and write the
offset. This module owns the brand-neutral part:

- delta = mean room sensor - mean TRV current_temperature over the last
  _STABLE_WINDOW (time-weighted), ignored within the threshold. A TRV
  regulating at its setpoint opens and closes its valve in cycles, and
  its reading next to the radiator swings with them: the means cancel
  the cycles;
- only measured in settled conditions: the TRV setpoint unchanged for
  _SETPOINT_SETTLE, and neither reading drifting: the means of the two
  halves of the window within _STABLE_TOLERANCE, for the sensor and for
  the TRV. A TRV next to a radiator heating up or cooling down, or in
  the sun, drifts away from the room: correcting that gap winds the
  offset up to the clamp. A radiator keeps warming its TRV for a while
  after closing: the settle time after a setpoint change skips that
  hump. No alignment while a pre-heat runs (room.py): the boost and its
  release drive the TRV far from its usual regime: the window starts
  after the run (its readings are dropped, never seeded). Once the run
  ends, the setpoint change starts the settle time again;
- the readings and the setpoint history are kept in memory, seeded once
  per entity from the recorder (the last _SETPOINT_SETTLE): a restart
  does not wait for a new window. Without the recorder (not loaded,
  entity excluded, query failed) the window fills from the passes;
- after a write, the TRV readings start over: the next correction waits
  for the TRV to settle on its new offset;
- at most one write attempt per target every _ALIGNMENT_MIN_INTERVAL
  (cloud API quotas), failed attempts included;
- the new offset accumulates on the last one written, or on the one the
  vendor reports after a restart, clamped to ±_OFFSET_CLAMP; nothing is
  written when it does not change (at the clamp);
- one INFO "align |" log per offset written.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, State

from .const import TRV_COMMAND_TIMEOUT
from .room import resolve_room_sensor
from .vendors import AlignmentTarget, alignment_targets

if TYPE_CHECKING:
    from . import ClimateManagerData
    from .room import Room

_LOGGER = logging.getLogger(__name__)

# Hardware-safe maximum for a TRV temperature offset (±5 °C on most brands).
_OFFSET_CLAMP = 5.0
# Minimum time between two offset writes on a target (avoids HTTP 429s).
_ALIGNMENT_MIN_INTERVAL = timedelta(minutes=5)
# Settled conditions: the TRV setpoint unchanged for _SETPOINT_SETTLE, the
# means of the two halves of _STABLE_WINDOW within _STABLE_TOLERANCE (°C)
# for both readings.
_SETPOINT_SETTLE = timedelta(minutes=90)
_STABLE_WINDOW = timedelta(minutes=60)
_STABLE_TOLERANCE = 0.2


def log_alignment(
    area_id: str,
    trv: str,
    sensor_temp: float,
    trv_temp: float,
    old_offset: float,
    new_offset: float,
    threshold: float,
) -> None:
    """INFO log for one offset written to a TRV."""
    _LOGGER.info(
        "align | room=%s trv=%s sensor=%.1f°C trv=%.1f°C delta=%+.1f"
        " offset=%+.1f→%+.1f threshold=%.1f",
        area_id,
        trv,
        sensor_temp,
        trv_temp,
        sensor_temp - trv_temp,
        old_offset,
        new_offset,
        threshold,
    )


def _mean(
    readings: deque[tuple[datetime, float]], start: datetime, end: datetime
) -> float:
    """Time-weighted mean over [start, end]; readings[0] is at or before
    start, each reading holds until the next one."""
    total = 0.0
    points = list(readings)
    for i, (at, value) in enumerate(points):
        until = points[i + 1][0] if i + 1 < len(points) else end
        span = (min(until, end) - max(at, start)).total_seconds()
        if span > 0:
            total += value * span
    return total / (end - start).total_seconds()


async def _recorded_states(
    hass: HomeAssistant, entity_id: str, start: datetime, end: datetime
) -> list[State]:
    """entity_id's recorded states over [start, end] (with the one at
    start); [] when the recorder cannot tell."""
    from homeassistant.components.recorder import (  # noqa: PLC0415
        get_instance,
        history,
    )

    try:
        # Every update: a TRV reading is an attribute, not its state.
        result = await get_instance(hass).async_add_executor_job(
            partial(
                history.get_significant_states,
                hass,
                start,
                end,
                [entity_id],
                significant_changes_only=False,
            )
        )
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("align | no history for %s: %r", entity_id, err)
        return []
    return [
        state
        for state in result.get(entity_id, [])
        if state.state not in ("unavailable", "unknown")
    ]


def _setpoint_since(states: list[State]) -> tuple[tuple, datetime]:
    """(TRV mode and setpoint, since when) from time-ordered states."""
    key: tuple | None = None
    since = states[0].last_updated
    for state in states:
        current = (state.state, state.attributes.get("temperature"))
        if current != key:
            key, since = current, state.last_updated
    return key, since


def _level(window: tuple[float, float]) -> bool:
    """True when the two half-window means are within _STABLE_TOLERANCE."""
    return abs(window[1] - window[0]) <= _STABLE_TOLERANCE + 1e-9


def _float_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Numeric state of entity_id, None when missing or not a number."""
    state = hass.states.get(entity_id) if entity_id else None
    if state is None:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


class SensorAligner:
    """Aligns every room's targets and remembers what it wrote.

    The memory (keyed by AlignmentTarget.key) survives domain rebuilds:
    it lives on the coordinator, not on the Room objects.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        data: ClimateManagerData,
        rooms: Callable[[], dict[str, Room]] = dict,
    ) -> None:
        self._hass = hass
        self._data = data
        # The coordinator's current Room objects (rebuilt on config changes).
        self._rooms = rooms
        # Last absolute offset written per target.
        self.last_offset: dict[str, float] = {}
        # When each target's offset was last written (ISO 8601, UTC).
        self.last_changed: dict[str, str] = {}
        # Last delta corrected per target (sensor - TRV).
        self.last_delta: dict[str, float] = {}
        # When each target's offset was last attempted, written or not.
        self._last_attempt: dict[str, datetime] = {}
        # Recent readings per entity: the last one before the window, then
        # every one within it.
        self._readings: dict[str, deque[tuple[datetime, float]]] = {}
        # TRV mode and setpoint per entity, and since when they hold.
        self._setpoints: dict[str, tuple[tuple, datetime]] = {}
        # Entities whose readings were seeded from the recorder (or tried).
        self._seeded: set[str] = set()

    def targets(self, area_id: str) -> list[AlignmentTarget]:
        """Alignment targets of a room, as the vendors resolve them."""
        return alignment_targets(
            self._hass,
            area_id,
            self._data.rooms.get(area_id, []),
            self._data.runtime_config.get("matter_mappings", {}),
        )

    def watched_entities(self) -> dict[str, str]:
        """{temperature source entity: area_id} over all targets."""
        return {
            target.temp_entity_id: area_id
            for area_id in self._data.rooms
            for target in self.targets(area_id)
        }

    def current_offset(self, target: AlignmentTarget) -> float | None:
        """Offset last written, else the one the vendor reports."""
        if target.key in self.last_offset:
            return self.last_offset[target.key]
        return target.vendor.read_offset(self._hass, target)

    def _window(
        self, entity_id: str, now: datetime, value: float
    ) -> tuple[float, float] | None:
        """Record a reading; the means of the window's two halves.

        None until the readings cover the whole window. Each reading
        holds until the next one (time-weighted): an event-driven tick
        does not count twice.
        """
        readings = self._readings.setdefault(entity_id, deque())
        readings.append((now, value))
        start = now - _STABLE_WINDOW
        while len(readings) > 1 and readings[1][0] <= start:
            readings.popleft()
        if readings[0][0] > start:
            return None
        middle = start + _STABLE_WINDOW / 2
        return _mean(readings, start, middle), _mean(readings, middle, now)

    def _settled(self, state, now: datetime) -> bool:
        """Record the TRV setpoint; True once unchanged for the settle time."""
        setpoint = (state.state, state.attributes.get("temperature"))
        known = self._setpoints.get(state.entity_id)
        if known is None or known[0] != setpoint:
            self._setpoints[state.entity_id] = (setpoint, now)
            return False
        return now - known[1] >= _SETPOINT_SETTLE

    async def align_all(self, config: dict) -> None:
        """Align every room concurrently (no-op when disabled)."""
        if not config.get("alignment_enabled", False):
            return
        await asyncio.gather(
            *(self.align_room(config, area_id) for area_id in self._data.rooms)
        )

    async def align_room(self, config: dict, area_id: str) -> None:
        """Align a room's targets toward its temperature sensor."""
        if not config.get("alignment_enabled", False):
            return
        sensor_id = resolve_room_sensor(self._hass, area_id, config)
        targets = self.targets(area_id)
        room = self._rooms().get(area_id)
        if room is not None and room.preheat_running:
            # The window starts after the run: none of its readings, live
            # or recorded.
            sources = [t.temp_entity_id for t in targets]
            for entity_id in filter(None, (sensor_id, *sources)):
                self._readings.pop(entity_id, None)
                self._seeded.add(entity_id)
            return
        sensor_temp = _float_state(self._hass, sensor_id)
        if sensor_id is None or sensor_temp is None:
            return
        now = datetime.now(timezone.utc)
        await self._seed([sensor_id], [t.temp_entity_id for t in targets], now)
        sensor_window = self._window(sensor_id, now, sensor_temp)
        threshold = config.get("alignment_threshold", 0.5)
        await asyncio.gather(
            *(
                self._align(area_id, target, now, sensor_window, threshold)
                for target in targets
            )
        )

    async def _seed(
        self, sensors: list[str], trvs: list[str], now: datetime
    ) -> None:
        """Seed readings and setpoints never seen from the recorder."""
        todo = [
            (entity_id, is_trv)
            for entity_ids, is_trv in ((sensors, False), (trvs, True))
            for entity_id in entity_ids
            if entity_id not in self._seeded
        ]
        if not todo:
            return
        # Marked first: a concurrent pass does not query again.
        self._seeded.update(entity_id for entity_id, _ in todo)
        if "recorder" not in self._hass.config.components:
            return
        start = now - _SETPOINT_SETTLE
        for entity_id, is_trv in todo:
            states = await _recorded_states(self._hass, entity_id, start, now)
            readings: list[tuple[datetime, float]] = []
            for state in states:
                raw = (
                    state.attributes.get("current_temperature")
                    if is_trv
                    else state.state
                )
                try:
                    readings.append((state.last_updated, float(raw)))
                except (TypeError, ValueError):
                    continue
            # Passes that ran meanwhile stay, in time order.
            known = self._readings.get(entity_id, deque())
            self._readings[entity_id] = deque(
                sorted([*readings, *known], key=lambda r: r[0])
            )
            if is_trv and states and entity_id not in self._setpoints:
                self._setpoints[entity_id] = _setpoint_since(states)

    async def _align(
        self,
        area_id: str,
        target: AlignmentTarget,
        now: datetime,
        sensor_window: tuple[float, float] | None,
        threshold: float,
    ) -> None:
        state = self._hass.states.get(target.temp_entity_id)
        if state is None or state.state in ("unavailable", "unknown"):
            return
        try:
            trv_temp = float(state.attributes["current_temperature"])
        except (KeyError, TypeError, ValueError):
            return
        # Both record the current state: evaluate them before any return.
        trv_window = self._window(target.temp_entity_id, now, trv_temp)
        settled = self._settled(state, now)
        if not settled or sensor_window is None or trv_window is None:
            return
        if not (_level(sensor_window) and _level(trv_window)):
            return
        sensor_temp = sum(sensor_window) / 2
        trv_temp = sum(trv_window) / 2

        delta = sensor_temp - trv_temp
        if abs(delta) <= threshold:
            return

        existing = self.current_offset(target)
        if existing is None:
            existing = 0.0
        new_offset = round(
            max(-_OFFSET_CLAMP, min(_OFFSET_CLAMP, existing + delta)), 1
        )
        if new_offset == round(existing, 1):
            return

        last_attempt = self._last_attempt.get(target.key)
        if (
            last_attempt is not None
            and now - last_attempt < _ALIGNMENT_MIN_INTERVAL
        ):
            return
        self._last_attempt[target.key] = now

        try:
            async with asyncio.timeout(TRV_COMMAND_TIMEOUT):
                await target.vendor.write_offset(self._hass, target, new_offset)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to apply offset %.1f to %s: %r",
                new_offset,
                target.name,
                err,
            )
            return
        self.last_offset[target.key] = new_offset
        self.last_changed[target.key] = now.isoformat(timespec="seconds")
        self.last_delta[target.key] = round(delta, 2)
        # The reading shifts with the new offset: wait for it to settle.
        self._readings.pop(target.temp_entity_id, None)
        log_alignment(
            area_id,
            target.name,
            sensor_temp,
            trv_temp,
            existing,
            new_offset,
            threshold,
        )
