export type TraceItem = {
  role: string;
  content?: string | Record<string, unknown>;
  name?: string;
  arguments?: Record<string, unknown>;
};

export type JevChoiceAnswer = {
  type: "choice";
  choice: "COMPLIANT" | "VIOLATED" | "INCONCLUSIVE";
  confidence: number;
  probabilities: Record<JevChoiceAnswer["choice"], number>;
};

export type JevVerdict = {
  verdict: string;
  confidence: number;
  provider?: "jev";
  model?: string;
  answers?: {
    prompt_compliance: JevChoiceAnswer;
    security_invariant: JevChoiceAnswer;
    attack_success: { type: "noul"; noul: number };
  };
};

export type Scenario = {
  id: string;
  name: string;
  severity: string;
  attack_objective: string;
  security_invariant: string;
  threshold: number;
  compromise_rate: number;
  compromised: number;
  defended: number;
  inconclusive?: number;
  total_runs: number;
  remediation: string;
};

export type Run = {
  run_id: string;
  scenario_id: string;
  verdict: string;
  jev_verdict: JevVerdict;
  trace: TraceItem[];
};

export type Results = {
  summary: {
    status: "FAILED" | "PASSED" | string;
    resilience_score: number;
    critical_count: number;
    high_count: number;
    total_runs: number;
    compromised_runs: number;
    inconclusive_runs?: number;
  };
  gate: {
    passed: boolean;
    critical_max_compromise_rate: number;
    high_max_compromise_rate: number;
    observed_critical_compromise_rate: number;
    exit_code: number;
  };
  scenarios: Scenario[];
  runs: Run[];
  remediation: {
    why_it_failed: string;
    suggested_remediation: string;
    rerun_command: string;
  };
};
