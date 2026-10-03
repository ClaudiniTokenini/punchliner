import { afterEach, describe, expect, it, vi } from "vitest";
import fixture from "../../../fixtures/results.failed.json";
import { formatTrace, highCompromiseRate, loadResults, pct } from "./report";
import { formatRunLabel, isSafeRunId, pickRunId, summarizeRun, type RunIndex } from "./runs";
import type { Results } from "@/types";

const newest: RunIndex = {
  id: "new",
  mtime: Date.parse("2026-10-03T18:00:00Z"),
  status: "PASSED",
  passed: true,
  total_runs: 1,
  compromised_runs: 0,
};
const older: RunIndex = {
  id: "old",
  mtime: Date.parse("2026-10-03T12:00:00Z"),
  status: "FAILED",
  passed: false,
  total_runs: 10,
  compromised_runs: 2,
};

afterEach(() => { vi.unstubAllGlobals(); document.body.innerHTML = ""; });

function stubRuns(index: RunIndex[], body: unknown = fixture) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (String(url).startsWith("/api/runs/")) return { ok: true, json: async () => body };
    return { ok: true, json: async () => index };
  }));
}

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

  it("summarizes a run and rejects unsafe ids", () => {
    expect(summarizeRun("abc", 10, fixture)).toMatchObject({ id: "abc", mtime: 10, status: "FAILED", passed: false, total_runs: 10, compromised_runs: 2 });
    expect(summarizeRun("abc", 10, {})).toBeNull();
    expect(isSafeRunId("20261003-120000")).toBe(true);
    expect(isSafeRunId("..")).toBe(false);
    expect(isSafeRunId("a/b")).toBe(false);
  });

  it("prefers the requested run over the newest", () => {
    expect(pickRunId([newest, older], "old")).toBe("old");
    expect(pickRunId([newest, older], "missing")).toBe("new");
    expect(pickRunId([], "old")).toBeNull();
    expect(formatRunLabel(older)).toContain("FAILED");
    expect(formatRunLabel(newest)).toContain("PASSED");
  });

  it("loads the requested run from the dev server", async () => {
    stubRuns([newest, older]);
    expect(await loadResults("old")).toEqual({ data: fixture, source: "results.json", runs: [newest, older], runId: "old" });
  });

  it.each(["empty", "invalid", "network"])("labels the sample fallback for a %s run list", async (reason) => {
    vi.stubGlobal("fetch", reason === "network"
      ? vi.fn().mockRejectedValue(new Error("Network error"))
      : vi.fn().mockResolvedValue({ ok: true, json: async () => (reason === "empty" ? [] : {}) }));
    expect(await loadResults()).toEqual({ data: fixture, source: "fixtures/results.failed.json", runs: [], runId: null });
  });
});
