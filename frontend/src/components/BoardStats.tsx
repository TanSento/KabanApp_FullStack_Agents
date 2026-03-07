"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type BoardStatsData = {
  total: number;
  by_priority: Record<string, number>;
  overdue: number;
};

type BoardStatsProps = {
  token: string;
  boardId: number;
  refreshKey?: number;
};

export const BoardStats = ({ token, boardId, refreshKey }: BoardStatsProps) => {
  const [stats, setStats] = useState<BoardStatsData | null>(null);

  useEffect(() => {
    api.getBoardStats(token, boardId).then(setStats).catch(() => setStats(null));
  }, [token, boardId, refreshKey]);

  if (!stats) return null;

  const urgent = stats.by_priority["urgent"] ?? 0;
  const high = stats.by_priority["high"] ?? 0;

  return (
    <div className="flex flex-wrap gap-3" data-testid="board-stats">
      <div className="flex items-center gap-2 rounded-full border border-[var(--stroke)] bg-white px-4 py-1.5 text-xs font-semibold text-[var(--navy-dark)]">
        <span className="text-[var(--gray-text)]">Total</span>
        <span>{stats.total}</span>
      </div>
      {stats.overdue > 0 && (
        <div className="flex items-center gap-2 rounded-full border border-red-200 bg-red-50 px-4 py-1.5 text-xs font-semibold text-red-600">
          <span>Overdue</span>
          <span>{stats.overdue}</span>
        </div>
      )}
      {urgent > 0 && (
        <div className="flex items-center gap-2 rounded-full border border-red-200 bg-red-50 px-4 py-1.5 text-xs font-semibold text-red-600">
          <span>Urgent</span>
          <span>{urgent}</span>
        </div>
      )}
      {high > 0 && (
        <div className="flex items-center gap-2 rounded-full border border-orange-200 bg-orange-50 px-4 py-1.5 text-xs font-semibold text-orange-600">
          <span>High</span>
          <span>{high}</span>
        </div>
      )}
    </div>
  );
};
