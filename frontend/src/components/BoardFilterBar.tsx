"use client";

import type { Priority } from "@/lib/kanban";

export type BoardFilters = {
  search: string;
  priority: Priority | "all";
  dueFilter: "all" | "overdue" | "due-today" | "due-week";
};

export const DEFAULT_FILTERS: BoardFilters = {
  search: "",
  priority: "all",
  dueFilter: "all",
};

type BoardFilterBarProps = {
  filters: BoardFilters;
  onChange: (filters: BoardFilters) => void;
};

export const BoardFilterBar = ({ filters, onChange }: BoardFilterBarProps) => {
  const hasActiveFilter =
    filters.search !== "" ||
    filters.priority !== "all" ||
    filters.dueFilter !== "all";

  return (
    <div className="flex flex-wrap items-center gap-3" data-testid="board-filter-bar">
      <input
        type="search"
        value={filters.search}
        onChange={(e) => onChange({ ...filters, search: e.target.value })}
        placeholder="Search cards..."
        className="rounded-full border border-[var(--stroke)] bg-white px-4 py-1.5 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
        data-testid="filter-search"
        aria-label="Search cards"
      />
      <select
        value={filters.priority}
        onChange={(e) => onChange({ ...filters, priority: e.target.value as Priority | "all" })}
        className="rounded-full border border-[var(--stroke)] bg-white px-3 py-1.5 text-sm text-[var(--gray-text)] outline-none transition focus:border-[var(--primary-blue)]"
        data-testid="filter-priority"
        aria-label="Filter by priority"
      >
        <option value="all">All priorities</option>
        <option value="none">No priority</option>
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
        <option value="urgent">Urgent</option>
      </select>
      <select
        value={filters.dueFilter}
        onChange={(e) => onChange({ ...filters, dueFilter: e.target.value as BoardFilters["dueFilter"] })}
        className="rounded-full border border-[var(--stroke)] bg-white px-3 py-1.5 text-sm text-[var(--gray-text)] outline-none transition focus:border-[var(--primary-blue)]"
        data-testid="filter-due"
        aria-label="Filter by due date"
      >
        <option value="all">All dates</option>
        <option value="overdue">Overdue</option>
        <option value="due-today">Due today</option>
        <option value="due-week">Due this week</option>
      </select>
      {hasActiveFilter && (
        <button
          type="button"
          onClick={() => onChange(DEFAULT_FILTERS)}
          className="rounded-full border border-[var(--stroke)] px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
          data-testid="filter-clear"
        >
          Clear filters
        </button>
      )}
    </div>
  );
};
