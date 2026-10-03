export type RunIndex = {
  id: string;
  mtime: number;
  status: string;
  passed: boolean;
  total_runs: number;
  compromised_runs: number;
};

const RUN_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$/;

export function isSafeRunId(id: string): boolean {
  return RUN_ID.test(id);
}

export function summarizeRun(id: string, mtime: number, data: unknown): RunIndex | null {
  if (!data || typeof data !== "object") return null;
  const row = data as {
    summary?: { status?: unknown; total_runs?: unknown; compromised_runs?: unknown };
    gate?: { passed?: unknown };
  };
  if (!row.summary || typeof row.summary.status !== "string" || !row.gate) return null;
  return {
    id,
    mtime,
    status: row.summary.status,
    passed: Boolean(row.gate.passed),
    total_runs: Number(row.summary.total_runs ?? 0),
    compromised_runs: Number(row.summary.compromised_runs ?? 0),
  };
}

export function pickRunId(runs: RunIndex[], requested: string | null): string | null {
  if (!runs.length) return null;
  if (requested && runs.some((run) => run.id === requested)) return requested;
  return runs[0].id;
}

export function formatRunLabel(run: RunIndex): string {
  const date = new Date(run.mtime);
  const pad = (value: number) => String(value).padStart(2, "0");
  const when = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  return `${when} ${run.passed ? "PASSED" : "FAILED"}`;
}
