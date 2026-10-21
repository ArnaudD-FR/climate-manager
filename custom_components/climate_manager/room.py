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
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from .const import (
    DEFAULT_PREHEAT_BOOST_FACTOR,
    DEFAULT_PREHEAT_MAX_LEAD_MINUTES,
    DEFAULT_TRV_MAX_TEMP,
    MODE_OFF,
    MODE_TIME_PROGRAM,
    MODE_TIME_PROGRAM_PRESENCES,
    PERIOD_FROST_PROTECTION,
    PERIOD_PREHEAT,
    PREHEAT_BOOST_MAX,
    PREHEAT_CALIBRATION_THRESHOLD,
    PREHEAT_CONVERGENCE_THRESHOLD,
    PRESENCE_ABSENT,
    PRESENCE_HA,
    PRESENCE_PRESENT,
    TRV_COMMAND_TIMEOUT,
)
from .preheat import (
    add_sample,
    compute_lead,
    learned_rate,
    make_sample,
    measure_cap,
    room_entry,
    run_from_json,
    run_to_json,
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
        # Running pre-heat, or empty dict (layout in preheat.py "run"):
        # {start_time, start_temp, target_temp, until, converged, measuring}.
        # Before `until` (and not measuring) apply_setpoint holds
        # target_temp when warmer than the scheduled setpoint. Persisted in
        # the pre-heat Store so it survives a restart.
        self._preheat_in_progress: dict = {}
        # Lead (minutes) computed at the last pre-heat pass, for status.
        self._preheat_lead: float | None = None
        # °C added to the setpoint pushed to the TRVs (None when no boost).
        self._preheat_boost_applied: float | None = None
        # Last setpoint actually applied (zone or pre-heat). A measuring run
        # ends when the zone setpoint drops below its target.
        self._last_setpoint: float | None = None

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
        Until the room reaches the target, the TRVs get a boosted setpoint
        (see _preheat_boost); _last_setpoint keeps the unboosted one.
        """
        ip = self._preheat_in_progress
        if (
            ip
            and not ip["measuring"]
            and ctx.now < ip["until"]
            and ip["target_temp"] > temp
        ):
            period, temp = PERIOD_PREHEAT, ip["target_temp"]
        # Record the effective period for status display before any early
        # return so even TRV-less rooms surface the correct badge.
        self._last_period = period
        self._last_setpoint = temp
        boost = self._preheat_boost(temp)
        self._preheat_boost_applied = boost or None
        if not self._trv_groups:
            return
        await asyncio.gather(
            *(
                group.push(temp + boost, period, ctx)
                for group in self._trv_groups
            )
        )

    @property
    def preheat_boosting(self) -> bool:
        """True while a pre-heat runs and the room has not reached it."""
        ip = self._preheat_in_progress
        return bool(ip) and not ip["converged"]

    def _preheat_boost(self, base: float) -> float:
        """°C added to base for the TRVs while a pre-heat runs.

        A TRV next to the radiator reads high while heating and throttles
        before the room is warm: push factor × (base − room temperature),
        capped at PREHEAT_BOOST_MAX and at the TRVs' max_temp, rounded to
        0.5 °C so TRVs with coarse steps report back what was pushed.
        Zero once the room reached the target, when base is below the
        pre-heat target, or without a room temperature.
        """
        if self._hass is None or not self.preheat_boosting:
            return 0.0
        if (
            base
            < self._preheat_in_progress["target_temp"]
            - PREHEAT_CONVERGENCE_THRESHOLD
        ):
            return 0.0
        config = getattr(
            getattr(self._hass, "_climate_manager_data", None),
            "runtime_config",
            {},
        )
        factor = (
            (config.get("rooms") or {})
            .get(self.area_id, {})
            .get("preheat_boost_factor", DEFAULT_PREHEAT_BOOST_FACTOR)
        )
        room_temp = self._room_temperature(config)
        if not factor or room_temp is None or room_temp >= base:
            return 0.0
        boost = min(factor * (base - room_temp), PREHEAT_BOOST_MAX)
        boost = min(boost, self._trv_max_temp() - base)
        return max(0.0, round((base + boost) * 2) / 2 - base)

    def _trv_max_temp(self) -> float:
        """Lowest max_temp among this room's TRVs (default 30 °C)."""
        max_temps: list[float] = []
        for group in self._trv_groups:
            for trv in getattr(group, "_trvs", []):
                state = self._hass.states.get(trv.entity_id)
                raw = state.attributes.get("max_temp") if state else None
                try:
                    max_temps.append(float(raw))
                except (ValueError, TypeError):
                    continue
        return min(max_temps, default=DEFAULT_TRV_MAX_TEMP)

    async def apply_off(self, frost_temp: float, ctx: "EvalContext") -> None:
        """Push MODE_OFF to all TRV groups: off for off-capable, frost for others."""
        self._last_period = PERIOD_FROST_PROTECTION
        self._last_setpoint = frost_temp
        if not self._trv_groups:
            return
        await asyncio.gather(
            *(group.push_off(frost_temp, ctx) for group in self._trv_groups)
        )

    # -------------------------------------------------------------------
    # Preheat pass (migrated from coordinator._async_preheat_room)
    # -------------------------------------------------------------------

    def _preheat_store_entry(self) -> dict | None:
        """This room's persisted pre-heat entry (samples + run), or None."""
        data = getattr(self._hass, "_climate_manager_data", None)
        preheat_data = getattr(data, "preheat_data", None)
        if not isinstance(preheat_data, dict):
            return None
        return room_entry(preheat_data, self.area_id)

    async def _save_preheat(self, sample: dict | None = None) -> None:
        """Persist the running pre-heat (and a new sample, if any)."""
        entry = self._preheat_store_entry()
        if entry is None:
            return
        if sample is not None:
            add_sample(entry, sample)
        entry["run"] = run_to_json(self._preheat_in_progress)
        data = getattr(self._hass, "_climate_manager_data", None)
        store = getattr(data, "preheat_store", None)
        if store is not None:
            await store.async_save(data.preheat_data)

    def restore_preheat_run(self) -> None:
        """Resume a pre-heat persisted before a restart."""
        entry = self._preheat_store_entry()
        if entry is None:
            return
        self._preheat_in_progress = run_from_json(entry.get("run"))
        ip = self._preheat_in_progress
        if ip and not ip["measuring"]:
            self._preheat_active = True
            self._preheat_target = ip["target_temp"]

    def learned_rate(self) -> float | None:
        """Learned heating rate (min/°C), or None while learning."""
        entry = self._preheat_store_entry()
        return learned_rate(entry["samples"]) if entry is not None else None

    def preheat_sample_count(self) -> int:
        """Number of stored pre-heat samples for this room."""
        entry = self._preheat_store_entry()
        return len(entry["samples"]) if entry is not None else 0

    async def _end_preheat(self, sample: dict | None = None) -> None:
        """End the running pre-heat, persisting the outcome."""
        had_run = bool(self._preheat_in_progress)
        self._clear_preheat()
        if had_run or sample is not None:
            await self._save_preheat(sample)

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
        self._preheat_lead = old._preheat_lead
        self._preheat_boost_applied = old._preheat_boost_applied
        self._last_period = old._last_period
        self._last_setpoint = old._last_setpoint

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

        Lifecycle of a run (_preheat_in_progress, persisted):
        1. TRIGGER: inside the lead window before the next occupied time
           (scheduled person arrival, else the next zone setpoint
           increase). Lead = learned rate (min/°C) × gap to the upcoming
           setpoint × (1 + margin), bounded [min lead, max lead]; max lead
           while learning. Pushes the upcoming setpoint at once.
        2. HOLD: until the occupied time, apply_setpoint keeps the upcoming
           setpoint, so the zone schedule never undoes the pre-heat.
        3. CONVERGENCE (room sensor within threshold of the target): one
           rate sample; the setpoint is still held until the occupied time.
        4. MEASURING: not converged at the occupied time — the zone
           setpoint takes over and the run keeps timing until the target is
           reached (real duration, may exceed the lead → the lead grows).
           Ends censored (elapsed time as a lower bound) when the zone
           setpoint drops below the target or after 2 × max lead.
        5. CANCEL: pre-heat disabled, zone off, presence suppressed, or the
           occupied time no longer within max lead — no sample.
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
            await self._end_preheat()
            self._preheat_suppressed = False
            self._preheat_lead = None
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
        # Running pre-heat: convergence, measuring, hold, cancel
        # ----------------------------------------------------------------
        ip = self._preheat_in_progress
        if ip:
            reached = (
                current_temp is not None
                and current_temp
                >= ip["target_temp"] - PREHEAT_CONVERGENCE_THRESHOLD
            )
            if reached and not ip["converged"]:
                ip["converged"] = True
                sample = make_sample(
                    ip["start_time"],
                    now,
                    ip["start_temp"],
                    ip["target_temp"],
                    censored=False,
                )
                self._log_sample(sample, "reached")
                if ip["measuring"]:
                    await self._end_preheat(sample)
                    await self._drop_boost(ctx)
                    return
                await self._save_preheat(sample)
                await self._drop_boost(ctx)

            if ip["measuring"]:
                setpoint_dropped = (
                    self._last_setpoint is not None
                    and self._last_setpoint
                    < ip["target_temp"] - PREHEAT_CONVERGENCE_THRESHOLD
                )
                if setpoint_dropped or (
                    now - ip["start_time"] > measure_cap(preheat_max_lead)
                ):
                    sample = make_sample(
                        ip["start_time"],
                        now,
                        ip["start_temp"],
                        ip["target_temp"],
                        censored=True,
                    )
                    self._log_sample(sample, "not reached, censored")
                    await self._end_preheat(sample)
                return

            if now >= ip["until"]:
                if ip["converged"]:
                    await self._end_preheat()
                else:
                    # Occupied time reached first: keep timing (no hold).
                    ip["measuring"] = True
                    self._preheat_active = False
                    self._preheat_target = None
                    await self._save_preheat()
                    return
                # fall through: maybe a later occupancy is already due

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

        ip = self._preheat_in_progress
        if ip:
            if (
                next_occupied is None
                or presence_suppressed
                or self._frost_locked
                or next_occupied - now > timedelta(minutes=preheat_max_lead)
            ):
                # The pre-heat lost its reason: cancel, no sample.
                await self._end_preheat()
            else:
                # HOLD — follow a moved occupied time (edited schedule).
                if ip["until"] != next_occupied:
                    ip["until"] = next_occupied
                    await self._save_preheat()
                self._preheat_active = True
                self._preheat_target = ip["target_temp"]
                return

        # ----------------------------------------------------------------
        # TRIGGER (D-08, T-12-03)
        # ----------------------------------------------------------------
        if next_occupied is None or presence_suppressed or self._frost_locked:
            self._preheat_active = False
            self._preheat_lead = None
            return

        # Determine the upcoming setpoint.
        upcoming_period = evaluate_schedule(time_program, next_occupied)
        upcoming_setpoint = period_temperatures.get(upcoming_period)
        if upcoming_setpoint is None:
            self._preheat_active = False
            self._preheat_lead = None
            return

        rate = self.learned_rate()
        delta = (
            upcoming_setpoint - current_temp
            if current_temp is not None
            else None
        )
        lead = compute_lead(rate, delta, preheat_max_lead)
        self._preheat_lead = lead

        trigger_start = next_occupied - timedelta(minutes=lead)
        if not (trigger_start <= now < next_occupied):
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
            "start_temp": current_temp,
            "target_temp": upcoming_setpoint,
            "until": next_occupied,
            "converged": False,
            "measuring": False,
        }
        self._preheat_active = True
        self._preheat_target = upcoming_setpoint
        _LOGGER.info(
            "preheat | room=%s target=%s°C until=%s lead=%smin rate=%s"
            " boost=%s",
            self.area_id,
            upcoming_setpoint,
            next_occupied.strftime("%H:%M"),
            round(lead),
            f"{rate}min/°C" if rate is not None else "learning",
            room_config.get(
                "preheat_boost_factor", DEFAULT_PREHEAT_BOOST_FACTOR
            ),
        )
        await self._save_preheat()
        await self.apply_setpoint(PERIOD_PREHEAT, upcoming_setpoint, ctx)

    async def _drop_boost(self, ctx: "EvalContext") -> None:
        """Re-push the unboosted setpoint now that the room is warm."""
        if self._preheat_boost_applied and self._last_setpoint is not None:
            await self.apply_setpoint(
                self._last_period or PERIOD_PREHEAT, self._last_setpoint, ctx
            )

    def _log_sample(self, sample: dict | None, outcome: str) -> None:
        """INFO log for a finished measurement (sample may be None)."""
        if sample is None:
            _LOGGER.info(
                "preheat | room=%s %s (gap too small, no sample)",
                self.area_id,
                outcome,
            )
            return
        _LOGGER.info(
            "preheat | room=%s %s after %smin (%s min/°C)",
            self.area_id,
            outcome,
            sample["duration_minutes"],
            sample["rate"],
        )

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
        threshold = calibration_threshold(config, self.preheat_boosting)
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
            log_calibration(
                self.area_id,
                entity_id.split(".", 1)[-1],
                sensor_temp,
                current_temp,
                existing_offset,
                new_offset,
                threshold,
            )
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
