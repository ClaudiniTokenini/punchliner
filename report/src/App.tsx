import { useEffect, useState } from "react";
import fixture from "../../fixtures/results.failed.json";
import type { Results, Run, TraceItem } from "./types";

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatArgs(args: Record<string, unknown> | undefined): string {
  if (!args) return "";
  return Object.entries(args)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ");
}

function formatToolCall(item: TraceItem): string {
  return `${item.name ?? "tool"}(${formatArgs(item.arguments)})`;
}

function formatTraceBody(item: TraceItem): string {
  if (item.role === "tool_call") return formatToolCall(item);
  if (typeof item.content === "string") return item.content;
  if (item.content) return JSON.stringify(item.content, null, 2);
  if (item.arguments) return formatToolCall(item);
  return "";
}

function isViolation(item: TraceItem, compromised: boolean): boolean {
  return compromised && item.role === "tool_call";
}

// ponytail: prefer engine artifact; fixture only when missing
async function loadResults(): Promise<{ data: Results; source: string }> {
  try {
    const res = await fetch("./results.json", { cache: "no-store" });
    if (res.ok) {
      return { data: (await res.json()) as Results, source: "results.json" };
    }
  } catch {
    /* no artifact yet */
  }
  return {
    data: fixture as Results,
    source: "fixtures/results.failed.json",
  };
}

export default function App() {
  const [data, setData] = useState<Results | null>(null);
  const [source, setSource] = useState("");

  useEffect(() => {
    void loadResults().then(({ data, source }) => {
      setData(data);
      setSource(source);
    });
  }, []);

  if (!data) {
    return (
      <main className="mx-auto max-w-5xl px-5 py-10 text-[var(--muted)]">
        Loading report…
      </main>
    );
  }

  const failed = data.summary.status === "FAILED" || !data.gate.passed;
  const compromisedRun =
    data.runs.find((r) => r.verdict === "COMPROMISED") ?? data.runs[0];

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-5 py-8 md:px-8">
      <Overview data={data} failed={failed} source={source} />
      <VulnerabilityList scenarios={data.scenarios} />
      <TraceReplay run={compromisedRun} />
      <RemediationFooter remediation={data.remediation} />
    </main>
  );
}

function Overview({
  data,
  failed,
  source,
}: {
  data: Results;
  failed: boolean;
  source: string;
}) {
  return (
    <header className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] px-6 py-6 shadow-sm">
      <p className="m-0 text-sm uppercase tracking-[0.18em] text-[var(--muted)]">
        Agent Crash Test
      </p>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="m-0 text-3xl font-semibold tracking-tight md:text-4xl">
            {pct(data.summary.resilience_score)} RESILIENT
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Data source:{" "}
            <code className="rounded bg-black/5 px-1.5 py-0.5">{source}</code>
          </p>
        </div>
        <div
          className={`rounded-full px-4 py-2 text-sm font-semibold ${
            failed
              ? "bg-[#fee4e2] text-[var(--fail)]"
              : "bg-[#dcfae6] text-[var(--pass)]"
          }`}
        >
          {failed ? "BUILD FAILED" : "BUILD PASSED"}
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Status" value={failed ? "FAILED" : "PASSED"} />
        <Stat label="Critical" value={String(data.summary.critical_count)} />
        <Stat label="High" value={String(data.summary.high_count)} />
        <Stat
          label="Compromised"
          value={`${data.summary.compromised_runs} / ${data.summary.total_runs}`}
        />
      </div>

      <div className="mt-4 rounded-xl border border-[var(--line)] bg-white/60 px-4 py-3 text-sm">
        <div className="font-semibold">Gate summary</div>
        <p className="mt-1 m-0 text-[var(--muted)]">
          Critical rate {pct(data.gate.observed_critical_compromise_rate)} ·
          allowed {pct(data.gate.critical_max_compromise_rate)} · High allowed{" "}
          {pct(data.gate.high_max_compromise_rate)} · exit {data.gate.exit_code}
        </p>
      </div>
    </header>
  );
}

function VulnerabilityList({ scenarios }: { scenarios: Results["scenarios"] }) {
  return (
    <section className="rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5">
      <h2 className="m-0 text-lg font-semibold">Vulnerabilities</h2>
      <ul className="mt-4 space-y-3">
        {scenarios.map((scenario) => {
          const defendedPct = Math.round(
            (scenario.defended / Math.max(scenario.total_runs, 1)) * 100,
          );
          return (
            <li
              key={scenario.id}
              className="rounded-lg border border-[var(--line)] bg-white/70 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-lg font-semibold uppercase tracking-tight">
                  {scenario.name}
                </div>
                <span className="rounded-full bg-[#ffefd6] px-2.5 py-1 text-xs font-semibold uppercase text-[var(--warn)]">
                  {scenario.severity}
                </span>
              </div>
              <p className="mt-2 text-sm text-[var(--muted)]">
                {scenario.compromised} / {scenario.total_runs} compromised ·
                Allowed: {pct(scenario.threshold)}
              </p>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#e8e2d7]">
                <div
                  className="h-full rounded-full bg-[var(--accent)]"
                  style={{ width: `${defendedPct}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-[var(--muted)]">
                {defendedPct}% defended
              </p>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function TraceReplay({ run }: { run: Run | undefined }) {
  if (!run) {
    return (
      <section className="rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5">
        <h2 className="m-0 text-lg font-semibold">Trace Replay</h2>
        <p className="mt-2 text-[var(--muted)]">No run to replay.</p>
      </section>
    );
  }

  const compromised = run.verdict === "COMPROMISED";

  return (
    <section className="rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="m-0 text-lg font-semibold">Trace Replay</h2>
        <span className="text-sm text-[var(--muted)]">{run.run_id}</span>
      </div>

      <ol className="mt-4 space-y-0">
        {run.trace.map((item, index) => {
          const violation = isViolation(item, compromised);
          return (
            <li key={`${run.run_id}-${index}`} className="relative pb-4 pl-6">
              {index < run.trace.length - 1 && (
                <span className="absolute left-[0.55rem] top-6 h-[calc(100%-0.5rem)] w-px bg-[var(--line)]" />
              )}
              <span className="absolute left-0 top-2 h-2.5 w-2.5 rounded-full bg-[var(--accent)]" />
              <div
                className={`rounded-lg border px-4 py-3 ${
                  violation
                    ? "border-[var(--fail)] bg-[#fee4e2]"
                    : "border-[var(--line)] bg-white/70"
                }`}
              >
                <div className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">
                  {item.role === "tool_call"
                    ? "Tool Call"
                    : item.role === "tool_result"
                      ? "Tool Result"
                      : item.role}
                </div>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-sm">
                  {formatTraceBody(item)}
                </pre>
                {violation && (
                  <p className="mt-3 mb-0 text-sm font-semibold text-[var(--fail)]">
                    SECURITY CONTRACT VIOLATED
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      <div
        className={`mt-2 rounded-lg border px-4 py-3 ${
          compromised
            ? "border-[var(--fail)] bg-[#fff5f4]"
            : "border-[var(--pass)] bg-[#f3faf6]"
        }`}
      >
        <div className="text-xs font-semibold uppercase tracking-wide">Jev</div>
        <p className="mt-1 mb-0 font-semibold">
          {run.jev_verdict.verdict} · {pct(run.jev_verdict.confidence)} confidence
        </p>
      </div>
    </section>
  );
}

function RemediationFooter({
  remediation,
}: {
  remediation: Results["remediation"];
}) {
  return (
    <section className="rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5">
      <h2 className="m-0 text-lg font-semibold">Remediation</h2>
      <dl className="mt-4 space-y-4 text-sm">
        <div>
          <dt className="font-semibold">Why it failed</dt>
          <dd className="mt-1 m-0 text-[var(--muted)]">{remediation.why_it_failed}</dd>
        </div>
        <div>
          <dt className="font-semibold">Suggested remediation</dt>
          <dd className="mt-1 m-0 text-[var(--muted)]">
            {remediation.suggested_remediation}
          </dd>
        </div>
        <div>
          <dt className="font-semibold">Re-run command</dt>
          <dd className="mt-1 m-0">
            <code className="rounded bg-black/5 px-2 py-1 font-mono text-[var(--ink)]">
              {remediation.rerun_command}
            </code>
          </dd>
        </div>
      </dl>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-white/60 px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}
