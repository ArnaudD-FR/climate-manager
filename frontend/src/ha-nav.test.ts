// SPDX-License-Identifier: MIT
/**
 * Unit tests for sharesClimateDevice.
 *
 * Run: npm test (from frontend/)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { sharesClimateDevice } from "./ha-nav.ts";

const entities = {
  "sensor.tado_room_temperature": {
    entity_id: "sensor.tado_room_temperature",
    device_id: "tado_room",
  },
  "climate.tado_room": {
    entity_id: "climate.tado_room",
    device_id: "tado_room",
  },
  "climate.matter_valve": {
    entity_id: "climate.matter_valve",
    device_id: "valve",
  },
  "sensor.ambient": { entity_id: "sensor.ambient", device_id: "ambient" },
  "sensor.no_device": { entity_id: "sensor.no_device", device_id: null },
};

test("sensor on the same device as a climate entity is a duplicate", () => {
  assert.equal(
    sharesClimateDevice(
      "sensor.tado_room_temperature",
      ["climate.tado_room"],
      entities,
    ),
    true,
  );
});

test("sensor on another device is kept", () => {
  assert.equal(
    sharesClimateDevice("sensor.ambient", ["climate.tado_room"], entities),
    false,
  );
  assert.equal(
    sharesClimateDevice(
      "sensor.tado_room_temperature",
      ["climate.matter_valve"],
      entities,
    ),
    false,
  );
});

test("missing sensor, device or registry is kept", () => {
  assert.equal(
    sharesClimateDevice(null, ["climate.tado_room"], entities),
    false,
  );
  assert.equal(
    sharesClimateDevice("sensor.no_device", ["climate.tado_room"], entities),
    false,
  );
  assert.equal(
    sharesClimateDevice(
      "sensor.tado_room_temperature",
      ["climate.tado_room"],
      undefined,
    ),
    false,
  );
});
