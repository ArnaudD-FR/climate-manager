# SPDX-License-Identifier: MIT
"""Pre-heat inertia model and persistence.

Each room learns a heating rate (minutes per °C) from its own pre-heat
runs. The lead of a given day is that rate times the gap left to close,
plus a margin, so a colder room starts earlier.

Persisted in the `climate_manager_preheat` Store (version 2):

    {"rooms": {area_id: {"samples": [sample, ...], "run": run | None}}}

    sample = {timestamp, duration_minutes, start_temp, target_temp, rate,
              censored}
    run    = {start_time, start_temp, target_temp, until, converged,
              measuring}   # datetimes as ISO strings with offset

A censored sample comes from a run that never reached its target: the
elapsed time is a lower bound of the real duration, so its rate pulls the
learned lead up instead of being dropped (which biased learning short).
"""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    PREHEAT_DEFAULT_SAMPLE_COUNT_THRESHOLD,
    PREHEAT_LEAD_MARGIN,
    PREHEAT_MAX_SAMPLES,
    PREHEAT_MIN_LEAD_MINUTES,
    PREHEAT_MIN_SAMPLE_DELTA,
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


def make_sample(
    start_time: datetime,
    now: datetime,
    start_temp: float | None,
    target_temp: float,
    *,
    censored: bool,
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
    return run


def measure_cap(max_lead: float) -> timedelta:
    """Longest a run is measured before it ends as a censored sample."""
    return timedelta(minutes=2 * max_lead)
