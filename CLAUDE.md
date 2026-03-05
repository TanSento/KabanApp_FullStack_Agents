# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kanban Studio - a single-board Kanban project management app. Next.js frontend compiled to static files and served by a FastAPI backend, packaged in Docker. Includes AI chat via OpenRouter that can manipulate board state.

Login credentials: `user` / `password` (hardcoded MVP).

## Running the App

**Preferred (Docker):**
```bash
./scripts/start_mac.sh    # Mac
./scripts/start_linux.sh  # Linux
./scripts/stop_mac.sh     # Stop
```
App runs at `http://localhost:8000`. Requires `OPENROUTER_API_KEY` in `.env`.

**Backend only (dev):**
```bash
cd backend
uv run uvicorn app.main:app --reload
```

**Frontend only (dev):**
```bash
cd frontend
npm run dev   # localhost:3000
```

## Testing

**Backend:**
```bash
cd backend
uv run pytest                          # all tests
uv run pytest tests/test_board_api.py  # single file
```

**Frontend:**
```bash
cd frontend
npm run test:unit   # vitest unit tests
npm run test:e2e    # playwright e2e
npm run test:all    # both
```

**Frontend dev server with hot reload:**
```bash
cd frontend && npm run test:unit:watch
```

## Architecture

### Request Flow

```
Browser -> FastAPI (port 8000)
  /api/*          -> Python route handlers
  / and /_next/*  -> Static Next.js files (backend/static/)
```

The Next.js app is pre-built into `backend/static/` during Docker build. In dev, Next.js runs separately on port 3000.

### Backend (`backend/app/`)

- `main.py` - FastAPI app factory (`create_app`), all route handlers, in-memory chat history per token
- `db.py` - SQLite via raw `sqlite3`, connection-per-request pattern, `get_connection()` + `init_db()` + CRUD functions
- `auth.py` - In-memory session store (token -> username), UUID tokens
- `ai.py` - OpenRouter via `openai` SDK with `openai/gpt-oss-120b`, structured JSON response parsing (`AIResponse` Pydantic model with `board_updates: list[BoardAction]`)

Database: `backend/data/kanban.db` (SQLite). Schema: `users -> boards -> columns -> cards`. Each user gets one board, seeded with 5 columns and 8 cards on first access. `ensure_user` + `ensure_board` are called on every authenticated request (idempotent).

Test fixtures in `tests/conftest.py` use a temp DB and `create_app(static_dir=None, db_path=tmp_path)`.

### Frontend (`frontend/src/`)

- `app/page.tsx` + `components/KanbanBoard.tsx` - root; owns all board state via `useState<BoardData>`
- `lib/kanban.ts` - types (`Card`, `Column`, `BoardData`), pure `moveCard` function, `createId` helper
- `components/` - `KanbanBoard`, `KanbanColumn`, `KanbanCard`, `KanbanCardPreview`, `NewCardForm`

Board data shape (matches backend API response):
```typescript
{ columns: Column[], cards: Record<string, Card> }
// Column: { id, title, cardIds: string[] }
// Card: { id, title, details }
```

All components use named exports (not default). `data-testid="column-{id}"` and `data-testid="card-{id}"` for test targeting.

### AI Chat Flow

1. Frontend sends `POST /api/ai/chat` with `{message, conversation_history: []}`
2. Backend fetches current board state from DB, prepends as system prompt
3. AI responds with `{response: string, board_updates: BoardAction[]}`
4. Backend applies each `BoardAction` (create/edit/delete/move card, rename column) to DB
5. Returns updated board state; frontend re-fetches board and appends AI message to chat

Conversation history is stored server-side in `_chat_history` dict keyed by session token (in-memory, lost on restart).

## Key Conventions

- No emojis anywhere in code or output
- Keep it simple - no over-engineering, no unnecessary defensive programming
- Python package manager: `uv` (not pip)
- Color tokens defined as CSS custom properties in `frontend/src/app/globals.css` - use `var(--accent-yellow)`, `var(--primary-blue)`, `var(--secondary-purple)`, `var(--navy-dark)`, `var(--gray-text)`
- All API routes prefixed with `/api/`
- Auth via `Authorization: Bearer <token>` header; `require_auth` dependency in `main.py`
