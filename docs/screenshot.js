"use strict";

const { chromium } = require("playwright");
const http = require("http");
const fs = require("fs");
const path = require("path");
const { URL } = require("url");
const mdi = require("@mdi/js");

// Extract only the MDI icon paths used by the panel
const MDI_KEYS = [
  "mdiAccount",
  "mdiAccountGroup",
  "mdiAlert",
  "mdiAlertCircle",
  "mdiCheckCircle",
  "mdiChevronDown",
  "mdiContentCopy",
  "mdiContentPaste",
  "mdiHomeFloor0",
  "mdiHomeFloor1",
  "mdiHomeFloor2",
  "mdiHomeFloor3",
  "mdiHomeFloorB",
  "mdiHomeFloorNegative1",
  "mdiHomeOutline",
  "mdiPlus",
  "mdiThermometer",
  "mdiWaterPercent",
];
const mdiPaths = Object.fromEntries(MDI_KEYS.map((k) => [k, mdi[k]]));

const PROJECT_ROOT = path.resolve(__dirname, "..");
const SCREENSHOTS_DIR = process.env.OUTPUT_DIR
  ? path.resolve(process.env.OUTPUT_DIR)
  : path.join(__dirname, "screenshots");
const PORT = 7654;

// ---------------------------------------------------------------------------
// Minimal static file server (serves project root)
// ---------------------------------------------------------------------------
const server = http.createServer((req, res) => {
  let pathname;
  try {
    pathname = new URL(req.url, `http://localhost:${PORT}`).pathname;
  } catch {
    res.writeHead(400);
    res.end();
    return;
  }

  if (pathname === "/" || pathname === "") pathname = "/docs/test-harness.html";

  const filePath = path.resolve(PROJECT_ROOT, pathname.replace(/^\//, ""));
  const normalized = filePath + (filePath.endsWith(path.sep) ? "" : "");
  if (!normalized.startsWith(PROJECT_ROOT)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }
  if (!fs.existsSync(filePath)) {
    res.writeHead(404);
    res.end("Not found");
    console.warn("  404", pathname);
    return;
  }

  const ext = path.extname(filePath);
  const mime = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css",
  };
  res.writeHead(200, {
    "Content-Type": mime[ext] || "text/plain",
    "Cache-Control": "no-store",
  });
  fs.createReadStream(filePath).pipe(res);
});

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });

  await new Promise((resolve) => server.listen(PORT, "127.0.0.1", resolve));
  console.log(`Serving on http://localhost:${PORT}`);

  const browser = await chromium.launch({
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  // Scenario mode: when a generated scenario.json is provided, pin the browser
  // clock + timezone to the scenario's moment so the panel's live computations
  // (zone active period, even/odd week parity, calendar "now") match the
  // coordinator-computed status in the same file. UTC throughout — schedule
  // "HH:MM" values are authored and evaluated in UTC.
  let pinnedTime = null;
  const contextOptions = {};
  if (process.env.SCENARIO_JSON) {
    const scenario = JSON.parse(
      fs.readFileSync(process.env.SCENARIO_JSON, "utf8"),
    );
    pinnedTime = new Date(scenario.now);
    contextOptions.timezoneId = "UTC";
  }

  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  if (pinnedTime) {
    await page.clock.install({ time: pinnedTime });
    await page.clock.pauseAt(pinnedTime);
  }
  await page.setViewportSize({ width: 1280, height: 900 });

  // Capture browser-side logs and errors for debugging
  page.on("console", (msg) => {
    if (msg.type() === "error") console.error("  [browser error]", msg.text());
    else console.log("  [browser]", msg.text());
  });
  page.on("pageerror", (err) => console.error("  [page error]", err.message));

  // Inject MDI path data before any page script runs
  await page.addInitScript(`window.__MDI__ = ${JSON.stringify(mdiPaths)};`);

  // ------------------------------------------------------------------
  // Load harness and wait for panel to be ready
  // ------------------------------------------------------------------
  const HARNESS_PATH = process.env.HARNESS_PATH || "/docs/test-harness.html";
  console.log("Loading harness…");
  await page.goto(`http://localhost:${PORT}${HARNESS_PATH}`);

  // Wait for the tab-bar (means config loaded and panel rendered)
  await page.waitForFunction(
    () => {
      const el = document.querySelector("#mount climate-manager-panel");
      return el?.shadowRoot?.querySelector(".tab-bar") != null;
    },
    undefined,
    { timeout: 20000 },
  );

  await page.waitForTimeout(800); // let Lit settle
  console.log("Panel ready.");

  // ------------------------------------------------------------------
  // Helper: click a tab by its label text
  // ------------------------------------------------------------------
  async function clickTab(label) {
    const found = await page.evaluate((text) => {
      const host = document.querySelector("#mount climate-manager-panel");
      const btns = [...(host?.shadowRoot?.querySelectorAll(".tab-btn") ?? [])];
      const btn = btns.find((b) => b.textContent.trim() === text);
      if (!btn) return false;
      btn.click();
      return true;
    }, label);
    if (!found) throw new Error(`Tab "${label}" not found`);
    await page.waitForTimeout(700);
  }

  // ------------------------------------------------------------------
  // Helper: click first card header inside a tab component (3-level shadow DOM)
  // rooms-tab   → climate-manager-room-card   → .card-header-row
  // persons-tab → climate-manager-person-card → .card-header-row
  // ------------------------------------------------------------------
  async function expandFirstCard(componentTag) {
    await page.evaluate((tag) => {
      const host = document.querySelector("#mount climate-manager-panel");
      const tab = host?.shadowRoot?.querySelector(tag);
      if (!tab) {
        console.warn("[screenshot] tab not found:", tag);
        return;
      }
      const isRooms = tag.includes("rooms");
      const cardTag = isRooms
        ? "climate-manager-room-card"
        : "climate-manager-person-card";
      const card = tab.shadowRoot?.querySelector(cardTag);
      if (!card) {
        console.warn("[screenshot] card not found:", cardTag);
        return;
      }
      const header = card.shadowRoot?.querySelector(".card-header-row");
      if (!header) {
        console.warn("[screenshot] .card-header-row not found in", cardTag);
        return;
      }
      header.click();
    }, componentTag);
    await page.waitForTimeout(900);
  }

  // ------------------------------------------------------------------
  // Screenshots
  // ------------------------------------------------------------------
  const out = (p) => path.join(SCREENSHOTS_DIR, p);

  if (process.env.HARNESS_PATH) {
    // Scenario mode: Overview + Rooms (zone/room layout) + expanded Persons
    // card (D-04). Overview shows the resulting present/absent state and the
    // per-zone tabs; Rooms shows how rooms are grouped into zones; Persons
    // shows the person ↔ room association and schedule.
    // 1. Overview (default tab, already active on load)
    await page.screenshot({ path: out("overview.png") });
    console.log("✓ overview.png");

    // 2. Rooms tab — expanded first room card (rooms grouped by zone)
    await clickTab("Rooms");
    await expandFirstCard("climate-manager-rooms-tab");
    await page.screenshot({ path: out("rooms.png") });
    console.log("✓ rooms.png");

    // 3. Persons tab — expanded first person card
    await clickTab("Persons");
    await expandFirstCard("climate-manager-persons-tab");
    await page.screenshot({ path: out("persons.png") });
    console.log("✓ persons.png");

    // 4. Zone schedule tabs — one screenshot per zone. The weekly time program
    // is what actually bounds heating: a zone cannot heat before its first
    // scheduled Normal/Comfort period or after the last one, even when an
    // assigned person is present. Enumerate every zone tab (all tab buttons
    // that are not the three fixed tabs or the "+" add button) and capture its
    // schedule grid.
    const slugify = (s) =>
      s
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    const zoneLabels = await page.evaluate(() => {
      const host = document.querySelector("#mount climate-manager-panel");
      const btns = [...(host?.shadowRoot?.querySelectorAll(".tab-btn") ?? [])];
      const fixed = new Set(["Overview", "Rooms", "Persons", "+"]);
      return btns
        .map((b) => b.textContent.trim())
        .filter((t) => t && !fixed.has(t));
    });
    for (const label of zoneLabels) {
      await clickTab(label);
      const file = `schedule-${slugify(label)}.png`;
      await page.screenshot({ path: out(file) });
      console.log(`✓ ${file}`);
    }
  } else {
    // Standard mode: existing 6-screenshot sequence (unchanged)

    // 1. Overview (default "global" tab)
    await page.screenshot({ path: out("overview.png") });
    console.log("✓ overview.png");

    // 2. Rooms tab
    await clickTab("Rooms");
    await expandFirstCard("climate-manager-rooms-tab");
    await page.screenshot({ path: out("rooms.png") });
    console.log("✓ rooms.png");

    // 3. Persons tab
    await clickTab("Persons");
    await expandFirstCard("climate-manager-persons-tab");
    await page.screenshot({ path: out("persons.png") });
    console.log("✓ persons.png");

    // 4. Default Zone tab (Home)
    await clickTab("Home");
    await page.screenshot({ path: out("zone.png") });
    console.log("✓ zone.png");

    // 5. Custom zone tab (Upstairs)
    await clickTab("Upstairs");
    await page.screenshot({ path: out("zone-upstairs.png") });
    console.log("✓ zone-upstairs.png");

    // 6. Overview again as global-settings alias (same component)
    await clickTab("Overview");
    await page.screenshot({ path: out("global-settings.png") });
    console.log("✓ global-settings.png");
  }

  // ------------------------------------------------------------------
  await browser.close();
  server.close();
  console.log(`\nDone! Screenshots saved to ${SCREENSHOTS_DIR}`);
}

main().catch((err) => {
  console.error("\nFailed:", err.message);
  server.close();
  process.exit(1);
});
