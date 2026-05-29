---
quick_id: 260528-417
slug: check-ha-tado-x-compatibility
description: checks if ha-tado-x is compatible
date: 2026-05-28
status: complete
---

# Summary: ha-tado-x Compatibility with Climate Manager

## Verdict: Compatible, with one known limitation

ha-tado-x v1.8.11 exposes standard HA `climate.*` entities. Climate Manager can
discover and control them correctly. One behavioral quirk from ha-tado-x's timer
termination can cause drift in long heating periods (see below).

---

## Compatibility Matrix

| What Climate Manager needs                              | What ha-tado-x provides                                                        | Status           |
| ------------------------------------------------------- | ------------------------------------------------------------------------------ | ---------------- |
| `climate.*` entity_id prefix                            | Standard `ClimateEntity` via HA                                                | ✅               |
| Entity/device assigned to HA area                       | Devices created by ha-tado-x; user assigns to areas                            | ✅               |
| `max_temp ≤ 45°C` (TRV filter)                          | `MAX_TEMP = 30.0`                                                              | ✅               |
| `climate.set_hvac_mode(hvac_mode="heat")`               | Handled → `set_room_temperature(MANUAL)`                                       | ✅               |
| `climate.set_temperature(temperature=N)`                | Handled → `set_room_temperature(TIMER, 1800s)`                                 | ✅ (with caveat) |
| `climate.set_hvac_mode(hvac_mode="off")`                | Handled → `set_room_off(MANUAL)`                                               | ✅               |
| `hvac_modes` includes `"off"` (for `supports_hvac_off`) | `_attr_hvac_modes = [HEAT, OFF, AUTO]`                                         | ✅               |
| Sensor entities in same area (temperature/humidity)     | `sensor.*` entities with device_class=temperature/humidity via Tado X hardware | ✅               |

---

## Known Limitation: 30-minute TIMER termination

**What happens:**  
ha-tado-x's `async_set_temperature` always uses `TERMINATION_TIMER` with
`DEFAULT_TIMER_DURATION = 1800s` (30 min). This means every
`climate.set_temperature` call sets a 30-minute Tado override — after which Tado
resumes its own built-in schedule.

**Climate Manager's D-02 push-on-change logic:**  
Climate Manager skips re-pushing when `last_pushed == desired_temp`. If the
desired temperature hasn't changed across a period transition, Climate Manager
won't re-push — even after Tado's timer expires and the TRV reverts to its own
schedule.

**Concrete scenario:**

1. Climate Manager wants 20°C for a 2-hour block. It pushes 20°C → Tado sets a
   30-min timer.
2. At t=30min, Tado timer expires → Tado reverts to its own schedule (e.g.,
   18°C).
3. At t=31min, Climate Manager evaluates: `desired=20`, `last_pushed=20` → D-02
   skips.
4. **Result:** Room stays at Tado's 18°C for the rest of the period, until the
   next period transition forces a re-push.

**Severity:** Medium. Affects long heating periods (>30 min) where Tado's
built-in schedule differs from Climate Manager's desired setpoint.

**Mitigation (no change required now):**  
If the Tado schedule is set to a flat temperature or disabled, the timer expiry
produces no conflict. In practice, users running Climate Manager as the sole
scheduler should clear or flatten the Tado built-in schedule in the Tado app.

**Future fix candidate:**  
In `coordinator.py/_push_if_changed`: after D-02 skips, add a drift check — if
`reported != desired_temp`, re-push. This would correct timer expiry without
conflating it with D-03 manual overrides (since D-03 hold only activates when
`last` exists AND `reported != last`, which is the same condition). Tracked as a
future improvement.

---

## Double API call per push (minor)

Climate Manager's two-step sequence (`set_hvac_mode("heat")` then
`set_temperature`) results in two Tado cloud API calls per push. The first
(MANUAL termination) is immediately overridden by the second (TIMER). This is
harmless — Climate Manager's push-on-change means pushes are infrequent.
Free-tier API budget (5000 req/day) is not at risk for typical households.

---

## Conclusion

ha-tado-x is compatible with Climate Manager for immediate use. Users should:

1. Assign Tado X devices to HA areas (Climate Manager discovers by area)
2. Optionally flatten the Tado built-in schedule if they want Climate Manager to
   be the sole scheduler and avoid 30-min drift
