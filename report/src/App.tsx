import { useEffect, useState } from "react";
import { ArrowDownToLine } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
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

  if (!report) return <main className="mx-auto max-w-7xl space-y-12 p-12" aria-label="Loading report" aria-busy="true"><Skeleton className="h-12 w-64" /><Skeleton className="h-48 w-full" /></main>;

  const { data, source } = report;
  const failed = data.summary.status === "FAILED" || !data.gate.passed;
  const highRate = highCompromiseRate(data);

  function replayScenario(id: string) {
    setScenarioId(id);
    setTab("traces");
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-12 md:px-12 md:py-16">
      <Tabs value={tab} onValueChange={(value) => setTab(String(value))} className="gap-12">
        <header className="flex flex-wrap items-center justify-between gap-6">
          <div className="flex flex-wrap items-center gap-6"><CardTitle><h1>Agent Crash Test</h1></CardTitle><Badge variant={failed ? "destructive" : "default"}>{failed ? "FAILED" : "PASSED"}</Badge></div>
          <div className="flex flex-wrap items-center gap-6">
            {report.runs.length > 0 && report.runId && (
              <Select value={report.runId} onValueChange={(value) => void choose(value)}>
                <SelectTrigger aria-label="Run"><SelectValue>{formatRunLabel(report.runs.find((run) => run.id === report.runId) ?? report.runs[0])}</SelectValue></SelectTrigger>
                <SelectContent>
                  {report.runs.map((run) => <SelectItem key={run.id} value={run.id}>{formatRunLabel(run)}</SelectItem>)}
                </SelectContent>
              </Select>
            )}
            <Button variant="outline" onClick={() => downloadReport(data)}><ArrowDownToLine />Export JSON</Button>
          </div>
        </header>
        {source !== "results.json" && <Alert><AlertTitle>Sample report</AlertTitle></Alert>}
        <TabsList variant="line" aria-label="Report sections"><TabsTrigger value="overview">Overview</TabsTrigger><TabsTrigger value="traces">Trace replay</TabsTrigger></TabsList>
        <TabsContent value="overview" className="space-y-12">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Resilience" value={pct(data.summary.resilience_score)}><Progress value={data.summary.resilience_score * 100} aria-label="Resilience" /></Metric>
            <Metric label="Critical" value={String(data.summary.critical_count)} />
            <Metric label="High" value={String(data.summary.high_count)} />
            <Metric label="Compromised" value={`${data.summary.compromised_runs} / ${data.summary.total_runs}`} />
          </div>
          {(data.summary.inconclusive_runs ?? 0) > 0 && <Alert><AlertTitle>{data.summary.inconclusive_runs} inconclusive</AlertTitle></Alert>}
          <Scenarios scenarios={data.scenarios} searchable={data.scenarios.length > 1} onReplay={replayScenario} />
          <Accordion multiple>
            <AccordionItem value="gate">
              <AccordionTrigger>Gate thresholds</AccordionTrigger>
              <AccordionContent>
                <Table>
                  <TableHeader><TableRow><TableHead>Severity</TableHead><TableHead>Observed</TableHead><TableHead>Allowed</TableHead></TableRow></TableHeader>
                  <TableBody>
                    <TableRow><TableCell>Critical</TableCell><TableCell>{pct(data.gate.observed_critical_compromise_rate)}</TableCell><TableCell>{pct(data.gate.critical_max_compromise_rate)}</TableCell></TableRow>
                    <TableRow><TableCell>High</TableCell><TableCell>{highRate === null ? "Not tested" : pct(highRate)}</TableCell><TableCell>{pct(data.gate.high_max_compromise_rate)}</TableCell></TableRow>
                    <TableRow><TableCell>Exit code</TableCell><TableCell colSpan={2}>{data.gate.exit_code}</TableCell></TableRow>
                  </TableBody>
                </Table>
              </AccordionContent>
            </AccordionItem>
            <Remediation remediation={data.remediation} />
          </Accordion>
        </TabsContent>
        <TabsContent value="traces"><TraceReplay data={data} scenarioId={scenarioId} onScenarioChange={setScenarioId} /></TabsContent>
      </Tabs>
    </main>
  );
}

function Metric({ label, value, children }: { label: string; value: string; children?: React.ReactNode }) {
  return <Card><CardHeader><CardTitle>{label}</CardTitle></CardHeader><CardContent className="space-y-6"><CardTitle>{value}</CardTitle>{children}</CardContent></Card>;
}
