// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — helpers to reach native HA UI from the panel.
 *
 * - openMoreInfo: opens HA's more-info dialog (state, history, logbook)
 * - navigateTo: in-app HA navigation (no page reload)
 * - historyPath: HA History page URL filtered on a set of entities
 * - sharesClimateDevice: sensor duplicating a climate entity's temperature
 * - createHistoryCard: native Lovelace history-graph card element
 */

import type { Hass } from "./types.js";

/** Minimal shape of a Lovelace card element. */
export type LovelaceCard = HTMLElement & { hass?: Hass };

interface CardHelpers {
  createCardElement(config: Record<string, unknown>): LovelaceCard;
}

declare global {
  interface Window {
    /** Provided by the HA frontend once Lovelace is loaded. */
    loadCardHelpers?: () => Promise<CardHelpers>;
  }
}

/** Valid HA entity_id: `<domain>.<object_id>`. */
const ENTITY_ID_RE = /^[a-z0-9_]+\.[a-z0-9_]+$/;

/** Keep well-formed ids only (deduplicated, order preserved). */
export function validEntityIds(
  entityIds: Array<string | null | undefined>,
): string[] {
  const ids = entityIds.filter(
    (id): id is string => !!id && ENTITY_ID_RE.test(id),
  );
  return [...new Set(ids)];
}

/**
 * True when `sensorId` belongs to the same device as one of `climateIds`.
 * Such a sensor repeats the climate entity's current_temperature (e.g. a
 * Tado X room), so plotting both draws the same curve twice.
 */
export function sharesClimateDevice(
  sensorId: string | null | undefined,
  climateIds: string[],
  entities: Hass["entities"],
): boolean {
  const device = sensorId ? entities?.[sensorId]?.device_id : null;
  if (!device) return false;
  return climateIds.some((id) => entities?.[id]?.device_id === device);
}

/** Open the HA more-info dialog for entityId (no-op when absent). */
export function openMoreInfo(
  el: HTMLElement,
  entityId: string | null | undefined,
): void {
  if (!entityId) return;
  el.dispatchEvent(
    new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId },
    }),
  );
}

/** Navigate inside the HA frontend without reloading the page. */
export function navigateTo(path: string): void {
  history.pushState(null, "", path);
  window.dispatchEvent(new CustomEvent("location-changed", { composed: true }));
}

/**
 * HA History page path for the given entities, or null when none is valid.
 * Invalid / missing ids are dropped so a stale status never builds a bad URL.
 */
export function historyPath(
  entityIds: Array<string | null | undefined>,
): string | null {
  const ids = validEntityIds(entityIds);
  if (!ids.length) return null;
  return `/history?entity_id=${encodeURIComponent(ids.join(","))}`;
}

/**
 * Build a native history-graph card for entityIds over the last
 * hoursToShow hours. Resolves to null when the HA card helpers are not
 * available (outside HA, e.g. the docs harness) or no id is valid.
 */
export async function createHistoryCard(
  entityIds: Array<string | null | undefined>,
  hoursToShow: number,
): Promise<LovelaceCard | null> {
  const entities = validEntityIds(entityIds);
  if (!entities.length || !window.loadCardHelpers) return null;
  const helpers = await window.loadCardHelpers();
  return helpers.createCardElement({
    type: "history-graph",
    entities,
    hours_to_show: hoursToShow,
  });
}
