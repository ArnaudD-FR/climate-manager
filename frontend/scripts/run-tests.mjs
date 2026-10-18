// SPDX-License-Identifier: MIT
/**
 * Run the panel unit tests (src/**\/*.test.ts) with node:test.
 *
 * Node builds without TypeScript support reject --experimental-strip-types,
 * so each test file is bundled to ESM with esbuild first, then the bundles
 * are run by `node --test`. Extra arguments are passed to node --test
 * (e.g. `npm test -- --test-name-pattern=parity`).
 */
import { spawnSync } from "node:child_process";
import { readdirSync, rmSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const srcDir = join(root, "src");
const outDir = join(root, "node_modules", ".cache", "panel-tests");

const entryPoints = readdirSync(srcDir, { recursive: true })
  .filter((file) => file.endsWith(".test.ts"))
  .map((file) => join(srcDir, file))
  .sort();

if (entryPoints.length === 0) {
  console.error("No test files found under src/");
  process.exit(1);
}

rmSync(outDir, { recursive: true, force: true });
await build({
  entryPoints,
  outdir: outDir,
  outbase: srcDir,
  outExtension: { ".js": ".mjs" },
  bundle: true,
  platform: "node",
  format: "esm",
  sourcemap: "inline",
  logLevel: "warning",
});

const bundles = entryPoints.map((file) =>
  join(outDir, relative(srcDir, file).replace(/\.ts$/, ".mjs")),
);
const result = spawnSync(
  process.execPath,
  ["--enable-source-maps", "--test", ...process.argv.slice(2), ...bundles],
  { stdio: "inherit" },
);
process.exit(result.status ?? 1);
