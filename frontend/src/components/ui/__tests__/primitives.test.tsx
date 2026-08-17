import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Badge from "../Badge";
import Button from "../Button";
import DataTable, { type Column } from "../DataTable";
import EmptyState from "../EmptyState";
import StatusIndicator from "../StatusIndicator";

describe("Button", () => {
  it("renders its children and fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);

    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("is disabled and swallows clicks while loading", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Save
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Save" });
    expect(button).toBeDisabled();

    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("Badge", () => {
  it("falls back to the neutral variant for an unknown one", () => {
    const { container } = render(<Badge variant="not-a-variant">Draft</Badge>);

    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(container.firstChild).toHaveClass("bg-gray-100");
  });
});

describe("StatusIndicator", () => {
  it("renders the optional label", () => {
    render(<StatusIndicator status="online" label="Connected" />);
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("renders without a label", () => {
    const { container } = render(<StatusIndicator status="offline" />);
    expect(container.querySelector("span")).toBeInTheDocument();
  });
});

describe("EmptyState", () => {
  it("shows the action button only when an action is supplied", async () => {
    const onClick = vi.fn();
    const { rerender } = render(
      <EmptyState title="No datasets" description="Upload one to begin." />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();

    rerender(
      <EmptyState
        title="No datasets"
        description="Upload one to begin."
        action={{ label: "Upload", onClick }}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Upload" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});

describe("DataTable", () => {
  interface Row {
    id: string;
    name: string;
    role: string;
  }

  const columns: Column<Row>[] = [
    { key: "name", label: "Name", sortable: true },
    { key: "role", label: "Role" },
  ];

  const rows: Row[] = [
    { id: "1", name: "Ada", role: "admin" },
    { id: "2", name: "Grace", role: "editor" },
  ];

  it("accepts an interface without an index signature", () => {
    render(<DataTable columns={columns} data={rows} />);

    expect(screen.getByText("Ada")).toBeInTheDocument();
    expect(screen.getByText("editor")).toBeInTheDocument();
  });

  it("renders the empty message when there are no rows", () => {
    render(<DataTable columns={columns} data={[]} />);
    expect(screen.getByText("No data available")).toBeInTheDocument();
  });

  it("reports sort key and toggles direction on repeated header clicks", async () => {
    const onSort = vi.fn();
    render(<DataTable columns={columns} data={rows} onSort={onSort} />);

    await userEvent.click(screen.getByText("Name"));
    expect(onSort).toHaveBeenLastCalledWith("name", "asc");

    await userEvent.click(screen.getByText("Name"));
    expect(onSort).toHaveBeenLastCalledWith("name", "desc");
  });

  it("does not sort on columns that are not sortable", async () => {
    const onSort = vi.fn();
    render(<DataTable columns={columns} data={rows} onSort={onSort} />);

    await userEvent.click(screen.getByText("Role"));
    expect(onSort).not.toHaveBeenCalled();
  });

  it("uses a column renderer when one is provided", () => {
    const withRenderer: Column<Row>[] = [
      {
        key: "role",
        label: "Role",
        render: (value) => <span>role:{String(value)}</span>,
      },
    ];
    render(<DataTable columns={withRenderer} data={rows} />);

    expect(screen.getByText("role:admin")).toBeInTheDocument();
  });
});
