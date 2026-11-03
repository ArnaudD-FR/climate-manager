// SPDX-License-Identifier: MIT
/**
 * Unit tests for the presence / absence period helpers.
 *
 * Run: npm test (from frontend/)
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import {
  currentAndUpcoming,
  formatPeriodDate,
  formatTime,
  hasPresenceZone,
  isLocalDateTime,
  joinLocal,
  personPeriodBadge,
  selectionToPersonIds,
  splitLocal,
  suggestedSetback,
  toLocalInput,
  useAmPm,
} from "./presence-periods.ts";
import type { ClimateConfig, PresencePeriod } from "./types.ts";

const TRIP: PresencePeriod = {
  id: "trip",
  kind: "absent",
  start: "2026-11-05T08:00",
  end: "2026-11-12T18:30",
};
const STAY: PresencePeriod = {
  id: "stay",
  kind: "present",
  start: "2026-11-20T08:00",
  end: "2026-11-22T20:00",
  person_ids: ["person.a"],
};

function config(modes: string[]): ClimateConfig {
  const [first, ...others] = modes;
  return {
    default_zone: { mode: first },
    zones: Object.fromEntries(others.map((mode, i) => [`z${i}`, { mode }])),
  } as unknown as ClimateConfig;
}

test("hasPresenceZone: default zone or any custom zone", () => {
  assert.equal(hasPresenceZone(config(["time_program"])), false);
  assert.equal(hasPresenceZone(config(["time_program_presences"])), true);
  assert.equal(
    hasPresenceZone(config(["off", "time_program", "time_program_presences"])),
    true,
  );
  assert.equal(hasPresenceZone(undefined), false);
});

test("toLocalInput: zero-padded local minutes", () => {
  assert.equal(
    toLocalInput(new Date(2026, 0, 2, 3, 4, 59)),
    "2026-01-02T03:04",
  );
});

test("currentAndUpcoming: drops ended periods, sorts by start", () => {
  const now = "2026-11-13T09:00";
  assert.deepEqual(
    currentAndUpcoming([STAY, TRIP], "2026-11-08T12:00").map((p) => p.id),
    ["trip", "stay"],
  );
  assert.deepEqual(
    currentAndUpcoming([STAY, TRIP], now).map((p) => p.id),
    ["stay"],
  );
});

test("formatPeriodDate: 24-hour by default, 12-hour on request", () => {
  assert.equal(formatPeriodDate("2026-11-02T08:05"), "2 Nov 08:05");
  assert.equal(formatPeriodDate("2026-11-02T21:47", true), "2 Nov 9:47 PM");
});

test("formatTime: midnight and noon on a 12-hour clock", () => {
  assert.equal(formatTime("00:30", true), "12:30 AM");
  assert.equal(formatTime("12:00", true), "12:00 PM");
  assert.equal(formatTime("00:30", false), "00:30");
});

test("useAmPm: explicit profile format, else the language's", () => {
  assert.equal(useAmPm({ language: "en", time_format: "24" }), false);
  assert.equal(useAmPm({ language: "fr", time_format: "12" }), true);
  assert.equal(useAmPm({ language: "fr", time_format: "language" }), false);
  assert.equal(useAmPm({ language: "en-US", time_format: "language" }), true);
});

test("splitLocal / joinLocal / isLocalDateTime", () => {
  assert.deepEqual(splitLocal("2026-11-07T18:30"), {
    date: "2026-11-07",
    time: "18:30",
  });
  assert.deepEqual(splitLocal(""), { date: "", time: "" });
  assert.equal(joinLocal("2026-11-07", "18:30:00"), "2026-11-07T18:30");
  assert.equal(joinLocal("2026-11-07", ""), "2026-11-07T");
  assert.equal(joinLocal("", ""), "");
  assert.equal(isLocalDateTime("2026-11-07T18:30"), true);
  assert.equal(isLocalDateTime("2026-11-07T"), false);
});

test("personPeriodBadge: active, upcoming, none", () => {
  const periods = [TRIP, STAY];
  assert.equal(
    personPeriodBadge(periods, "person.b", "2026-11-08T12:00"),
    "Away until 12 Nov 18:30",
  );
  assert.equal(
    personPeriodBadge(periods, "person.a", "2026-11-13T12:00"),
    "Home from 20 Nov 08:00",
  );
  assert.equal(
    personPeriodBadge(periods, "person.b", "2026-11-13T12:00"),
    null,
  );
  assert.equal(
    personPeriodBadge(periods, "person.a", "2026-11-12T18:30"),
    "Home from 20 Nov 08:00",
  );
});

test("selectionToPersonIds: everyone selected → undefined", () => {
  const all = ["person.a", "person.b"];
  assert.equal(selectionToPersonIds(["person.b", "person.a"], all), undefined);
  assert.deepEqual(selectionToPersonIds(["person.b"], all), ["person.b"]);
});

test("suggestedSetback: Frost protection beyond 2 days", () => {
  assert.equal(
    suggestedSetback("2026-11-05T08:00", "2026-11-07T08:00"),
    "reduced",
  );
  assert.equal(
    suggestedSetback("2026-11-05T08:00", "2026-11-07T08:01"),
    "frost_protection",
  );
  assert.equal(
    suggestedSetback("2026-02-14T09:00", "2026-02-22T17:00"),
    "frost_protection",
  );
  // A DST change in between does not shift the length.
  assert.equal(
    suggestedSetback("2026-03-27T12:00", "2026-03-29T12:00"),
    "reduced",
  );
  assert.equal(suggestedSetback("2026-11-05T08:00", ""), "reduced");
});
