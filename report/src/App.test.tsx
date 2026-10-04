import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import fixture from "../../fixtures/results.failed.json";
import App from "./App";
import type { RunIndex } from "./lib/runs";
import type { Results } from "./types";

function installFetch(data: Results, runs?: RunIndex[]) {
  const index: RunIndex[] = runs ?? [{
    id: "latest",
    mtime: Date.parse("2026-10-03T12:00:00Z"),
    status: String(data.summary.status),
    passed: Boolean(data.gate.passed),
    total_runs: data.summary.total_runs,
    compromised_runs: data.summary.compromised_runs,
  }];
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (String(url).startsWith("/api/runs/")) return { ok: true, json: async () => structuredClone(data) };
    return { ok: true, json: async () => index };
  }));
}

beforeEach(() => {
  installFetch(fixture as Results);
  vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("shows Punchliner with details collapsed", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: "Punchliner" });
  expect(screen.getByRole("heading", { name: "Punches" })).toBeTruthy();
  expect(screen.getByText("8/10")).toBeTruthy();
  expect(screen.getByText("2/10")).toBeTruthy();
  expect(screen.queryByText(fixture.remediation.suggested_remediation)).toBeNull();
});

it("opens the recorded trace for a scenario", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Punchliner" });
  await user.click(screen.getByRole("button", { name: "Replay Unauthorized Refund" }));
  expect(screen.getByRole("tab", { name: "Trace replay" }).getAttribute("aria-selected")).toBe("true");
});

it("shows remediation only on request", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Punchliner" });
  await user.click(screen.getByRole("button", { name: "Remediation" }));
  expect(screen.getByText(fixture.remediation.suggested_remediation)).toBeTruthy();
});
