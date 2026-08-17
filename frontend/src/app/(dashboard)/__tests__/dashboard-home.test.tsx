import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const get = vi.fn();
const post = vi.fn();

vi.mock("@/lib/api", () => ({
  default: {
    get: (...args: unknown[]) => get(...args),
    post: (...args: unknown[]) => post(...args),
  },
}));

import DashboardHome from "../page";

/**
 * The dashboard mounts several self-fetching children. Each expects a
 * different response shape, so route the stub by URL rather than returning one
 * catch-all body.
 */
function stubEndpoints(overrides: Record<string, unknown> = {}) {
  get.mockImplementation((url: string) => {
    for (const [fragment, data] of Object.entries(overrides)) {
      if (url.includes(fragment)) return Promise.resolve({ data });
    }
    if (url.includes("/api/dashboard/activity")) return Promise.resolve({ data: [] });
    if (url.includes("/api/dashboard/stats")) return Promise.resolve({ data: {} });
    if (url.includes("/api/runtime/metrics")) {
      return Promise.resolve({ data: { gpu: 0, cpu: 0, storage: 0 } });
    }
    return Promise.resolve({ data: { items: [] } });
  });
}

describe("dashboard home", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
  });

  it("renders the stat tiles when the stats API returns an empty body", async () => {
    stubEndpoints();

    render(<DashboardHome />);

    expect(await screen.findByText("Active Streams")).toBeInTheDocument();
    expect(screen.getByText("Models in Production")).toBeInTheDocument();
    expect(screen.getByText("Open Alerts")).toBeInTheDocument();
    expect(screen.getByText("Total Assets")).toBeInTheDocument();
  });

  it("renders counts returned by the stats API", async () => {
    stubEndpoints({
      "/api/dashboard/stats": {
        active_streams: 42,
        models_production: 7,
        open_alerts: 3,
        total_assets: 128,
      },
    });

    render(<DashboardHome />);

    await waitFor(() => expect(screen.getByText("42")).toBeInTheDocument());
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("128")).toBeInTheDocument();
  });

  it("surfaces the failure instead of showing zeroed tiles", async () => {
    get.mockRejectedValue(new Error("network down"));

    render(<DashboardHome />);

    // The stats row must report the error rather than silently rendering
    // placeholder numbers that look like real measurements.
    expect((await screen.findAllByText("network down")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Active Streams")).not.toBeInTheDocument();
  });

  it("points the quick actions at their routes", async () => {
    stubEndpoints();

    render(<DashboardHome />);

    const capture = await screen.findByRole("link", { name: /Start Capture/ });
    expect(capture).toHaveAttribute("href", "/capture");
  });
});
