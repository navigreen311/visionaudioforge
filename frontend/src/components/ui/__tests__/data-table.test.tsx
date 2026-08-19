import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import DataTable, { type Column } from "../DataTable";

/**
 * DataTable holds the only real logic among the primitives: which column is
 * sorted, in which direction, and whether the pager may move.
 *
 * Sorting here is *reported*, not applied — the table asks its caller to
 * re-fetch. That distinction is the thing most worth pinning: a change that
 * quietly started sorting the current page in place would look right on one
 * page of data and silently mis-order every page after it.
 */

interface Row extends Record<string, unknown> {
  name: string;
  size: number;
}

const columns: Column<Row>[] = [
  { key: "name", label: "Name", sortable: true },
  { key: "size", label: "Size", sortable: true },
  { key: "note", label: "Note" }, // deliberately not sortable
];

const rows: Row[] = [
  { name: "beta", size: 2 },
  { name: "alpha", size: 10 },
];

describe("DataTable sorting", () => {
  it("reports the first click on a column as ascending", async () => {
    const onSort = vi.fn();
    render(<DataTable columns={columns} data={rows} onSort={onSort} />);

    await userEvent.click(screen.getByText("Name"));

    expect(onSort).toHaveBeenCalledWith("name", "asc");
  });

  it("reverses direction when the same column is clicked again", async () => {
    const onSort = vi.fn();
    render(<DataTable columns={columns} data={rows} onSort={onSort} />);

    await userEvent.click(screen.getByText("Name"));
    await userEvent.click(screen.getByText("Name"));

    expect(onSort).toHaveBeenLastCalledWith("name", "desc");
  });

  it("starts a different column ascending rather than inheriting the last direction", async () => {
    const onSort = vi.fn();
    render(<DataTable columns={columns} data={rows} onSort={onSort} />);

    await userEvent.click(screen.getByText("Name"));
    await userEvent.click(screen.getByText("Name")); // now desc
    await userEvent.click(screen.getByText("Size"));

    expect(onSort).toHaveBeenLastCalledWith("size", "asc");
  });

  it("ignores clicks on a column that is not sortable", async () => {
    const onSort = vi.fn();
    render(<DataTable columns={columns} data={rows} onSort={onSort} />);

    await userEvent.click(screen.getByText("Note"));

    expect(onSort).not.toHaveBeenCalled();
  });

  it("leaves the row order to the caller", async () => {
    // The table reports the sort; it does not reorder what it was given.
    const onSort = vi.fn();
    render(<DataTable columns={columns} data={rows} onSort={onSort} />);

    await userEvent.click(screen.getByText("Name"));

    const cells = screen.getAllByRole("cell").map((c) => c.textContent);
    expect(cells[0]).toBe("beta");
  });
});

describe("DataTable pagination", () => {
  const pagination = (page: number, total: number) => ({
    page,
    pageSize: 10,
    total,
    onPageChange: vi.fn(),
  });

  it("cannot go back from the first page", () => {
    render(<DataTable columns={columns} data={rows} pagination={pagination(1, 30)} />);
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
  });

  it("cannot go past the last page", () => {
    // 30 rows at 10 per page is three pages, so page 3 is the end.
    render(<DataTable columns={columns} data={rows} pagination={pagination(3, 30)} />);
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
  });

  it("asks for the next and previous page by number", async () => {
    const config = pagination(2, 30);
    render(<DataTable columns={columns} data={rows} pagination={config} />);

    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    expect(config.onPageChange).toHaveBeenCalledWith(3);

    await userEvent.click(screen.getByRole("button", { name: /previous/i }));
    expect(config.onPageChange).toHaveBeenCalledWith(1);
  });

  it("treats a partial final page as a real page", () => {
    // 21 rows at 10 per page is three pages, not two: the off-by-one here
    // would strand the last row where nobody could reach it.
    render(<DataTable columns={columns} data={rows} pagination={pagination(3, 21)} />);
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /previous/i })).toBeEnabled();
  });
});
