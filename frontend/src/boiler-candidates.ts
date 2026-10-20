// SPDX-License-Identifier: MIT
/**
 * Climate Manager Panel — boiler entity candidates.
 *
 * The backend list (get_config boiler_candidates, built with the device
 * registry) is used when present. Without it, a local fallback keeps:
 * - climate: heating devices only (max_temp > 45 °C — the backend
 *   is_trv_entity threshold), so radiator valves are left out;
 * - switch / input_boolean: user-facing entities only (no config or
 *   diagnostic entity, not hidden, not created by Climate Manager).
 * The current boiler is always kept, whatever these rules say.
 */

import type { Hass } from "./types.js";

/** Same threshold as trv.py _TRV_MAX_TEMP_THRESHOLD. */
const TRV_MAX_TEMP = 45;

export type BoilerGroup = "climate" | "switch" | "input_boolean";

export interface BoilerCandidate {
  id: string;
  name: string;
  group: BoilerGroup;
}

/** Display order and labels of the candidate groups. */
export const BOILER_GROUPS: [BoilerGroup, string][] = [
  ["climate", "Heating devices"],
  ["switch", "Switches"],
  ["input_boolean", "Helpers"],
];

function isCandidate(
  id: string,
  attributes: Record<string, unknown>,
  entry: NonNullable<Hass["entities"]>[string] | undefined,
): boolean {
  if (entry?.hidden || entry?.entity_category) return false;
  if (entry?.platform === "climate_manager") return false;
  if (id.startsWith("climate.")) {
    const maxTemp = Number(attributes.max_temp);
    return Number.isFinite(maxTemp) && maxTemp > TRV_MAX_TEMP;
  }
  return true;
}

/** Candidate boiler entities, grouped then sorted by name. */
export function boilerCandidates(
  states: Hass["states"],
  entities: Hass["entities"],
  current?: string | null,
  allowed?: string[],
): BoilerCandidate[] {
  const order = BOILER_GROUPS.map(([group]) => group);
  const allowedSet = allowed ? new Set(allowed) : null;
  return Object.entries(states)
    .filter(([id]) => order.includes(id.split(".")[0] as BoilerGroup))
    .filter(
      ([id, st]) =>
        id === current ||
        (allowedSet
          ? allowedSet.has(id)
          : isCandidate(id, st.attributes, entities?.[id])),
    )
    .map(([id, st]) => ({
      id,
      name: String(st.attributes.friendly_name ?? id),
      group: id.split(".")[0] as BoilerGroup,
    }))
    .sort(
      (a, b) =>
        order.indexOf(a.group) - order.indexOf(b.group) ||
        a.name.localeCompare(b.name),
    );
}
