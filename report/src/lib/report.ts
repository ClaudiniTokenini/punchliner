import fixture from "../../../fixtures/results.failed.json";
import type { Results, TraceItem } from "@/types";

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

export async function loadResults(): Promise<{ data: Results; source: string }> {
  try {
    const embedded = document.getElementById("crashtest-results")?.textContent;
    if (window.location.protocol === "file:" && embedded) {
      return { data: JSON.parse(embedded) as Results, source: "results.json" };
    }
    const response = await fetch("./results.json", { cache: "no-store" });
    if (!response.ok) throw new Error("No report artifact");
    const data = (await response.json()) as Results;
    if (!data.summary || !data.gate || !Array.isArray(data.scenarios) || !Array.isArray(data.runs) || !data.remediation) {
      throw new Error("Invalid report artifact");
    }
    return { data, source: "results.json" };
  } catch {
    return { data: fixture as Results, source: "fixtures/results.failed.json" };
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
