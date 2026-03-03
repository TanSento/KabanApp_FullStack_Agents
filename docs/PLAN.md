# High Level Steps for Project

## Part 1: Plan

Enrich this document with detailed substeps, checklists, tests and success criteria. Create a `strategy.md` in `frontend/.agent/rules/` describing the existing frontend code. Get user approval.

- [x] Read and understand entire existing frontend codebase
- [x] Enrich PLAN.md with detailed substeps per part
- [x] Write `frontend/.agent/rules/strategy.md`

**Success criteria:** User approves the plan and the strategy document.

---

## Part 2: Scaffolding

Set up Docker infrastructure, FastAPI backend in `backend/`, and start/stop scripts in `scripts/`. Serve example static HTML to confirm a "hello world" works locally, plus a test API call.

- [x] Create `backend/` Python project: `pyproject.toml` (managed by `uv`), `backend/app/main.py` with a FastAPI app
- [x] Add a `GET /` returning a hello-world HTML page
- [x] Add a `GET /api/health` returning `{"status": "ok"}`
- [x] Write `Dockerfile` at project root: `python:3.13-slim` base, install `uv`, copy backend, install deps, expose port 8000
- [x] Write `docker-compose.yml` for easy local orchestration
- [x] Write scripts: `scripts/start_mac.sh`, `scripts/start_linux.sh`, `scripts/start_windows.ps1` (build + run)
- [x] Write scripts: `scripts/stop_mac.sh`, `scripts/stop_linux.sh`, `scripts/stop_windows.ps1` (stop + remove)

**Tests:**
- [x] `pytest` unit test: call `/api/health`, assert 200 and JSON body
- [x] `pytest` unit test: call `/`, assert 200 and HTML response
- [x] Manual: run `scripts/start_mac.sh`, open `http://localhost:8000`, see hello-world; open `http://localhost:8000/api/health`, see JSON; run `scripts/stop_mac.sh`, confirm container stops

**Success criteria:** Docker container builds and runs; browser shows hello-world at `/`; `/api/health` returns JSON; start/stop scripts work.

---

## Part 3: Add in Frontend

Update so the frontend is statically built inside Docker and served by FastAPI at `/`. The demo Kanban board displays correctly.

- [x] Add `output: "export"` to `next.config.ts` so `next build` produces a static `out/` directory
- [x] Update `Dockerfile` to add a Node build stage: install deps, run `next build`, copy `out/` into the Python image
- [x] Update FastAPI to mount the `out/` directory as static files at `/`
- [x] Remove the temporary hello-world route
- [x] Ensure Tailwind, fonts, and all assets load correctly from the static build

**Tests:**
- [x] `pytest` unit test: `GET /` returns 200 with HTML containing "Kanban Studio"
- [x] `pytest` unit test: `GET /api/health` still returns 200
- [x] Frontend unit tests still pass inside the container: `npm run test:unit`
- [x] Manual: rebuild and run Docker, open `http://localhost:8000`, confirm full Kanban board renders with drag-and-drop, column rename, card add/delete

**Success criteria:** Full Kanban board renders at `/` when served from Docker. All existing tests pass.

---

## Part 4: Add in a Fake User Sign In Experience

Add a login gate: on first hitting `/`, the user must sign in with `user` / `password` to see the Kanban board. Add logout capability.

- [x] Add a `POST /api/auth/login` endpoint: accepts `{username, password}`, returns a session token (simple JWT or UUID stored server-side)
- [x] Add a `POST /api/auth/logout` endpoint: invalidates the session
- [x] Add a `GET /api/auth/me` endpoint: returns current user info if authenticated, else 401
- [x] Add auth middleware or dependency in FastAPI to protect `/api/*` routes (except login)
- [x] Add a `LoginPage` component in the frontend
- [x] Add an `AuthContext` provider in the frontend to manage token state (stored in memory or sessionStorage)
- [x] Gate the Kanban board behind authentication: if not logged in, show the login page; if logged in, show the board with a logout button
- [x] Rebuild static frontend; update Docker setup if needed

**Tests:**
- [x] `pytest`: login with correct credentials returns 200 + token
- [x] `pytest`: login with wrong credentials returns 401
- [x] `pytest`: accessing protected route without token returns 401
- [x] `pytest`: accessing protected route with valid token returns 200
- [x] `pytest`: logout invalidates token
- [x] Frontend unit test: `LoginPage` renders form, submits credentials, shows error on failure
- [x] Frontend unit test: `AuthContext` stores/clears token correctly
- [x] Frontend unit test: unauthenticated state shows login page, authenticated state shows board
- [x] Manual: open app, see login page, enter wrong password (see error), enter correct credentials (see board), refresh (still logged in or re-prompted), click logout (return to login)

**Success criteria:** The app requires login before showing the Kanban board. Logout works. All tests pass.

---

## Part 5: Database Modeling

Propose a database schema for the Kanban, save it as JSON. Document the approach in `docs/`.

- [x] Design SQLite schema supporting: users, boards (one per user for MVP), columns (ordered), cards (ordered within columns)
- [x] Save schema definition as `docs/schema.json`
- [x] Write `docs/DATABASE.md` explaining the schema, relationships, and migration strategy
- [x] Get user sign-off on the schema before implementation

**Success criteria:** Schema is documented, saved as JSON, and approved by user.

---

## Part 6: Backend

Add API routes for reading and modifying the Kanban board for a given user. The database is created automatically if it does not exist.

- [x] Add database initialization code: create tables on startup if they do not exist
- [x] Seed default board data for a user if they have no board yet
- [x] Add `GET /api/board` -- returns the full board (columns + cards) for the authenticated user
- [x] Add `PUT /api/board/columns/{id}` -- rename a column
- [x] Add `POST /api/board/cards` -- create a new card in a column
- [x] Add `PUT /api/board/cards/{id}` -- edit a card (title, details)
- [x] Add `DELETE /api/board/cards/{id}` -- delete a card
- [x] Add `PUT /api/board/cards/{id}/move` -- move a card to a different column/position
- [x] Add `PUT /api/board` -- bulk update (for AI-driven batch changes)

**Tests:**
- [x] `pytest` for each endpoint: CRUD operations, edge cases (missing card, duplicate move, empty title)
- [x] `pytest` for database auto-creation: start with no DB file, call an endpoint, verify DB is created
- [x] `pytest` for auth enforcement: all board routes require authentication

**Success criteria:** All CRUD operations work via API. Database is created on first use. All tests pass.

---

## Part 7: Frontend + Backend

Connect the frontend to the backend API so the Kanban board is fully persistent.

- [x] Replace local `useState` board state with API calls: fetch board on mount, update via API on every user action
- [x] Add an API client module in the frontend (`lib/api.ts`) with typed fetch wrappers
- [x] Update `KanbanBoard` to load data from `GET /api/board`
- [x] Update column rename, card add, card edit, card delete, card move handlers to call the respective API endpoints
- [x] Show loading and error states
- [x] Ensure optimistic updates or proper refetching for a smooth UX

**Tests:**
- [x] Frontend unit tests with mocked API responses: board loads, CRUD operations trigger correct API calls
- [x] Integration tests (Playwright): full user flow -- login, see board, add card, rename column, drag card, delete card, refresh and verify persistence
- [x] `pytest`: end-to-end flow via API -- login, get board, modify, get board again, verify changes persisted

**Success criteria:** All changes persist across page refreshes. Frontend and backend work together seamlessly. All tests pass.

---

## Part 8: AI Connectivity

Allow the backend to make AI calls via OpenRouter. Verify with a simple "2+2" test.

- [x] Add OpenRouter client module in backend (`app/ai.py`): reads `OPENROUTER_API_KEY` from env, calls `openai/gpt-oss-120b` via the OpenAI-compatible API
- [x] Add `POST /api/ai/test` endpoint: sends "What is 2+2?" to the model, returns the response
- [x] Handle errors gracefully (missing API key, rate limits, timeouts)

**Tests:**
- [x] `pytest`: mock the OpenRouter call, verify request format and response parsing
- [x] Manual/integration: with a real API key, call `/api/ai/test` and confirm the model responds with "4"

**Success criteria:** AI calls work end-to-end. Error handling is robust. Tests pass.

---

## Part 9: AI Structured Outputs

Extend the AI call so it always receives the board JSON + user question + conversation history. The AI returns structured outputs including a response and optional board updates.

- [x] Define a Pydantic model for the AI structured output: `{response: str, board_updates: Optional[...]}`
- [x] Board updates should support: create card, edit card, delete card, move card, rename column
- [x] Add `POST /api/ai/chat` endpoint: accepts `{message, conversation_history}`, sends board state + message to AI, parses structured output, applies board updates if any, returns response
- [x] Apply board updates transactionally (all-or-nothing)
- [x] Store conversation history per session

**Tests:**
- [x] `pytest` with mocked AI: verify structured output parsing for various scenarios (response only, response + card creation, response + multiple updates)
- [x] `pytest`: verify board updates are applied correctly to the database
- [x] `pytest`: verify invalid structured outputs are handled gracefully
- [x] Integration: send a real chat message like "Add a card called Testing to the Backlog column", verify the card appears

**Success criteria:** AI receives full board context. Structured outputs correctly update the board. Conversation history is maintained. All tests pass.

---

## Part 10: AI Chat Sidebar

Add a sidebar widget to the UI for AI chat. When the AI updates the board via structured outputs, the UI refreshes automatically.

- [ ] Add `AiChatSidebar` component: collapsible panel on the right side of the board
- [ ] Chat UI: message input, scrollable message history, send button
- [ ] On sending a message, call `POST /api/ai/chat`, display the AI response
- [ ] If the AI response includes board updates, automatically refetch and re-render the board
- [ ] Style the sidebar to match the app design system (color scheme, fonts, spacing)
- [ ] Add a toggle button to open/close the sidebar

**Tests:**
- [ ] Frontend unit test: sidebar opens/closes, messages render, input submits
- [ ] Frontend unit test with mocked API: AI response displays, board refresh triggers on updates
- [ ] Playwright E2E: open sidebar, send a message, see AI response, verify board updates if applicable
- [ ] Manual: full conversational flow -- ask AI to create cards, move cards, rename columns; verify board updates in real time

**Success criteria:** Chat sidebar works end-to-end. AI can read and modify the board through natural conversation. UI updates automatically. All tests pass.