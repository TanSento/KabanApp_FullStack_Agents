import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AiChatSidebar } from "@/components/AiChatSidebar";
import * as apiModule from "@/lib/api";

const TOKEN = "test-token";

describe("AiChatSidebar", () => {
    let onBoardUpdate: ReturnType<typeof vi.fn>;

    beforeEach(() => {
        vi.clearAllMocks();
        onBoardUpdate = vi.fn();
    });

    it("shows toggle button when closed", () => {
        render(<AiChatSidebar token={TOKEN} onBoardUpdate={onBoardUpdate} />);
        expect(screen.getByTestId("ai-chat-toggle")).toBeInTheDocument();
        expect(screen.queryByTestId("ai-chat-sidebar")).not.toBeInTheDocument();
    });

    it("opens sidebar when toggle is clicked", async () => {
        render(<AiChatSidebar token={TOKEN} onBoardUpdate={onBoardUpdate} />);
        await userEvent.click(screen.getByTestId("ai-chat-toggle"));
        expect(screen.getByTestId("ai-chat-sidebar")).toBeInTheDocument();
        expect(screen.getByTestId("ai-chat-input")).toBeInTheDocument();
    });

    it("closes sidebar when close button is clicked", async () => {
        render(<AiChatSidebar token={TOKEN} onBoardUpdate={onBoardUpdate} />);
        await userEvent.click(screen.getByTestId("ai-chat-toggle"));
        expect(screen.getByTestId("ai-chat-sidebar")).toBeInTheDocument();
        await userEvent.click(screen.getByTestId("ai-chat-close"));
        expect(screen.queryByTestId("ai-chat-sidebar")).not.toBeInTheDocument();
        expect(screen.getByTestId("ai-chat-toggle")).toBeInTheDocument();
    });

    it("sends a message and displays AI response", async () => {
        vi.spyOn(apiModule.api, "chatWithAi").mockResolvedValue({
            response: "Hello! I can help.",
            board_updates: [],
        });

        render(<AiChatSidebar token={TOKEN} onBoardUpdate={onBoardUpdate} />);
        await userEvent.click(screen.getByTestId("ai-chat-toggle"));

        const input = screen.getByTestId("ai-chat-input");
        await userEvent.type(input, "Hi there");
        await userEvent.click(screen.getByTestId("ai-chat-send"));

        await waitFor(() => {
            expect(screen.getByText("Hi there")).toBeInTheDocument();
            expect(screen.getByText("Hello! I can help.")).toBeInTheDocument();
        });

        expect(onBoardUpdate).not.toHaveBeenCalled();
    });

    it("calls onBoardUpdate when AI returns board_updates", async () => {
        vi.spyOn(apiModule.api, "chatWithAi").mockResolvedValue({
            response: "Done! Card created.",
            board_updates: [{ action: "create_card", column_id: "col-1", card_id: "card-new", title: "Test" }],
        });

        render(<AiChatSidebar token={TOKEN} onBoardUpdate={onBoardUpdate} />);
        await userEvent.click(screen.getByTestId("ai-chat-toggle"));

        await userEvent.type(screen.getByTestId("ai-chat-input"), "Add a card");
        await userEvent.click(screen.getByTestId("ai-chat-send"));

        await waitFor(() => {
            expect(screen.getByText("Done! Card created.")).toBeInTheDocument();
        });

        expect(onBoardUpdate).toHaveBeenCalledTimes(1);
    });

    it("shows loading indicator while waiting for response", async () => {
        let resolvePromise: (value: apiModule.ChatResponse) => void;
        vi.spyOn(apiModule.api, "chatWithAi").mockImplementation(
            () => new Promise((resolve) => { resolvePromise = resolve; })
        );

        render(<AiChatSidebar token={TOKEN} onBoardUpdate={onBoardUpdate} />);
        await userEvent.click(screen.getByTestId("ai-chat-toggle"));

        await userEvent.type(screen.getByTestId("ai-chat-input"), "Hello");
        await userEvent.click(screen.getByTestId("ai-chat-send"));

        await waitFor(() => {
            expect(screen.getByTestId("ai-loading")).toBeInTheDocument();
        });

        resolvePromise!({ response: "Hi!", board_updates: [] });

        await waitFor(() => {
            expect(screen.queryByTestId("ai-loading")).not.toBeInTheDocument();
            expect(screen.getByText("Hi!")).toBeInTheDocument();
        });
    });

    it("shows error message on API failure", async () => {
        vi.spyOn(apiModule.api, "chatWithAi").mockRejectedValue(new Error("Network error"));

        render(<AiChatSidebar token={TOKEN} onBoardUpdate={onBoardUpdate} />);
        await userEvent.click(screen.getByTestId("ai-chat-toggle"));

        await userEvent.type(screen.getByTestId("ai-chat-input"), "Hello");
        await userEvent.click(screen.getByTestId("ai-chat-send"));

        await waitFor(() => {
            expect(screen.getByText("Sorry, something went wrong. Please try again.")).toBeInTheDocument();
        });
    });

    it("submits on Enter key", async () => {
        vi.spyOn(apiModule.api, "chatWithAi").mockResolvedValue({
            response: "Got it!",
            board_updates: [],
        });

        render(<AiChatSidebar token={TOKEN} onBoardUpdate={onBoardUpdate} />);
        await userEvent.click(screen.getByTestId("ai-chat-toggle"));

        await userEvent.type(screen.getByTestId("ai-chat-input"), "Test{Enter}");

        await waitFor(() => {
            expect(screen.getByText("Got it!")).toBeInTheDocument();
        });
    });

    it("disables send button when input is empty", async () => {
        render(<AiChatSidebar token={TOKEN} onBoardUpdate={onBoardUpdate} />);
        await userEvent.click(screen.getByTestId("ai-chat-toggle"));
        expect(screen.getByTestId("ai-chat-send")).toBeDisabled();
    });
});
