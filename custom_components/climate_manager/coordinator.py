# SPDX-License-Identifier: MIT
"""Climate Manager coordinator — the integration's control loop.

Evaluates each managed room independently against its zone (Default Zone or
custom zone) every minute and on HA startup, then pushes to TRVs only when
the target temperature changes.

Design decisions from CONTEXT.md / RESEARCH.md:
- D-01: Poll every minute via async_track_time_interval (caller registers this)
- D-02: Push-on-change only — _last_pushed dict tracks last pushed temp per entity
- D-03: Manual override hold — if TRV reports a temp different from last pushed,
         skip this entity this tick; hold lifts automatically at next period transition
- D-04: On HA restart _last_pushed is empty → startup push always fires (INFRA-03)
- D-07/D-08: global_mode is the Default Zone's mode — not a system-wide override.
         Rooms in custom zones follow their own zone's mode/schedule independently.
- D-09: Per-room algorithm: resolve zone → branch on zone.mode
- D-11: Presence evaluation for time_program_presences zones uses all configured
         persons (not scoped to zone members)

Requirements addressed:
- GLOBAL-01: Default Zone branches on global_mode (Off / Time program / Presences)
- GLOBAL-02: Default Zone MODE_OFF → frost protection; custom zones unaffected (D-08)
- GLOBAL-03: period_temperatures dict provides configurable temps per period mode
- EVAL-01..05: per-zone independent evaluation via _resolve_zone_config
- PERSON-06: persons have associated room_ids
- PERSON-07: present person → heat from first Normal/Comfort period to end of last
- PERSON-08: sandwiched Reduced/Frost in occupied window → hold preceding N/C temp
- PERSON-09: absent person → Reduced temperature
- INFRA-03: immediate push on HA startup before first tick
- INFRA-05: DST-safe — always calls dt_util.now(), never uses callback's UTC arg

Pitfalls mitigated:
- Pitfall 1: cancel callback stored externally on runtime_data and called on unload
- Pitfall 2: _utc_now arg ignored; dt_util.now() is the single time source
- Pitfall 3: last=None on startup bypasses override hold, ensuring startup push
- Pitfall 6: reads attributes["temperature"] (the setpoint), not the sensor reading
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Callable

from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .boiler import Boiler
from .const import (
    DOMAIN,
    MODE_TIME_PROGRAM,
    PRESENCE_HA,
    PRESENCE_PERIOD_ABSENT,
    PRESENCE_PERIOD_PRESENT,
)
from .entity import (
    boiler_demand_unique_id,
    room_period_unique_id,
    room_sensor_unique_id,
    zone_mode_unique_id,
    zone_period_unique_id,
)
from .alignment import SensorAligner
from .eval_context import EvalContext
from .person import Person
from .room import Room
from .schedule import (
    household_setback,
    period_bounds,
    presence_override,
)
from .trv import (
    TRV,
    TRVGroup,
    is_trv_entity,
)
from .zone import Zone

if TYPE_CHECKING:
    from . import ClimateManagerData

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = timedelta(minutes=1)

# TRV states meaning "not reachable": a transition from one of these (or from
# no state at all) to a valid state re-applies the setpoint.
_OFFLINE_STATES = ("unavailable", "unknown")


class ClimateManagerCoordinator:
    """Control loop: evaluates schedules every minute and pushes temps to TRVs.

    Created in async_setup_entry and stored on entry.runtime_data.coordinator.
    The minute-polling scheduler is registered by the caller (async_setup_entry)
    via async_track_time_interval — the cancel callback is stored on runtime_data
    and called in async_unload_entry (Pitfall 1 — no ghost listeners).
    """

    def __init__(self, hass: HomeAssistant, data: "ClimateManagerData") -> None:
        """Initialise the coordinator.

        Args:
            hass: The Home Assistant instance.
            data: The integration's runtime data (shared reference — mutations
                  from Phase 3 WebSocket handlers are visible on the next tick).
        """
        self._hass = hass
        self._data = data
        # Expose data on hass so Room.compute_preheat / resolve_room_sensor
        # can read runtime_config and preheat_data without a coordinator
        # reference.
        self._hass._climate_manager_data = self._data
        # D-09 domain objects — instantiated from config at init and rebuilt
        # on config change (fingerprint-based, T-16-13).
        self._zones: dict[str, Zone] = {}
        self._persons: dict[str, Person] = {}
        self._rooms: dict[str, Room] = {}
        # Boiler driven by the rooms' demand (None = not controlled).
        self._boiler: Boiler | None = None
        # Fingerprint of the zones/persons/rooms config structure.
        # Compared each cycle; rebuild triggered on change (T-16-13).
        self._config_fingerprint: int = 0
        # Wave 2: track last evaluation results for status push and get_status WS command.
        self._last_active_period: str | None = None
        self._last_present_persons: list[str] = []
        # Household presence forced by a period (None: no period), for the
        # presence log on change.
        # (home, setback) of the last household period logged.
        self._last_household: tuple[bool | None, str | None] = (None, None)
        # Per-room effective period (may differ from global in time_program_presences mode).
        self._last_room_periods: dict[str, str] = {}
        # D-05: per-zone active period dict — "default" plus one key per custom
        # zone UUID. Populated by async_evaluate; consumed by _build_status_payload.
        self._last_zone_periods: dict[str, str | None] = {}
        # Offset alignment and its memory (last offset written per
        # target), kept across domain rebuilds.
        self._aligner = SensorAligner(hass, data, lambda: self._rooms)
        # Cancel callbacks for active ha-tracker watchers, keyed by notif_id.
        # One entry per person: person_state_cancel — dismisses the notification
        # immediately when device_trackers becomes non-empty again.
        # User dismissal is detected on the next tick by querying hass.data
        # directly (no event listener needed — more robust across HA versions).
        self._ha_tracker_listeners: dict[str, list] = {}
        # D-04: tracks entity IDs for which the calendar "unavailable" WARNING
        # has already been issued. Entry is added on first failure and removed
        # on the next successful fetch so the warning re-fires after recovery.
        # Retained here (not migrated to EvalContext) so the suppression persists
        # across evaluation cycles (T-16-13 retention list).
        self._calendar_warn_issued: set[str] = set()
        # _frost_locked_rooms: snapshot from last zone evaluation pass.
        # Retained until consumed by Room (T-16-13 retention list).
        self._frost_locked_rooms: set[str] = set()
        # D-08 (Phase 13): cancel callbacks for the alignment
        # state_changed listeners, keyed by the alignment targets'
        # temperature source entity. Single Callable per key — unlike
        # _ha_tracker_listeners (list). Cancel-all-then-rebuild via
        # _async_refresh_alignment_listeners().
        self._alignment_listeners: dict[str, Callable] = {}
        # Cancel callbacks for the TRV availability listeners, keyed by
        # entity_id. A TRV coming back online (or appearing after startup)
        # gets its setpoint re-applied immediately.
        self._availability_listeners: dict[str, Callable] = {}
        # Set when an entity without a TRV object (no state at the last
        # rebuild) becomes available: the next evaluation rebuilds the graph.
        self._rebuild_requested = False
        # Only one evaluation runs at a time; a request arriving meanwhile
        # is coalesced into one catch-up run (never lost, never stacked).
        self._eval_lock = asyncio.Lock()
        self._eval_requested = False
        # Update listeners (HA entities) notified at the end of every
        # async_evaluate cycle — DataUpdateCoordinator-style contract.
        self._listeners: list[Callable[[], None]] = []

        # Build initial domain object graph from config.
        self._build_domain_objects(data.runtime_config)

    # ------------------------------------------------------------------
    # D-09: Domain object graph construction
    # ------------------------------------------------------------------

    def _compute_config_fingerprint(self, config: dict) -> int:
        """Compute a cheap fingerprint of the zones/persons/rooms config.

        Used to detect WS-driven config mutations between ticks (T-16-13).
        Hash covers the three dicts that affect domain object graph structure.
        """
        key_parts = (
            repr(config.get("default_zone", {})),
            repr(config.get("zones", {})),
            repr(config.get("persons", {})),
            repr(config.get("rooms", {})),
            # Discovered climate entities per room (registry refresh).
            repr(sorted(self._data.rooms.items())),
            repr(config.get("boiler")),
        )
        return hash("".join(key_parts))

    def _build_domain_objects(self, config: dict) -> None:
        """Construct Zone/Person/Room/TRVGroup graphs from stored config.

        Called at __init__ and re-called when the config fingerprint changes
        (i.e. a WS handler mutated runtime_config between ticks — T-16-13).
        Domain objects are the SINGLE strong references so weakrefs in
        ZoneMode/PersonMode instances resolve correctly (Pitfall 1).

        Assembly order:
        1. Zones — default + each custom zone UUID.
        2. Persons — one per entry in config["persons"].
        3. Rooms — one per area_id in self._data.rooms; each room gets:
           a. TRVGroup via TRVGroup.from_room_config (Matter dedup — Pitfall 4).
           b. _zone wired to its owning Zone.
           c. assigned_persons populated from each person's room_ids.
        4. zone._rooms populated from Room objects.
        """
        matter_mappings: dict[str, list[str]] = config.get(
            "matter_mappings", {}
        )
        boiler_cfg = config.get("boiler") or {}
        boiler = (
            Boiler(self._hass, boiler_cfg)
            if boiler_cfg.get("entity_id")
            else None
        )

        # -- Step 1: Zones ---------------------------------------------------
        dz_cfg = config.get("default_zone", {})
        default_zone = Zone(
            zone_id="default",
            hass=self._hass,
            initial_mode=dz_cfg.get("mode", MODE_TIME_PROGRAM),
            time_program=dz_cfg.get("time_program", {}),
            preheat_enabled=dz_cfg.get("preheat_enabled", False),
        )

        zones: dict[str, Zone] = {"default": default_zone}
        for zone_id, zone_cfg in config.get("zones", {}).items():
            zones[zone_id] = Zone(
                zone_id=zone_id,
                hass=self._hass,
                initial_mode=zone_cfg.get("mode", MODE_TIME_PROGRAM),
                time_program=zone_cfg.get("time_program", {}),
                preheat_enabled=zone_cfg.get("preheat_enabled", False),
            )

        # -- Step 2: Persons -------------------------------------------------
        persons: dict[str, Person] = {}
        for person_id, person_cfg in config.get("persons", {}).items():
            p = Person(
                person_id=person_id,
                hass=self._hass,
                person_config=person_cfg,
                room_ids=person_cfg.get("room_ids", []),
            )
            persons[person_id] = p

        # -- Step 3: Rooms + TRVGroups ---------------------------------------
        rooms: dict[str, Room] = {}
        for area_id, entity_ids in self._data.rooms.items():
            room_cfg = config.get("rooms", {}).get(area_id, {})
            zone_id = room_cfg.get("zone_id")
            owning_zone: Zone = (
                zones.get(zone_id, default_zone)
                if zone_id is not None
                else default_zone
            )

            room = Room(area_id=area_id, hass=self._hass)
            room._zone = owning_zone  # wire owning zone reference

            # Build TRVGroup from entity list + matter_mappings.
            # room_name and zone_name used for DEBUG log short names.
            # The boiler is never pushed as a valve, whatever its max_temp.
            room.climate_entity_ids = [
                eid
                for eid in entity_ids
                if boiler is None or eid != boiler.entity_id
            ]
            group = TRVGroup.from_room_config(
                hass=self._hass,
                entity_ids=room.climate_entity_ids,
                matter_mappings=matter_mappings,
                room_name=area_id,
                zone_name=owning_zone.zone_id,
            )
            room._trv_groups = [group]

            rooms[area_id] = room

        # Populate assigned_persons on each room (from person.room_ids).
        for person in persons.values():
            for area_id in person.room_ids:
                if area_id in rooms:
                    rooms[area_id].assigned_persons.append(person)

        # Populate zone._rooms from the assembled rooms.
        for zone in zones.values():
            zone._rooms = [
                room for room in rooms.values() if room._zone is zone
            ]

        # Carry forward anti-spam state from previous Zone/Person objects so a
        # config-triggered rebuild doesn't reset log-state and spam the log.
        for zone_id, zone in zones.items():
            old = self._zones.get(zone_id)
            if old is not None and old._current_period is not None:
                zone._current_period = old._current_period
                zone._current_mode_name = old._current_mode_name

        for person_id, person in persons.items():
            old_p = self._persons.get(person_id)
            if old_p is not None and old_p._last_home is not None:
                person._last_home = old_p._last_home

        # Carry forward running pre-heats so a config edit doesn't restart
        # them (and corrupt the rate sample). A room seen for the first time
        # (startup) resumes the run persisted before the restart.
        for area_id, room in rooms.items():
            old_room = self._rooms.get(area_id)
            if old_room is not None:
                room.carry_preheat_state(old_room)
            else:
                room.restore_preheat_run()

        # Carry forward TRV push state so a config edit doesn't re-force a
        # push to every valve. Only TRVs new to the graph get a forced push.
        old_trvs = {trv.entity_id: trv for trv in self._iter_trvs()}
        for room in rooms.values():
            for group in room._trv_groups:
                for trv in group.trvs:
                    old_trv = old_trvs.get(trv.entity_id)
                    if old_trv is not None:
                        trv.carry_push_state(old_trv)

        # Carry forward the boiler switch state (min on/off reference).
        if boiler is not None and self._boiler is not None:
            boiler.carry_state(self._boiler)

        # Commit the new graph (single atomic update — Pitfall 1).
        self._zones = zones
        self._persons = persons
        self._rooms = rooms
        self._boiler = boiler
        self._config_fingerprint = self._compute_config_fingerprint(config)
        self._rebuild_requested = False
        self._refresh_availability_listeners()

    # ------------------------------------------------------------------
    # Public read API + update listeners (HA entity platforms)
    # ------------------------------------------------------------------

    @property
    def zones(self) -> dict[str, Zone]:
        """Live Zone objects keyed by zone_id ("default" + custom UUIDs)."""
        return self._zones

    @property
    def rooms(self) -> dict[str, Room]:
        """Live Room objects keyed by area_id."""
        return self._rooms

    @property
    def boiler(self) -> Boiler | None:
        """Live Boiler, or None when no boiler is controlled."""
        return self._boiler

    @callback
    def async_add_listener(
        self, update_callback: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a callback fired after each evaluation; return unsub."""
        self._listeners.append(update_callback)

        @callback
        def _remove_listener() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove_listener

    @callback
    def _async_notify_listeners(self) -> None:
        """Fire every registered update listener (copy: may unsub)."""
        for update_callback in list(self._listeners):
            update_callback()

    async def async_set_zone_mode(self, zone_id: str, mode: str) -> None:
        """Set a zone's mode, persist it, and schedule a re-evaluation.

        Shared by the set_zone_mode WS command and the zone mode select
        entity. zone_id="default" writes runtime_config["default_zone"]
        (T-05-01 sentinel checked before any zones{} lookup).

        Raises:
            KeyError: zone_id is neither "default" nor a custom zone.
            Exception: store.async_save failure (config rolled back).
        """
        runtime_config = self._data.runtime_config
        # Capture live Zone BEFORE any await so the periodic async_evaluate
        # timer cannot rebuild self._zones between mutation and change_mode.
        live_zone = self._zones.get(zone_id)
        if zone_id == "default":
            zone_cfg = runtime_config["default_zone"]
        else:
            zones_cfg = runtime_config.get("zones", {})
            if zone_id not in zones_cfg:
                raise KeyError(zone_id)
            zone_cfg = zones_cfg[zone_id]
        old_mode = zone_cfg.get("mode")
        zone_cfg["mode"] = mode
        try:
            await self._data.store.async_save(runtime_config)
        except Exception:
            zone_cfg["mode"] = old_mode
            raise
        # Emit OBS-01 mode-change log on the live Zone (captured pre-await).
        if live_zone is not None:
            live_zone.change_mode(mode)
        # async_evaluate re-derives _last_zone_periods/_last_room_periods
        # and notifies status subscribers + entities once done.
        self._hass.async_create_task(self.async_evaluate())

    def _get_trv(self, entity_id: str) -> "TRV | None":
        """Return the TRV domain object for entity_id, or None if not found.

        Searches self._rooms for a TRV with the matching entity_id.
        Used by the event-driven alignment path.
        """
        for room in self._rooms.values():
            for group in room._trv_groups:
                for trv in group._trvs:
                    if trv.entity_id == entity_id:
                        return trv
        return None

    def _iter_trvs(self):
        """Yield every TRV push target of the current domain graph."""
        for room in self._rooms.values():
            for group in room._trv_groups:
                yield from group.trvs

    # ------------------------------------------------------------------
    # TRV availability listeners — re-apply setpoint when back online
    # ------------------------------------------------------------------

    def _refresh_availability_listeners(self) -> None:
        """Track every TRV and room climate entity for availability changes.

        Covers the TRV push targets plus every climate entity of the rooms,
        so an entity that had no state at the last rebuild (integration still
        loading at HA startup) is picked up as soon as it appears.
        Re-run on every _build_domain_objects; cancelled on unload.
        """
        from homeassistant.helpers.event import (  # noqa: PLC0415
            async_track_state_change_event,
        )

        self.cancel_availability_listeners()
        entity_ids = {trv.entity_id for trv in self._iter_trvs()}
        for room_entity_ids in self._data.rooms.values():
            entity_ids.update(room_entity_ids)
        if self._boiler is not None:
            entity_ids.add(self._boiler.entity_id)
        for entity_id in sorted(entity_ids):
            self._availability_listeners[entity_id] = (
                async_track_state_change_event(
                    self._hass, entity_id, self._on_trv_state_changed
                )
            )

    def cancel_availability_listeners(self) -> None:
        """Cancel all TRV availability listeners."""
        for cancel in self._availability_listeners.values():
            cancel()
        self._availability_listeners.clear()

    @callback
    def _on_trv_state_changed(self, event: object) -> None:
        """Re-apply the setpoint of a TRV that just became available.

        Fires on missing/unavailable/unknown → any valid state. The TRV's
        push state is reset so the next push is forced (its setpoint may have
        changed while offline) and the manual-override hold is lifted.
        """
        data = getattr(event, "data", {})
        new_state = data.get("new_state")
        if new_state is None or new_state.state in _OFFLINE_STATES:
            return
        old_state = data.get("old_state")
        if old_state is not None and old_state.state not in _OFFLINE_STATES:
            return
        entity_id = new_state.entity_id
        trv = self._get_trv(entity_id)
        if self._boiler is not None and entity_id == self._boiler.entity_id:
            self._boiler.resync()
            _LOGGER.info(
                "online | boiler=%s back online, re-applying demand",
                entity_id.split(".", 1)[-1],
            )
        elif trv is not None:
            trv.reset_push_state()
            _LOGGER.info(
                "online | trv=%s back online, re-applying setpoint",
                entity_id.split(".", 1)[-1],
            )
        else:
            # Room entity left out of the graph (no state at the last
            # rebuild): rebuild so its push targets are assembled.
            _LOGGER.debug("%s became available — rebuilding rooms", entity_id)
            self._rebuild_requested = True
        self._hass.async_create_task(self.async_evaluate())

    async def async_evaluate(self, _utc_now: datetime | None = None) -> None:
        """Evaluate all managed rooms and push temperatures as needed.

        Called immediately after registration (INFRA-03 startup push), every
        minute by async_track_time_interval, after WS mutations and when a
        TRV comes back online.

        Only one evaluation runs at a time. A call arriving while one runs
        returns at once and schedules exactly one catch-up run, so stalled
        evaluations never pile up and no trigger is lost.

        The _utc_now argument is provided by async_track_time_interval but is
        deliberately ignored — it carries UTC time (Pitfall 2). Local wall-clock
        time is always derived from dt_util.now() (INFRA-05 / DST-safe).
        """
        if self._eval_lock.locked():
            self._eval_requested = True
            _LOGGER.debug("Evaluation already running — coalescing request")
            return
        async with self._eval_lock:
            self._eval_requested = True
            while self._eval_requested:
                self._eval_requested = False
                await self._async_evaluate_once()

    async def _async_prune_presence_periods(
        self, config: dict, now: datetime
    ) -> list:
        """Drop the presence periods whose return has passed, and save.

        Returns the periods left. A failed save keeps them pruned in
        memory; the next config save persists it.
        """
        periods: list = config.get("presence_periods") or []
        kept = [p for p in periods if period_bounds(p, now.tzinfo)[1] > now]
        if len(kept) == len(periods):
            return periods
        config["presence_periods"] = kept
        _LOGGER.info(
            "presence | %d period(s) ended, removed", len(periods) - len(kept)
        )
        try:
            await self._data.store.async_save(config)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Saving the pruned presence periods: %s", err)
        return kept

    def _log_household_presence(self, periods: list, now: datetime) -> None:
        """Log a household period (covering everyone) starting or ending."""
        household = presence_override(periods, now)
        setback = household_setback(periods, now)
        state = (household, setback)
        if state == self._last_household:
            return
        if household is None:
            _LOGGER.info("presence | household period ended")
        elif household:
            _LOGGER.info(
                "presence | household home=True reason=%s_period",
                PRESENCE_PERIOD_PRESENT,
            )
        else:
            _LOGGER.info(
                "presence | household home=False reason=%s_period setback=%s",
                PRESENCE_PERIOD_ABSENT,
                setback,
            )
        self._last_household = state

    async def _async_evaluate_once(self) -> None:
        """Run one evaluation cycle (see async_evaluate).

        Each room is evaluated independently via its owning Zone — there is
        no top-level global_mode branch. global_mode is the Default Zone's
        mode only (D-07/D-08).
        """
        now = dt_util.now()
        config = self._data.runtime_config
        period_temperatures: dict[str, float] = config["period_temperatures"]

        # T-16-13: rebuild domain objects when WS handler mutated runtime_config.
        # Fingerprint covers zones/persons/rooms structure; cheap hash comparison.
        new_fp = self._compute_config_fingerprint(config)
        if new_fp != self._config_fingerprint or self._rebuild_requested:
            self._build_domain_objects(config)

        presence_periods = await self._async_prune_presence_periods(config, now)
        self._log_household_presence(presence_periods, now)

        # D-09: build one EvalContext per cycle (OBS-01 / RESEARCH D-02).
        ctx = EvalContext(
            now=now,
            hass=self._hass,
            period_temperatures=period_temperatures,
            presence_periods=presence_periods,
            _warn_issued=self._calendar_warn_issued,
        )

        # Evaluate every person first so ctx._presence_cache is complete
        # before the zones run concurrently (no duplicate calendar fetch) and
        # status reporting has every person's state (D-11 / INFRA-03).
        for person in self._persons.values():
            await person.evaluate(ctx)

        # All zones at once — each Zone delegates to its ZoneMode which pushes
        # all its rooms concurrently: room.apply_setpoint → TRVGroup.push →
        # TRV.push_temperature. Every valve receives its command at the same
        # time; a slow valve only delays itself (TRV_COMMAND_TIMEOUT).
        results = await asyncio.gather(
            *(zone.evaluate(ctx) for zone in self._zones.values()),
            return_exceptions=True,
        )
        for zone_id, result in zip(self._zones, results):
            if isinstance(result, BaseException):
                _LOGGER.warning(
                    "Zone %s evaluation failed: %r", zone_id, result
                )

        # Per-room pre-heat pass (D-09), right after the zone pushes and
        # before the status snapshot so a pre-heat started this tick shows
        # up at once. Room.compute_preheat owns all preheat state (D-06).
        for room in self._rooms.values():
            await room.compute_preheat(ctx)

        # Boiler after pre-heat: a pre-heat started this tick already set
        # its room period, so the boiler follows in the same tick.
        if self._boiler is not None:
            await self._boiler.evaluate(now, self._rooms)

        # Warn via persistent notification when an ha-mode person has no tracker.
        self._check_ha_tracker_warnings(config)

        # Update status-payload tracking fields from EvalContext (D-09).
        # _last_present_persons: list of person_ids where ctx returned True.
        self._last_present_persons = [
            pid for pid, home in ctx._presence_cache.items() if home
        ]

        # _last_room_periods: per-room effective period from the owning Zone.
        # In time_program_presences mode this is the last period returned by
        # ZoneModeProgramPresences.evaluate — same for all rooms in the zone.
        self._last_room_periods = {}
        for area_id, room in self._rooms.items():
            # Per-room period wins: in presence mode each room resolves its
            # own effective period (e.g. empty room → reduced) while the
            # zone-level _current_period only holds the last room's value.
            if room._last_period is not None:
                self._last_room_periods[area_id] = room._last_period
                continue
            zone = room._zone
            if zone is not None and zone._current_period is not None:
                self._last_room_periods[area_id] = zone._current_period

        # _last_active_period: Default Zone's current period (status fallback).
        default_zone = self._zones.get("default")
        self._last_active_period = (
            default_zone._current_period if default_zone is not None else None
        )

        # _last_zone_periods: per-zone current period dict (D-05).
        self._last_zone_periods = {
            zone_id: zone._current_period
            for zone_id, zone in self._zones.items()
        }

        # D-10 (Phase 13): (re)register alignment listeners whenever the
        # watched entities change: first evaluate, room or pairing change,
        # a valve appearing in the registry.
        if set(self._aligner.watched_entities()) != set(
            self._alignment_listeners
        ):
            await self._async_refresh_alignment_listeners()

        # Alignment pass (D-09).
        await self._async_align(config, ctx)

        # RESEARCH Open Question 1: fire status AFTER preheat/align passes
        # so the panel receives up-to-date preheat_active / preheat_suppressed
        # in the same cycle that triggered the preheat (avoids one-cycle lag).
        self._hass.bus.async_fire(
            f"{DOMAIN}_status_update",
            self._build_status_payload(),
        )
        self._async_notify_listeners()

    @property
    def aligner(self) -> SensorAligner:
        """Offset alignment (targets and memory, for the panel status)."""
        return self._aligner

    async def _async_align(
        self,
        config: dict,
        ctx: "EvalContext | None" = None,
    ) -> None:
        """Offset-align every room's TRVs toward their room sensors.

        D-04: no-op when alignment_enabled is False.
        D-03: concurrent gather over all rooms, same pattern as push pass.
        """
        await self._aligner.align_all(config)

    # -----------------------------------------------------------------------
    # Phase 13: alignment listener lifecycle (D-08..D-11)
    # -----------------------------------------------------------------------

    @callback
    def _make_alignment_listener(self, area_id: str) -> Callable:
        """Factory: create a state_changed callback for an entity in area_id.

        D-09: only fires alignment when current_temperature changes.
        Guards old_state=None (Pitfall 5 — entity startup event).
        Schedules _async_align_for_room via hass.async_create_task
        (listener is @callback; cannot await directly).
        """

        @callback
        def _on_state_changed(event: object) -> None:
            new_state = getattr(event, "data", {}).get("new_state")
            if new_state is None:
                return
            old_state = getattr(event, "data", {}).get("old_state")
            new_temp = (new_state.attributes or {}).get("current_temperature")
            old_temp = (
                (old_state.attributes or {}).get("current_temperature")
                if old_state is not None
                else None
            )
            if new_temp == old_temp:
                return
            self._hass.async_create_task(self._async_align_for_room(area_id))

        return _on_state_changed

    async def _async_refresh_alignment_listeners(self) -> None:
        """Cancel all alignment listeners and re-register.

        D-10: cancel-all-then-rebuild. Safe because WS commands are
        serialised on the HA event loop — no concurrent registration race.
        One listener per alignment target temperature source (a paired
        Matter valve rather than its cloud entity), so a fresh local
        reading triggers the room's alignment immediately.
        """
        from homeassistant.helpers.event import (  # noqa: PLC0415
            async_track_state_change_event,
        )

        # Cancel all existing listeners before rebuild (Pitfall 1)
        for cancel in self._alignment_listeners.values():
            cancel()
        self._alignment_listeners.clear()

        for entity_id, area_id in self._aligner.watched_entities().items():
            self._alignment_listeners[entity_id] = (
                async_track_state_change_event(
                    self._hass,
                    entity_id,
                    self._make_alignment_listener(area_id),
                )
            )

    async def _async_align_for_room(self, area_id: str) -> None:
        """Run alignment for a single room (event-driven path).

        Called from the alignment listener callback via
        hass.async_create_task.
        """
        await self._aligner.align_room(self._data.runtime_config, area_id)

    def _dismiss_ha_tracker_notif(self, notif_id: str) -> None:
        """Cancel the tracker-restored watcher and dismiss the notification."""
        from homeassistant.components.persistent_notification import (  # noqa: PLC0415
            async_dismiss,
        )

        for cancel in self._ha_tracker_listeners.pop(notif_id, []):
            cancel()
        async_dismiss(self._hass, notif_id)

    def _check_ha_tracker_warnings(self, config: dict) -> None:
        """Create or dismiss persistent notifications for ha-mode persons.

        Runs on every tick. Notification existence is checked directly against
        hass.data["persistent_notification"] so user dismissals are detected
        on the next tick (≤1 min) and the notification is recreated — no event
        listener needed for dismissal detection.

        Tracker restoration: immediate via a per-person state-change listener
        registered once when the notification is first shown.
        """
        from homeassistant.components.persistent_notification import (  # noqa: PLC0415
            async_create,
        )
        from homeassistant.helpers.event import (  # noqa: PLC0415
            async_track_state_change_event,
        )

        pn_data = self._hass.data.get("persistent_notification", {})

        for person_id, person_cfg in config.get("persons", {}).items():
            notif_id = f"{DOMAIN}_ha_no_tracker_{person_id.replace('.', '_')}"
            mode_is_ha = person_cfg.get("mode") == PRESENCE_HA
            state_obj = self._hass.states.get(person_id)
            trackers = (
                state_obj.attributes.get("device_trackers", [])
                if state_obj is not None
                else []
            )
            has_trackers = isinstance(trackers, list) and len(trackers) > 0
            should_notify = mode_is_ha and not has_trackers

            if not should_notify:
                # Dismiss if shown and cancel any watcher.
                if isinstance(pn_data, dict) and notif_id in pn_data:
                    self._dismiss_ha_tracker_notif(notif_id)
                elif notif_id in self._ha_tracker_listeners:
                    for cancel in self._ha_tracker_listeners.pop(notif_id):
                        cancel()
                continue

            # Create or recreate when user dismissed (not in pn_data anymore).
            notif_present = isinstance(pn_data, dict) and notif_id in pn_data
            if not notif_present:
                name = (
                    state_obj.attributes.get("friendly_name", person_id)
                    if state_obj is not None
                    else person_id
                )
                slug = person_id.removeprefix("person.")
                async_create(
                    self._hass,
                    (
                        f"**{name}** is set to *HA home tracking* but has no "
                        f"device tracker linked in Home Assistant. Presence "
                        f"detection will not work until a device tracker is "
                        f"added.\n\n"
                        f"[Edit {name} in HA](/config/person/edit/{slug})"
                    ),
                    title="Climate Manager — HA Tracking",
                    notification_id=notif_id,
                )

            # Register the tracker-restored watcher only once per person.
            if notif_id not in self._ha_tracker_listeners:

                @callback
                def _on_tracker_restored(
                    event: object,
                    _notif_id: str = notif_id,
                ) -> None:
                    new_state = getattr(event, "data", {}).get("new_state")
                    if new_state is None:
                        return
                    t = new_state.attributes.get("device_trackers", [])
                    if isinstance(t, list) and len(t) > 0:
                        self._dismiss_ha_tracker_notif(_notif_id)

                self._ha_tracker_listeners[notif_id] = [
                    async_track_state_change_event(
                        self._hass, person_id, _on_tracker_restored
                    ),
                ]

    def _build_status_payload(self) -> dict:
        """Build the status dict pushed to subscribed panel connections after each evaluation.

        Used by the Wave 2 subscribe_status WS command and the hass.bus event.
        Includes rooms_status so the Rooms tab populates from push events.
        """
        from homeassistant.helpers import (  # noqa: PLC0415
            area_registry as ar,
            entity_registry as er,
        )

        _area_reg = ar.async_get(self._hass)
        _entity_reg = er.async_get(self._hass)
        entry_id = self._data.entry_id

        def _entity_id(
            platform: str, unique_id_fn: Callable[[str, str], str], item_id: str
        ) -> str | None:
            """Resolve a Climate Manager entity_id (None if not registered).

            Entity IDs are user-renamable, so the panel never guesses them.
            """
            if entry_id is None:
                return None
            return _entity_reg.async_get_entity_id(
                platform, DOMAIN, unique_id_fn(entry_id, item_id)
            )

        # D-24: pre-compute persons join data for present_person_count
        persons_config: dict = self._data.runtime_config.get("persons", {})
        present_set = set(self._last_present_persons)

        rooms_status = []
        for area_id, entity_ids in self._data.rooms.items():
            _area = _area_reg.async_get_area(area_id)
            room_entry: dict = {
                "area_id": area_id,
                "name": _area.name if _area else area_id,
                "active_period": self._last_room_periods.get(
                    area_id, self._last_active_period
                ),
                "entity_ids": entity_ids,
                "period_entity_id": _entity_id(
                    "sensor", room_period_unique_id, area_id
                ),
                # Learned pre-heat parameter sensors (card history).
                "preheat_rate_entity_id": _entity_id(
                    "sensor",
                    lambda e, a: room_sensor_unique_id(e, a, "preheat_rate"),
                    area_id,
                ),
                "preheat_anticipation_entity_id": _entity_id(
                    "sensor",
                    lambda e, a: room_sensor_unique_id(
                        e, a, "preheat_anticipation"
                    ),
                    area_id,
                ),
            }

            # D-24: count persons assigned to this area who are currently present
            room_entry["present_person_count"] = sum(
                1
                for person_id, person_config in persons_config.items()
                if area_id in person_config.get("room_ids", [])
                and person_id in present_set
            )

            # D-10 / PREHEAT-04: per-room pre-heat status fields.
            # State now lives on Room domain object (D-06 migration).
            _room_obj = self._rooms.get(area_id)
            room_entry["preheat_active"] = (
                _room_obj._preheat_active if _room_obj is not None else False
            )
            room_entry["preheat_target"] = (
                _room_obj._preheat_target if _room_obj is not None else None
            )
            room_entry["preheat_suppressed"] = (
                _room_obj._preheat_suppressed
                if _room_obj is not None
                else False
            )
            # Learned inertia: rate (min/°C, None while learning), sample
            # count and the lead computed at the last pre-heat pass.
            room_entry["preheat_rate"] = (
                _room_obj.learned_rate() if _room_obj is not None else None
            )
            room_entry["preheat_samples"] = (
                _room_obj.preheat_sample_count() if _room_obj is not None else 0
            )
            room_entry["preheat_lead"] = (
                round(_room_obj._preheat_lead)
                if _room_obj is not None and _room_obj._preheat_lead is not None
                else None
            )
            # °C currently added to the TRV setpoint by the pre-heat boost.
            room_entry["preheat_boost"] = (
                _room_obj._preheat_boost_applied
                if _room_obj is not None
                else None
            )
            # Absence whose return the room is pre-heating for.
            room_entry["preheat_return"] = (
                _room_obj.preheat_return_period()
                if _room_obj is not None
                else None
            )
            # Learned anticipation (minutes) releasing the boost.
            room_entry["preheat_anticipation"] = (
                _room_obj.anticipation() if _room_obj is not None else None
            )

            auto = self._data.room_auto_sensors.get(area_id, {})

            # Temperature/humidity: HA area registry (HA 2026.5+) → auto-discovered → TRV built-in
            temp_sensor = getattr(
                _area, "temperature_entity_id", None
            ) or auto.get("temperature")
            humidity_sensor = getattr(
                _area, "humidity_entity_id", None
            ) or auto.get("humidity")
            # Exposed so the panel room card can graph their history.
            room_entry["temperature_entity_id"] = temp_sensor or None
            room_entry["humidity_entity_id"] = humidity_sensor or None
            if temp_sensor:
                sensor_state = self._hass.states.get(temp_sensor)
                if sensor_state is not None and sensor_state.state not in (
                    "unavailable",
                    "unknown",
                ):
                    try:
                        room_entry["temperature"] = float(sensor_state.state)
                    except (ValueError, TypeError):
                        pass  # leave temperature absent (invalid sensor state)
            elif entity_ids:
                trv_state = self._hass.states.get(entity_ids[0])
                if trv_state is not None:
                    current_temp = trv_state.attributes.get(
                        "current_temperature"
                    )
                    if current_temp is not None:
                        room_entry["temperature"] = current_temp

            if humidity_sensor:
                hum_state = self._hass.states.get(humidity_sensor)
                if hum_state is not None and hum_state.state not in (
                    "unavailable",
                    "unknown",
                ):
                    try:
                        room_entry["humidity"] = float(hum_state.state)
                    except (ValueError, TypeError):
                        pass  # leave humidity absent (invalid sensor state)

            room_entry["has_trv"] = any(
                is_trv_entity(self._hass, eid) for eid in entity_ids
            )

            rooms_status.append(room_entry)

        def _zone_status(zone_id: str, mode: str) -> dict:
            return {
                "mode": mode,
                "active_period": self._last_zone_periods.get(zone_id),
                "mode_entity_id": _entity_id(
                    "select", zone_mode_unique_id, zone_id
                ),
                "period_entity_id": _entity_id(
                    "sensor", zone_period_unique_id, zone_id
                ),
            }

        config = self._data.runtime_config
        return {
            "zones": {
                "default": _zone_status(
                    "default", config["default_zone"]["mode"]
                ),
                **{
                    zone_id: _zone_status(zone_id, zone["mode"])
                    for zone_id, zone in config.get("zones", {}).items()
                },
            },
            "present_persons": self._last_present_persons,
            "rooms_status": rooms_status,
            "boiler": self._boiler_status(_entity_reg),
        }

    def _boiler_status(self, entity_reg) -> dict | None:
        """Boiler status entry, with the demand sensor's entity_id."""
        if self._boiler is None:
            return None
        status = self._boiler.status()
        entry_id = self._data.entry_id
        status["demand_entity_id"] = (
            entity_reg.async_get_entity_id(
                "binary_sensor", DOMAIN, boiler_demand_unique_id(entry_id)
            )
            if entry_id is not None
            else None
        )
        return status
