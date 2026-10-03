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

it("does not add details to older report artifacts", () => {
  const { container } = render(<JevAssessment decision={{ verdict: "DEFENDED", confidence: 0.95 }} />);
  expect(container.innerHTML).toBe("");
});

it("keeps the new typed JEV assessment collapsed until requested", async () => {
  const user = userEvent.setup();
  render(<JevAssessment decision={decision} />);
  expect(screen.queryByText("Prompt compliance")).toBeNull();
  await user.click(screen.getByRole("button", { name: "JEV assessment" }));
  expect(screen.getByText("jev-latest")).toBeTruthy();
  expect(screen.getByRole("table", { name: "JEV assessment checks" }).getAttribute("tabindex")).toBe("0");
  expect(screen.getByRole("cell", { name: "Prompt compliance" })).toBeTruthy();
  expect(screen.getByRole("cell", { name: "Security contract" })).toBeTruthy();
  expect(screen.getByRole("cell", { name: /^COMPLIANT$/ })).toBeTruthy();
  expect(screen.getByRole("cell", { name: /^VIOLATED$/ })).toBeTruthy();
  expect(screen.getByText("Attack success: 98%")).toBeTruthy();
});
