import fixture from "../../../fixtures/results.failed.json";
import { pickRunId, type RunIndex } from "@/lib/runs";
import type { Results, TraceItem } from "@/types";

export type LoadedReport = {
  data: Results;
  source: string;
  runs: RunIndex[];
  runId: string | null;
};

export const pct = (value: number) => `${Math.round(value * 100)}%`;
export const isCompromised = (verdict: string) => verdict === "COMPROMISED";

export function formatTrace(item: TraceItem): string {
  if (item.role === "tool_call") {
    const args = Object.entries(item.arguments ?? {})
      .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
      .join(", ");
    return `${item.name ?? "tool"}(${args})`;
  }
  return typeof item.content === "string"
    ? item.content
    : JSON.stringify(item.content ?? item.arguments ?? {}, null, 2);
}

export function highCompromiseRate(data: Results): number | null {
  const high = data.scenarios.filter((scenario) => scenario.severity === "high");
  const total = high.reduce((sum, scenario) => sum + scenario.total_runs, 0);
  return total ? high.reduce((sum, scenario) => sum + scenario.compromised, 0) / total : null;
}

function isResults(data: unknown): data is Results {
  if (!data || typeof data !== "object") return false;
  const row = data as Results;
  return Boolean(row.summary && row.gate && Array.isArray(row.scenarios) && Array.isArray(row.runs) && row.remediation);
}

function isRunIndex(item: unknown): item is RunIndex {
  if (!item || typeof item !== "object" || !("id" in item)) return false;
  return typeof item.id === "string";
}

export async function fetchRunIndex(): Promise<RunIndex[]> {
  const response = await fetch("/api/runs", { cache: "no-store" });
  if (!response.ok) return [];
  const data: unknown = await response.json();
  if (!Array.isArray(data)) return [];
  return data.filter(isRunIndex);
}

export async function fetchRun(id: string): Promise<Results> {
  const response = await fetch(`/api/runs/${encodeURIComponent(id)}`, { cache: "no-store" });
  if (!response.ok) throw new Error("No report artifact");
  const data: unknown = await response.json();
  if (!isResults(data)) throw new Error("Invalid report artifact");
  return data;
}

export async function loadResults(requested: string | null = null): Promise<LoadedReport> {
  const embedded = document.getElementById("crashtest-results")?.textContent;
  if (window.location.protocol === "file:" && embedded) {
    return { data: JSON.parse(embedded) as Results, source: "results.json", runs: [], runId: null };
  }
  try {
    const runs = await fetchRunIndex();
    const runId = pickRunId(runs, requested);
    if (!runId) throw new Error("No runs");
    const data = await fetchRun(runId);
    return { data, source: "results.json", runs, runId };
  } catch {
    return { data: fixture as Results, source: "fixtures/results.failed.json", runs: [], runId: null };
  }
}

export function downloadReport(data: Results) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "crashtest-results.json";
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
