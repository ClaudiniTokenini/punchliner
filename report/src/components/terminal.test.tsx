import { act, cleanup, render } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DotRow } from "./terminal";

afterEach(() => { cleanup(); vi.restoreAllMocks(); });

const CHAR = 10;

/** Monospace stand-in for jsdom: every glyph is CHAR px wide, the row is 40 glyphs wide. */
function mockMonospace() {
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(40 * CHAR);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockImplementation(function (this: HTMLElement) {
    return (this.textContent?.length ?? 0) * CHAR;
  });
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({ width: CHAR } as DOMRect);
}

function leader(container: HTMLElement) {
  const spans = container.querySelectorAll("span");
  return { label: spans[0].textContent ?? "", dots: spans[1].textContent ?? "", value: spans[3].textContent ?? "" };
}

it("fills the gap with exactly enough dots so every row ends on the same edge", () => {
  mockMonospace();
  const a = leader(render(<DotRow label="Resilience" value="100%" />).container);
  const b = leader(render(<DotRow label="Compromised" value="0/15" />).container);
  expect(a.dots).toBe(".".repeat(26));
  expect(b.dots).toBe(".".repeat(25));
  const width = ({ label, dots, value }: typeof a) => label.length + dots.length + value.length;
  expect(width(a)).toBe(40);
  expect(width(b)).toBe(40);
});

it("re-measures when the row is resized", () => {
  mockMonospace();
  let onResize: (() => void) | undefined;
  vi.stubGlobal("ResizeObserver", class { constructor(cb: () => void) { onResize = cb; } observe() {} unobserve() {} disconnect() {} });
  const { container } = render(<DotRow label="High" value="0" />);
  expect(leader(container).dots).toHaveLength(35);
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(20 * CHAR);
  act(() => onResize?.());
  expect(leader(container).dots).toHaveLength(15);
  vi.unstubAllGlobals();
});
