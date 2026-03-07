"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  pointerWithin,
  closestCenter,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useAuth } from "@/components/AuthContext";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AiChatSidebar } from "@/components/AiChatSidebar";
import { CardDetailModal } from "@/components/CardDetailModal";
import { BoardFilterBar, DEFAULT_FILTERS, type BoardFilters } from "@/components/BoardFilterBar";
import { BoardStats } from "@/components/BoardStats";
import { createId, moveCard, type BoardData, type Priority, type Card } from "@/lib/kanban";
import { api, type BoardMeta } from "@/lib/api";

export const KanbanBoard = () => {
  const { token, username, logout } = useAuth();
  const [boards, setBoards] = useState<BoardMeta[]>([]);
  const [activeBoardId, setActiveBoardId] = useState<number | null>(null);
  const [board, setBoard] = useState<BoardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [newBoardTitle, setNewBoardTitle] = useState("");
  const [showNewBoardInput, setShowNewBoardInput] = useState(false);
  const [renamingBoardId, setRenamingBoardId] = useState<number | null>(null);
  const [renameBoardTitle, setRenameBoardTitle] = useState("");
  const [newColumnTitle, setNewColumnTitle] = useState("");
  const [showNewColumnInput, setShowNewColumnInput] = useState(false);
  const [editingCard, setEditingCard] = useState<Card | null>(null);
  const [filters, setFilters] = useState<BoardFilters>(DEFAULT_FILTERS);
  const [statsVersion, setStatsVersion] = useState(0);
  const renameTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const collisionDetection: CollisionDetection = useCallback((args) => {
    const pw = pointerWithin(args);
    if (pw.length > 0) return pw;
    return closestCenter(args);
  }, []);

  const fetchBoards = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.listBoards(token);
      setBoards(data.boards);
      if (data.boards.length > 0 && activeBoardId === null) {
        setActiveBoardId(data.boards[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load boards");
      setLoading(false);
    }
  }, [token, activeBoardId]);

  const fetchBoard = useCallback(async () => {
    if (!token || activeBoardId === null) return;
    try {
      const data = await api.getBoardById(token, activeBoardId);
      setBoard(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load board");
    } finally {
      setLoading(false);
    }
  }, [token, activeBoardId]);

  useEffect(() => {
    fetchBoards();
  }, [token]);

  useEffect(() => {
    if (activeBoardId !== null) {
      setLoading(true);
      fetchBoard();
    }
  }, [activeBoardId]);

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const matchesFilters = useCallback((card: Card): boolean => {
    const { search, priority, dueFilter } = filters;
    if (search && !card.title.toLowerCase().includes(search.toLowerCase()) &&
        !card.details.toLowerCase().includes(search.toLowerCase())) {
      return false;
    }
    if (priority !== "all" && card.priority !== priority) {
      return false;
    }
    if (dueFilter !== "all") {
      if (!card.due_date) return false;
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const due = new Date(card.due_date);
      if (dueFilter === "overdue" && due >= today) return false;
      if (dueFilter === "due-today") {
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        if (due < today || due >= tomorrow) return false;
      }
      if (dueFilter === "due-week") {
        const weekEnd = new Date(today);
        weekEnd.setDate(weekEnd.getDate() + 7);
        if (due < today || due >= weekEnd) return false;
      }
    }
    return true;
  }, [filters]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id || !board || !token || activeBoardId === null) return;

    const updatedColumns = moveCard(
      board.columns,
      active.id as string,
      over.id as string
    );

    setBoard((prev) => (prev ? { ...prev, columns: updatedColumns } : prev));

    const targetCol = updatedColumns.find((col) =>
      col.cardIds.includes(active.id as string)
    );
    if (targetCol) {
      const position = targetCol.cardIds.indexOf(active.id as string);
      api
        .moveCardOnBoard(token, activeBoardId, active.id as string, targetCol.id, position)
        .catch(() => fetchBoard());
    }
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!token || !board || activeBoardId === null) return;

    setBoard((prev) =>
      prev
        ? {
          ...prev,
          columns: prev.columns.map((col) =>
            col.id === columnId ? { ...col, title } : col
          ),
        }
        : prev
    );

    if (renameTimerRef.current) clearTimeout(renameTimerRef.current);
    renameTimerRef.current = setTimeout(() => {
      api.renameColumnOnBoard(token, activeBoardId, columnId, title).catch(() => fetchBoard());
    }, 400);
  };

  const handleAddCard = (columnId: string, title: string, details: string, due_date: string | null = null, priority: Priority = "none") => {
    if (!token || !board || activeBoardId === null) return;
    const id = createId("card");
    const cardDetails = details || "";

    setBoard((prev) =>
      prev
        ? {
          ...prev,
          cards: { ...prev.cards, [id]: { id, title, details: cardDetails, due_date, priority } },
          columns: prev.columns.map((col) =>
            col.id === columnId
              ? { ...col, cardIds: [...col.cardIds, id] }
              : col
          ),
        }
        : prev
    );

    setStatsVersion((v) => v + 1);
    api
      .createCardOnBoard(token, activeBoardId, columnId, id, title, cardDetails, due_date, priority)
      .catch(() => fetchBoard());
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (!token || !board || activeBoardId === null) return;

    setBoard((prev) =>
      prev
        ? {
          ...prev,
          cards: Object.fromEntries(
            Object.entries(prev.cards).filter(([id]) => id !== cardId)
          ),
          columns: prev.columns.map((col) =>
            col.id === columnId
              ? { ...col, cardIds: col.cardIds.filter((id) => id !== cardId) }
              : col
          ),
        }
        : prev
    );

    setStatsVersion((v) => v + 1);
    api.deleteCardOnBoard(token, activeBoardId, cardId).catch(() => fetchBoard());
  };

  const handleSaveCard = (cardId: string, title: string, details: string, due_date: string | null, priority: Priority) => {
    if (!token || activeBoardId === null) return;
    setBoard((prev) =>
      prev
        ? { ...prev, cards: { ...prev.cards, [cardId]: { ...prev.cards[cardId], title, details, due_date, priority } } }
        : prev
    );
    setStatsVersion((v) => v + 1);
    api.updateCardOnBoard(token, activeBoardId, cardId, title, details, due_date, priority).catch(() => fetchBoard());
  };

  const handleAddColumn = async () => {
    if (!token || !newColumnTitle.trim() || activeBoardId === null) return;
    try {
      const col = await api.createColumn(token, activeBoardId, newColumnTitle.trim());
      setBoard((prev) =>
        prev
          ? { ...prev, columns: [...prev.columns, { id: col.id, title: col.title, cardIds: [] }] }
          : prev
      );
      setNewColumnTitle("");
      setShowNewColumnInput(false);
    } catch {
      fetchBoard();
    }
  };

  const handleDeleteColumn = async (columnId: string) => {
    if (!token || activeBoardId === null) return;
    setBoard((prev) =>
      prev
        ? {
          ...prev,
          columns: prev.columns.filter((col) => col.id !== columnId),
          cards: Object.fromEntries(
            Object.entries(prev.cards).filter(([, card]) => {
              const col = prev.columns.find((c) => c.id === columnId);
              return !col?.cardIds.includes(card.id);
            })
          ),
        }
        : prev
    );
    try {
      await api.deleteColumn(token, activeBoardId, columnId);
    } catch {
      fetchBoard();
    }
  };

  const handleCreateBoard = async () => {
    if (!token || !newBoardTitle.trim()) return;
    try {
      const newBoard = await api.createBoard(token, newBoardTitle.trim());
      setBoards((prev) => [...prev, newBoard]);
      setNewBoardTitle("");
      setShowNewBoardInput(false);
      setActiveBoardId(newBoard.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create board");
    }
  };

  const handleDeleteBoard = async (boardId: number) => {
    if (!token) return;
    try {
      await api.deleteBoard(token, boardId);
      const remaining = boards.filter((b) => b.id !== boardId);
      setBoards(remaining);
      if (activeBoardId === boardId && remaining.length > 0) {
        setActiveBoardId(remaining[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete board");
    }
  };

  const handleRenameBoardSubmit = async (boardId: number) => {
    if (!token || !renameBoardTitle.trim()) return;
    try {
      await api.renameBoard(token, boardId, renameBoardTitle.trim());
      setBoards((prev) =>
        prev.map((b) => (b.id === boardId ? { ...b, title: renameBoardTitle.trim() } : b))
      );
      setRenamingBoardId(null);
      setRenameBoardTitle("");
    } catch {
      setRenamingBoardId(null);
    }
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;
  const activeBoardMeta = boards.find((b) => b.id === activeBoardId);

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-sm text-red-600" role="alert">{error}</p>
        <button
          onClick={() => { setError(null); setLoading(true); fetchBoards(); fetchBoard(); }}
          className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--navy-dark)]"
        >
          Retry
        </button>
      </div>
    );
  }

  if (loading && boards.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-[var(--gray-text)]">Loading...</p>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Project Management
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Manage your projects across multiple boards. Rename columns, drag cards, and let AI help you stay organized.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="flex flex-col items-end gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                  {username}
                </p>
                <button
                  type="button"
                  onClick={logout}
                  className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--navy-dark)]"
                  data-testid="logout-button"
                >
                  Sign out
                </button>
              </div>
            </div>
          </div>

          {/* Board selector */}
          <div className="flex flex-wrap items-center gap-3">
            {boards.map((b) => (
              <div key={b.id} className="group relative flex items-center">
                {renamingBoardId === b.id ? (
                  <form
                    onSubmit={(e) => { e.preventDefault(); handleRenameBoardSubmit(b.id); }}
                    className="flex items-center gap-2"
                  >
                    <input
                      autoFocus
                      value={renameBoardTitle}
                      onChange={(e) => setRenameBoardTitle(e.target.value)}
                      className="rounded-lg border border-[var(--primary-blue)] px-3 py-1.5 text-xs font-semibold text-[var(--navy-dark)] outline-none"
                      onBlur={() => { setRenamingBoardId(null); }}
                    />
                  </form>
                ) : (
                  <button
                    type="button"
                    onClick={() => setActiveBoardId(b.id)}
                    onDoubleClick={() => {
                      setRenamingBoardId(b.id);
                      setRenameBoardTitle(b.title);
                    }}
                    className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] transition ${
                      activeBoardId === b.id
                        ? "bg-[var(--primary-blue)] text-white"
                        : "border border-[var(--stroke)] text-[var(--gray-text)] hover:border-[var(--primary-blue)] hover:text-[var(--navy-dark)]"
                    }`}
                    data-testid={`board-tab-${b.id}`}
                  >
                    {b.title}
                  </button>
                )}
                {boards.length > 1 && activeBoardId === b.id && (
                  <button
                    type="button"
                    onClick={() => handleDeleteBoard(b.id)}
                    className="ml-1 hidden rounded-full p-1 text-[var(--gray-text)] hover:text-red-500 group-hover:flex"
                    title="Delete board"
                  >
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M2 2l8 8M10 2l-8 8" />
                    </svg>
                  </button>
                )}
              </div>
            ))}

            {showNewBoardInput ? (
              <form
                onSubmit={(e) => { e.preventDefault(); handleCreateBoard(); }}
                className="flex items-center gap-2"
              >
                <input
                  autoFocus
                  value={newBoardTitle}
                  onChange={(e) => setNewBoardTitle(e.target.value)}
                  placeholder="Board name"
                  className="rounded-lg border border-[var(--stroke)] px-3 py-1.5 text-xs font-medium text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                  onBlur={() => { if (!newBoardTitle.trim()) setShowNewBoardInput(false); }}
                />
                <button type="submit" className="rounded-full bg-[var(--primary-blue)] px-3 py-1.5 text-xs font-semibold text-white">
                  Add
                </button>
                <button type="button" onClick={() => setShowNewBoardInput(false)} className="text-xs text-[var(--gray-text)] hover:text-[var(--navy-dark)]">
                  Cancel
                </button>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setShowNewBoardInput(true)}
                className="rounded-full border border-dashed border-[var(--stroke)] px-4 py-2 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
                data-testid="new-board-button"
              >
                + New board
              </button>
            )}
          </div>

          {/* Column pills */}
          {board && (
            <div className="flex flex-wrap items-center gap-4">
              {board.columns.map((column) => (
                <div
                  key={column.id}
                  className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
                >
                  <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                  {column.title}
                </div>
              ))}
            </div>
          )}

          {board && token && activeBoardId !== null && (
            <BoardStats token={token} boardId={activeBoardId} refreshKey={statsVersion} />
          )}

          {board && (
            <BoardFilterBar filters={filters} onChange={setFilters} />
          )}
        </header>

        {loading ? (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-sm text-[var(--gray-text)]">Loading board...</p>
          </div>
        ) : board ? (
          <DndContext
            sensors={sensors}
            collisionDetection={collisionDetection}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6" style={{ gridTemplateColumns: `repeat(${board.columns.length}, minmax(0, 1fr))` }}>
              {board.columns.map((column) => {
                const allCards = column.cardIds.map((cardId) => board.cards[cardId]).filter(Boolean);
                const hasActiveFilter = filters.search !== "" || filters.priority !== "all" || filters.dueFilter !== "all";
                const filteredCardIds = hasActiveFilter
                  ? column.cardIds.filter((cardId) => board.cards[cardId] && matchesFilters(board.cards[cardId]))
                  : column.cardIds;
                const filteredCards = hasActiveFilter
                  ? allCards.filter(matchesFilters)
                  : allCards;
                return (
                  <KanbanColumn
                    key={column.id}
                    column={{ ...column, cardIds: filteredCardIds }}
                    cards={filteredCards}
                    onRename={handleRenameColumn}
                    onAddCard={handleAddCard}
                    onDeleteCard={handleDeleteCard}
                    onDeleteColumn={handleDeleteColumn}
                    onEditCard={(cardId) => setEditingCard(board.cards[cardId])}
                  />
                );
              })}

              {/* Add column */}
              <div className="flex flex-col gap-3">
                {showNewColumnInput ? (
                  <form
                    onSubmit={(e) => { e.preventDefault(); handleAddColumn(); }}
                    className="flex flex-col gap-2 rounded-2xl border border-dashed border-[var(--stroke)] p-4"
                  >
                    <input
                      autoFocus
                      value={newColumnTitle}
                      onChange={(e) => setNewColumnTitle(e.target.value)}
                      placeholder="Column name"
                      className="rounded-lg border border-[var(--stroke)] px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
                    />
                    <div className="flex gap-2">
                      <button type="submit" className="flex-1 rounded-full bg-[var(--primary-blue)] py-2 text-xs font-semibold text-white">
                        Add
                      </button>
                      <button
                        type="button"
                        onClick={() => { setShowNewColumnInput(false); setNewColumnTitle(""); }}
                        className="flex-1 rounded-full border border-[var(--stroke)] py-2 text-xs font-semibold text-[var(--gray-text)]"
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowNewColumnInput(true)}
                    className="rounded-2xl border border-dashed border-[var(--stroke)] px-4 py-6 text-sm font-medium text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
                    data-testid="add-column-button"
                  >
                    + Add column
                  </button>
                )}
              </div>
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>
        ) : null}

        {token && activeBoardId !== null && (
          <AiChatSidebar
            token={token}
            boardId={activeBoardId}
            onBoardUpdate={fetchBoard}
          />
        )}

        {editingCard && token && activeBoardId !== null && (
          <CardDetailModal
            card={editingCard}
            token={token}
            boardId={activeBoardId}
            onSave={handleSaveCard}
            onClose={() => setEditingCard(null)}
          />
        )}
      </main>
    </div>
  );
};
