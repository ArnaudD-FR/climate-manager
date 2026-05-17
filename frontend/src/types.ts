/**
 * Climate Manager Panel — shared TypeScript types.
 *
 * Types for the WebSocket message contracts, config shapes,
 * and the HA `hass` connection object.
 */

/** A single period entry in a daily program. */
export interface Period {
  /** "HH:MM" start time */
  start: string;
  /** Period mode (schedule bar): frost_protection | reduced | normal | comfort */
  mode?: string;
  /** Presence state (presence bar): present | absent */
  state?: string;
}

/** Seven-day program map keyed by lowercase day abbreviation. */
export type DailyProgram = Record<
  "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun",
  Period[]
>;

/** Per-room configuration stored in ClimateConfig.rooms. */
export interface RoomConfig {
  temperature_sensor?: string;
  humidity_sensor?: string;
  time_program?: DailyProgram;
}

/** Per-person configuration stored in ClimateConfig.persons. */
export interface PersonConfig {
  mode?: string;
  room_ids?: string[];
  schedule?: DailyProgram;
}

/** Full integration configuration returned by climate_manager/get_config. */
export interface ClimateConfig {
  global_mode: string;
  period_temperatures: Record<string, number>;
  global_time_program: DailyProgram;
  rooms: Record<string, RoomConfig>;
  persons: Record<string, PersonConfig>;
}

/** Per-room live status entry inside StatusPayload.rooms_status. */
export interface RoomStatus {
  area_id: string;
  temperature?: number | null;
  humidity?: number | null;
  active_period?: string | null;
}

/** Payload pushed by climate_manager/subscribe_status and returned by get_status. */
export interface StatusPayload {
  global_mode: string;
  active_period: string | null;
  present_persons: string[];
  rooms_status: RoomStatus[];
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
  states: Record<string, { state: string; attributes: Record<string, unknown> }>;
}

// ---------------------------------------------------------------------------
// Period color palettes (D-03 — fixed semantic colors, NOT theme variables)
// ---------------------------------------------------------------------------

/** Colors for 4-mode schedule bars. */
export const PERIOD_COLORS: Record<string, string> = {
  frost_protection: "#1565C0",
  reduced: "#64B5F6",
  normal: "#F57C00",
  comfort: "#D32F2F",
};

/** Colors for 2-mode presence bars. */
export const PRESENCE_COLORS: Record<string, string> = {
  present: "#388E3C",
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
