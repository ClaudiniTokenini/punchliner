import results from "../../fixtures/results.failed.json";
import type { Results, Run, TraceItem } from "./types";

const data = results as Results;

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function formatTraceContent(item: TraceItem): string {
  if (typeof item.content === "string") return item.content;
  if (item.content) return JSON.stringify(item.content, null, 2);
  if (item.arguments) return JSON.stringify(item.arguments, null, 2);
  return "";
}

function TracePlaceholder({ run }: { run: Run | undefined }) {
  if (!run) {
    return (
      <section className="rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5">
        <h2 className="m-0 text-lg font-semibold">Trace Replay</h2>
        <p className="mt-2 text-[var(--muted)]">No compromised run in fixture.</p>
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="m-0 text-lg font-semibold">Trace Replay</h2>
        <span className="text-sm text-[var(--muted)]">
          {run.run_id} · Jev {run.jev_verdict.verdict} (
          {pct(run.jev_verdict.confidence)})
        </span>
      </div>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Sprint 1 placeholder — full interactive replay lands in Sprint 2.
      </p>
      <ol className="mt-4 space-y-3">
        {run.trace.map((item, index) => (
          <li
            key={`${run.run_id}-${index}`}
            className="rounded-lg border border-[var(--line)] bg-white/70 px-4 py-3"
          >
            <div className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">
              {item.role}
              {item.name ? ` · ${item.name}` : ""}
            </div>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-sm text-[var(--ink)]">
              {formatTraceContent(item)}
            </pre>
          </li>
        ))}
      </ol>
    </section>
  );
}

export default function App() {
  const failed = data.summary.status === "FAILED" || !data.gate.passed;
  const compromisedRun =
    data.runs.find((run) => run.verdict === "COMPROMISED") ?? data.runs[0];

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-5 py-8 md:px-8">
      <header className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] px-6 py-6 shadow-sm">
        <p className="m-0 text-sm uppercase tracking-[0.18em] text-[var(--muted)]">
          Agent Crash Test
        </p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="m-0 text-3xl font-semibold tracking-tight md:text-4xl">
              Security Report
            </h1>
            <p className="mt-2 max-w-xl text-[var(--muted)]">
              Fixture-backed report v0. Reads{" "}
              <code className="rounded bg-black/5 px-1.5 py-0.5 text-sm">
                fixtures/results.failed.json
              </code>
              .
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
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Stat
            label="Resilience"
            value={pct(data.summary.resilience_score)}
          />
          <Stat label="Critical" value={String(data.summary.critical_count)} />
          <Stat
            label="Compromised"
            value={`${data.summary.compromised_runs} / ${data.summary.total_runs}`}
          />
        </div>
      </header>

      <section className="rounded-xl border border-[var(--line)] bg-[var(--panel)] p-5">
        <h2 className="m-0 text-lg font-semibold">Scenarios</h2>
        <ul className="mt-4 space-y-3">
          {data.scenarios.map((scenario) => {
            const defendedPct = Math.round(
              (scenario.defended / scenario.total_runs) * 100,
            );
            return (
              <li
                key={scenario.id}
                className="rounded-lg border border-[var(--line)] bg-white/70 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold">{scenario.name}</div>
                  <span className="rounded-full bg-[#ffefd6] px-2.5 py-1 text-xs font-semibold uppercase text-[var(--warn)]">
                    {scenario.severity}
                  </span>
                </div>
                <p className="mt-2 text-sm text-[var(--muted)]">
                  {scenario.compromised} / {scenario.total_runs} compromised ·
                  rate {pct(scenario.compromise_rate)} · allowed{" "}
                  {pct(scenario.threshold)}
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

      <TracePlaceholder run={compromisedRun} />
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-white/60 px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}
