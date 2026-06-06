# SPDX-License-Identifier: MIT
"""Climate Manager person domain model.

Defines the PersonMode state machine (plain base class, assert-False overloads,
no ABC) and the Person class that owns presence evaluation, INFO log emission on
_last_home flip (OBS-01), and ctx._presence_cache deduplication (D-02).

Design decisions:
- D-05: PersonMode is a plain base class with weakref back-link to Person.
- D-08: presence log reason= is the mode name only (scheduled|ha|calendar|
  force_present|force_absent). No extra detail.
- D-10: anti-spam is driven by Person._last_home — no separate log-state dict.
  Log fires only when result flips from the previous value.
- D-01: person name in log is short-stripped (person.alice → alice).
- Pitfall 6: ctx._presence_cache keyed by full person_id, not short name.
"""

from __future__ import annotations

import asyncio
import logging
import weakref
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_PREHEAT_LEAD_MINUTES,
    PRESENCE_ABSENT,
    PRESENCE_AUTOMATIC,
    PRESENCE_CALENDAR,
    PRESENCE_HA,
    PRESENCE_PRESENT,
)
from .schedule import resolve_calendar_presence, resolve_presence

if TYPE_CHECKING:
    from .eval_context import EvalContext

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Short-name helper (D-01)
# ---------------------------------------------------------------------------


def _short_name(entity_id: str) -> str:
    """Strip domain/prefix for log display (D-01).

    Examples:
      person.alice   → alice
      area_kitchen   → kitchen  (strip area_ prefix)
      zone_main      → main     (strip zone_ prefix)
      climate.trv    → trv
      kitchen        → kitchen  (no change)
    """
    if "." in entity_id:
        return entity_id.split(".", 1)[1]
    for prefix in ("area_", "zone_"):
        if entity_id.startswith(prefix):
            return entity_id[len(prefix) :]
    return entity_id


# ---------------------------------------------------------------------------
# PersonMode base class
# ---------------------------------------------------------------------------


class PersonMode:
    """Plain base class for all Person presence modes.

    Uses a weakref back-link to the owning Person instance so that mode
    objects do not create reference cycles (D-05). All config is read
    through self.person.<field> at call time — no config stored on the mode.

    Subclasses MUST override is_present. The base raises AssertionError (not
    NotImplementedError and not via ABC) — a clear runtime crash if a
    subclass fails to override.
    """

    reason_label: str = ""  # overridden per subclass (D-08)

    def __init__(self, person: "Person") -> None:
        self._person_ref: weakref.ref["Person"] = weakref.ref(person)

    @property
    def person(self) -> "Person":
        """Dereference the weakref; assert the Person is still alive."""
        p = self._person_ref()
        assert p is not None, (
            "PersonMode: owning Person has been garbage-collected"
        )
        return p

    async def is_present(self, ctx: "EvalContext") -> bool:
        """Return True if the person is home this cycle.

        Subclasses MUST override this method.
        """
        assert False, f"{type(self).__name__}.is_present() not implemented"

    def next_occupied_at(self, ctx: "EvalContext"):
        """Return the next datetime when the person will be present, or None.

        Base returns None. Only PersonModeScheduled and PersonModeCalendar
        override this with a meaningful implementation.
        """
        return None


# ---------------------------------------------------------------------------
# Concrete PersonMode subclasses
# ---------------------------------------------------------------------------


class PersonModeScheduled(PersonMode):
    """Presence driven by the person's periodic presence schedule.

    Delegates to schedule.resolve_presence, which handles PRESENCE_AUTOMATIC,
    PRESENCE_PRESENT, PRESENCE_ABSENT, and calendar-period fall-through.
    """

    reason_label = "scheduled"

    async def is_present(self, ctx: "EvalContext") -> bool:
        person = self.person
        # Pre-fetch calendar entities referenced in "calendar" period states
        # so ctx._calendar_cache is populated before resolve_presence reads it.
        # Covers the single-week layout ("schedule") and the even/odd layout
        # ("schedule_odd" / "schedule_even") — resolve_presence selects the
        # active week by parity, so both weeks must be pre-fetched.
        cfg = person.person_config
        for key in ("schedule", "schedule_odd", "schedule_even"):
            schedule = cfg.get(key, {})
            if not isinstance(schedule, dict):
                continue
            for day_slots in schedule.values():
                if isinstance(day_slots, list):
                    for slot in day_slots:
                        if slot.get("state") == "calendar":
                            eid = (slot.get("calendar_config") or {}).get(
                                "entity_id"
                            )
                            if eid:
                                await ctx.calendar_events(eid)
        return resolve_presence(
            person.person_config,
            ctx.now,
            calendar_cache=ctx._calendar_cache,
            start_of_local_day=dt_util.start_of_local_day,
        )

    def next_occupied_at(self, ctx: "EvalContext"):
        """Forward-walk the schedule to find the next presence window start.

        Returns None for now — full forward-walk is a future enhancement.
        """
        return None


class PersonModeHA(PersonMode):
    """Presence driven by HA's built-in person.* entity state.

    Person is present iff hass.states.get(person_id).state == "home".
    All other states (not_home, unknown, unavailable, zone names, None) mean
    absent (D-21).
    """

    reason_label = "ha"

    async def is_present(self, ctx: "EvalContext") -> bool:
        person = self.person
        state_obj = person.hass.states.get(person.person_id)
        return state_obj is not None and state_obj.state == "home"


class PersonModeCalendar(PersonMode):
    """Presence driven by a Home Assistant calendar entity.

    Fetches events lazily via ctx.calendar_events(entity_id) (D-02 dedup)
    and delegates to schedule.resolve_calendar_presence with the same args
    that coordinator._compute_present_persons uses (CAL-01).
    """

    reason_label = "calendar"

    async def is_present(self, ctx: "EvalContext") -> bool:
        person = self.person
        cal_cfg: dict = person.calendar_config or {}
        eid: str = cal_cfg.get("entity_id", "")
        events = await ctx.calendar_events(eid)

        # Wakeup advance: fallback chain supports both old and new key names.
        preheat = person.person_config.get(
            "wakeup_advance_minutes",
            person.person_config.get(
                "preheat_lead_minutes",
                DEFAULT_PREHEAT_LEAD_MINUTES,
            ),
        )
        return resolve_calendar_presence(
            events,
            cal_cfg.get("event_means", "absent"),
            ctx.now,
            gap_handling=cal_cfg.get("gap_handling", "exact"),
            gap_threshold_minutes=cal_cfg.get("gap_threshold_minutes", 0),
            preheat_lead_minutes=preheat,
            start_of_local_day=dt_util.start_of_local_day,
        )

    def next_occupied_at(self, ctx: "EvalContext"):
        """Calendar forward-look: returns None for now (future enhancement)."""
        return None


class PersonModeForcePresent(PersonMode):
    """Force-presence mode — person is always considered home."""

    reason_label = "force_present"

    async def is_present(self, ctx: "EvalContext") -> bool:
        return True


class PersonModeForceAbsent(PersonMode):
    """Force-absent mode — person is never considered home."""

    reason_label = "force_absent"

    async def is_present(self, ctx: "EvalContext") -> bool:
        return False


# ---------------------------------------------------------------------------
# Mode factory
# ---------------------------------------------------------------------------

_MODE_FACTORY: dict[str, type[PersonMode]] = {
    PRESENCE_AUTOMATIC: PersonModeScheduled,
    PRESENCE_HA: PersonModeHA,
    PRESENCE_CALENDAR: PersonModeCalendar,
    PRESENCE_PRESENT: PersonModeForcePresent,
    PRESENCE_ABSENT: PersonModeForceAbsent,
}


def _make_mode(person: "Person", mode_key: str) -> PersonMode:
    """Construct the correct PersonMode subclass for a PRESENCE_* constant."""
    cls = _MODE_FACTORY.get(mode_key, PersonModeScheduled)
    return cls(person)


# ---------------------------------------------------------------------------
# Person class
# ---------------------------------------------------------------------------


class Person:
    """Domain object representing a tracked person.

    Owns:
    - person_id: the HA entity ID (e.g. "person.alice")
    - hass: HomeAssistant instance (needed by PersonModeHA)
    - person_config: full person config dict (for schedule/calendar modes)
    - calendar_config: shortcut to person_config["calendar_config"]
    - room_ids: list of room/area IDs this person is assigned to
    - _mode: the active PersonMode subclass instance
    - _last_home: bool | None — last evaluated presence result (D-10 anti-spam)

    Person.evaluate(ctx) implements:
    1. Presence cache check — if already evaluated this cycle, return cached
       value without re-running the mode (Pitfall 6: key by full person_id).
    2. Mode evaluation — await self._mode.is_present(ctx).
    3. Anti-spam log — INFO once per _last_home flip (D-10).
    4. Cache write — store result in ctx._presence_cache and self._last_home.
    """

    def __init__(
        self,
        person_id: str,
        hass=None,
        person_config: dict | None = None,
        room_ids: list[str] | None = None,
    ) -> None:
        self.person_id: str = person_id
        self.hass = hass
        self.person_config: dict = person_config or {}
        self.calendar_config: dict = (
            self.person_config.get("calendar_config", {}) or {}
        )
        self.room_ids: list[str] = room_ids or []
        self._last_home: bool | None = None

        # Build mode from config; default to scheduled if key absent.
        mode_key = self.person_config.get("mode", PRESENCE_AUTOMATIC)
        self._mode: PersonMode = _make_mode(self, mode_key)

    async def evaluate(self, ctx: "EvalContext") -> bool:
        """Return True if this person is currently home.

        Checks ctx._presence_cache first (Pitfall 6 — key by full person_id).
        On cache miss: evaluates the mode, logs INFO on _last_home flip (D-10),
        then stores result in both ctx._presence_cache and self._last_home.
        """
        # D-02 / Pitfall 6: cache keyed by full person_id (not short name)
        if self.person_id in ctx._presence_cache:
            return ctx._presence_cache[self.person_id]

        result: bool = await self._mode.is_present(ctx)

        # D-10: log only on flip — anti-spam via _last_home, no separate dict
        if result != self._last_home:
            _LOGGER.info(
                "presence | person=%s home=%s reason=%s",
                _short_name(self.person_id),
                result,
                self._mode.reason_label,
            )
            self._last_home = result

        ctx._presence_cache[self.person_id] = result
        return result

    def evaluate_sync(self, ctx: "EvalContext") -> bool:
        """Synchronous wrapper around evaluate() for use in sync test code."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.evaluate(ctx))
        finally:
            loop.close()

    def change_mode(self, new_mode_key: str) -> None:
        """Swap PersonMode and log the transition (user-driven, D-08/D-10).

        Emits: presence | person=<name> mode=<old>→<new> reason=user
        Resets _last_home so the next evaluate() always logs the new presence
        state regardless of whether the boolean value changed.
        """
        old_label = self._mode.reason_label
        new_cls = _MODE_FACTORY.get(new_mode_key)
        if new_cls is None:
            _LOGGER.warning(
                "Unknown mode %r for person %s — ignoring change_mode",
                new_mode_key,
                self.person_id,
            )
            return
        self._mode = new_cls(self)
        _LOGGER.info(
            "presence | person=%s mode=%s→%s reason=user",
            _short_name(self.person_id),
            old_label,
            self._mode.reason_label,
        )
        self._last_home = None

    def next_occupied_at(self, ctx: "EvalContext"):
        """Return the next datetime when the person will be home, or None."""
        return self._mode.next_occupied_at(ctx)
