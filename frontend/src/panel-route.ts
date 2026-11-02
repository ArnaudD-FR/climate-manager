// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — the panel's view, read from and written to the URL.
 *
 * HA hands the panel a `route` ({prefix: "/climate_manager", path}). The path
 * names the tab and, on Rooms / Persons, the card to expand:
 *
 *   ""  or "/"            Overview          tab "global"
 *   /rooms[/<room_id>]     Rooms             tab "rooms"
 *   /persons[/<person_id>] Persons           tab "persons"
 *   /zone/default          Default Zone      tab "zone_default"
 *   /zone/<zone_id>        custom zone       tab "zone_<zone_id>"
 *
 * Anything else reads as the Overview.
 */

/** Route object HA passes to custom panels. */
export interface PanelRoute {
  prefix: string;
  path: string;
}

/** Tab id plus the card to expand on Rooms / Persons. */
export interface PanelView {
  tab: string;
  cardId: string | null;
}

const OVERVIEW: PanelView = { tab: "global", cardId: null };

/** View named by a route path (the part after the panel prefix). */
export function parseRoute(path: string | null | undefined): PanelView {
  const parts = (path ?? "")
    .split("/")
    .filter(Boolean)
    .map((p) => decodeURIComponent(p));
  const [head, id, ...rest] = parts;
  if (rest.length) return OVERVIEW;
  if (head === "rooms" || head === "persons") {
    return { tab: head, cardId: id ?? null };
  }
  if (head === "zone" && id) {
    return { tab: "zone_" + id, cardId: null };
  }
  return OVERVIEW;
}

/** Full URL path of a view under the panel prefix. */
export function buildPath(prefix: string, view: PanelView): string {
  const { tab, cardId } = view;
  if (tab === "rooms" || tab === "persons") {
    return cardId
      ? `${prefix}/${tab}/${encodeURIComponent(cardId)}`
      : `${prefix}/${tab}`;
  }
  if (tab.startsWith("zone_")) {
    return `${prefix}/zone/${encodeURIComponent(tab.slice(5))}`;
  }
  return prefix;
}
