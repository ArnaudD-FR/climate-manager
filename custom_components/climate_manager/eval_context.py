# SPDX-License-Identifier: MIT
"""Climate Manager evaluation context — per-cycle shared cache.

EvalContext is created once at the start of every async_evaluate call and
passed down to all domain objects (Zone, Person, Room, TRV). It provides:

- A lazy, deduplicated calendar event cache: calendar_events(entity_id)
  fetches via hass.services.async_call at most once per entity per cycle.
  Subsequent calls for the same entity return the cached list.
- A presence cache: _presence_cache[person_id] stores the result of
  Person.evaluate() so a person shared across multiple zones is evaluated
  exactly once per cycle (D-02).
- Warning-once semantics for calendar fetch failures: per-entity WARNING
  fires once; repeated failures within a cycle are suppressed (T-16-04).

Security — T-16-03: entity_id must start with "calendar." before being
used as a hass.services.async_call target (ASVS V5 input validation,
inherited from coordinator._prefetch_calendars).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class EvalContext:
    """Per-evaluation-cycle shared cache.

    Required positional fields (must be provided at construction):
        now:                 The evaluation timestamp (dt_util.now() result).
        hass:                The HomeAssistant core object.
        period_temperatures: Mapping from period name to target temperature.

    Internal cache fields (populated lazily during the cycle):
        _calendar_cache:  entity_id → list of event dicts (filled on demand).
        _presence_cache:  person_id → is_home bool (filled by Person.evaluate).
        _warn_issued:     Set of entity_ids for which a WARNING was already
                          emitted this cycle (suppresses repeated log spam).
    """

    now: datetime
    hass: "HomeAssistant"
    period_temperatures: dict[str, float]
    _calendar_cache: dict[str, list] = field(default_factory=dict)
    _presence_cache: dict[str, bool] = field(default_factory=dict)
    _warn_issued: set[str] = field(default_factory=set)

    async def calendar_events(self, entity_id: str) -> list:
        """Return calendar events for entity_id, fetching at most once.

        D-02: If entity_id is already in _calendar_cache, return the cached
        list immediately without issuing a second service call.

        T-16-03: entity_id must start with "calendar." — any other value is
        rejected immediately with an empty list and a WARNING (ASVS V5).

        T-16-04: On HomeAssistantError, returns [] and logs a WARNING once per
        entity per cycle (suppressed on further failures via _warn_issued set).

        Args:
            entity_id: The calendar entity to fetch events for.

        Returns:
            List of event dicts for today's 24-hour window, or [] on error.
        """
        # D-02: return cached result if already fetched this cycle
        if entity_id in self._calendar_cache:
            return self._calendar_cache[entity_id]

        # T-16-03 / ASVS V5: validate entity_id domain before service call
        if not entity_id.startswith("calendar."):
            if entity_id not in self._warn_issued:
                _LOGGER.warning(
                    "calendar_events: entity_id %r does not start with"
                    " 'calendar.' — skipping fetch",
                    entity_id,
                )
                self._warn_issued.add(entity_id)
            self._calendar_cache[entity_id] = []
            return []

        # Compute the 24-hour window starting from start-of-local-day
        start = dt_util.start_of_local_day(self.now)
        end = start + timedelta(hours=24)

        try:
            result = await self.hass.services.async_call(
                "calendar",
                "get_events",
                service_data={
                    "start_date_time": start,
                    "end_date_time": end,
                },
                target={"entity_id": entity_id},
                blocking=True,
                return_response=True,
            )
            # Service response is keyed by entity_id
            events: list = (result or {}).get(entity_id, {}).get("events", [])
            self._calendar_cache[entity_id] = events
            # D-04: clear warn flag so WARNING re-fires after recovery
            self._warn_issued.discard(entity_id)
        except HomeAssistantError:
            # T-16-04: log WARNING once per entity; suppress repeats
            if entity_id not in self._warn_issued:
                _LOGGER.warning(
                    "Calendar entity %s unavailable — falling back to"
                    " absent (further failures will be suppressed"
                    " until recovery)",
                    entity_id,
                )
                self._warn_issued.add(entity_id)
            self._calendar_cache[entity_id] = []

        return self._calendar_cache[entity_id]
