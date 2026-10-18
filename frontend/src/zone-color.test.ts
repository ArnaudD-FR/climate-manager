// SPDX-License-Identifier: MIT
/**
 * Unit tests for getZoneColor.
 *
 * Run: node --test --experimental-strip-types src/zone-color.test.ts
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { ZONE_COLORS, getZoneColor } from "./types.ts";

const CUSTOM_SLOTS = ZONE_COLORS.length - 1;

/** Deterministic pseudo-UUIDs (no crypto dependency). */
function fakeIds(n: number, seed = 1): string[] {
  const ids: string[] = [];
  let x = seed;
  for (let i = 0; i < n; i++) {
    x = (x * 1103515245 + 12345) >>> 0;
    ids.push(`${x.toString(16).padStart(8, "0")}-zone-${i}`);
  }
  return ids;
}

test("default zone is violet and never reused by custom zones", () => {
  assert.equal(getZoneColor(undefined, []), ZONE_COLORS[0]);
  for (const id of fakeIds(CUSTOM_SLOTS)) {
    assert.notEqual(getZoneColor(id, fakeIds(CUSTOM_SLOTS)), ZONE_COLORS[0]);
  }
});

test("live zones that collided before get distinct colors", () => {
  const ids = [
    "644020d2-4e53-43dc-93a5-643c2819a01c", // Guest
    "f3dd8200-f4f6-49d5-94ba-cf4d9e311623", // Pièces d'eau
  ];
  assert.notEqual(getZoneColor(ids[0], ids), getZoneColor(ids[1], ids));
});

test("adding zones always yields a new color up to the palette size", () => {
  for (let seed = 1; seed <= 50; seed++) {
    const all = fakeIds(CUSTOM_SLOTS, seed);
    for (let n = 1; n <= all.length; n++) {
      const ids = all.slice(0, n);
      const colors = new Set(ids.map((id) => getZoneColor(id, ids)));
      assert.equal(colors.size, n, `seed ${seed}: ${n} zones`);
    }
  }
});

test("existing zones keep their color when a zone is added", () => {
  for (let seed = 1; seed <= 50; seed++) {
    const all = fakeIds(CUSTOM_SLOTS + 2, seed);
    for (let n = 1; n < all.length; n++) {
      const before = all.slice(0, n);
      const after = all.slice(0, n + 1);
      for (const id of before) {
        assert.equal(getZoneColor(id, before), getZoneColor(id, after));
      }
    }
  }
});
