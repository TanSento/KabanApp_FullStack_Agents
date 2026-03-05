# Code Review

Reviewed all source files across `backend/app/`, `backend/tests/`, `frontend/src/`, and `frontend/tests/`.

---

## Summary

The codebase is clean, well-structured, and appropriate for an MVP. Tests are comprehensive and the architecture is clear. There are a few genuine bugs, one significant test regression, and some patterns worth addressing.

---

## Bugs

### 1. AI board actions are not atomic (backend)

**File:** `backend/app/main.py:186-202`, `backend/app/db.py` (all CRUD functions)

Each DB function (`create_card`, `move_card`, etc.) calls `conn.commit()` internally before returning. In `ai_chat`, the actions loop wraps execution in a `try/except` that calls `conn.rollback()` on failure:

```python
try:
    for action in result.board_updates:
        create_card(...)  # commits internally
        update_card(...)  # commits internally - if this raises, first commit is permanent
except Exception:
    conn.rollback()  # too late - prior commits cannot be undone
    raise
```

`conn.rollback()` only rolls back un-committed work. Once each individual function commits, that data is permanent. If an AI response contains 3 actions and action 2 fails, action 1 is permanently applied and action 3 is not. The rollback is misleading and non-functional.

**Action:** Remove `conn.commit()` calls from individual DB functions and commit only once at the call site after all actions succeed, or document that actions are applied best-effort.

---

### 2. Column rename fires an API call on every keystroke (frontend)

**File:** `frontend/src/components/KanbanColumn.tsx:42`, `frontend/src/components/KanbanBoard.tsx:94-110`

The column title `<input>` fires `onChange` on every keystroke, which calls `handleRenameColumn`, which immediately calls `api.renameColumn`. Typing a 10-character column name produces 10 separate HTTP requests and 10 SQLite writes.

**Action:** Add a debounce (e.g., 400ms) to `handleRenameColumn`, or switch to blur/Enter to submit.

---

### 3. `_chat_history` memory leak (backend)

**File:** `backend/app/main.py:102`, `backend/app/auth.py:19-21`

`_chat_history` is a dict keyed by session token. When a user logs out, `logout(token)` removes the entry from `_sessions` but never removes it from `_chat_history`. Over many login/logout cycles, stale token entries accumulate in memory and are never collected.

Additionally, because history is keyed by token and a new token is issued on each login, users lose their conversation history when they log out and log back in.

**Action:** Clear the `_chat_history` entry for the token in the `auth_logout` handler.

---

### 4. `handleAddCard` silently overwrites empty details (frontend)

**File:** `frontend/src/components/KanbanBoard.tsx:115`

```typescript
const cardDetails = details || "No details yet.";
```

A user who intentionally leaves details blank when creating a card via the form gets a card with `"No details yet."` as the details text. This is invisible to the user. The AI, by contrast, can create cards with genuinely empty details via the backend. This creates an inconsistency between UI-created and AI-created cards.

**Action:** Remove the fallback and allow empty strings.

---

## Regressions

### 5. Playwright E2E tests do not handle authentication

**File:** `frontend/tests/kanban.spec.ts`

All three Playwright tests navigate to `/` and immediately expect the Kanban board to be visible:

```typescript
await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
```

The app now shows `LoginPage` to unauthenticated users. These tests will fail because the board is never rendered without a valid session. The tests appear to have been written before authentication was added and were not updated.

**Action:** Add a `beforeEach` or a `test.beforeEach` fixture that logs in via the UI (or by calling `/api/auth/login` and setting `sessionStorage`) before navigating to the board.

---

## Code Quality

### 6. Dead parameter in `ChatRequest` (backend)

**File:** `backend/app/main.py:74-76`

```python
class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict[str, str]] = []
```

`conversation_history` is part of the request model but is never read in the `ai_chat` handler. The backend maintains its own history server-side in `_chat_history`. This field misleads API consumers into thinking they can supply history from the client.

**Action:** Remove `conversation_history` from `ChatRequest`.

---

### 7. `_get_board_id` calls `init_db` on every authenticated request (backend)

**File:** `backend/app/main.py:118-123`

```python
def _get_board_id(username: str) -> tuple:
    conn = get_connection(db_path)
    init_db(conn)  # idempotent -- ensures tables exist
    ...
```

`init_db` runs `CREATE TABLE IF NOT EXISTS` for every API call that touches the board. While idempotent and not incorrect, it is unnecessary overhead after startup. Tables are already initialised in the `lifespan` handler.

**Action:** Remove the `init_db(conn)` call from `_get_board_id`.

---

### 8. `ensure_user` password parameter is misleading (backend)

**File:** `backend/app/db.py:65`, `backend/app/main.py:121`

`ensure_user(conn, username, "password")` is called with the literal string `"password"` on every request. The function looks like it creates or fetches a user account, but it doesn't validate the password - it only uses the parameter when inserting a new row. This gives the impression the function handles authentication when it does not.

**Action:** Remove the `password` parameter. The function's role is provisioning, not authentication. Hard-code the seed password inside the function if needed, or restructure so provisioning and auth are not conflated.

---

### 9. Auth endpoints return 422 instead of 401 for missing header (backend)

**File:** `backend/app/main.py:80-87`, and tests `test_board_api.py:14`, `test_board_api.py:141-153`

FastAPI's `Header()` dependency without a default raises `422 Unprocessable Entity` when the `Authorization` header is entirely absent (validation error). The tests acknowledge this with `assert resp.status_code == 422 or resp.status_code == 401`. RFC 7235 specifies 401 for missing/invalid credentials.

**Action:** Change the header dependency to `Header(default=None)` and manually return a 401 when it is `None`.

---

### 10. `ChatResponse.board_updates` is typed too loosely (frontend)

**File:** `frontend/src/lib/api.ts:27`

```typescript
board_updates: Record<string, unknown>[];
```

The actual shape is a known structure (`action`, `column_id`, `card_id`, `title`, etc.). The loose typing means `AiChatSidebar` only checks `data.board_updates.length > 0` to decide whether to refresh the board, which works, but the type gives no help if this code is extended.

**Action:** Define a `BoardAction` type that mirrors the backend's `BoardAction` model.

---

## Security

### 11. API key appears to be a real credential in `.env`

**File:** `.env`

The `.env` file contains what appears to be a live `OPENROUTER_API_KEY` value. The file is correctly listed in `.gitignore` and is not tracked by git. However, if this key is real it should be rotated as a precaution, particularly if the repository is ever moved or mirrored.

**Action:** Rotate the OpenRouter API key and treat `.env` values as secrets that should never be placed in any file that could be committed.

---

### 12. Passwords stored as plaintext in SQLite (backend)

**File:** `backend/app/db.py:70-76`

Passwords are stored as raw strings in the `users` table. For the MVP with a single hardcoded user this is an acceptable shortcut, but should be noted for any future expansion.

**Action:** If multiple real users are ever supported, use `bcrypt` or `argon2` for password hashing before this becomes a production concern.

---

## Testing Gaps

| Gap | Location |
|-----|----------|
| No test for partial AI action failure (actions 1 commits, action 2 raises) | `test_ai_chat.py` |
| No test that `_chat_history` is cleared on logout | `test_auth_api.py` |
| Playwright tests cover the happy path only; no auth flow covered | `tests/kanban.spec.ts` |
| No test for the column rename debounce behaviour (once fixed) | `KanbanBoard.test.tsx` |

---

## Prioritised Actions

| Priority | Item |
|----------|------|
| High | Fix Playwright E2E tests to handle auth (item 5) |
| High | Fix AI action atomicity (item 1) |
| High | Rotate OpenRouter API key (item 11) |
| Medium | Debounce column rename (item 2) |
| Medium | Clear chat history on logout (item 3) |
| Medium | Remove dead `conversation_history` from `ChatRequest` (item 6) |
| Low | Remove `init_db` from `_get_board_id` (item 7) |
| Low | Fix empty details fallback in `handleAddCard` (item 4) |
| Low | Fix 422 vs 401 on missing auth header (item 9) |
| Low | Improve `ChatResponse` typing in `api.ts` (item 10) |
| Low | Refactor `ensure_user` password parameter (item 8) |
