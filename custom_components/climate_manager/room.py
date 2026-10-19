# SPDX-License-Identifier: MIT
"""Climate Manager Room domain class (D-06).

Room is a plain class (no state machine) that owns:
  - Its assigned TRV groups (_trv_groups: list[TRVGroup])
  - Its assigned persons (_assigned_persons: list)
  - Preheat state migrated from coordinator dicts, collapsed to per-room
    scalars: _preheat_active, _preheat_target, _preheat_suppressed,
    _preheat_in_progress
  - Calibration tracking fields: _calibration_last_changed,
    _calibration_last_delta, _calibration_last_offset
  - A reference to its owning Zone (_zone) so compute_preheat can read
    zone.preheat_enabled

Public methods:
  apply_setpoint(period, temp, ctx) — push temp to all TRVGroups
  compute_preheat(ctx)              — per-room preheat pass (D-09)
  calibrate_trvs(ctx)              — per-room calibration pass (CALIB-03)
"""

from __future__ import annotations

import asyncio
import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from .const import (
    DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
    PERIOD_PREHEAT,
    PREHEAT_CONVERGENCE_THRESHOLD,
    PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD,
    PREHEAT_MAX_SAMPLES,
    PRESENCE_ABSENT,
    PRESENCE_HA,
    PRESENCE_PRESENT,
    TRV_COMMAND_TIMEOUT,
)
from .schedule import (
    evaluate_schedule,
    next_occupied_at,
    next_setpoint_increase_at,
    resolve_presence,
)
from .trv import (
    is_trv_entity,
    set_trv_offset,
    supports_offset_calibration,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .eval_context import EvalContext

_LOGGER = logging.getLogger(__name__)

# Hardware-safe maximum for TRV temperature offset.
_OFFSET_CLAMP = 5.0


class Room:
    """Room domain class — plain class owning TRV groups and preheat state.

    One Room instance is created per HA area that the coordinator manages.
    The coordinator populates _trv_groups and _zone at setup time.

    Design decisions:
    - D-06: preheat/calibration state is per-room (not coordinator dicts)
    - D-07: TRVGroup assembly happens at coordinator init
    - D-09: apply_setpoint delegates to every TRVGroup via asyncio.gather
    - T-16-09: inertia-model corruption guard (exclude samples that never
      reached target) preserved verbatim from _async_preheat_room (PREHEAT-03)
    - T-16-10: no unguarded service calls added here; TRV methods are already
      exception-safe (plan 16-03)
    """

    def __init__(
        self,
        area_id: str,
        hass: "HomeAssistant | None" = None,
    ) -> None:
        """Initialise the Room.

        Args:
            area_id: The HA area_id this room represents.
            hass:    The HomeAssistant instance (optional at test time).
        """
        self.area_id: str = area_id
        self._hass: "HomeAssistant | None" = hass

        # TRV groups populated at coordinator init (D-07).
        self._trv_groups: list = []

        # Persons assigned to this room (list of person config dicts or ids).
        self.assigned_persons: list = []

        # Reference to the owning Zone (set at coordinator init so
        # compute_preheat can read zone.preheat_enabled without re-reading
        # the config dict — per 16-PATTERNS preheat zone-enabled lookup).
        self._zone: object | None = None

        # Effective period last applied to this room (status display). In
        # presence mode each room resolves its own period, so the zone-level
        # _current_period is not accurate per-room — track it here instead.
        self._last_period: str | None = None

        # ---------------------------------------------------------------
        # Preheat state — migrated from coordinator dicts (D-06)
        # Original coordinator __init__ lines 155-159; keys collapsed to
        # per-room scalars.
        # ---------------------------------------------------------------
        self._preheat_active: bool = False
        self._preheat_target: float | None = None
        self._preheat_suppressed: bool = False
        # Running pre-heat, or empty dict:
        # {start_time: datetime, target_temp: float, until: datetime,
        #  converged: bool}. While set and before `until`, apply_setpoint
        # holds target_temp (when warmer than the scheduled setpoint).
        self._preheat_in_progress: dict = {}

        # ---------------------------------------------------------------
        # Frost-lock flag — set at zone evaluation time (coordinator
        # _frost_locked_rooms snapshot migrated to per-room bool).
        # ---------------------------------------------------------------
        self._frost_locked: bool = False

        # ---------------------------------------------------------------
        # Calibration tracking — migrated from coordinator dicts (D-06)
        # Original coordinator __init__ lines 127-132.
        # ---------------------------------------------------------------
        self._calibration_last_changed: str | None = None
        self._calibration_last_delta: float | None = None
        self._calibration_last_offset: float = 0.0

    @property
    def current_period(self) -> str | None:
        """Effective period last applied (None before first evaluation)."""
        return self._last_period

    # -------------------------------------------------------------------
    # Core delegation
    # -------------------------------------------------------------------

    async def apply_setpoint(
        self, period: str, temp: float, ctx: "EvalContext"
    ) -> None:
        """Push temp to all TRV groups in this room.

        D-09 apply_setpoint → TRVGroup delegation.
        Uses asyncio.gather for concurrent pushes (16-PATTERNS asyncio.gather
        pattern).  Zero groups is a no-op.

        While a pre-heat runs (until the occupied time it anticipates), its
        target overrides a lower scheduled setpoint and the room reports the
        "preheat" period — the zone evaluation never undoes a pre-heat.
        """
        ip = self._preheat_in_progress
        if ip and ctx.now < ip["until"] and ip["target_temp"] > temp:
            period, temp = PERIOD_PREHEAT, ip["target_temp"]
        # Record the effective period for status display before any early
        # return so even TRV-less rooms surface the correct badge.
        self._last_period = period
        if not self._trv_groups:
            return
        await asyncio.gather(
            *(group.push(temp, period, ctx) for group in self._trv_groups)
        )

    async def apply_off(self, frost_temp: float, ctx: "EvalContext") -> None:
        """Push MODE_OFF to all TRV groups: off for off-capable, frost for others."""
        self._last_period = PERIOD_FROST_PROTECTION
        if not self._trv_groups:
            return
        await asyncio.gather(
            *(group.push_off(frost_temp, ctx) for group in self._trv_groups)
        )

    # -------------------------------------------------------------------
    # Preheat pass (migrated from coordinator._async_preheat_room)
    # -------------------------------------------------------------------

    def _clear_preheat(self) -> None:
        """Stop any pre-heat; the next zone push restores the schedule."""
        self._preheat_active = False
        self._preheat_target = None
        self._preheat_in_progress = {}

    def carry_preheat_state(self, old: "Room") -> None:
        """Copy pre-heat state from the Room it replaces on a rebuild."""
        self._preheat_active = old._preheat_active
        self._preheat_target = old._preheat_target
        self._preheat_suppressed = old._preheat_suppressed
        self._preheat_in_progress = old._preheat_in_progress

    def _room_temperature(self, config: dict) -> float | None:
        """Current room temperature: room sensor first, else the first TRV.

        The room sensor is the same reference calibration aims for; a TRV
        reads the radiator's surroundings and reaches the target early.
        """
        candidates: list[tuple[str, str | None]] = []
        sensor_id = self._resolve_room_sensor(config)
        if sensor_id:
            candidates.append((sensor_id, None))
        trv_id = next(
            (
                trv.entity_id
                for group in self._trv_groups
                for trv in getattr(group, "_trvs", [])
                if is_trv_entity(self._hass, trv.entity_id)
            ),
            None,
        )
        if trv_id:
            candidates.append((trv_id, "current_temperature"))
        for entity_id, attribute in candidates:
            state = self._hass.states.get(entity_id)
            if state is None or state.state in ("unavailable", "unknown"):
                continue
            raw = (
                state.state
                if attribute is None
                else state.attributes.get(attribute)
            )
            try:
                return float(raw)
            except (ValueError, TypeError):
                continue
        return None

    async def compute_preheat(self, ctx: "EvalContext") -> None:
        """Pre-heat logic for this room (runs after the zone pushes).

        Lifecycle:
        1. TRIGGER: inside the learned lead window before the next occupied
           time (scheduled person arrival, else the next zone setpoint
           increase), push the upcoming setpoint and record the run in
           _preheat_in_progress (until = that occupied time).
        2. HOLD: until then, apply_setpoint keeps the upcoming setpoint on
           every tick, so the zone schedule never undoes the pre-heat.
        3. CONVERGENCE: the room reaching the target records one lead-time
           sample (PREHEAT-03); the setpoint is still held until `until`.
        4. END: at the occupied time the zone setpoint takes over. A run
           that never reached its target is discarded without a sample
           (T-16-09). A run whose reason vanished (preheat disabled, zone
           off, presence suppressed, occupied time no longer imminent) is
           cancelled.
        """
        if self._hass is None or ctx is None:
            return

        zone_mode: str = (
            getattr(self._zone, "mode", MODE_TIME_PROGRAM)
            if self._zone is not None
            else MODE_TIME_PROGRAM
        )
        preheat_enabled = (
            getattr(self._zone, "preheat_enabled", False)
            if self._zone is not None
            else False
        )

        if not preheat_enabled or zone_mode == MODE_OFF:
            self._clear_preheat()
            self._preheat_suppressed = False
            return

        # Room config for max lead; read from coordinator data via hass
        # (fallback to default when not available).
        config = getattr(
            getattr(self._hass, "_climate_manager_data", None),
            "runtime_config",
            {},
        )
        room_config = (config.get("rooms") or {}).get(self.area_id, {})
        preheat_max_lead = room_config.get(
            "preheat_max_lead_minutes", DEFAULT_PREHEAT_MAX_LEAD_MINUTES
        )

        now = ctx.now
        current_temp = self._room_temperature(config)

        # ----------------------------------------------------------------
        # Next occupied time: earliest scheduled arrival, else the next
        # zone setpoint increase.
        # ----------------------------------------------------------------
        persons_config: dict = config.get("persons", {})
        assigned = [
            pc
            for pc in persons_config.values()
            if self.area_id in pc.get("room_ids", [])
        ]
        unpredictable = {PRESENCE_HA, PRESENCE_PRESENT, PRESENCE_ABSENT}

        calendar_cache = getattr(ctx, "_calendar_cache", {})
        start_of_local_day = __import__(
            "homeassistant.util.dt",
            fromlist=["start_of_local_day"],
        ).start_of_local_day

        next_arrival: datetime | None = None
        for pc in assigned:
            if pc.get("mode") in unpredictable:
                continue
            if resolve_presence(pc, now, calendar_cache, start_of_local_day):
                continue
            candidate = next_occupied_at(
                pc, now, calendar_cache, start_of_local_day
            )
            if candidate is not None:
                if next_arrival is None or candidate < next_arrival:
                    next_arrival = candidate

        time_program: dict = (
            getattr(self._zone, "time_program", {})
            if self._zone is not None
            else {}
        )
        period_temperatures: dict[str, float] = config.get(
            "period_temperatures", {}
        )

        if next_arrival is not None:
            next_occupied: datetime | None = next_arrival
        else:
            next_occupied = next_setpoint_increase_at(
                time_program, period_temperatures, now
            )

        presence_suppressed = (
            zone_mode == MODE_TIME_PROGRAM_PRESENCES
            and bool(assigned)
            and all(pc.get("mode") in unpredictable for pc in assigned)
        )
        self._preheat_suppressed = next_occupied is None or presence_suppressed

        # ----------------------------------------------------------------
        # Running pre-heat: END / CONVERGENCE / HOLD
        # ----------------------------------------------------------------
        ip = self._preheat_in_progress
        if ip:
            # CONVERGENCE first: reaching the target is a valid lead-time
            # sample even on the tick the run ends.
            if (
                not ip["converged"]
                and current_temp is not None
                and current_temp
                >= ip["target_temp"] - PREHEAT_CONVERGENCE_THRESHOLD
            ):
                ip["converged"] = True
                await self._record_preheat_sample(ip["start_time"], now)
            max_lead = timedelta(minutes=preheat_max_lead)
            if (
                now >= ip["until"]
                or next_occupied is None
                or presence_suppressed
                or self._frost_locked
                or next_occupied - now > max_lead
            ):
                # Occupied time reached (zone setpoint takes over) or the
                # pre-heat lost its reason. Unconverged runs are discarded
                # without a sample (T-16-09 / PREHEAT-03).
                self._clear_preheat()
            else:
                # Follow a moved occupied time (e.g. edited schedule).
                ip["until"] = next_occupied
                self._preheat_active = True
                self._preheat_target = ip["target_temp"]
                return

        # ----------------------------------------------------------------
        # TRIGGER (D-08, T-12-03)
        # ----------------------------------------------------------------
        if next_occupied is None or presence_suppressed or self._frost_locked:
            self._preheat_active = False
            return

        # Compute learned lead.
        data = getattr(self._hass, "_climate_manager_data", None)
        samples = (
            data.preheat_samples.get(self.area_id, [])
            if data is not None
            else []
        )
        if len(samples) >= PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD:
            avg = statistics.mean(s["duration_minutes"] for s in samples)
            learned_lead = min(avg, preheat_max_lead)
        else:
            learned_lead = preheat_max_lead

        trigger_start = next_occupied - timedelta(minutes=learned_lead)

        if not (trigger_start <= now < next_occupied):
            self._preheat_active = False
            return

        # Determine the upcoming setpoint.
        upcoming_period = evaluate_schedule(time_program, next_occupied)
        upcoming_setpoint = period_temperatures.get(upcoming_period)
        if upcoming_setpoint is None:
            self._preheat_active = False
            return

        # Guard: in TIME_PROGRAM mode, skip if current period already warm.
        if zone_mode == MODE_TIME_PROGRAM:
            current_period = evaluate_schedule(time_program, now)
            current_period_temp = period_temperatures.get(current_period)
            if (
                current_period_temp is not None
                and current_period_temp >= upcoming_setpoint
            ):
                self._preheat_active = False
                return

        # Guard: room already warm.
        if (
            current_temp is not None
            and current_temp
            >= upcoming_setpoint - PREHEAT_CONVERGENCE_THRESHOLD
        ):
            self._preheat_active = False
            return

        # Start the run, then push now (the zone already pushed its
        # scheduled setpoint this tick); later ticks hold it via
        # apply_setpoint.
        self._preheat_in_progress = {
            "start_time": now,
            "target_temp": upcoming_setpoint,
            "until": next_occupied,
            "converged": False,
        }
        self._preheat_active = True
        self._preheat_target = upcoming_setpoint
        _LOGGER.info(
            "preheat | room=%s target=%s°C until=%s lead=%smin",
            self.area_id,
            upcoming_setpoint,
            next_occupied.strftime("%H:%M"),
            round(learned_lead),
        )
        await self.apply_setpoint(PERIOD_PREHEAT, upcoming_setpoint, ctx)

    async def _record_preheat_sample(
        self, start_time: datetime, now: datetime
    ) -> None:
        """Store one lead-time sample (minutes to reach the target)."""
        duration_min = int((now - start_time).total_seconds() / 60)
        # WR-03: skip zero-duration samples (same-tick convergence).
        if duration_min < 1:
            return
        _LOGGER.info(
            "preheat | room=%s target reached after %smin",
            self.area_id,
            duration_min,
        )
        data = getattr(self._hass, "_climate_manager_data", None)
        if data is None:
            return
        samples = data.preheat_samples.setdefault(self.area_id, [])
        samples.append(
            {
                "duration_minutes": duration_min,
                "timestamp": now.isoformat(),
            }
        )
        # Keep only last PREHEAT_MAX_SAMPLES (D-06)
        if len(samples) > PREHEAT_MAX_SAMPLES:
            data.preheat_samples[self.area_id] = samples[-PREHEAT_MAX_SAMPLES:]
        # Persist on sample change (T-12-05 — bounded write rate).
        preheat_store = getattr(data, "preheat_store", None)
        if preheat_store is not None:
            await preheat_store.async_save(data.preheat_samples)

    # -------------------------------------------------------------------
    # Calibration pass (migrated from coordinator._async_calibrate_room)
    # -------------------------------------------------------------------

    async def calibrate_trvs(self, ctx: "EvalContext") -> None:
        """Calibrate all TRVs in this room toward the room's reference sensor.

        Reproduces coordinator._async_calibrate_room for all TRVs in this
        room.  Writes go through TRV.calibrate(offset, ctx) (plan 16-03).
        Calibration tracking fields updated in-place on Room.

        Silently returns when any guard condition fails (CALIB-03/05).
        """
        if self._hass is None or ctx is None:
            return

        config = getattr(
            getattr(self._hass, "_climate_manager_data", None),
            "runtime_config",
            {},
        )
        if not config.get("calibration_enabled", False):
            return

        sensor_entity_id = self._resolve_room_sensor(config)

        for group in self._trv_groups:
            for trv in getattr(group, "_trvs", []):
                await self._calibrate_one_trv(
                    trv.entity_id, sensor_entity_id, config, ctx
                )

    async def _calibrate_one_trv(
        self,
        entity_id: str,
        sensor_entity_id: str | None,
        config: dict,
        ctx: "EvalContext",
    ) -> None:
        """Calibrate a single TRV toward its room sensor.

        Mirrors coordinator._async_calibrate_room (lines 995-1068).
        """
        if not sensor_entity_id:
            return

        if not supports_offset_calibration(self._hass, entity_id):
            return

        state = self._hass.states.get(entity_id)
        if state is None or state.state == "unavailable":
            return

        sensor_state = self._hass.states.get(sensor_entity_id)
        if sensor_state is None or sensor_state.state in (
            "unavailable",
            "unknown",
        ):
            return
        try:
            sensor_temp = float(sensor_state.state)
        except (ValueError, TypeError):
            return

        current_temp = state.attributes.get("current_temperature")
        if current_temp is None:
            return
        try:
            current_temp = float(current_temp)
        except (ValueError, TypeError):
            return

        delta = sensor_temp - current_temp
        threshold = config.get("calibration_threshold", 0.5)
        if abs(delta) <= threshold:
            return

        try:
            existing_offset = float(
                state.attributes.get("temperature_offset", 0.0)
            )
        except (ValueError, TypeError):
            existing_offset = 0.0
        new_offset = max(
            -_OFFSET_CLAMP,
            min(_OFFSET_CLAMP, existing_offset + delta),
        )

        try:
            async with asyncio.timeout(TRV_COMMAND_TIMEOUT):
                await set_trv_offset(self._hass, entity_id, new_offset)
            self._calibration_last_changed = datetime.now(
                timezone.utc
            ).isoformat(timespec="seconds")
            self._calibration_last_delta = round(delta, 2)
        except Exception:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to apply offset %.1f to %s", new_offset, entity_id
            )

    def _resolve_room_sensor(self, config: dict) -> str | None:
        """Return the temperature sensor entity_id for this room.

        Resolution order:
          1. area_reg.temperature_entity_id (HA 2026.5+ area registry)
          2. room_auto_sensors (discovered from device registry)
          3. rooms_config explicit override (test + manual config)
        """
        from homeassistant.helpers import area_registry as ar  # noqa: PLC0415

        area_reg = ar.async_get(self._hass)
        _area = area_reg.async_get_area(self.area_id)
        data = getattr(self._hass, "_climate_manager_data", None)
        return (
            getattr(_area, "temperature_entity_id", None)
            or (
                data.room_auto_sensors.get(self.area_id, {}).get("temperature")
                if data is not None
                else None
            )
            or config.get("rooms", {})
            .get(self.area_id, {})
            .get("temperature_sensor")
        )
