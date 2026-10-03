import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import fixture from "../../fixtures/results.failed.json";
import App from "./App";
import type { Results } from "./types";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => structuredClone(fixture) }));
  vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("shows only report data and keeps details collapsed", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: "Agent Crash Test" });
  expect(screen.getAllByText("80%")).toHaveLength(2);
  expect(screen.getAllByText("2 / 10")).toHaveLength(2);
  expect(screen.queryByText(fixture.remediation.suggested_remediation)).toBeNull();
  expect(screen.queryByText("Sample report")).toBeNull();
});

it("opens the recorded trace for a scenario", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Agent Crash Test" });
  await user.click(screen.getByRole("button", { name: "Replay Unauthorized Refund" }));
  expect(screen.getByRole("tab", { name: "Trace replay" }).getAttribute("aria-selected")).toBe("true");
  expect(screen.getByText('issue_refund(order_id="4812", amount=499, currency="PLN")')).toBeTruthy();
  expect(screen.getByText("JEV: 97% confidence")).toBeTruthy();
});

it("shows remediation only on request", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { name: "Agent Crash Test" });
  await user.click(screen.getByRole("button", { name: "Remediation" }));
  expect(screen.getByText(fixture.remediation.suggested_remediation)).toBeTruthy();
  expect(screen.getByText("npm test")).toBeTruthy();
});

it("does not hide inconclusive evaluations", async () => {
  const data = structuredClone(fixture) as Results;
  data.summary.inconclusive_runs = 1;
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => data }));
  render(<App />);
  expect(await screen.findByText("1 inconclusive")).toBeTruthy();
});

it("labels the bundled sample", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("No artifact")));
  render(<App />);
  expect(await screen.findByText("Sample report")).toBeTruthy();
});
