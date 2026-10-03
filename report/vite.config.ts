import path from "node:path";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "embed-report-artifact",
      apply: "build",
      transformIndexHtml() {
        const artifact = path.join(rootDir, "public/results.json");
        if (!existsSync(artifact)) return [];
        // Escape markup so attacker-controlled trace content stays inert JSON.
        const data = JSON.stringify(JSON.parse(readFileSync(artifact, "utf8"))).replaceAll("<", "\\u003c");
        return [{ tag: "script", attrs: { id: "crashtest-results", type: "application/json" }, children: data, injectTo: "head-prepend" }];
      },
    },
    viteSingleFile(),
  ],
  resolve: {
    alias: { "@": path.resolve(rootDir, "src") },
  },
  server: {
    port: 5173,
    fs: {
      allow: [rootDir, path.resolve(rootDir, "..")],
    },
  },
});
