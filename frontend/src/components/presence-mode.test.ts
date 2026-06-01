// SPDX-License-Identifier: MIT
/**
 * Unit tests for presence-mode helpers (UI-01, UI-02).
 *
 * Run: node --test --experimental-strip-types \
 *        frontend/src/components/presence-mode.test.ts
 *
 * Verifies all five behaviors from the Phase 10 validation architecture:
 *   UI-02: MODE_LABEL_HA equals "HA home tracking"
 *   UI-01: computeHasDeviceTrackers handles absent/empty/populated arrays
 *   UI-01: shouldShowHaOption gates on hasDeviceTrackers boolean
 *   UI-01/D-05: presenceModeHint returns stuck-mode warning when
 *               ha + no trackers
 *   UI-02: presenceModeHint returns ha-with-trackers hint string
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  MODE_LABEL_HA,
  computeHasDeviceTrackers,
  shouldShowHaOption,
  presenceModeHint,
} from "./presence-mode.ts";

// UI-02: D-01 — badge/label text for "ha" mode
test('UI-02: MODE_LABEL_HA equals "HA home tracking"', () => {
  assert.equal(MODE_LABEL_HA, "HA home tracking");
});

// UI-01: D-02 — hasDeviceTrackers treats absent/empty as false
test("UI-01: computeHasDeviceTrackers returns false for undefined", () => {
  assert.equal(computeHasDeviceTrackers(undefined), false);
});

test("UI-01: computeHasDeviceTrackers returns false for empty array", () => {
  assert.equal(computeHasDeviceTrackers([]), false);
});

test("UI-01: computeHasDeviceTrackers returns true for non-empty array", () => {
  assert.equal(computeHasDeviceTrackers(["device_tracker.phone"]), true);
});

// UI-01: D-04 — ha option visible only when device trackers exist
test("UI-01: shouldShowHaOption returns false when no trackers", () => {
  assert.equal(shouldShowHaOption(false), false);
});

test("UI-01: shouldShowHaOption returns true when trackers exist", () => {
  assert.equal(shouldShowHaOption(true), true);
});

// UI-01/D-05 — stuck-mode warning when ha + no trackers
test("UI-01/D-05: presenceModeHint returns stuck-mode warning", () => {
  assert.equal(
    presenceModeHint("ha", false),
    "HA home tracking requires a device tracker linked to" +
      " this person in HA.",
  );
});

// UI-02: presenceModeHint returns correct string for ha+trackers
test("UI-02: presenceModeHint returns ha-with-trackers hint", () => {
  assert.equal(
    presenceModeHint("ha", true),
    "Presence mirrors Home Assistant home/away tracking.",
  );
});
