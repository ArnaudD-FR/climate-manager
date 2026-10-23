# SPDX-License-Identifier: MIT
"""Pre-heat inertia model and persistence.

Each room learns a heating rate (minutes per °C) from its own pre-heat
runs. The lead of a given day is that rate times the gap left to close,
plus a margin, so a colder room starts earlier.

Persisted in the `climate_manager_preheat` Store (version 2):

    {"rooms": {area_id: {"samples": [sample, ...], "run": run | None,
                         "boost_factor": float, "observe": observe | None}}}

    sample  = {timestamp, duration_minutes, start_temp, target_temp, rate,
               censored, [outdoor_temp, flow_temp, curve_slope,
               curve_shift, program]}
    run     = {start_time, start_temp, target_temp, until, converged,
               measuring, boosted, outdoor_temp, curve_slope, curve_shift,
               program, flow_sum, flow_n}  # datetimes as ISO with offset
    observe = {target_temp, until, peak, late}   # overshoot watch

boost_factor is the learned (auto) boost factor; absent until the first
boosted run is judged. observe watches the room after a boosted run reached
its target, to measure the overshoot that tunes it.

The boiler's conditions (vendors.boiler_readings) are recorded with each
run and copied into its sample, for later analysis: the outdoor
temperature, heating curve and program at the start, the mean flow
temperature over the run (it saw-tooths while the burner cycles). Unknown
values are left out.

A censored sample comes from a run that never reached its target: the
elapsed time is a lower bound of the real duration, so its rate pulls the
learned lead up instead of being dropped (which biased learning short).
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .vendors import BoilerReadings
from .const import (
    DEFAULT_PREHEAT_BOOST_FACTOR,
    PREHEAT_BOOST_FACTOR_MAX,
    PREHEAT_BOOST_FACTOR_MIN,
    PREHEAT_BOOST_FACTOR_STEP,
    PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD,
    PREHEAT_LEAD_MARGIN,
    PREHEAT_MAX_SAMPLES,
    PREHEAT_MIN_LEAD_MINUTES,
    PREHEAT_MIN_SAMPLE_DELTA,
    PREHEAT_OVERSHOOT_HIGH,
    PREHEAT_OVERSHOOT_LOW,
)

PREHEAT_STORE_KEY = "climate_manager_preheat"
PREHEAT_STORE_VERSION = 2

_RUN_DATETIMES = ("start_time", "until")


class PreheatStore(Store):
    """Pre-heat Store with the v1 → v2 migration."""

    def __init__(self, hass) -> None:
        super().__init__(
            hass, version=PREHEAT_STORE_VERSION, key=PREHEAT_STORE_KEY
        )

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data
    ):
        """Migrate older layouts.

        v1 was {area_id: [{duration_minutes, timestamp}]}: without the start
        temperature a sample cannot yield a heating rate, so learning starts
        over (each room falls back to its max lead for 3 runs).
        """
        if old_major_version < 2:
            return empty_preheat_data()
        return old_data


def empty_preheat_data() -> dict:
    """Return an empty v2 pre-heat data structure."""
    return {"rooms": {}}


def room_entry(data: dict, area_id: str) -> dict:
    """Return (creating it) the persisted entry of one room."""
    rooms = data.setdefault("rooms", {})
    entry = rooms.setdefault(area_id, {})
    entry.setdefault("samples", [])
    entry.setdefault("run", None)
    return entry


def learned_rate(samples: list[dict]) -> float | None:
    """Median heating rate (min/°C) of the last samples, or None.

    None until PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD samples exist. The
    median ignores one odd day (window left open, sun on the sensor).
    """
    rates = [
        s["rate"]
        for s in samples[-PREHEAT_MAX_SAMPLES:]
        if isinstance(s.get("rate"), (int, float))
    ]
    if len(rates) < PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD:
        return None
    return statistics.median(rates)


def learned_boost_factor(entry: dict) -> float:
    """Auto boost factor of a room (default until tuned)."""
    factor = entry.get("boost_factor")
    if isinstance(factor, (int, float)) and not isinstance(factor, bool):
        return float(factor)
    return DEFAULT_PREHEAT_BOOST_FACTOR


def tune_boost_factor(
    factor: float, overshoot: float | None, late: bool
) -> float:
    """Next auto boost factor after one boosted run.

    overshoot: peak above the target once reached (None: never reached).
    late: the target was reached after the occupied time, or never.
    Too much overshoot lowers the factor; a late run without overshoot
    raises it; otherwise it stays. One step at a time, so the learned rate
    (measured with the boost) can follow.
    """
    if overshoot is not None and overshoot > PREHEAT_OVERSHOOT_HIGH:
        factor -= PREHEAT_BOOST_FACTOR_STEP
    elif late and (overshoot is None or overshoot < PREHEAT_OVERSHOOT_LOW):
        factor += PREHEAT_BOOST_FACTOR_STEP
    return min(max(factor, PREHEAT_BOOST_FACTOR_MIN), PREHEAT_BOOST_FACTOR_MAX)


def compute_lead(
    rate: float | None, delta: float | None, max_lead: float
) -> float:
    """Lead (minutes) to close `delta` °C at `rate` min/°C, with margin.

    Falls back to max_lead while learning (rate None) or when the room
    temperature is unknown (delta None). Bounded to
    [PREHEAT_MIN_LEAD_MINUTES, max_lead].
    """
    if rate is None or delta is None:
        return float(max_lead)
    lead = rate * max(delta, 0.0) * (1 + PREHEAT_LEAD_MARGIN)
    return float(min(max(lead, PREHEAT_MIN_LEAD_MINUTES), max_lead))


# Run fields copied as is into the sample (flow_temp is averaged).
_CONDITIONS = ("outdoor_temp", "curve_slope", "curve_shift", "program")


def start_conditions(readings: BoilerReadings) -> dict:
    """Run fields recording the boiler's conditions at the start."""
    return {
        "outdoor_temp": readings.outdoor_temp,
        "curve_slope": readings.curve_slope,
        "curve_shift": readings.curve_shift,
        "program": readings.program,
        "flow_sum": 0.0,
        "flow_n": 0,
    }


def record_flow(run: dict, flow_temp: float | None) -> None:
    """Add one flow temperature reading to the run's mean."""
    if flow_temp is None:
        return
    run["flow_sum"] = run.get("flow_sum", 0.0) + flow_temp
    run["flow_n"] = run.get("flow_n", 0) + 1


def run_conditions(run: dict) -> dict:
    """The run's known boiler conditions, as sample fields."""
    out = {key: run[key] for key in _CONDITIONS if run.get(key) is not None}
    if run.get("flow_n"):
        out["flow_temp"] = round(run["flow_sum"] / run["flow_n"], 1)
    return out


def make_sample(
    start_time: datetime,
    now: datetime,
    start_temp: float | None,
    target_temp: float,
    *,
    censored: bool,
    conditions: dict | None = None,
) -> dict | None:
    """Build one sample, or None when it would only be noise.

    No sample when the start temperature is unknown, the gap to close was
    under PREHEAT_MIN_SAMPLE_DELTA, or under a minute elapsed.
    """
    if start_temp is None:
        return None
    delta = target_temp - start_temp
    if delta < PREHEAT_MIN_SAMPLE_DELTA:
        return None
    duration = int((now - start_time).total_seconds() / 60)
    if duration < 1:
        return None
    return {
        "timestamp": now.isoformat(),
        "duration_minutes": duration,
        "start_temp": round(start_temp, 2),
        "target_temp": target_temp,
        "rate": round(duration / delta, 2),
        "censored": censored,
        **(conditions or {}),
    }


def add_sample(entry: dict, sample: dict) -> None:
    """Append a sample, keeping the last PREHEAT_MAX_SAMPLES."""
    samples = entry["samples"]
    samples.append(sample)
    del samples[:-PREHEAT_MAX_SAMPLES]


def run_to_json(run: dict) -> dict | None:
    """Serialise a running pre-heat (datetimes → ISO strings)."""
    if not run:
        return None
    out = dict(run)
    for key in _RUN_DATETIMES:
        out[key] = run[key].isoformat()
    return out


def run_from_json(raw) -> dict:
    """Restore a running pre-heat; {} when absent or malformed."""
    if not isinstance(raw, dict):
        return {}
    run = dict(raw)
    try:
        for key in _RUN_DATETIMES:
            parsed = dt_util.parse_datetime(run[key])
            if parsed is None:
                return {}
            run[key] = parsed
        run["target_temp"] = float(run["target_temp"])
    except (KeyError, TypeError, ValueError):
        return {}
    run.setdefault("start_temp", None)
    run.setdefault("converged", False)
    run.setdefault("measuring", False)
    run.setdefault("boosted", False)
    return run


def measure_cap(max_lead: float) -> timedelta:
    """Longest a run is measured before it ends as a censored sample."""
    return timedelta(minutes=2 * max_lead)
