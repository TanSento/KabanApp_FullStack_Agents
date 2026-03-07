import type { BoardData } from "./kanban";

const BASE = "/api";

async function request<T>(
    path: string,
    token: string,
    options: RequestInit = {}
): Promise<T> {
    const res = await fetch(`${BASE}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
            ...options.headers,
        },
    });
    if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed: ${res.status}`);
    }
    return res.json();
}

export type ChatResponse = {
    response: string;
    board_updates: Record<string, unknown>[];
};

export type BoardMeta = {
    id: number;
    title: string;
};

export const api = {
    // -- Legacy single-board routes (used for default board) --

    getBoard: (token: string) => request<BoardData>("/board", token),

    chatWithAi: (token: string, message: string) =>
        request<ChatResponse>("/ai/chat", token, {
            method: "POST",
            body: JSON.stringify({ message }),
        }),

    renameColumn: (token: string, columnId: string, title: string) =>
        request("/board/columns/" + columnId, token, {
            method: "PUT",
            body: JSON.stringify({ title }),
        }),

    createCard: (
        token: string,
        columnId: string,
        id: string,
        title: string,
        details: string
    ) =>
        request("/board/cards", token, {
            method: "POST",
            body: JSON.stringify({ column_id: columnId, id, title, details }),
        }),

    deleteCard: (token: string, cardId: string) =>
        request("/board/cards/" + cardId, token, { method: "DELETE" }),

    moveCard: (
        token: string,
        cardId: string,
        columnId: string,
        position: number
    ) =>
        request("/board/cards/" + cardId + "/move", token, {
            method: "PUT",
            body: JSON.stringify({ column_id: columnId, position }),
        }),

    // -- Multi-board management --

    listBoards: (token: string) =>
        request<{ boards: BoardMeta[] }>("/boards", token),

    createBoard: (token: string, title: string) =>
        request<BoardMeta>("/boards", token, {
            method: "POST",
            body: JSON.stringify({ title }),
        }),

    renameBoard: (token: string, boardId: number, title: string) =>
        request("/boards/" + boardId, token, {
            method: "PATCH",
            body: JSON.stringify({ title }),
        }),

    deleteBoard: (token: string, boardId: number) =>
        request("/boards/" + boardId, token, { method: "DELETE" }),

    getBoardById: (token: string, boardId: number) =>
        request<BoardData>("/boards/" + boardId, token),

    // -- Board-specific column management --

    createColumn: (token: string, boardId: number, title: string) =>
        request<{ id: string; title: string }>("/boards/" + boardId + "/columns", token, {
            method: "POST",
            body: JSON.stringify({ title }),
        }),

    deleteColumn: (token: string, boardId: number, columnId: string) =>
        request("/boards/" + boardId + "/columns/" + columnId, token, {
            method: "DELETE",
        }),

    // -- Board-specific card operations --

    renameColumnOnBoard: (token: string, boardId: number, columnId: string, title: string) =>
        request("/boards/" + boardId + "/columns/" + columnId, token, {
            method: "PUT",
            body: JSON.stringify({ title }),
        }),

    createCardOnBoard: (
        token: string,
        boardId: number,
        columnId: string,
        id: string,
        title: string,
        details: string,
        due_date: string | null = null,
        priority: string = "none"
    ) =>
        request("/boards/" + boardId + "/cards", token, {
            method: "POST",
            body: JSON.stringify({ column_id: columnId, id, title, details, due_date, priority }),
        }),

    updateCardOnBoard: (
        token: string,
        boardId: number,
        cardId: string,
        title: string,
        details: string,
        due_date: string | null = null,
        priority: string = "none"
    ) =>
        request("/boards/" + boardId + "/cards/" + cardId, token, {
            method: "PUT",
            body: JSON.stringify({ title, details, due_date, priority }),
        }),

    deleteCardOnBoard: (token: string, boardId: number, cardId: string) =>
        request("/boards/" + boardId + "/cards/" + cardId, token, {
            method: "DELETE",
        }),

    moveCardOnBoard: (
        token: string,
        boardId: number,
        cardId: string,
        columnId: string,
        position: number
    ) =>
        request("/boards/" + boardId + "/cards/" + cardId + "/move", token, {
            method: "PUT",
            body: JSON.stringify({ column_id: columnId, position }),
        }),

    chatWithAiOnBoard: (token: string, boardId: number, message: string) =>
        request<ChatResponse>("/boards/" + boardId + "/ai/chat", token, {
            method: "POST",
            body: JSON.stringify({ message }),
        }),

    getBoardStats: (token: string, boardId: number) =>
        request<{ total: number; by_priority: Record<string, number>; overdue: number }>(
            "/boards/" + boardId + "/stats", token
        ),

    searchCards: (token: string, boardId: number, q: string) =>
        request<{ cards: Array<{ id: string; title: string; details: string; column_id: string; due_date: string | null; priority: string }> }>(
            "/boards/" + boardId + "/search?q=" + encodeURIComponent(q), token
        ),

    getComments: (token: string, boardId: number, cardId: string) =>
        request<{ comments: Array<{ id: number; body: string; created_at: string; username: string }> }>(
            "/boards/" + boardId + "/cards/" + cardId + "/comments", token
        ),

    addComment: (token: string, boardId: number, cardId: string, body: string) =>
        request<{ id: number; body: string; created_at: string; username: string }>(
            "/boards/" + boardId + "/cards/" + cardId + "/comments", token, {
                method: "POST",
                body: JSON.stringify({ body }),
            }
        ),

    deleteComment: (token: string, boardId: number, cardId: string, commentId: number) =>
        request("/boards/" + boardId + "/cards/" + cardId + "/comments/" + commentId, token, {
            method: "DELETE",
        }),

    getLabels: (token: string, boardId: number) =>
        request<{ labels: Array<{ id: number; name: string; color: string }> }>(
            "/boards/" + boardId + "/labels", token
        ),

    createLabel: (token: string, boardId: number, name: string, color: string) =>
        request<{ id: number; name: string; color: string }>(
            "/boards/" + boardId + "/labels", token, {
                method: "POST",
                body: JSON.stringify({ name, color }),
            }
        ),

    deleteLabel: (token: string, boardId: number, labelId: number) =>
        request("/boards/" + boardId + "/labels/" + labelId, token, { method: "DELETE" }),

    getCardLabels: (token: string, boardId: number, cardId: string) =>
        request<{ labels: Array<{ id: number; name: string; color: string }> }>(
            "/boards/" + boardId + "/cards/" + cardId + "/labels", token
        ),

    setCardLabel: (token: string, boardId: number, cardId: string, labelId: number) =>
        request("/boards/" + boardId + "/cards/" + cardId + "/labels/" + labelId, token, {
            method: "POST",
        }),

    removeCardLabel: (token: string, boardId: number, cardId: string, labelId: number) =>
        request("/boards/" + boardId + "/cards/" + cardId + "/labels/" + labelId, token, {
            method: "DELETE",
        }),
};
