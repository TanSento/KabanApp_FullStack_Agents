import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BoardFilterBar, DEFAULT_FILTERS } from "@/components/BoardFilterBar";
import { vi } from "vitest";

describe("BoardFilterBar", () => {
  it("renders search input and selects", () => {
    render(<BoardFilterBar filters={DEFAULT_FILTERS} onChange={vi.fn()} />);
    expect(screen.getByTestId("filter-search")).toBeInTheDocument();
    expect(screen.getByTestId("filter-priority")).toBeInTheDocument();
    expect(screen.getByTestId("filter-due")).toBeInTheDocument();
  });

  it("does not show clear button when no filters active", () => {
    render(<BoardFilterBar filters={DEFAULT_FILTERS} onChange={vi.fn()} />);
    expect(screen.queryByTestId("filter-clear")).not.toBeInTheDocument();
  });

  it("shows clear button when search is active", () => {
    render(<BoardFilterBar filters={{ ...DEFAULT_FILTERS, search: "hello" }} onChange={vi.fn()} />);
    expect(screen.getByTestId("filter-clear")).toBeInTheDocument();
  });

  it("shows clear button when priority filter is active", () => {
    render(<BoardFilterBar filters={{ ...DEFAULT_FILTERS, priority: "high" }} onChange={vi.fn()} />);
    expect(screen.getByTestId("filter-clear")).toBeInTheDocument();
  });

  it("calls onChange when search is typed", async () => {
    const onChange = vi.fn();
    render(<BoardFilterBar filters={DEFAULT_FILTERS} onChange={onChange} />);
    await userEvent.type(screen.getByTestId("filter-search"), "r");
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ search: "r" }));
  });

  it("calls onChange with DEFAULT_FILTERS when clear is clicked", async () => {
    const onChange = vi.fn();
    render(<BoardFilterBar filters={{ ...DEFAULT_FILTERS, search: "hello" }} onChange={onChange} />);
    await userEvent.click(screen.getByTestId("filter-clear"));
    expect(onChange).toHaveBeenCalledWith(DEFAULT_FILTERS);
  });

  it("calls onChange when priority changes", async () => {
    const onChange = vi.fn();
    render(<BoardFilterBar filters={DEFAULT_FILTERS} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByTestId("filter-priority"), "urgent");
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ priority: "urgent" }));
  });

  it("calls onChange when due date filter changes", async () => {
    const onChange = vi.fn();
    render(<BoardFilterBar filters={DEFAULT_FILTERS} onChange={onChange} />);
    await userEvent.selectOptions(screen.getByTestId("filter-due"), "overdue");
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ dueFilter: "overdue" }));
  });
});
