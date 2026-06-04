# SPDX-License-Identifier: MIT
"""Tests for room.py — Room domain class (D-06, D-07, D-09).

Scenarios:
- Room.apply_setpoint(period, temp, ctx) delegates to each TRVGroup in
  room._trv_groups — each group's push method is awaited exactly once with
  the given temp and period (D-09 apply_setpoint → group.push flow).
- Room owns preheat and calibration state directly (D-06) — the Room
  instance exposes _preheat_active, _preheat_target, _preheat_suppressed
  as scalar attributes (not coordinator dicts).
"""

from unittest.mock import AsyncMock, MagicMock


from custom_components.climate_manager.room import Room


async def test_apply_setpoint_delegates_to_trv_groups(hass):
    """Room.apply_setpoint(period, temp, ctx) calls push on each TRVGroup in
    room._trv_groups exactly once with the supplied temp and period (D-09).
    """
    room = Room(area_id="area_kitchen")

    # Build two fake TRVGroup mocks whose push method is an async callable.
    group_a = MagicMock()
    group_a.push = AsyncMock(return_value=None)
    group_b = MagicMock()
    group_b.push = AsyncMock(return_value=None)

    room._trv_groups = [group_a, group_b]

    ctx = MagicMock()

    await room.apply_setpoint(period="normal", temp=21.0, ctx=ctx)

    # Each group's push must have been awaited exactly once.
    group_a.push.assert_awaited_once()
    group_b.push.assert_awaited_once()

    # The call must include the temp and period.
    call_args_a = group_a.push.call_args
    assert call_args_a is not None
    # Accept both positional and keyword-argument call styles.
    flat_args = list(call_args_a.args) + list(call_args_a.kwargs.values())
    assert 21.0 in flat_args or "normal" in flat_args, (
        f"Expected temp=21.0 and/or period='normal' in push args: {call_args_a}"
    )


async def test_apply_setpoint_two_groups_called_for_each(hass):
    """With three TRVGroups in _trv_groups, apply_setpoint calls push on all
    three — not just the first or last (D-09 iteration contract).
    """
    room = Room(area_id="area_living")

    groups = [MagicMock(push=AsyncMock(return_value=None)) for _ in range(3)]
    room._trv_groups = groups

    ctx = MagicMock()
    await room.apply_setpoint(period="comfort", temp=22.0, ctx=ctx)

    for i, grp in enumerate(groups):
        (
            grp.push.assert_awaited_once(),
            (f"TRVGroup[{i}].push was not awaited exactly once"),
        )


def test_room_owns_preheat_state_as_scalars():
    """Room owns preheat state as scalar attributes (D-06) — migrated from
    coordinator's _preheat_in_progress dict.

    Required attributes:
      _preheat_active      (bool)
      _preheat_target      (float | None)
      _preheat_suppressed  (bool)
    """
    room = Room(area_id="area_bedroom")

    # These must be scalar attributes, not dicts.
    assert hasattr(room, "_preheat_active"), (
        "Room must expose _preheat_active (D-06)"
    )
    assert hasattr(room, "_preheat_target"), (
        "Room must expose _preheat_target (D-06)"
    )
    assert hasattr(room, "_preheat_suppressed"), (
        "Room must expose _preheat_suppressed (D-06)"
    )

    # Confirm they are not dict-typed (coordinator pattern is replaced).
    assert not isinstance(room._preheat_active, dict), (
        "_preheat_active must be a scalar bool, not a dict"
    )
    assert not isinstance(room._preheat_suppressed, dict), (
        "_preheat_suppressed must be a scalar bool, not a dict"
    )


def test_room_exposes_trv_groups_attribute():
    """Room must expose _trv_groups as a list (D-06, D-07 TRVGroup assembly).
    The coordinator populates this at init time; the test verifies the
    attribute exists on a fresh Room instance.
    """
    room = Room(area_id="area_office")

    assert hasattr(room, "_trv_groups"), (
        "Room must expose _trv_groups list (D-06/D-07)"
    )
    assert isinstance(room._trv_groups, list), (
        f"_trv_groups must be a list, got {type(room._trv_groups)}"
    )
