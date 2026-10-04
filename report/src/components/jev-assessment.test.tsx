import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it } from "vitest";
import { JevAssessment } from "./jev-assessment";
import type { JevVerdict } from "@/types";

const decision: JevVerdict = {
  verdict: "COMPROMISED",
  confidence: 0.97,
  provider: "jev",
  model: "jev-latest",
  answers: {
    prompt_compliance: {
      type: "choice",
      choice: "COMPLIANT",
      confidence: 0.94,
      probabilities: { COMPLIANT: 0.94, VIOLATED: 0.02, INCONCLUSIVE: 0.04 },
    },
    security_invariant: {
      type: "choice",
      choice: "VIOLATED",
      confidence: 0.97,
      probabilities: { COMPLIANT: 0.01, VIOLATED: 0.97, INCONCLUSIVE: 0.02 },
    },
    attack_success: { type: "noul", noul: 0.98 },
  },
};

afterEach(cleanup);

it("keeps the typed JEV assessment collapsed until requested", async () => {
  const user = userEvent.setup();
  render(<JevAssessment decision={decision} />);
  expect(screen.queryByText("Prompt compliance")).toBeNull();
  await user.click(screen.getByRole("button", { name: "JEV assessment" }));
  expect(screen.getByText("Prompt compliance")).toBeTruthy();
});
