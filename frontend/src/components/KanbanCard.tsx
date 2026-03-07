import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card, Priority } from "@/lib/kanban";

const PRIORITY_STYLES: Record<Priority, { label: string; className: string }> = {
  none: { label: "", className: "" },
  low: { label: "Low", className: "bg-blue-50 text-blue-600" },
  medium: { label: "Medium", className: "bg-yellow-50 text-yellow-700" },
  high: { label: "High", className: "bg-orange-50 text-orange-600" },
  urgent: { label: "Urgent", className: "bg-red-50 text-red-600" },
};

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  onEdit?: (cardId: string) => void;
};

export const KanbanCard = ({ card, onDelete, onEdit }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const priority = card.priority ?? "none";
  const priorityInfo = PRIORITY_STYLES[priority];

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div
          className="min-w-0 flex-1 cursor-pointer"
          onClick={() => onEdit?.(card.id)}
          role={onEdit ? "button" : undefined}
          aria-label={onEdit ? `Edit ${card.title}` : undefined}
        >
          <h4 className="font-display text-base font-semibold text-[var(--navy-dark)]">
            {card.title}
          </h4>
          {card.details && (
            <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
              {card.details}
            </p>
          )}
          <div className="mt-2 flex flex-wrap gap-2">
            {priority !== "none" && (
              <span className={clsx("rounded-full px-2 py-0.5 text-xs font-medium", priorityInfo.className)}>
                {priorityInfo.label}
              </span>
            )}
            {card.due_date && (
              <span className="rounded-full bg-gray-50 px-2 py-0.5 text-xs font-medium text-gray-500">
                {card.due_date}
              </span>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={() => onDelete(card.id)}
          className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
          aria-label={`Delete ${card.title}`}
        >
          Remove
        </button>
      </div>
    </article>
  );
};
