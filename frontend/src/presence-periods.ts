// SPDX-License-Identifier: MIT
/**
 * Pure helpers for the dated presence / absence periods.
 *
 * Period bounds are local "YYYY-MM-DDTHH:MM" strings (HA time zone, the
 * browser's in practice); in that fixed format string order is time
 * order, so the helpers compare strings and never build Date objects
 * from the bounds.
 */

import type { ClimateConfig, Hass, PresencePeriod } from "./types.js";

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** True if at least one zone is in Time program & presences. */
export function hasPresenceZone(config: ClimateConfig | undefined): boolean {
  if (!config) return false;
  const zones = [config.default_zone, ...Object.values(config.zones ?? {})];
  return zones.some((zone) => zone?.mode === "time_program_presences");
}

/** A Date as a local "YYYY-MM-DDTHH:MM" string (datetime-local value). */
export function toLocalInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-` +
    `${pad(date.getDate())}T${pad(date.getHours())}:` +
    `${pad(date.getMinutes())}`
  );
}

/** True if the period applies to the person (no person_ids = everyone). */
export function covers(period: PresencePeriod, personId: string): boolean {
  return !period.person_ids || period.person_ids.includes(personId);
}

/** Periods not ended at `now`, by start. */
export function currentAndUpcoming(
  periods: PresencePeriod[] | undefined,
  now: string,
): PresencePeriod[] {
  return (periods ?? [])
    .filter((p) => p.end > now)
    .sort((a, b) => a.start.localeCompare(b.start));
}

/**
 * True when times are shown on a 12-hour clock, per the HA profile's time
 * format; "language" and "system" follow that locale's convention (same
 * test as HA's own useAmPm).
 */
export function useAmPm(locale: Hass["locale"] | undefined): boolean {
  const format = locale?.time_format ?? "language";
  if (format === "12") return true;
  if (format === "24") return false;
  const language = format === "language" ? locale?.language : undefined;
  const test = new Date(2023, 0, 1, 22, 0, 0).toLocaleString(language);
  return test.includes("10");
}

/** "HH:MM" on the chosen clock: "21:05" or "9:05 PM". */
export function formatTime(time: string, amPm: boolean): string {
  if (!amPm) return time;
  const [hour, minute] = time.split(":").map(Number);
  const suffix = hour < 12 ? "AM" : "PM";
  return `${hour % 12 || 12}:${String(minute).padStart(2, "0")} ${suffix}`;
}

/** "2026-11-12T18:30" → "12 Nov 18:30" (or "12 Nov 6:30 PM"). */
export function formatPeriodDate(value: string, amPm = false): string {
  const [date, time] = value.split("T");
  const [, month, day] = date.split("-");
  const when = formatTime(time, amPm);
  return `${Number(day)} ${MONTHS[Number(month) - 1]} ${when}`;
}

/** "YYYY-MM-DDTHH:MM" → its date and "HH:MM" ("" parts when empty). */
export function splitLocal(value: string): { date: string; time: string } {
  const [date = "", time = ""] = value.split("T");
  return { date, time };
}

/**
 * Join a date and a time ("HH:MM" or "HH:MM:SS", as ha-time-input sends)
 * into "YYYY-MM-DDTHH:MM". A part may still be empty while editing
 * ("2026-11-07T"); isLocalDateTime tells when both are set.
 */
export function joinLocal(date: string, time: string): string {
  if (!date && !time) return "";
  return `${date}T${time.slice(0, 5)}`;
}

/** True for a complete local "YYYY-MM-DDTHH:MM". */
export function isLocalDateTime(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value);
}

/**
 * Badge text for a person: the period covering them now ("Away until …",
 * "Home until …"), else the next one ("Away from …"), else null.
 */
export function personPeriodBadge(
  periods: PresencePeriod[] | undefined,
  personId: string,
  now: string,
  amPm = false,
): string | null {
  const own = currentAndUpcoming(periods, now).filter((p) =>
    covers(p, personId),
  );
  const period = own[0];
  if (!period) return null;
  const label = period.kind === "absent" ? "Away" : "Home";
  if (period.start <= now) {
    return `${label} until ${formatPeriodDate(period.end, amPm)}`;
  }
  return `${label} from ${formatPeriodDate(period.start, amPm)}`;
}

/**
 * person_ids to send: undefined (everyone) when every person is selected,
 * so persons added later are covered too.
 */
export function selectionToPersonIds(
  selected: string[],
  allPersonIds: string[],
): string[] | undefined {
  const everyone = allPersonIds.every((id) => selected.includes(id));
  return everyone ? undefined : [...selected].sort();
}
