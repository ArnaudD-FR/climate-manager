// SPDX-License-Identifier: MIT
/**
 * Unit tests for boilerCandidates.
 *
 * Run: npm test (from frontend/)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { boilerCandidates } from "./boiler-candidates.ts";

const state = (attributes: Record<string, unknown> = {}) => ({
  state: "off",
  attributes,
});

const states = {
  "climate.vitodens": state({ friendly_name: "Vitodens", max_temp: 60 }),
  "climate.trv": state({ friendly_name: "Valve", max_temp: 30 }),
  "climate.no_max": state({ friendly_name: "No max" }),
  "switch.relay": state({ friendly_name: "Relay" }),
  "switch.child_lock": state({ friendly_name: "Child lock" }),
  "switch.hidden": state({ friendly_name: "Hidden" }),
  "input_boolean.boiler": state({ friendly_name: "Boiler helper" }),
  "light.kitchen": state({ friendly_name: "Kitchen" }),
};

const entities = {
  "switch.child_lock": {
    entity_id: "switch.child_lock",
    entity_category: "config",
  },
  "switch.hidden": { entity_id: "switch.hidden", hidden: true },
};

test("keeps heating devices, user switches and helpers, grouped", () => {
  assert.deepEqual(
    boilerCandidates(states, entities).map((c) => c.id),
    ["climate.vitodens", "switch.relay", "input_boolean.boiler"],
  );
});

test("the current boiler is always kept", () => {
  const ids = boilerCandidates(states, entities, "climate.trv").map(
    (c) => c.id,
  );
  assert.ok(ids.includes("climate.trv"));
});

test("works without the entity registry", () => {
  assert.equal(boilerCandidates(states, undefined).length, 5);
});

test("the backend list wins over the local rules", () => {
  assert.deepEqual(
    boilerCandidates(states, entities, null, [
      "switch.relay",
      "climate.vitodens",
    ]).map((c) => c.id),
    ["climate.vitodens", "switch.relay"],
  );
});
