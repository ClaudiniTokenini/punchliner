import { Fragment, useState } from "react";
import { ArrowUpRight, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DashBar } from "@/components/terminal";
import type { Scenario } from "@/types";

const severityClass: Record<string, string> = { critical: "text-destructive", high: "text-foreground" };

export function Scenarios({ scenarios, searchable = false, onReplay }: {
  scenarios: Scenario[];
  searchable?: boolean;
  onReplay: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const visible = scenarios.filter((scenario) =>
    (severity === "all" || scenario.severity === severity) &&
    `${scenario.name} ${scenario.attack_objective}`.toLowerCase().includes(query.toLowerCase()),
  );
  const severities = [...new Set(scenarios.map((scenario) => scenario.severity))];
  const index = (position: number) => String(position + 1).padStart(2, "0");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-6">
        <h2 className="text-3xl font-bold">Punches</h2>
        {searchable && (
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="relative w-56 before:absolute before:top-1/2 before:left-2 before:-translate-y-1/2 before:text-muted-foreground before:content-['>']">
              <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter directory..." aria-label="Search scenarios" className="h-8 border-border pr-2 pl-6 text-xs md:text-xs" />
            </div>
            <Select value={severity} onValueChange={(value) => setSeverity(value ?? "all")}>
              <SelectTrigger size="sm" aria-label="Filter by severity" className="h-8 border-border px-3 text-xs"><SelectValue>{severity === "all" ? "All severities" : severity}</SelectValue></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All severities</SelectItem>
                {severities.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>
      <DashBar />
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-12 text-[0.625rem]">#</TableHead>
            <TableHead className="text-[0.625rem]">Scenario / Target</TableHead>
            <TableHead className="text-[0.625rem]">Severity</TableHead>
            <TableHead className="text-[0.625rem]">Defended</TableHead>
            <TableHead className="text-[0.625rem]">Compromised</TableHead>
            <TableHead className="text-right text-[0.625rem]">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {visible.map((scenario, position) => (
            <Fragment key={scenario.id}>
              <TableRow className="h-14">
                <TableCell className="text-xs text-muted-foreground">{index(position)}</TableCell>
                <TableCell>
                  <button type="button" className="inline-flex items-center gap-2 text-xs font-bold tracking-wider uppercase hover:text-muted-foreground" onClick={() => setExpanded(expanded === scenario.id ? null : scenario.id)} aria-expanded={expanded === scenario.id} aria-controls={`scenario-${scenario.id}`}>
                    {scenario.name}<ChevronDown className="size-3 text-muted-foreground" />
                  </button>
                </TableCell>
                <TableCell className={`text-[0.625rem] font-bold tracking-widest uppercase ${severityClass[scenario.severity] ?? "text-muted-foreground"}`}>{scenario.severity}</TableCell>
                <TableCell className="text-sm font-bold">{scenario.defended} / {scenario.total_runs}</TableCell>
                <TableCell className={`text-sm ${scenario.compromised ? "font-bold text-destructive" : "text-muted-foreground"}`}>{scenario.compromised} / {scenario.total_runs}</TableCell>
                <TableCell className="text-right"><Button variant="outline" size="xs" onClick={() => onReplay(scenario.id)} aria-label={`Replay ${scenario.name}`}><ArrowUpRight />Replay</Button></TableCell>
              </TableRow>
              {expanded === scenario.id && (
                <TableRow id={`scenario-${scenario.id}`} className="hover:bg-transparent"><TableCell colSpan={6} className="whitespace-normal">
                  <dl className="grid gap-3 py-2 text-sm text-muted-foreground md:grid-cols-[10rem_1fr]">
                    <dt className="text-[0.625rem] font-bold tracking-widest text-foreground uppercase">Attack objective</dt><dd>{scenario.attack_objective}</dd>
                    <dt className="text-[0.625rem] font-bold tracking-widest text-foreground uppercase">Security invariant</dt><dd>{scenario.security_invariant}</dd>
                    <dt className="text-[0.625rem] font-bold tracking-widest text-foreground uppercase">Remediation</dt><dd>{scenario.remediation}</dd>
                  </dl>
                </TableCell></TableRow>
              )}
            </Fragment>
          ))}
          {!visible.length && <TableRow><TableCell colSpan={6} className="text-muted-foreground">{scenarios.length ? "No matching scenarios." : "No scenarios recorded."}</TableCell></TableRow>}
        </TableBody>
      </Table>
      <DashBar />
      {searchable && (query || severity !== "all") && <Button variant="outline" size="xs" onClick={() => { setQuery(""); setSeverity("all"); }}>Clear filters</Button>}
    </div>
  );
}
