import { Fragment, useState } from "react";
import { ArrowUpRight, ChevronDown } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { pct } from "@/lib/report";
import type { Scenario } from "@/types";

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

  return (
    <Card>
      <CardHeader><CardTitle><h2>Scenarios</h2></CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {searchable && (
          <div className="flex flex-wrap items-center gap-4">
            <div className="min-w-0 flex-1"><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search scenarios" aria-label="Search scenarios" /></div>
            <Select value={severity} onValueChange={(value) => setSeverity(value ?? "all")}>
              <SelectTrigger aria-label="Filter by severity"><SelectValue>{severity === "all" ? "All severities" : severity}</SelectValue></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All severities</SelectItem>
                {severities.map((value) => <SelectItem key={value} value={value}>{value}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}
        <Table>
          <TableHeader><TableRow><TableHead>Scenario</TableHead><TableHead>Severity</TableHead><TableHead>Compromised</TableHead><TableHead>Defended</TableHead><TableHead>Trace</TableHead></TableRow></TableHeader>
          <TableBody>
            {visible.map((scenario) => (
              <Fragment key={scenario.id}>
                <TableRow>
                  <TableCell><Button variant="ghost" size="sm" onClick={() => setExpanded(expanded === scenario.id ? null : scenario.id)} aria-expanded={expanded === scenario.id} aria-controls={`scenario-${scenario.id}`}>{scenario.name}<ChevronDown /></Button></TableCell>
                  <TableCell><Badge variant={scenario.severity === "critical" || scenario.severity === "high" ? "destructive" : "secondary"}>{scenario.severity}</Badge></TableCell>
                  <TableCell>{scenario.compromised} / {scenario.total_runs}</TableCell>
                  <TableCell>{pct(scenario.total_runs ? scenario.defended / scenario.total_runs : 0)}</TableCell>
                  <TableCell><Button variant="outline" size="sm" onClick={() => onReplay(scenario.id)} aria-label={`Replay ${scenario.name}`}><ArrowUpRight />Replay</Button></TableCell>
                </TableRow>
                {expanded === scenario.id && (
                  <TableRow id={`scenario-${scenario.id}`}><TableCell colSpan={5} className="whitespace-normal">
                    <div className="space-y-4">
                      <p>{scenario.attack_objective}</p>
                      <Alert><AlertTitle>Security invariant</AlertTitle><AlertDescription>{scenario.security_invariant}</AlertDescription></Alert>
                      <p>{scenario.remediation}</p>
                    </div>
                  </TableCell></TableRow>
                )}
              </Fragment>
            ))}
            {!visible.length && <TableRow><TableCell colSpan={5}>{scenarios.length ? "No matching scenarios." : "No scenarios recorded."}</TableCell></TableRow>}
          </TableBody>
        </Table>
        {searchable && (query || severity !== "all") && <Button variant="outline" onClick={() => { setQuery(""); setSeverity("all"); }}>Clear filters</Button>}
      </CardContent>
    </Card>
  );
}
