// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — helpers to reach native HA UI from the panel.
 *
 * - openMoreInfo: opens HA's more-info dialog (state, history, logbook)
 * - navigateTo: in-app HA navigation (no page reload)
 * - historyPath: HA History page URL filtered on a set of entities
 * - sharesClimateDevice: sensor duplicating a climate entity's temperature
 * - createHistoryCard: native Lovelace history-graph card element
 * - loadFormElements: defines the HA form elements the panel uses
 */

import type { Hass } from "./types.js";

/** Minimal shape of a Lovelace card element. */
export type LovelaceCard = HTMLElement & { hass?: Hass };

interface CardHelpers {
  createCardElement(config: Record<string, unknown>): LovelaceCard;
}

/** A Lovelace card class that can load its editor (and its ha-form). */
interface EditableCard {
  getConfigElement?: () => Promise<HTMLElement>;
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
 * cloud TRV room entity), so plotting both draws the same curve twice.
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
 * hours: show the last hours (start_date); HA's default range otherwise.
 */
export function historyPath(
  entityIds: Array<string | null | undefined>,
  hours?: number,
  now: Date = new Date(),
): string | null {
  const ids = validEntityIds(entityIds);
  if (!ids.length) return null;
  let path = `/history?entity_id=${encodeURIComponent(ids.join(","))}`;
  if (hours) {
    const start = new Date(now.getTime() - hours * 3_600_000);
    path += `&start_date=${encodeURIComponent(start.toISOString())}`;
  }
  return path;
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

/**
 * HA form elements used by the panel, and the selector whose module
 * imports them: ha-selector-datetime brings ha-date-input and
 * ha-time-input, ha-selector-select brings ha-select and ha-button.
 */
const FORM_ELEMENTS: Array<[Record<string, unknown>, string[]]> = [
  [{ datetime: {} }, ["ha-date-input", "ha-time-input"]],
  [{ select: { options: [] } }, ["ha-selector-select", "ha-button"]],
];

let formElements: Promise<boolean> | undefined;

/** Resolves to true once `tag` is defined, false after `ms`. */
function whenDefined(tag: string, ms: number): Promise<boolean> {
  return Promise.race([
    customElements.whenDefined(tag).then(() => true),
    new Promise<boolean>((resolve) => setTimeout(() => resolve(false), ms)),
  ]);
}

async function doLoadFormElements(hass: Hass): Promise<boolean> {
  const tags = FORM_ELEMENTS.flatMap(([, t]) => t);
  if (tags.every((tag) => customElements.get(tag))) return true;
  // HA lazy-loads its form elements. ha-selector comes with ha-form, which
  // a card editor imports; an ha-selector of a given type then imports
  // that selector's module and the elements it renders.
  if (!customElements.get("ha-selector")) {
    if (!window.loadCardHelpers) return false;
    const helpers = await window.loadCardHelpers();
    const card = await helpers.createCardElement({
      type: "button",
      entity: "sun.sun",
    });
    await (card.constructor as EditableCard).getConfigElement?.();
    if (!(await whenDefined("ha-selector", 5000))) return false;
  }
  const selectors = FORM_ELEMENTS.map(([config]) => {
    const el = document.createElement("ha-selector") as HTMLElement & {
      hass: Hass;
      selector: Record<string, unknown>;
    };
    el.hass = hass;
    el.selector = config;
    el.style.display = "none";
    document.body.appendChild(el);
    return el;
  });
  try {
    const defined = await Promise.all(
      tags.map((tag) => whenDefined(tag, 5000)),
    );
    return defined.every(Boolean);
  } finally {
    selectors.forEach((el) => el.remove());
  }
}

/**
 * Make sure the HA form elements the panel uses are defined: date and
 * time inputs (they follow the user profile's date and 12/24-hour
 * formats), the select selector and ha-button. Resolves to false outside
 * HA or if HA no longer ships them; callers then use native elements.
 */
export function loadFormElements(hass: Hass): Promise<boolean> {
  formElements ??= doLoadFormElements(hass).catch(() => false);
  return formElements;
}
