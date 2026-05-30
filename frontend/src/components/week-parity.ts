// SPDX-License-Identifier: MIT
/**
 * ISO week-parity helpers — pure date computation, no Lit dependencies.
 *
 * Extracted to a separate module so `node --experimental-strip-types`
 * can run unit tests directly without needing to parse Lit decorators
 * (legacy `@property` decorators in person-card.ts are incompatible with
 * Node's native strip-types mode).
 *
 * Backend reference (schedule.py lines 156-157):
 *   week_parity = now.date().isocalendar().week % 2
 *   schedule_key = "schedule_even" if week_parity == 0 else "schedule_odd"
 *
 * Known limitation (WR-03): In years with ISO week 53 (e.g. 2026, 2032),
 * week 53 and the following week 1 are both "odd" — two consecutive odd
 * weeks, one skipped even week. Accepted for v1.
 */

/** Return the ISO 8601 week number for a given date. */
export function getISOWeekNumber(date: Date): number {
  const d = new Date(
    Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()),
  );
  // Thursday is the ISO 8601 pivot day; Sun (0) treated as 7.
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

/** Return "even" or "odd" matching Python isocalendar().week % 2.
 *
 * Even ISO week number → "even"; odd → "odd". Total function: every
 * Date maps to exactly one of the two values, never undefined.
 */
export function getWeekParity(date: Date): "even" | "odd" {
  return getISOWeekNumber(date) % 2 === 0 ? "even" : "odd";
}
