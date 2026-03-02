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

export const api = {
    getBoard: (token: string) => request<BoardData>("/board", token),

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
};
