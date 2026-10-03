import { useState } from "react";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select";

const labels = ["2026-10-03 23:14 FAILED", "2026-10-03 21:27 FAILED"];

function RunSelect() {
  const [value, setValue] = useState("0");
  return (
    <Select value={value} onValueChange={(next) => setValue(next ?? "0")}>
      <SelectTrigger aria-label="Run"><SelectValue>{labels[Number(value)]}</SelectValue></SelectTrigger>
      <SelectContent>
        {labels.map((label, index) => <SelectItem key={label} value={String(index)}>{label}</SelectItem>)}
      </SelectContent>
    </Select>
  );
}

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", class { observe() {} unobserve() {} disconnect() {} });
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("opens below the trigger and selects a run", async () => {
  const user = userEvent.setup();
  render(<RunSelect />);
  const trigger = screen.getByRole("combobox", { name: "Run" });
  await user.click(trigger);
  const option = await screen.findByRole("option", { name: labels[1] });
  expect(option.closest('[data-slot="select-content"]')?.getAttribute("data-align-trigger")).toBe("false");
  await user.click(option);
  expect(trigger.querySelector('[data-slot="select-value"]')?.textContent).toBe(labels[1]);
  expect(screen.queryByRole("listbox")).toBeNull();
});

it("supports keyboard selection and restores focus on Escape", async () => {
  const user = userEvent.setup();
  render(<RunSelect />);
  const trigger = screen.getByRole("combobox", { name: "Run" });
  trigger.focus();
  await user.keyboard("{Enter}{ArrowDown}{Enter}");
  expect(trigger.querySelector('[data-slot="select-value"]')?.textContent).toBe(labels[1]);
  await user.click(trigger);
  await screen.findByRole("listbox");
  await user.keyboard("{Escape}");
  expect(screen.queryByRole("listbox")).toBeNull();
  expect(document.activeElement).toBe(trigger);
});
