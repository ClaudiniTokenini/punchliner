import { afterEach, expect, it, vi } from "vitest";
import fixture from "../../../fixtures/results.failed.json";
import { loadResults } from "./report";

afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = ""; });

it("falls back to the sample when runs cannot be loaded", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));
  const loaded = await loadResults();
  expect(loaded.source).toBe("fixtures/results.failed.json");
  expect(loaded.data.summary.status).toBe((fixture as { summary: { status: string } }).summary.status);
});
