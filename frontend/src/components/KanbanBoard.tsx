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
import { createId, moveCard, type BoardData } from "@/lib/kanban";
import { api } from "@/lib/api";

export const KanbanBoard = () => {
  const { token, username, logout } = useAuth();
  const [board, setBoard] = useState<BoardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const renameTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  // Use pointerWithin first (handles empty columns and bottom-of-list drops),
  // fall back to closestCenter for fine-grained card-to-card sorting.
  const collisionDetection: CollisionDetection = useCallback((args) => {
    const pw = pointerWithin(args);
    if (pw.length > 0) return pw;
    return closestCenter(args);
  }, []);

  const fetchBoard = useCallback(async () => {
    if (!token) return;
    try {
      const data = await api.getBoard(token);
      setBoard(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load board");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchBoard();
  }, [fetchBoard]);

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id || !board || !token) return;

    const updatedColumns = moveCard(
      board.columns,
      active.id as string,
      over.id as string
    );

    // Optimistic update
    setBoard((prev) => (prev ? { ...prev, columns: updatedColumns } : prev));

    // Find which column the card ended up in and its position
    const targetCol = updatedColumns.find((col) =>
      col.cardIds.includes(active.id as string)
    );
    if (targetCol) {
      const position = targetCol.cardIds.indexOf(active.id as string);
      api
        .moveCard(token, active.id as string, targetCol.id, position)
        .catch(() => fetchBoard()); // revert on failure
    }
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    if (!token || !board) return;

    // Optimistic update immediately
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

    // Debounce the API call — only fire 400ms after the user stops typing
    if (renameTimerRef.current) clearTimeout(renameTimerRef.current);
    renameTimerRef.current = setTimeout(() => {
      api.renameColumn(token, columnId, title).catch(() => fetchBoard());
    }, 400);
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    if (!token || !board) return;
    const id = createId("card");
    const cardDetails = details || "No details yet.";

    // Optimistic update
    setBoard((prev) =>
      prev
        ? {
          ...prev,
          cards: { ...prev.cards, [id]: { id, title, details: cardDetails } },
          columns: prev.columns.map((col) =>
            col.id === columnId
              ? { ...col, cardIds: [...col.cardIds, id] }
              : col
          ),
        }
        : prev
    );

    api
      .createCard(token, columnId, id, title, cardDetails)
      .catch(() => fetchBoard());
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    if (!token || !board) return;

    // Optimistic update
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

    api.deleteCard(token, cardId).catch(() => fetchBoard());
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-[var(--gray-text)]">Loading board...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <p className="text-sm text-red-600" role="alert">{error}</p>
        <button
          onClick={fetchBoard}
          className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:border-[var(--primary-blue)] hover:text-[var(--navy-dark)]"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!board) return null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="flex items-start gap-4">
              <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                  Focus
                </p>
                <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                  One board. Five columns. Zero clutter.
                </p>
              </div>
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
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={collisionDetection}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
        {token && <AiChatSidebar token={token} onBoardUpdate={fetchBoard} />}
      </main>
    </div>
  );
};
