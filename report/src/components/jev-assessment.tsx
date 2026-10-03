import type { JevVerdict } from "../types";
import "./jev-assessment.css";

const pct = (value: number) => `${Math.round(value * 100)}%`;

export function JevAssessment({ decision }: { decision: JevVerdict }) {
  if (!decision.answers) return null; // Older artifacts contain only the aggregate verdict.
  const checks = [
    { label: "Prompt compliance", answer: decision.answers.prompt_compliance },
    { label: "Security contract", answer: decision.answers.security_invariant },
  ];
  return (
    <details className="jev-assessment">
      <summary>Jev assessment{decision.model && ` · ${decision.model}`}</summary>
      <dl>
        {checks.map(({ label, answer }) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>
              <strong className={answer.choice === "COMPLIANT" ? "green" : answer.choice === "VIOLATED" ? "red" : "amber"}>{answer.choice}</strong>
              <span>{pct(answer.confidence)} confidence</span>
              <ul aria-label={`${label} probabilities`}>
                {Object.entries(answer.probabilities).map(([option, probability]) => (
                  <li key={option}>{option.toLowerCase()}: {pct(probability)}</li>
                ))}
              </ul>
            </dd>
          </div>
        ))}
        <div>
          <dt>Attack success probability</dt>
          <dd>{pct(decision.answers.attack_success.noul)}</dd>
        </div>
      </dl>
    </details>
  );
}
