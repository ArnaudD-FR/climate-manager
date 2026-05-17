import { defineConfig, type Plugin } from "vite";
import { resolve } from "path";
import { writeFileSync } from "fs";

/**
 * Post-build plugin: recreate www/.gitignore after emptyOutDir deletes it.
 * emptyOutDir: true cleans all files including .gitignore on each build;
 * this plugin restores it so git keeps ignoring the generated panel.js.
 */
function restoreWwwGitignore(): Plugin {
  return {
    name: "restore-www-gitignore",
    closeBundle() {
      const gitignorePath = resolve(
        __dirname,
        "../custom_components/climate_manager/www/.gitignore",
      );
      writeFileSync(
        gitignorePath,
        "# Generated build artifacts — do not commit.\npanel.js\n*.map\n",
        "utf8",
      );
    },
  };
}

export default defineConfig({
  plugins: [restoreWwwGitignore()],
  build: {
    lib: {
      entry: resolve(__dirname, "src/main.ts"),
      name: "ClimateManagerPanel",
      fileName: "panel",
      formats: ["es"],
    },
    outDir: "../custom_components/climate_manager/www",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
        entryFileNames: "panel.js",
      },
    },
    cssCodeSplit: false,
  },
});
