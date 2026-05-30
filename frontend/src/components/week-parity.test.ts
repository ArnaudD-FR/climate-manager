// SPDX-License-Identifier: MIT
/**
 * Unit tests for getISOWeekNumber and getWeekParity helpers.
 *
 * Run: node --test --experimental-strip-types \
 *        src/components/week-parity.test.ts
 *
 * Verifies that JS parity matches Python isocalendar().week % 2 logic.
 * Backend reference: schedule.py lines 156-157
 *   week_parity = now.date().isocalendar().week % 2
 *   schedule_key = "schedule_even" if week_parity == 0 else "schedule_odd"
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { getISOWeekNumber, getWeekParity } from "./week-parity.ts";

test("getISOWeekNumber: 2026-05-25 is ISO week 22 (even)", () => {
  assert.equal(getISOWeekNumber(new Date("2026-05-25")), 22);
});

test("getWeekParity: 2026-05-25 is even (week 22 % 2 === 0)", () => {
  assert.equal(getWeekParity(new Date("2026-05-25")), "even");
});

test("getWeekParity: 2026-06-01 is odd (week 23 % 2 === 1)", () => {
  assert.equal(getWeekParity(new Date("2026-06-01")), "odd");
});

test("getISOWeekNumber: 2027-01-04 is ISO week 1 (odd)", () => {
  assert.equal(getISOWeekNumber(new Date("2027-01-04")), 1);
});

test("getWeekParity: 2027-01-04 is odd (week 1 % 2 === 1)", () => {
  assert.equal(getWeekParity(new Date("2027-01-04")), "odd");
});

test("getISOWeekNumber: 2026-12-28 is ISO week 53 (WR-03 boundary)", () => {
  assert.equal(getISOWeekNumber(new Date("2026-12-28")), 53);
});

test("getWeekParity: 2026-12-28 is odd (week 53 % 2 === 1, WR-03)", () => {
  assert.equal(getWeekParity(new Date("2026-12-28")), "odd");
});

test("getWeekParity is total: never returns undefined for any Date", () => {
  const dates = [
    new Date("2020-01-01"),
    new Date("2020-12-31"),
    new Date("2024-02-29"), // leap day
    new Date("2026-01-01"),
    new Date("2026-12-31"),
  ];
  for (const d of dates) {
    const result = getWeekParity(d);
    assert.ok(
      result === "even" || result === "odd",
      `Expected "even" or "odd" for ${d.toISOString()}, got ${result}`,
    );
  }
});
