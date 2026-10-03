import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { pct } from "@/lib/report";
import type { JevVerdict } from "@/types";

export function JevAssessment({ decision }: { decision: JevVerdict }) {
  if (!decision.answers) return null;
  const checks = [
    { label: "Prompt compliance", answer: decision.answers.prompt_compliance },
    { label: "Security contract", answer: decision.answers.security_invariant },
  ];

  return (
    <Accordion>
      <AccordionItem value="jev-assessment">
        <AccordionTrigger>JEV assessment</AccordionTrigger>
        <AccordionContent className="space-y-6">
          {decision.model && <p>{decision.model}</p>}
          <Table tabIndex={0} aria-label="JEV assessment checks">
            <TableHeader><TableRow><TableHead>Check</TableHead><TableHead>Verdict</TableHead><TableHead>Confidence</TableHead><TableHead>Compliant</TableHead><TableHead>Violated</TableHead><TableHead>Inconclusive</TableHead></TableRow></TableHeader>
            <TableBody>
              {checks.map(({ label, answer }) => (
                <TableRow key={label}>
                  <TableCell>{label}</TableCell>
                  <TableCell><Badge variant={answer.choice === "VIOLATED" ? "destructive" : answer.choice === "INCONCLUSIVE" ? "secondary" : "default"}>{answer.choice}</Badge></TableCell>
                  <TableCell>{pct(answer.confidence)}</TableCell>
                  <TableCell>{pct(answer.probabilities.COMPLIANT)}</TableCell>
                  <TableCell>{pct(answer.probabilities.VIOLATED)}</TableCell>
                  <TableCell>{pct(answer.probabilities.INCONCLUSIVE)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p>Attack success: {pct(decision.answers.attack_success.noul)}</p>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
