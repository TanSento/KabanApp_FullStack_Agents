"use client";

import { useState, useEffect, type FormEvent } from "react";
import type { Card, Priority } from "@/lib/kanban";
import { api } from "@/lib/api";

type Comment = { id: number; body: string; created_at: string; username: string };
type Label = { id: number; name: string; color: string };

type CardDetailModalProps = {
  card: Card;
  token: string;
  boardId: number;
  onSave: (cardId: string, title: string, details: string, due_date: string | null, priority: Priority) => void;
  onClose: () => void;
};

export const CardDetailModal = ({ card, token, boardId, onSave, onClose }: CardDetailModalProps) => {
  const [title, setTitle] = useState(card.title);
  const [details, setDetails] = useState(card.details);
  const [dueDate, setDueDate] = useState(card.due_date ?? "");
  const [priority, setPriority] = useState<Priority>(card.priority ?? "none");
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [commentLoading, setCommentLoading] = useState(false);
  const [cardLabels, setCardLabels] = useState<Label[]>([]);
  const [allLabels, setAllLabels] = useState<Label[]>([]);

  useEffect(() => {
    api.getComments(token, boardId, card.id).then((data) => setComments(data.comments)).catch(() => {});
    api.getCardLabels(token, boardId, card.id).then((data) => setCardLabels(data.labels)).catch(() => {});
    api.getLabels(token, boardId).then((data) => setAllLabels(data.labels)).catch(() => {});
  }, [token, boardId, card.id]);

  const handleToggleLabel = async (label: Label) => {
    const isAssigned = cardLabels.some((l) => l.id === label.id);
    if (isAssigned) {
      await api.removeCardLabel(token, boardId, card.id, label.id);
      setCardLabels((prev) => prev.filter((l) => l.id !== label.id));
    } else {
      await api.setCardLabel(token, boardId, card.id, label.id);
      setCardLabels((prev) => [...prev, label]);
    }
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return;
    onSave(card.id, title.trim(), details.trim(), dueDate || null, priority);
    onClose();
  };

  const handleAddComment = async (e: FormEvent) => {
    e.preventDefault();
    if (!newComment.trim() || commentLoading) return;
    setCommentLoading(true);
    try {
      const comment = await api.addComment(token, boardId, card.id, newComment.trim());
      setComments((prev) => [...prev, comment]);
      setNewComment("");
    } finally {
      setCommentLoading(false);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    await api.deleteComment(token, boardId, card.id, commentId);
    setComments((prev) => prev.filter((c) => c.id !== commentId));
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-md rounded-3xl border border-[var(--stroke)] bg-white p-6 shadow-[0_24px_48px_rgba(3,33,71,0.15)]">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-lg font-semibold text-[var(--navy-dark)]">Edit Card</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1 text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
            aria-label="Close"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M2 2l12 12M14 2L2 14" />
            </svg>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
              Title
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              required
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
              Details
            </label>
            <textarea
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              rows={4}
              className="w-full resize-none rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--gray-text)] outline-none transition focus:border-[var(--primary-blue)]"
            />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as Priority)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--gray-text)] outline-none transition focus:border-[var(--primary-blue)]"
              >
                <option value="none">None</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
                Due Date
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--gray-text)] outline-none transition focus:border-[var(--primary-blue)]"
              />
            </div>
          </div>
          {allLabels.length > 0 && (
            <div>
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
                Labels
              </label>
              <div className="flex flex-wrap gap-2">
                {allLabels.map((label) => {
                  const isAssigned = cardLabels.some((l) => l.id === label.id);
                  return (
                    <button
                      key={label.id}
                      type="button"
                      onClick={() => handleToggleLabel(label)}
                      style={{ backgroundColor: label.color + (isAssigned ? "ff" : "33"), color: label.color, borderColor: label.color }}
                      className="rounded-full border px-3 py-1 text-xs font-semibold transition"
                    >
                      {label.name}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              className="rounded-full bg-[var(--primary-blue)] px-5 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
            >
              Save
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)] transition hover:text-[var(--navy-dark)]"
            >
              Cancel
            </button>
          </div>
        </form>

        {/* Comments section */}
        <div className="mt-5 border-t border-[var(--stroke)] pt-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--gray-text)]">
            Comments ({comments.length})
          </h3>
          <div className="mb-3 space-y-2 max-h-40 overflow-y-auto">
            {comments.map((comment) => (
              <div key={comment.id} className="group flex items-start gap-2 rounded-xl bg-[var(--surface-strong)] px-3 py-2 text-sm">
                <div className="flex-1">
                  <span className="font-semibold text-[var(--navy-dark)]">{comment.username}</span>
                  <span className="ml-2 text-xs text-[var(--gray-text)]">{comment.created_at.slice(0, 16).replace("T", " ")}</span>
                  <p className="mt-1 text-[var(--gray-text)]">{comment.body}</p>
                </div>
                <button
                  type="button"
                  onClick={() => handleDeleteComment(comment.id)}
                  className="hidden text-[var(--gray-text)] hover:text-red-500 group-hover:block"
                  aria-label="Delete comment"
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M2 2l8 8M10 2l-8 8" />
                  </svg>
                </button>
              </div>
            ))}
            {comments.length === 0 && (
              <p className="text-xs text-[var(--gray-text)]">No comments yet.</p>
            )}
          </div>
          <form onSubmit={handleAddComment} className="flex gap-2">
            <input
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Add a comment..."
              className="flex-1 rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              data-testid="comment-input"
            />
            <button
              type="submit"
              disabled={commentLoading || !newComment.trim()}
              className="rounded-full bg-[var(--primary-blue)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110 disabled:opacity-50"
            >
              Post
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
