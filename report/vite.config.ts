import path from "node:path";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import type { IncomingMessage, ServerResponse } from "node:http";
import { fileURLToPath } from "node:url";
import { defineConfig, type ViteDevServer } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";
import { isSafeRunId, summarizeRun } from "./src/lib/runs";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const runsDir = path.resolve(rootDir, "../.punchliner/runs");

function listRuns() {
  if (!existsSync(runsDir)) return [];
  const items = [];
  for (const name of readdirSync(runsDir)) {
    if (!isSafeRunId(name)) continue;
    const file = path.join(runsDir, name, "results.json");
    if (!existsSync(file)) continue;
    try {
      const item = summarizeRun(name, statSync(file).mtimeMs, JSON.parse(readFileSync(file, "utf8")));
      if (item) items.push(item);
    } catch {
      continue;
    }
  }
  items.sort((left, right) => right.mtime - left.mtime);
  return items;
}

function readRun(id: string): string | null {
  if (!isSafeRunId(id)) return null;
  const root = path.resolve(runsDir);
  const file = path.resolve(root, id, "results.json");
  if (!file.startsWith(`${root}${path.sep}`) || !existsSync(file)) return null;
  return readFileSync(file, "utf8");
}

function sendJson(res: ServerResponse, status: number, body: string) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json");
  res.end(body);
}

function serveRuns(server: ViteDevServer) {
  server.middlewares.use((req: IncomingMessage, res: ServerResponse, next: () => void) => {
    const url = req.url?.split("?")[0] ?? "";
    if (url === "/api/runs") {
      sendJson(res, 200, JSON.stringify(listRuns()));
      return;
    }
    const match = /^\/api\/runs\/([^/]+)$/.exec(url);
    if (!match) {
      next();
      return;
    }
    const body = readRun(decodeURIComponent(match[1]));
    if (body === null) {
      sendJson(res, 404, JSON.stringify({ error: "not_found" }));
      return;
    }
    sendJson(res, 200, body);
  });
}

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    { name: "serve-run-artifacts", configureServer: serveRuns },
    {
      name: "embed-report-artifact",
      apply: "build",
      transformIndexHtml() {
        const artifact = path.join(rootDir, "public/results.json");
        if (!existsSync(artifact)) return [];
        // Escape markup so attacker-controlled trace content stays inert JSON.
        const data = JSON.stringify(JSON.parse(readFileSync(artifact, "utf8"))).replaceAll("<", "\\u003c");
        return [{ tag: "script", attrs: { id: "punchliner-results", type: "application/json" }, children: data, injectTo: "head-prepend" }];
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
