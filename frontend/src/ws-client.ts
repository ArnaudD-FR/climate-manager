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
  ZoneConfig,
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

  /**
   * Create a new custom zone. Resolves with the new zone's id and full ZoneConfig (D-02/D-03 phase 6).
   */
  createZone(name: string): Promise<{ zone_id: string; name: string; mode: string; time_program: DailyProgram }> {
    return this.hass.connection.sendMessagePromise<{ zone_id: string; name: string; mode: string; time_program: DailyProgram }>({
      type: "climate_manager/create_zone",
      name,
    });
  }

  /**
   * Delete a custom zone. Assigned rooms revert to the Default Zone on the backend (Phase 5 EVAL behaviour).
   */
  deleteZone(zoneId: string): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/delete_zone",
      zone_id: zoneId,
    });
  }

  /**
   * Rename a zone. Pass zoneId="default" to rename the Default Zone (D-05 phase 5 sentinel).
   */
  renameZone(zoneId: string, name: string): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/rename_zone",
      zone_id: zoneId,
      name,
    });
  }

  /**
   * Set the heating mode for a zone. Same enum as global_mode (off / time_program / time_program_presences).
   */
  setZoneMode(zoneId: string, mode: string): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/set_zone_mode",
      zone_id: zoneId,
      mode,
    });
  }

  /**
   * Replace the time program for a zone (all 7 day keys required).
   */
  setZoneTimeProgram(zoneId: string, program: DailyProgram): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/set_zone_time_program",
      zone_id: zoneId,
      program,
    });
  }

  /**
   * Reset a zone's time program to a target (verify the backend's accepted target values against websocket.py before passing user input).
   */
  resetZoneTimeProgram(zoneId: string, target: string): Promise<{ success: boolean }> {
    return this.hass.connection.sendMessagePromise<{ success: boolean }>({
      type: "climate_manager/reset_zone_time_program",
      zone_id: zoneId,
      target,
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
