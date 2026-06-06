// SPDX-License-Identifier: MIT
/**
 * Presence-mode display helpers — pure functions, no Lit dependencies.
 *
 * Extracted to a separate module so `node --experimental-strip-types`
 * can run unit tests directly without needing to parse Lit decorators
 * (legacy `@property` decorators in person-card.ts and persons-tab.ts
 * are incompatible with Node's native strip-types mode).
 *
 * Encodes all Phase 10 UI decisions:
 *   D-01 / UI-02 — "HA home tracking" label for the "ha" presence mode
 *   D-02 / UI-01 — device-tracker detection (absent/empty → false)
 *   D-04 / UI-01 — "ha" option always shown; ⚠ appended when no trackers
 *   D-05 / UI-01 — stuck-mode warning when ha + no trackers
 *
 * Plan 02 wires these helpers into the Lit components.
 */

/** Display label for the "ha" presence mode (D-01, UI-02). */
export const MODE_LABEL_HA = "HA home tracking";

/**
 * Return true if the given device_trackers attribute value represents
 * at least one tracked device (D-02).
 *
 * Handles all shapes that may arrive from hass.states:
 *   - undefined / null  → false
 *   - non-array value   → false
 *   - empty array       → false
 *   - non-empty array   → true
 */
export function computeHasDeviceTrackers(trackers: unknown): boolean {
  return (Array.isArray(trackers) ? trackers.length : 0) > 0;
}

/**
 * Return the display label for the "HA home tracking" select option (D-04).
 * Appends ⚠ when no device trackers are linked so the user sees the issue
 * directly in the dropdown without needing to select the option first.
 */
export function haOptionLabel(hasDeviceTrackers: boolean): string {
  return hasDeviceTrackers ? MODE_LABEL_HA : `${MODE_LABEL_HA} ⚠`;
}

/**
 * Return the schedule-hint paragraph text for the given presence mode
 * and device-tracker availability (D-05, UI-01, UI-02).
 *
 * String values match the Lit template in person-card.ts exactly so
 * Plan 02 can replace the inline ternary with a single call.
 */
export function presenceModeHint(
  mode: string,
  hasDeviceTrackers: boolean,
): string {
  if (mode === "force_present") {
    return "Always considered present, regardless of schedule.";
  }
  if (mode === "force_absent") {
    return "Always absent. Rooms are not heated for presence.";
  }
  if (mode === "ha" && !hasDeviceTrackers) {
    return (
      "HA home tracking requires a device tracker linked to" +
      " this person in HA."
    );
  }
  if (mode === "ha") {
    return "Presence mirrors Home Assistant home/away tracking.";
  }
  return "Presence follows a weekly schedule.";
}
