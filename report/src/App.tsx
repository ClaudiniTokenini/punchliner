import { useEffect, useState } from "react";
import { ArrowDownToLine, Check, HandFist, X } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CloseButton, DashBar, DotRow, Window } from "@/components/terminal";
import { Scenarios } from "@/components/scenarios";
import { TraceReplay } from "@/components/trace-replay";
import { Remediation } from "@/components/remediation";
import { downloadReport, fetchRun, highCompromiseRate, loadResults, pct, type LoadedReport } from "@/lib/report";
import { formatRunLabel } from "@/lib/runs";

export default function App() {
  const [report, setReport] = useState<LoadedReport | null>(null);
  const [tab, setTab] = useState("overview");
  const [scenarioId, setScenarioId] = useState("all");

  useEffect(() => {
    let cancelled = false;
    const requested = new URLSearchParams(window.location.search).get("run");
    void loadResults(requested).then((result) => { if (!cancelled) setReport(result); });
    return () => { cancelled = true; };
  }, []);

  async function choose(id: string | null) {
    if (!id || !report || id === report.runId) return;
    try {
      const data = await fetchRun(id);
      const url = new URL(window.location.href);
      url.searchParams.set("run", id);
      window.history.replaceState(null, "", url);
      setScenarioId("all");
      setReport({ ...report, data, source: "results.json", runId: id });
    } catch {
      return;
    }
  }

  if (!report) return <main className="mx-auto max-w-7xl p-12 text-sm text-muted-foreground" aria-label="Loading report" aria-busy="true">&gt; loading report<span className="animate-pulse">_</span></main>;

  const { data, source } = report;
  const failed = data.summary.status === "FAILED" || !data.gate.passed;
  const highRate = highCompromiseRate(data);
  const defendedRuns = data.summary.total_runs - data.summary.compromised_runs - (data.summary.inconclusive_runs ?? 0);

  function replayScenario(id: string) {
    setScenarioId(id);
    setTab("traces");
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-10 md:px-12">
      <Tabs value={tab} onValueChange={(value) => setTab(String(value))} className="gap-0">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-6">
          <div className="flex flex-wrap items-center gap-4">
            <h1 className="inline-flex items-center gap-3 text-2xl font-bold"><HandFist aria-hidden="true" className="size-6 shrink-0" />Punchliner</h1>
            <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 text-[0.625rem] font-bold tracking-widest uppercase ${failed ? "bg-destructive text-background" : "bg-foreground text-background"}`}>
              {failed ? <X className="size-3" /> : <Check className="size-3" />}{failed ? "FAILED" : "PASSED"}
            </span>
            {source !== "results.json" && <span className="text-xs text-muted-foreground">Sample report</span>}
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {report.runs.length > 0 && report.runId && (
              <Select value={report.runId} onValueChange={(value) => void choose(value)}>
                <SelectTrigger aria-label="Run" className="h-10 border-border px-3 text-xs"><SelectValue>{formatRunLabel(report.runs.find((run) => run.id === report.runId) ?? report.runs[0])}</SelectValue></SelectTrigger>
                <SelectContent>
                  {report.runs.map((run) => <SelectItem key={run.id} value={run.id}>{formatRunLabel(run)}</SelectItem>)}
                </SelectContent>
              </Select>
            )}
            <Button variant="secondary" onClick={() => downloadReport(data)}><ArrowDownToLine />Export JSON</Button>
          </div>
        </header>

        <div className="flex items-end justify-between">
          <TabsList aria-label="Report sections" className="h-9 items-end gap-1 bg-transparent p-0 group-data-horizontal/tabs:h-9">
            <TabsTrigger value="overview" className="h-9 border-border px-5 text-[0.75rem] normal-case tracking-normal data-active:bg-muted data-active:text-foreground">Overview</TabsTrigger>
            <TabsTrigger value="traces" className="h-9 border-border px-5 text-[0.75rem] normal-case tracking-normal data-active:bg-muted data-active:text-foreground">
              Trace replay<span aria-hidden="true" className="bg-foreground/10 px-1.5 text-[0.625rem] text-muted-foreground">{data.scenarios.length}</span>
            </TabsTrigger>
          </TabsList>
          <CloseButton />
        </div>

        <TabsContent value="overview" className="space-y-6">
          <Window>
            <div className="grid gap-x-16 gap-y-6 lg:grid-cols-2">
              <DotRow label="Resilience" value={`${defendedRuns}/${data.summary.total_runs}`} critical={failed} />
              <DotRow label="High" value={String(data.summary.high_count)} critical={data.summary.high_count > 0} />
              <DotRow label="Compromised" value={`${data.summary.compromised_runs}/${data.summary.total_runs}`} critical={data.summary.compromised_runs > 0} />
              <DotRow label="Critical" value={String(data.summary.critical_count)} critical={data.summary.critical_count > 0} />
            </div>
            {(data.summary.inconclusive_runs ?? 0) > 0 && <p className="mt-6 text-sm text-muted-foreground">{data.summary.inconclusive_runs} inconclusive</p>}
            <DashBar className="mt-10" />
          </Window>

          <Window>
            <Scenarios scenarios={data.scenarios} searchable={data.scenarios.length > 1} onReplay={replayScenario} />
          </Window>

          <Window>
            <Accordion multiple>
              <AccordionItem value="gate">
                <AccordionTrigger className="tracking-widest uppercase">Gate thresholds</AccordionTrigger>
                <AccordionContent>
                  <Table>
                    <TableHeader><TableRow><TableHead>Severity</TableHead><TableHead>Observed</TableHead><TableHead>Allowed</TableHead></TableRow></TableHeader>
                    <TableBody>
                      <TableRow><TableCell>Critical</TableCell><TableCell className={data.gate.observed_critical_compromise_rate > data.gate.critical_max_compromise_rate ? "text-destructive" : ""}>{pct(data.gate.observed_critical_compromise_rate)}</TableCell><TableCell>{pct(data.gate.critical_max_compromise_rate)}</TableCell></TableRow>
                      <TableRow><TableCell>High</TableCell><TableCell>{highRate === null ? "Not tested" : pct(highRate)}</TableCell><TableCell>{pct(data.gate.high_max_compromise_rate)}</TableCell></TableRow>
                      <TableRow><TableCell>Exit code</TableCell><TableCell colSpan={2} className={data.gate.exit_code ? "text-destructive" : ""}>{data.gate.exit_code}</TableCell></TableRow>
                    </TableBody>
                  </Table>
                </AccordionContent>
              </AccordionItem>
              <Remediation remediation={data.remediation} />
            </Accordion>
          </Window>
        </TabsContent>
        <TabsContent value="traces"><Window><TraceReplay data={data} scenarioId={scenarioId} onScenarioChange={setScenarioId} /></Window></TabsContent>
      </Tabs>
    </main>
  );
}
