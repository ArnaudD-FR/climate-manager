/**
 * Climate Manager Panel — WebSocket client wrapper.
 *
 * Thin typed wrapper over hass.connection that maps every backend
 * climate_manager/* command to a method call.  All mutating methods return
 * the Promise from sendMessagePromise so callers can show success/error toasts.
 */

import type {
  Hass,
  ClimateConfig,
  StatusPayload,
  RoomConfig,
  PersonConfig,
  DailyProgram,
} from "./types.js";

export class WsClient {
  constructor(private readonly hass: Hass) {}

  /** Return the full merged runtime config. */
  getConfig(): Promise<ClimateConfig> {
    return this.hass.connection.sendMessagePromise<ClimateConfig>({
      type: "climate_manager/get_config",
    });
  }

  /** Return the current coordinator status snapshot. */
  getStatus(): Promise<StatusPayload> {
    return this.hass.connection.sendMessagePromise<StatusPayload>({
      type: "climate_manager/get_status",
    });
  }

  /** Set the global heating mode. */
  setGlobalMode(mode: string): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/set_global_mode",
      mode,
    });
  }

  /** Update default temperatures for all four period modes. */
  setPeriodTemperatures(
    temperatures: Record<string, number>,
  ): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/set_period_temperatures",
      temperatures,
    });
  }

  /** Replace the global time program (all 7 day keys required). */
  setTimeProgram(program: DailyProgram): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/set_time_program",
      program,
    });
  }

  /** Reset period temperatures to backend defaults (DEFAULT_PERIOD_TEMPERATURES in const.py). */
  resetPeriodTemperatures(): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/reset_period_temperatures",
    });
  }

  /** Reset global time program to backend defaults (_DEFAULT_DAILY_PROGRAM in const.py). */
  resetTimeProgram(): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/reset_time_program",
    });
  }

  /** Reset a room's time_program to the current global_time_program (deep-copied on the backend). */
  resetRoomToGlobalProgram(roomId: string): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/reset_room_to_global_program",
      room_id: roomId,
    });
  }

  /** Sparse-merge a config delta into a specific room. */
  setRoomConfig(
    roomId: string,
    config: Partial<RoomConfig>,
  ): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/set_room_config",
      room_id: roomId,
      config,
    });
  }

  /** Sparse-merge a config delta into a specific person. */
  setPersonConfig(
    personId: string,
    config: Partial<PersonConfig>,
  ): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/set_person_config",
      person_id: personId,
      config,
    });
  }

  /**
   * Subscribe to coordinator status push events.
   * Returns Promise<unsubscribe fn> — store and call on disconnect.
   */
  subscribeStatus(
    callback: (status: StatusPayload) => void,
  ): Promise<() => void> {
    return this.hass.connection.subscribeMessage<StatusPayload>(callback, {
      type: "climate_manager/subscribe_status",
    });
  }
}
