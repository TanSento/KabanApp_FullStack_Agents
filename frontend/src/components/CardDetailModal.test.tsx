import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CardDetailModal } from "@/components/CardDetailModal";
import * as apiModule from "@/lib/api";
import { vi } from "vitest";
import type { Card } from "@/lib/kanban";

const MOCK_CARD: Card = {
  id: "card-1",
  title: "Test card",
  details: "Some details",
  due_date: "2026-06-01",
  priority: "high",
};

const DEFAULT_PROPS = {
  token: "test-token",
  boardId: 1,
};

describe("CardDetailModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(apiModule.api, "getComments").mockResolvedValue({ comments: [] });
    vi.spyOn(apiModule.api, "addComment").mockResolvedValue({ id: 1, body: "test", created_at: "2026-01-01", username: "user" });
    vi.spyOn(apiModule.api, "deleteComment").mockResolvedValue({});
    vi.spyOn(apiModule.api, "getLabels").mockResolvedValue({ labels: [] });
    vi.spyOn(apiModule.api, "getCardLabels").mockResolvedValue({ labels: [] });
  });

  it("renders with card values", () => {
    render(<CardDetailModal card={MOCK_CARD} {...DEFAULT_PROPS} onSave={vi.fn()} onClose={vi.fn()} />);
    expect(screen.getByDisplayValue("Test card")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Some details")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2026-06-01")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toHaveValue("high");
  });

  it("calls onClose when Cancel is clicked", async () => {
    const onClose = vi.fn();
    render(<CardDetailModal card={MOCK_CARD} {...DEFAULT_PROPS} onSave={vi.fn()} onClose={onClose} />);
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onSave with updated values on submit", async () => {
    const onSave = vi.fn();
    const onClose = vi.fn();
    render(<CardDetailModal card={MOCK_CARD} {...DEFAULT_PROPS} onSave={onSave} onClose={onClose} />);

    const titleInput = screen.getByDisplayValue("Test card");
    await userEvent.clear(titleInput);
    await userEvent.type(titleInput, "Updated title");

    await userEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(onSave).toHaveBeenCalledWith(
      "card-1",
      "Updated title",
      "Some details",
      "2026-06-01",
      "high"
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when backdrop is clicked", async () => {
    const onClose = vi.fn();
    const { container } = render(<CardDetailModal card={MOCK_CARD} {...DEFAULT_PROPS} onSave={vi.fn()} onClose={onClose} />);
    const backdrop = container.firstChild as HTMLElement;
    await userEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  it("does not submit with empty title", async () => {
    const onSave = vi.fn();
    render(<CardDetailModal card={MOCK_CARD} {...DEFAULT_PROPS} onSave={onSave} onClose={vi.fn()} />);
    const titleInput = screen.getByDisplayValue("Test card");
    await userEvent.clear(titleInput);
    await userEvent.click(screen.getByRole("button", { name: /save/i }));
    expect(onSave).not.toHaveBeenCalled();
  });

  it("renders with null due_date and none priority", () => {
    const card: Card = { ...MOCK_CARD, due_date: null, priority: "none" };
    render(<CardDetailModal card={card} {...DEFAULT_PROPS} onSave={vi.fn()} onClose={vi.fn()} />);
    // priority select should show "none"
    expect(screen.getByRole("combobox")).toHaveValue("none");
  });

  it("shows comments section", async () => {
    vi.spyOn(apiModule.api, "getComments").mockResolvedValue({
      comments: [{ id: 1, body: "Nice work!", created_at: "2026-01-01T10:00:00", username: "user" }],
    });
    render(<CardDetailModal card={MOCK_CARD} {...DEFAULT_PROPS} onSave={vi.fn()} onClose={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("Nice work!")).toBeInTheDocument();
    });
  });
});
