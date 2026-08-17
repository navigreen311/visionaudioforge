import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";

const listAssets = vi.fn();
const deleteAsset = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("@/lib/api");
  return {
    ...actual,
    listAssets: (...args: unknown[]) => listAssets(...args),
    deleteAsset: (...args: unknown[]) => deleteAsset(...args),
    downloadAssetUrl: (id: string) => `/download/${id}`,
    default: { get: vi.fn(), post: vi.fn(), delete: vi.fn() },
  };
});

import AssetsPage from "../assets/page";

function renderWithQuery(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function asset(overrides: Record<string, unknown> = {}) {
  return {
    id: "a1",
    filename: "cat.png",
    type: "image",
    size: 2048,
    tags: [],
    mime_type: "image/png",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("assets page", () => {
  beforeEach(() => {
    listAssets.mockReset();
    deleteAsset.mockReset();
  });

  it("renders assets returned by the API", async () => {
    listAssets.mockResolvedValue({
      items: [asset(), asset({ id: "a2", filename: "dog.png" })],
      total: 2,
    });

    renderWithQuery(<AssetsPage />);

    expect(await screen.findByText("cat.png")).toBeInTheDocument();
    expect(screen.getByText("dog.png")).toBeInTheDocument();
  });

  it("shows the empty state when the API returns no items", async () => {
    listAssets.mockResolvedValue({ items: [], total: 0 });

    renderWithQuery(<AssetsPage />);

    expect(await screen.findByText("No assets yet")).toBeInTheDocument();
  });

  it("tolerates a malformed response body without crashing", async () => {
    // The page guards against `items` being absent; assert that guard holds
    // rather than letting a bad payload throw during render.
    listAssets.mockResolvedValue({ unexpected: true });

    renderWithQuery(<AssetsPage />);

    expect(await screen.findByText("No assets yet")).toBeInTheDocument();
  });

  it("does not render asset rows when the query fails", async () => {
    listAssets.mockRejectedValue(new Error("boom"));

    renderWithQuery(<AssetsPage />);

    await waitFor(() => expect(listAssets).toHaveBeenCalled());
    expect(screen.queryByText("cat.png")).not.toBeInTheDocument();
  });
});
