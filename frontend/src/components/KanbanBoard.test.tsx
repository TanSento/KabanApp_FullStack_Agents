import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import * as AuthContext from "@/components/AuthContext";
import * as apiModule from "@/lib/api";
import { vi } from "vitest";
import type { BoardData } from "@/lib/kanban";

const MOCK_BOARD: BoardData = {
  columns: [
    { id: "col-1", title: "Backlog", cardIds: ["card-1"] },
    { id: "col-2", title: "Done", cardIds: [] },
  ],
  cards: {
    "card-1": { id: "card-1", title: "Test card", details: "Details" },
  },
};

const mockAuth = {
  token: "test-token",
  username: "user",
  isLoading: false,
  error: null,
  login: vi.fn(),
  logout: vi.fn(),
};

describe("KanbanBoard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(AuthContext, "useAuth").mockReturnValue(mockAuth);
    vi.spyOn(apiModule.api, "getBoard").mockResolvedValue(MOCK_BOARD);
    vi.spyOn(apiModule.api, "renameColumn").mockResolvedValue({});
    vi.spyOn(apiModule.api, "createCard").mockResolvedValue({});
    vi.spyOn(apiModule.api, "deleteCard").mockResolvedValue({});
    vi.spyOn(apiModule.api, "moveCard").mockResolvedValue({});
  });

  it("fetches and renders the board", async () => {
    render(<KanbanBoard />);
    await waitFor(() => {
      expect(screen.getByText("Test card")).toBeInTheDocument();
    });
    expect(apiModule.api.getBoard).toHaveBeenCalledWith("test-token");
    expect(screen.getAllByTestId(/column-/i)).toHaveLength(2);
  });

  it("shows loading state", () => {
    vi.spyOn(apiModule.api, "getBoard").mockImplementation(
      () => new Promise(() => { }) // never resolves
    );
    render(<KanbanBoard />);
    expect(screen.getByText("Loading board...")).toBeInTheDocument();
  });

  it("shows error state with retry button", async () => {
    vi.spyOn(apiModule.api, "getBoard").mockRejectedValueOnce(
      new Error("Network error")
    );
    render(<KanbanBoard />);
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Network error");
    });
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("shows username and sign out", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByText("user")).toBeInTheDocument());
    expect(screen.getByTestId("logout-button")).toBeInTheDocument();
  });

  it("calls logout when sign out is clicked", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByTestId("logout-button")).toBeInTheDocument());
    await userEvent.click(screen.getByTestId("logout-button"));
    expect(mockAuth.logout).toHaveBeenCalled();
  });

  it("calls renameColumn API on column rename after debounce", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByText("Test card")).toBeInTheDocument());
    const column = screen.getAllByTestId(/column-/i)[0];
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    // API should not be called synchronously (debounced)
    expect(apiModule.api.renameColumn).not.toHaveBeenCalled();
    // Wait for the 400ms debounce to fire
    await waitFor(() => expect(apiModule.api.renameColumn).toHaveBeenCalled(), { timeout: 1000 });
  });

  it("calls createCard API on add card", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByText("Test card")).toBeInTheDocument());
    const column = screen.getAllByTestId(/column-/i)[0];
    const addButton = within(column).getByRole("button", { name: /add a card/i });
    await userEvent.click(addButton);
    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));
    expect(apiModule.api.createCard).toHaveBeenCalled();
  });

  it("calls deleteCard API on delete", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByText("Test card")).toBeInTheDocument());
    const column = screen.getAllByTestId(/column-/i)[0];
    const deleteButton = within(column).getByRole("button", { name: /delete test card/i });
    await userEvent.click(deleteButton);
    expect(apiModule.api.deleteCard).toHaveBeenCalledWith("test-token", "card-1");
  });
});
