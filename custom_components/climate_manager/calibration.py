# SPDX-License-Identifier: MIT
"""Offset calibration: keep each TRV reading aligned on its room sensor.

The vendors say what can be calibrated in a room (CalibrationTarget: which
offset, compared with which climate entity) and how to read and write the
offset. This module owns the brand-neutral part:

- delta = room sensor - TRV current_temperature, ignored within the
  threshold (tighter while a pre-heat runs);
- at most one write per target every _CALIBRATION_MIN_INTERVAL (cloud API
  quotas);
- the new offset accumulates on the last one written, or on the one the
  vendor reports after a restart, clamped to ±_OFFSET_CLAMP;
- one INFO "calibrate |" log per offset written.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from .const import PREHEAT_CALIBRATION_THRESHOLD, TRV_COMMAND_TIMEOUT
from .room import resolve_room_sensor
from .vendors import CalibrationTarget, calibration_targets

if TYPE_CHECKING:
    from . import ClimateManagerData
    from .room import Room

_LOGGER = logging.getLogger(__name__)

# Hardware-safe maximum for a TRV temperature offset (±5 °C on most brands).
_OFFSET_CLAMP = 5.0
# Minimum time between two offset writes on a target (avoids HTTP 429s).
_CALIBRATION_MIN_INTERVAL = timedelta(minutes=5)


def calibration_threshold(config: dict, preheating: bool) -> float:
    """Offset calibration threshold (°C), tighter while a pre-heat runs."""
    threshold = config.get("calibration_threshold", 0.5)
    if preheating:
        return min(threshold, PREHEAT_CALIBRATION_THRESHOLD)
    return threshold


def log_calibration(
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
        "calibrate | room=%s trv=%s sensor=%.1f°C trv=%.1f°C delta=%+.1f"
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


def _float_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    """Numeric state of entity_id, None when missing or not a number."""
    state = hass.states.get(entity_id) if entity_id else None
    if state is None:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


class Calibrator:
    """Calibrates every room's targets and remembers what it wrote.

    The memory (keyed by CalibrationTarget.key) survives domain rebuilds:
    it lives on the coordinator, not on the Room objects.
    """

    def __init__(self, hass: HomeAssistant, data: ClimateManagerData) -> None:
        self._hass = hass
        self._data = data
        # Last absolute offset written per target.
        self.last_offset: dict[str, float] = {}
        # When each target's offset was last written (ISO 8601, UTC).
        self.last_changed: dict[str, str] = {}
        # Last delta corrected per target (sensor - TRV).
        self.last_delta: dict[str, float] = {}

    def targets(self, area_id: str) -> list[CalibrationTarget]:
        """Calibration targets of a room, as the vendors resolve them."""
        return calibration_targets(
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

    def current_offset(self, target: CalibrationTarget) -> float | None:
        """Offset last written, else the one the vendor reports."""
        if target.key in self.last_offset:
            return self.last_offset[target.key]
        return target.vendor.read_offset(self._hass, target)

    async def calibrate_all(
        self, config: dict, rooms: dict[str, Room]
    ) -> None:
        """Calibrate every room concurrently (no-op when disabled)."""
        if not config.get("calibration_enabled", False):
            return
        await asyncio.gather(
            *(
                self.calibrate_room(config, area_id, rooms.get(area_id))
                for area_id in self._data.rooms
            )
        )

    async def calibrate_room(
        self, config: dict, area_id: str, room: Room | None
    ) -> None:
        """Calibrate a room's targets toward its temperature sensor."""
        if not config.get("calibration_enabled", False):
            return
        sensor_temp = _float_state(
            self._hass, resolve_room_sensor(self._hass, area_id, config)
        )
        if sensor_temp is None:
            return
        threshold = calibration_threshold(
            config, room is not None and room.preheat_boosting
        )
        await asyncio.gather(
            *(
                self._calibrate(area_id, target, sensor_temp, threshold)
                for target in self.targets(area_id)
            )
        )

    async def _calibrate(
        self,
        area_id: str,
        target: CalibrationTarget,
        sensor_temp: float,
        threshold: float,
    ) -> None:
        state = self._hass.states.get(target.temp_entity_id)
        if state is None or state.state in ("unavailable", "unknown"):
            return
        try:
            trv_temp = float(state.attributes["current_temperature"])
        except (KeyError, TypeError, ValueError):
            return

        delta = sensor_temp - trv_temp
        if abs(delta) <= threshold:
            return

        last_changed = self.last_changed.get(target.key)
        if last_changed is not None:
            elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(
                last_changed
            )
            if elapsed < _CALIBRATION_MIN_INTERVAL:
                return

        existing = self.current_offset(target)
        if existing is None:
            existing = 0.0
        new_offset = round(
            max(-_OFFSET_CLAMP, min(_OFFSET_CLAMP, existing + delta)), 1
        )
        try:
            async with asyncio.timeout(TRV_COMMAND_TIMEOUT):
                await target.vendor.write_offset(
                    self._hass, target, new_offset
                )
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to apply offset %.1f to %s", new_offset, target.name
            )
            return
        self.last_offset[target.key] = new_offset
        self.last_changed[target.key] = datetime.now(timezone.utc).isoformat(
            timespec="seconds"
        )
        self.last_delta[target.key] = round(delta, 2)
        log_calibration(
            area_id,
            target.name,
            sensor_temp,
            trv_temp,
            existing,
            new_offset,
            threshold,
        )
