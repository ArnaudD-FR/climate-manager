// SPDX-License-Identifier: MIT
/**
 * Unit tests for presence-mode helpers (UI-01, UI-02).
 *
 * Run: node --test --experimental-strip-types \
 *        frontend/src/components/presence-mode.test.ts
 *
 * Covers all Phase 10 UI decisions:
 *   UI-02: MODE_LABEL_HA equals "HA home tracking"
 *   UI-01: computeHasDeviceTrackers handles absent/empty/populated arrays
 *   UI-01/D-04: shouldShowHaOption always returns true (option always shown)
 *   UI-01/D-04: haOptionLabel appends ⚠ when no trackers
 *   UI-01/D-05: presenceModeHint returns correct string per mode+trackers
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  MODE_LABEL_HA,
  computeHasDeviceTrackers,
  shouldShowHaOption,
  haOptionLabel,
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

// UI-01: D-04 — ha option always shown regardless of tracker state
test("UI-01: shouldShowHaOption always returns true (no trackers)", () => {
  assert.equal(shouldShowHaOption(false), true);
});

test("UI-01: shouldShowHaOption always returns true (with trackers)", () => {
  assert.equal(shouldShowHaOption(true), true);
});

// UI-01: D-04 — haOptionLabel appends ⚠ when no trackers
test("UI-01: haOptionLabel appends ⚠ when no trackers", () => {
  assert.equal(haOptionLabel(false), `${MODE_LABEL_HA} ⚠`);
});

test("UI-01: haOptionLabel returns plain label when trackers exist", () => {
  assert.equal(haOptionLabel(true), MODE_LABEL_HA);
});

// UI-01/D-05 — presenceModeHint per mode + tracker state
test("UI-01/D-05: presenceModeHint returns stuck-mode warning for ha+no trackers", () => {
  assert.equal(
    presenceModeHint("ha", false),
    "HA home tracking requires a device tracker linked to" +
      " this person in HA.",
  );
});

test("UI-02: presenceModeHint returns ha-with-trackers hint", () => {
  assert.equal(
    presenceModeHint("ha", true),
    "Presence mirrors Home Assistant home/away tracking.",
  );
});

test("presenceModeHint: force_present", () => {
  assert.equal(
    presenceModeHint("force_present", false),
    "Always considered present, regardless of schedule.",
  );
});

test("presenceModeHint: force_absent", () => {
  assert.equal(
    presenceModeHint("force_absent", false),
    "Always absent. Rooms are not heated for presence.",
  );
});

test("presenceModeHint: scheduled (default)", () => {
  assert.equal(
    presenceModeHint("scheduled", false),
    "Presence follows a weekly schedule.",
  );
});
