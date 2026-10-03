import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import { AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { Results } from "@/types";

export function Remediation({ remediation }: { remediation: Results["remediation"] }) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  useEffect(() => {
    if (copyState === "idle") return;
    const timeout = window.setTimeout(() => setCopyState("idle"), 2500);
    return () => window.clearTimeout(timeout);
  }, [copyState]);

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(remediation.rerun_command);
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }
  }

  return (
    <AccordionItem value="remediation">
      <AccordionTrigger>Remediation</AccordionTrigger>
      <AccordionContent className="space-y-6">
        <p>{remediation.why_it_failed}</p>
        <p>{remediation.suggested_remediation}</p>
        <div className="flex flex-wrap items-center justify-between gap-4"><code>{remediation.rerun_command}</code><Button variant="outline" onClick={() => void copyCommand()} aria-label="Copy re-run command">{copyState === "copied" ? <Check /> : <Copy />}{copyState === "copied" ? "Copied" : "Copy"}</Button></div>
        {copyState === "error" && <Alert variant="destructive"><AlertTitle>Select and copy the command manually.</AlertTitle></Alert>}
      </AccordionContent>
    </AccordionItem>
  );
}
