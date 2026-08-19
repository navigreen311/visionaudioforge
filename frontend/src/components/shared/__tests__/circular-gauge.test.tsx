import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import CircularGauge from "../CircularGauge";

/**
 * The gauge's job when it has no number is to say so.
 *
 * A gauge that renders 0% for "not measured" is the failure this guards: an
 * empty arc and a confident "0%" is indistinguishable from a real reading of
 * zero, and an operator reading a dashboard cannot tell that the metric was
 * never collected. Every unknown-ish input has to reach the same honest state.
 */
describe("CircularGauge", () => {
  it("reports a known value as a percentage", () => {
    render(<CircularGauge value={72} label="CPU" />);
    expect(screen.getByRole("img", { name: /cpu: 72%/i })).toBeInTheDocument();
  });

  it.each([
    ["null", null],
    ["undefined", undefined],
    ["NaN", Number.NaN],
    ["Infinity", Number.POSITIVE_INFINITY],
  ])("says the value is not measured when it is %s", (_name, value) => {
    render(<CircularGauge value={value as number | null | undefined} label="CPU" />);

    const gauge = screen.getByRole("img", { name: /cpu: not measured/i });
    expect(gauge).toBeInTheDocument();
    // Specifically not "0%": that is a reading, and this is the absence of one.
    expect(gauge.getAttribute("aria-label")).not.toMatch(/0%/);
  });

  it("clamps a value above the scale rather than overdrawing the arc", () => {
    render(<CircularGauge value={140} label="Disk" />);
    expect(screen.getByRole("img", { name: /disk: 100%/i })).toBeInTheDocument();
  });

  it("clamps a negative value to zero", () => {
    render(<CircularGauge value={-20} label="Disk" />);
    expect(screen.getByRole("img", { name: /disk: 0%/i })).toBeInTheDocument();
  });
});
