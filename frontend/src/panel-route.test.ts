// SPDX-License-Identifier: MIT
/**
 * Unit tests for the panel route helpers.
 *
 * Run: npm test (from frontend/)
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildPath, parseRoute } from "./panel-route.ts";

const P = "/climate_manager";

test("empty path and slash are the Overview", () => {
  for (const path of ["", "/", undefined, null]) {
    assert.deepEqual(parseRoute(path), { tab: "global", cardId: null });
  }
});

test("rooms and persons, with or without a card", () => {
  assert.deepEqual(parseRoute("/rooms"), { tab: "rooms", cardId: null });
  assert.deepEqual(parseRoute("/rooms/salon"), {
    tab: "rooms",
    cardId: "salon",
  });
  assert.deepEqual(parseRoute("/persons/person.alice"), {
    tab: "persons",
    cardId: "person.alice",
  });
});

test("zone tabs", () => {
  assert.deepEqual(parseRoute("/zone/default"), {
    tab: "zone_default",
    cardId: null,
  });
  assert.deepEqual(parseRoute("/zone/abc-123"), {
    tab: "zone_abc-123",
    cardId: null,
  });
});

test("unknown paths read as the Overview", () => {
  for (const path of ["/zone", "/foo", "/rooms/a/b", "/zone/x/y"]) {
    assert.deepEqual(parseRoute(path), { tab: "global", cardId: null }, path);
  }
});

test("buildPath round-trips through parseRoute", () => {
  const views = [
    { tab: "global", cardId: null },
    { tab: "rooms", cardId: null },
    { tab: "rooms", cardId: "salle de bain" },
    { tab: "persons", cardId: "person.alice" },
    { tab: "zone_default", cardId: null },
    { tab: "zone_abc-123", cardId: null },
  ];
  for (const view of views) {
    const path = buildPath(P, view);
    assert.ok(path.startsWith(P));
    assert.deepEqual(parseRoute(path.slice(P.length)), view, path);
  }
});

test("buildPath: Overview is the bare prefix", () => {
  assert.equal(buildPath(P, { tab: "global", cardId: null }), P);
  assert.equal(
    buildPath(P, { tab: "rooms", cardId: "a/b" }),
    `${P}/rooms/a%2Fb`,
  );
});
