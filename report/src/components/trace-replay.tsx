import { useEffect, useState } from "react";
import { ChevronDown, ChevronsUpDown } from "lucide-react";
import { JevAssessment } from "@/components/jev-assessment";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatTrace, isCompromised, pct } from "@/lib/report";
import type { Results, TraceItem } from "@/types";

export function TraceReplay({ data, scenarioId, onScenarioChange }: {
  data: Results;
  scenarioId: string;
  onScenarioChange: (id: string) => void;
}) {
  const [selectedId, setSelectedId] = useState("");
  const [verdict, setVerdict] = useState("all");
  const [expandResults, setExpandResults] = useState(false);
  const runs = data.runs.filter((run) =>
    (scenarioId === "all" || run.scenario_id === scenarioId) && (verdict === "all" || run.verdict === verdict),
  );
  const run = runs.find((item) => item.run_id === selectedId) ?? runs.find((item) => isCompromised(item.verdict)) ?? runs[0];
  const scenarioName = data.scenarios.find((item) => item.id === scenarioId)?.name ?? "All scenarios";
  const verdicts = [...new Set(data.runs.map((item) => item.verdict))];

  return (
    <Card>
      <CardHeader>
        <CardTitle><h2>Trace replay</h2></CardTitle>
        <CardAction><Button variant="ghost" size="icon" onClick={() => setExpandResults(!expandResults)} aria-label={expandResults ? "Collapse results" : "Expand results"} aria-pressed={expandResults}><ChevronsUpDown /></Button></CardAction>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex flex-wrap gap-4">
          <Select value={scenarioId} onValueChange={(value) => { onScenarioChange(value ?? "all"); setSelectedId(""); }}>
            <SelectTrigger aria-label="Filter traces by scenario"><SelectValue>{scenarioName}</SelectValue></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All scenarios</SelectItem>
              {data.scenarios.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={verdict} onValueChange={(value) => { setVerdict(value ?? "all"); setSelectedId(""); }}>
            <SelectTrigger aria-label="Filter traces by verdict"><SelectValue>{verdict === "all" ? "All verdicts" : verdict}</SelectValue></SelectTrigger>
            <SelectContent><SelectItem value="all">All verdicts</SelectItem>{verdicts.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}</SelectContent>
          </Select>
          {run && (
            <Select value={run.run_id} onValueChange={(value) => setSelectedId(value ?? "")}>
              <SelectTrigger aria-label="Select run"><SelectValue>{run.run_id}</SelectValue></SelectTrigger>
              <SelectContent>{runs.map((item) => <SelectItem key={item.run_id} value={item.run_id}>{item.run_id}</SelectItem>)}</SelectContent>
            </Select>
          )}
        </div>
        {run ? (
          <Table className="table-fixed">
            <TableHeader><TableRow><TableHead className="w-12">#</TableHead><TableHead className="w-28">Role</TableHead><TableHead>Event</TableHead></TableRow></TableHeader>
            <TableBody>
              {run.trace.map((item, index) => (
                <TableRow key={`${run.run_id}-${index}`}>
                  <TableCell>{index + 1}</TableCell>
                  <TableCell>{item.role.replaceAll("_", " ")}</TableCell>
                  <TableCell><TraceEvent item={item} expanded={expandResults} /></TableCell>
                </TableRow>
              ))}
              {!run.trace.length && <TableRow><TableCell colSpan={3}>No trace events recorded.</TableCell></TableRow>}
            </TableBody>
          </Table>
        ) : <p>No recorded traces.</p>}
        {run && <JevAssessment key={run.run_id} decision={run.jev_verdict} />}
      </CardContent>
      {run && <CardFooter className="flex flex-wrap gap-4"><Badge variant={isCompromised(run.jev_verdict.verdict) ? "destructive" : run.jev_verdict.verdict === "INCONCLUSIVE" ? "secondary" : "default"}>{run.jev_verdict.verdict}</Badge><span>JEV: {pct(run.jev_verdict.confidence)} confidence</span></CardFooter>}
    </Card>
  );
}

function TraceEvent({ item, expanded }: { item: TraceItem; expanded: boolean }) {
  const [open, setOpen] = useState(expanded);
  useEffect(() => setOpen(expanded), [expanded]);
  const content = <pre className="whitespace-pre-wrap break-all">{formatTrace(item)}</pre>;
  if (item.role !== "tool_result") return content;
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger render={<Button variant="ghost" size="sm" />}>{item.name ?? "Tool response"}<ChevronDown /></CollapsibleTrigger>
      <CollapsibleContent>{content}</CollapsibleContent>
    </Collapsible>
  );
}
