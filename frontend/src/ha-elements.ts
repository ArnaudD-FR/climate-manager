// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — load the HA elements the panel renders.
 *
 * HA lazy-loads most of its UI elements: a custom panel only gets them once
 * some HA module importing them has run. The panel uses HA's own controls
 * wherever HA has one, so it loads them once at startup:
 *
 * - ha-selector comes with ha-form, which a card editor imports (the card
 *   helpers come with the Lovelace panel module, loaded if needed);
 * - each ha-selector type imports its module and the elements it renders
 *   (ha-select, ha-button, ha-input, ha-switch, ha-area-picker, chips…);
 * - ha-tab-group comes with the stack card editor.
 *
 * The docs harness defines stubs for every tag, so the loader returns at
 * once there.
 */

import type { Hass } from "./types.js";

interface CardHelpers {
  createCardElement(config: Record<string, unknown>): HTMLElement;
}

/** A Lovelace card class that can load its editor. */
interface EditableCard {
  getConfigElement?: () => Promise<HTMLElement>;
}

/** Selector types mounted (hidden) to load their modules. */
const SELECTORS: Record<string, unknown>[] = [
  { datetime: {} },
  { select: { options: [] } },
  { number: { mode: "box" } },
  { boolean: {} },
  { area: {} },
  { entity: {} },
  { ui_state_content: {} },
];

/** Every HA element tag the panel renders. */
export const HA_ELEMENTS = [
  "ha-alert",
  "ha-area-picker",
  "ha-assist-chip",
  "ha-button",
  "ha-chip-set",
  "ha-date-input",
  "ha-entity-picker",
  "ha-filter-chip",
  "ha-input",
  "ha-input-chip",
  "ha-selector",
  "ha-selector-entity",
  "ha-selector-number",
  "ha-selector-select",
  "ha-switch",
  "ha-tab-group",
  "ha-tab-group-tab",
  "ha-time-input",
];

/**
 * How long the panel waits for the elements before rendering anyway: HA
 * fetches each module on demand, which takes seconds on a slow link.
 */
const TIMEOUT_MS = 20000;

let loading: Promise<string[]> | undefined;

/** Resolves to true once `tag` is defined, false after `ms`. */
function whenDefined(tag: string, ms: number): Promise<boolean> {
  return Promise.race([
    customElements.whenDefined(tag).then(() => true),
    new Promise<boolean>((resolve) => setTimeout(() => resolve(false), ms)),
  ]);
}

function missing(): string[] {
  return HA_ELEMENTS.filter((tag) => !customElements.get(tag));
}

/** Import a Lovelace card's editor module (and what it imports). */
async function loadCardEditor(
  helpers: CardHelpers,
  config: Record<string, unknown>,
): Promise<void> {
  const card = await helpers.createCardElement(config);
  await (card.constructor as EditableCard).getConfigElement?.();
}

type LoadCardHelpers = () => Promise<CardHelpers>;

/** HA's panel router (an ancestor of the panel) and its lazy routes. */
interface PanelResolver extends HTMLElement {
  routerOptions?: {
    routes?: Record<string, { tag?: string; load?: () => Promise<unknown> }>;
  };
}

/** The nearest ancestor of `el` with tag `tag`, across shadow roots. */
function ancestor(el: Node, tag: string): HTMLElement | null {
  let node: Node | null = el;
  while (node) {
    if (node instanceof HTMLElement && node.localName === tag) return node;
    node = node.parentNode ?? (node as ShadowRoot).host ?? null;
  }
  return null;
}

/**
 * window.loadCardHelpers, defined by the Lovelace panel module: when the
 * panel is opened directly (no dashboard visited yet), load that module
 * through HA's panel router.
 */
async function cardHelpersLoader(
  host: HTMLElement,
): Promise<LoadCardHelpers | undefined> {
  const get = () =>
    (window as { loadCardHelpers?: LoadCardHelpers }).loadCardHelpers;
  if (!get()) {
    const resolver = ancestor(
      host,
      "partial-panel-resolver",
    ) as PanelResolver | null;
    const routes = Object.values(resolver?.routerOptions?.routes ?? {});
    await routes.find((r) => r.tag === "ha-panel-lovelace")?.load?.();
  }
  return get();
}

async function load(hass: Hass, host: HTMLElement): Promise<string[]> {
  if (!missing().length) return [];
  const loadCardHelpers = await cardHelpersLoader(host);
  if (!loadCardHelpers) return missing();
  const helpers = await loadCardHelpers();
  await Promise.all([
    loadCardEditor(helpers, { type: "button", entity: "sun.sun" }),
    loadCardEditor(helpers, { type: "vertical-stack", cards: [] }),
  ]);
  if (await whenDefined("ha-selector", TIMEOUT_MS)) {
    const mounted = SELECTORS.map((selector) => {
      const el = document.createElement("ha-selector") as HTMLElement & {
        hass: Hass;
        selector: Record<string, unknown>;
      };
      el.hass = hass;
      el.selector = selector;
      el.style.display = "none";
      // Inside HA's tree: the date and time inputs read the user's locale
      // from a context <home-assistant> provides; outside it they throw.
      host.appendChild(el);
      return el;
    });
    try {
      await Promise.all(HA_ELEMENTS.map((tag) => whenDefined(tag, TIMEOUT_MS)));
    } finally {
      mounted.forEach((el) => el.remove());
    }
  }
  return missing();
}

/**
 * Load every HA element the panel renders. Resolves to the tags still
 * undefined after the timeout (empty when all are there); never rejects.
 * A late tag still works once defined: the elements upgrade in place.
 */
export function loadHaElements(
  hass: Hass,
  host: HTMLElement,
): Promise<string[]> {
  loading ??= load(hass, host).catch((err) => {
    console.error("Climate Manager: loading HA elements failed", err);
    return missing();
  });
  return loading;
}
