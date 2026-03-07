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

const MOCK_BOARDS = { boards: [{ id: 1, title: "My Board" }] };

const mockAuth = {
  token: "test-token",
  username: "user",
  isLoading: false,
  error: null,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
};

describe("KanbanBoard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(AuthContext, "useAuth").mockReturnValue(mockAuth);
    vi.spyOn(apiModule.api, "listBoards").mockResolvedValue(MOCK_BOARDS);
    vi.spyOn(apiModule.api, "getBoardById").mockResolvedValue(MOCK_BOARD);
    vi.spyOn(apiModule.api, "renameColumnOnBoard").mockResolvedValue({});
    vi.spyOn(apiModule.api, "createCardOnBoard").mockResolvedValue({});
    vi.spyOn(apiModule.api, "deleteCardOnBoard").mockResolvedValue({});
    vi.spyOn(apiModule.api, "moveCardOnBoard").mockResolvedValue({});
  });

  it("fetches and renders the board", async () => {
    render(<KanbanBoard />);
    await waitFor(() => {
      expect(screen.getByText("Test card")).toBeInTheDocument();
    });
    expect(apiModule.api.listBoards).toHaveBeenCalledWith("test-token");
    expect(apiModule.api.getBoardById).toHaveBeenCalledWith("test-token", 1);
    expect(screen.getAllByTestId(/^column-/)).toHaveLength(2);
  });

  it("shows initial loading state", () => {
    vi.spyOn(apiModule.api, "listBoards").mockImplementation(
      () => new Promise(() => { }) // never resolves
    );
    render(<KanbanBoard />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows board loading state after boards load", async () => {
    vi.spyOn(apiModule.api, "getBoardById").mockImplementation(
      () => new Promise(() => { }) // never resolves
    );
    render(<KanbanBoard />);
    await waitFor(() => {
      expect(screen.getByText("Loading board...")).toBeInTheDocument();
    });
  });

  it("shows error state with retry button", async () => {
    vi.spyOn(apiModule.api, "listBoards").mockRejectedValueOnce(
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

  it("calls renameColumnOnBoard API on column rename after debounce", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByText("Test card")).toBeInTheDocument());
    const column = screen.getAllByTestId(/^column-/)[0];
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(apiModule.api.renameColumnOnBoard).not.toHaveBeenCalled();
    await waitFor(() => expect(apiModule.api.renameColumnOnBoard).toHaveBeenCalled(), { timeout: 1000 });
  });

  it("calls createCardOnBoard API on add card", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByText("Test card")).toBeInTheDocument());
    const column = screen.getAllByTestId(/^column-/)[0];
    const addButton = within(column).getByRole("button", { name: /add a card/i });
    await userEvent.click(addButton);
    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));
    expect(apiModule.api.createCardOnBoard).toHaveBeenCalled();
  });

  it("calls deleteCardOnBoard API on delete", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByText("Test card")).toBeInTheDocument());
    const column = screen.getAllByTestId(/^column-/)[0];
    const deleteButton = within(column).getByRole("button", { name: /delete test card/i });
    await userEvent.click(deleteButton);
    expect(apiModule.api.deleteCardOnBoard).toHaveBeenCalledWith("test-token", 1, "card-1");
  });

  it("shows board tabs and new board button", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByText("Test card")).toBeInTheDocument());
    expect(screen.getByTestId("board-tab-1")).toBeInTheDocument();
    expect(screen.getByTestId("new-board-button")).toBeInTheDocument();
  });

  it("shows add column button", async () => {
    render(<KanbanBoard />);
    await waitFor(() => expect(screen.getByText("Test card")).toBeInTheDocument());
    expect(screen.getByTestId("add-column-button")).toBeInTheDocument();
  });
});
