// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — shared TypeScript types.
 *
 * Types for the WebSocket message contracts, config shapes,
 * and the HA `hass` connection object.
 */

/**
 * A single period entry in a daily program.
 * Discriminated union: exactly one of `mode` (schedule bar) or `state`
 * (presence bar) must be present. TypeScript will flag access to
 * `period.mode` without checking the
 * discriminant, preventing silent undefined rendering (WR-03).
 */
export type Period =
  | { start: string; mode: string; state?: never }
  | { start: string; state: string; mode?: never };

/** Seven-day program map keyed by lowercase day abbreviation. */
export type DailyProgram = Record<
  "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun",
  Period[]
>;

/** Per-room configuration stored in ClimateConfig.rooms. */
export interface RoomConfig {
  /**
   * Room heating mode (D-20). Absent key implies "global".
   * Legal values: "global" | "frost_protection" | "custom"
   */
  room_mode?: "global" | "frost_protection" | "custom";
  time_program?: DailyProgram | null;
  /**
   * Absent = Default Zone member (D-06); UUID string for custom zone (D-07).
   * Sparse model — never written as null.
   */
  zone_id?: string;
}

/** Per-person configuration stored in ClimateConfig.persons. */
export interface PersonConfig {
  mode?: string;
  room_ids?: string[];
  schedule?: DailyProgram;
  // Phase 7: even/odd week scheduling (SCHED-01, SCHED-03)
  schedule_type?: "single" | "even_odd";
  schedule_even?: DailyProgram;
  schedule_odd?: DailyProgram;
}

/** Custom zone configuration stored in ClimateConfig.zones. */
export interface ZoneConfig {
  /** Display name for the zone (user-editable). */
  name: string;
  /** Same enum as global_mode values. */
  mode: string;
  /** Same structure as global_time_program (7-day weekly schedule). */
  time_program: DailyProgram;
}

/** Full integration configuration returned by climate_manager/get_config. */
export interface ClimateConfig {
  global_mode: string;
  period_temperatures: Record<string, number>;
  global_time_program: DailyProgram;
  /** D-03: Default Zone display name. Always present in get_config payloads. */
  default_zone_name: string;
  /** ZONE-01: custom zones keyed by UUID. Empty = all rooms in Default Zone. */
  zones: Record<string, ZoneConfig>;
  rooms: Record<string, RoomConfig>;
  persons: Record<string, PersonConfig>;
  climate_entities: string[];
  /** CALIB-01: global calibration on/off. Absent = false (sparse config). */
  calibration_enabled?: boolean;
  /**
   * CALIB-04: jitter threshold in degrees C. Absent = 0.5 (sparse config).
   * TODO(phase-10): no mutation path exists yet — backend const only.
   * Remove this field or add a setCalibrationThreshold WS command in
   * the phase that exposes threshold configuration to the user.
   */
  calibration_threshold?: number;
}

/** Per-room live status entry inside StatusPayload.rooms_status. */
export interface RoomStatus {
  area_id: string;
  name: string;
  entity_ids?: string[];
  temperature?: number | null;
  humidity?: number | null;
  active_period?: string | null;
  present_person_count: number;
  /** True when at least one entity reports current_temperature (TRV). */
  has_trv?: boolean;
}

/** Payload pushed by subscribe_status and returned by get_status. */
export interface StatusPayload {
  global_mode: string;
  active_period: string | null;
  present_persons: string[];
  rooms_status: RoomStatus[];
}

/** Per-TRV calibration status returned by get_calibration_status. */
export interface TRVCalibrationEntry {
  entity_id: string;
  friendly_name: string;
  supports_calibration: boolean;
  last_applied_delta: number | null;
  last_calibrated_at: string | null;
}

/**
 * Minimal subset of the HA `HomeAssistant` object exposed to a custom panel.
 * HA injects this as the `hass` property on the root panel element.
 */
export interface Hass {
  connection: {
    sendMessagePromise<T = unknown>(msg: Record<string, unknown>): Promise<T>;
    subscribeMessage<T = unknown>(
      callback: (msg: T) => void,
      subscribeMessage: Record<string, unknown>,
      options?: { resubscribe?: boolean },
    ): Promise<() => void>;
  };
  states: Record<
    string,
    { state: string; attributes: Record<string, unknown> }
  >;
  areas: Record<
    string,
    { area_id: string; name: string; floor_id: string | null }
  >;
  floors: Record<
    string,
    { floor_id: string; name: string; level: number; icon?: string | null }
  >;
  callService(
    domain: string,
    service: string,
    serviceData?: Record<string, unknown>,
  ): Promise<void>;
}

// ---------------------------------------------------------------------------
// Period color palettes (D-03 — fixed semantic colors, NOT theme variables)
// ---------------------------------------------------------------------------

/** Colors for 4-mode schedule bars. */
export const PERIOD_COLORS: Record<string, string> = {
  frost_protection: "#1565C0",
  reduced: "#0277BD",
  normal: "#F57C00",
  comfort: "#C62828",
};

/** Colors for 2-mode presence bars. */
export const PRESENCE_COLORS: Record<string, string> = {
  present: "#2E7D32",
  absent: "#9E9E9E",
};

/** Short single-character labels for accessibility (F/R/N/C, P/A). */
export const PERIOD_LABELS: Record<string, string> = {
  frost_protection: "F",
  reduced: "R",
  normal: "N",
  comfort: "C",
  present: "P",
  absent: "A",
};

/** Full display names shown inside period blocks (ellipsized when narrow). */
export const PERIOD_DISPLAY_NAMES: Record<string, string> = {
  frost_protection: "Frost protection",
  reduced: "Reduced",
  normal: "Normal",
  comfort: "Comfort",
  present: "Present",
  absent: "Absent",
};

// ---------------------------------------------------------------------------
// Zone color palette — 5 distinct colors for zone badges
// ---------------------------------------------------------------------------

export interface ZoneColor {
  background: string;
  color: string;
  border: string;
}

/** Index 0 = Default Zone (violet). Indices 1-4 = custom zone palette. */
export const ZONE_COLORS: ZoneColor[] = [
  {
    background: "rgba(124, 58, 237, 0.12)",
    color: "#7c3aed",
    border: "rgba(124, 58, 237, 0.25)",
  }, // violet
  {
    background: "rgba(13, 148, 136, 0.12)",
    color: "#0d9488",
    border: "rgba(13, 148, 136, 0.25)",
  }, // teal
  {
    background: "rgba(217, 119, 6, 0.12)",
    color: "#d97706",
    border: "rgba(217, 119, 6, 0.25)",
  }, // amber
  {
    background: "rgba(2, 132, 199, 0.12)",
    color: "#0284c7",
    border: "rgba(2, 132, 199, 0.25)",
  }, // sky
  {
    background: "rgba(190, 18, 60, 0.12)",
    color: "#be123c",
    border: "rgba(190, 18, 60, 0.25)",
  }, // rose
];

/**
 * Returns a deterministic color for a zone.
 * Default Zone (no zone_id) → violet (index 0).
 * Custom zones → indices 1-4 via UUID hash, never overlapping with Default.
 */
export function getZoneColor(zoneId: string | undefined): ZoneColor {
  if (!zoneId) return ZONE_COLORS[0];
  let hash = 0;
  for (let i = 0; i < zoneId.length; i++) {
    hash = (hash * 31 + zoneId.charCodeAt(i)) >>> 0;
  }
  return ZONE_COLORS[1 + (hash % (ZONE_COLORS.length - 1))];
}
