import { afterEach, describe, expect, it, vi } from "vitest";
import fixture from "../../../fixtures/results.failed.json";
import { formatTrace, highCompromiseRate, loadResults, pct } from "./report";
import type { Results } from "@/types";

afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = ""; });

describe("report data", () => {
  it("formats percentages and tool calls", () => {
    expect(pct(0.8)).toBe("80%");
    expect(formatTrace({ role: "tool_call", name: "issue_refund", arguments: { amount: 499 } })).toBe("issue_refund(amount=499)");
    expect(formatTrace({ role: "agent", content: "Not authorized." })).toBe("Not authorized.");
  });

  it("does not treat an untested severity as a pass", () => {
    expect(highCompromiseRate(fixture as Results)).toBeNull();
    const data = structuredClone(fixture) as Results;
    data.scenarios[0].severity = "high";
    expect(highCompromiseRate(data)).toBe(0.2);
  });

  it("loads the engine artifact", async () => {
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => fixture });
    vi.stubGlobal("fetch", fetch);
    expect(await loadResults()).toEqual({ data: fixture, source: "results.json" });
    expect(fetch).toHaveBeenCalledWith("./results.json", { cache: "no-store" });
  });

  it.each(["missing", "invalid", "network"])("labels the sample fallback for a %s artifact", async (reason) => {
    vi.stubGlobal("fetch", reason === "network"
      ? vi.fn().mockRejectedValue(new Error("Network error"))
      : vi.fn().mockResolvedValue({ ok: reason !== "missing", json: async () => ({}) }));
    expect(await loadResults()).toEqual({ data: fixture, source: "fixtures/results.failed.json" });
  });
});
