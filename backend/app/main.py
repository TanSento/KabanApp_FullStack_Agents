from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.ai import AINotConfiguredError, AIServiceError, chat, chat_with_board
from app.auth import create_session, get_user, login, logout
from app.db import (
    add_comment,
    authenticate_user,
    bulk_update,
    create_board,
    create_card,
    create_column,
    create_label,
    delete_board,
    delete_card,
    delete_column,
    delete_comment,
    delete_label,
    ensure_board,
    ensure_user,
    get_board,
    get_board_stats,
    get_boards,
    get_card_labels,
    get_comments,
    get_connection,
    get_labels,
    get_user_id,
    init_db,
    move_card,
    register_user,
    remove_card_label,
    rename_board,
    rename_column,
    reorder_columns,
    search_cards,
    set_card_label,
    update_card,
)

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# -- Pydantic models --

class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


class UserResponse(BaseModel):
    username: str


class RenameColumnRequest(BaseModel):
    title: str


VALID_PRIORITIES = {"none", "low", "medium", "high", "urgent"}


class CreateCardRequest(BaseModel):
    column_id: str
    id: str
    title: str
    details: str = ""
    due_date: str | None = None
    priority: str = "none"


class UpdateCardRequest(BaseModel):
    title: str
    details: str
    due_date: str | None = None
    priority: str = "none"


class ReorderColumnsRequest(BaseModel):
    column_ids: list[str]


class MoveCardRequest(BaseModel):
    column_id: str
    position: int


class BulkUpdateRequest(BaseModel):
    columns: list[dict]
    cards: dict[str, dict]


class AddCommentRequest(BaseModel):
    body: str


class CreateLabelRequest(BaseModel):
    name: str
    color: str = "#6366f1"


class ChatRequest(BaseModel):
    message: str


class CreateBoardRequest(BaseModel):
    title: str


class RenameBoardRequest(BaseModel):
    title: str


class CreateColumnRequest(BaseModel):
    title: str


# -- Auth dependency --

def require_auth(authorization: str = Header()) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    username = get_user(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username


def require_auth_with_token(authorization: str = Header()) -> tuple[str, str]:
    """Return (username, token) for endpoints that need the token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    username = get_user(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username, token


# In-memory conversation history: token -> [{role, content}]
_chat_history: dict[str, list[dict[str, str]]] = {}


def create_app(static_dir: Path | None = None, db_path: Path | None = None) -> FastAPI:
    if static_dir is None:
        static_dir = DEFAULT_STATIC_DIR

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        conn = get_connection(db_path)
        init_db(conn)
        conn.close()
        yield

    application = FastAPI(title="Kanban Studio API", lifespan=lifespan)

    def _get_board_id(username: str) -> tuple:
        conn = get_connection(db_path)
        init_db(conn)
        user_id = ensure_user(conn, username, "password")
        board_id = ensure_board(conn, user_id)
        return conn, board_id

    def _get_board_for_user(username: str, board_id: int) -> tuple:
        """Get connection and verify the board belongs to the user."""
        conn = get_connection(db_path)
        init_db(conn)
        user_id = get_user_id(conn, username)
        if user_id is None:
            user_id = ensure_user(conn, username, "password")
        board = conn.execute(
            "SELECT id FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id)
        ).fetchone()
        if not board:
            conn.close()
            raise HTTPException(status_code=404, detail="Board not found")
        return conn, board_id

    # -- Health --

    @application.get("/api/health")
    async def health():
        return {"status": "ok"}

    # -- Auth --

    @application.post("/api/auth/login")
    async def auth_login(body: LoginRequest) -> LoginResponse:
        # Check DB first (handles registered users)
        conn = get_connection(db_path)
        try:
            init_db(conn)
            user_id = authenticate_user(conn, body.username, body.password)
        finally:
            conn.close()

        if user_id is not None:
            token = create_session(body.username)
            return LoginResponse(token=token, username=body.username)

        # Fall back to hardcoded credentials
        token = login(body.username, body.password)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return LoginResponse(token=token, username=body.username)

    @application.post("/api/auth/register")
    async def auth_register(body: RegisterRequest) -> LoginResponse:
        if len(body.username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        conn = get_connection(db_path)
        try:
            init_db(conn)
            user_id = register_user(conn, body.username, body.password)
            if user_id is None:
                raise HTTPException(status_code=409, detail="Username already taken")
        finally:
            conn.close()
        token = create_session(body.username)
        return LoginResponse(token=token, username=body.username)

    @application.post("/api/auth/logout")
    async def auth_logout(authorization: str = Header()):
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        token = authorization.removeprefix("Bearer ")
        logout(token)
        _chat_history.pop(token, None)
        return {"status": "ok"}

    @application.get("/api/auth/me")
    async def auth_me(authorization: str = Header(default="")) -> UserResponse:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        token = authorization.removeprefix("Bearer ")
        user = get_user(token)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return UserResponse(username=user)

    # -- AI --

    @application.post("/api/ai/test")
    async def ai_test(username: str = Depends(require_auth)):
        try:
            answer = chat([{"role": "user", "content": "What is 2+2?"}])
            return {"response": answer}
        except AINotConfiguredError:
            raise HTTPException(status_code=503, detail="AI service not configured")
        except AIServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

    @application.post("/api/ai/chat")
    async def ai_chat(body: ChatRequest, auth: tuple[str, str] = Depends(require_auth_with_token)):
        username, token = auth
        conn, board_id = _get_board_id(username)
        try:
            board_state = get_board(conn, board_id)
            history = _chat_history.get(token, [])

            try:
                result = chat_with_board(board_state, body.message, history)
            except AINotConfiguredError:
                raise HTTPException(status_code=503, detail="AI service not configured")
            except AIServiceError as exc:
                raise HTTPException(status_code=502, detail=str(exc))

            applied = []
            try:
                for action in result.board_updates:
                    if action.action == "create_card":
                        create_card(conn, board_id, action.column_id, action.card_id, action.title, action.details or "", action.due_date, action.priority or "none", commit=False)
                    elif action.action == "edit_card":
                        update_card(conn, board_id, action.card_id, action.title, action.details or "", action.due_date, action.priority or "none", commit=False)
                    elif action.action == "delete_card":
                        delete_card(conn, board_id, action.card_id, commit=False)
                    elif action.action == "move_card":
                        move_card(conn, board_id, action.card_id, action.column_id, action.position, commit=False)
                    elif action.action == "rename_column":
                        rename_column(conn, board_id, action.column_id, action.title, commit=False)
                    applied.append(action.model_dump(exclude_none=True))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

            history.append({"role": "user", "content": body.message})
            history.append({"role": "assistant", "content": result.response})
            _chat_history[token] = history

            return {"response": result.response, "board_updates": applied}
        finally:
            conn.close()

    # -- Multi-board management --

    @application.get("/api/boards")
    async def api_list_boards(username: str = Depends(require_auth)):
        conn = get_connection(db_path)
        try:
            init_db(conn)
            user_id = ensure_user(conn, username, "password")
            ensure_board(conn, user_id)  # ensure at least one board exists
            boards = get_boards(conn, user_id)
            return {"boards": boards}
        finally:
            conn.close()

    @application.post("/api/boards")
    async def api_create_board(body: CreateBoardRequest, username: str = Depends(require_auth)):
        if not body.title.strip():
            raise HTTPException(status_code=400, detail="Board title cannot be empty")
        conn = get_connection(db_path)
        try:
            init_db(conn)
            user_id = ensure_user(conn, username, "password")
            ensure_board(conn, user_id)  # ensure default board exists
            board_id = create_board(conn, user_id, body.title.strip())
            return {"id": board_id, "title": body.title.strip()}
        finally:
            conn.close()

    @application.patch("/api/boards/{board_id}")
    async def api_rename_board(board_id: int, body: RenameBoardRequest, username: str = Depends(require_auth)):
        if not body.title.strip():
            raise HTTPException(status_code=400, detail="Board title cannot be empty")
        conn = get_connection(db_path)
        try:
            init_db(conn)
            user_id = ensure_user(conn, username, "password")
            if not rename_board(conn, board_id, user_id, body.title.strip()):
                raise HTTPException(status_code=404, detail="Board not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.delete("/api/boards/{board_id}")
    async def api_delete_board(board_id: int, username: str = Depends(require_auth)):
        conn = get_connection(db_path)
        try:
            init_db(conn)
            user_id = ensure_user(conn, username, "password")
            # Check ownership first
            board = conn.execute(
                "SELECT id FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id)
            ).fetchone()
            if not board:
                raise HTTPException(status_code=404, detail="Board not found")
            # Don't allow deleting the last board
            boards = get_boards(conn, user_id)
            if len(boards) <= 1:
                raise HTTPException(status_code=400, detail="Cannot delete the last board")
            delete_board(conn, board_id, user_id)
            return {"status": "ok"}
        finally:
            conn.close()

    @application.get("/api/boards/{board_id}")
    async def api_get_board_by_id(board_id: int, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            return get_board(conn, bid)
        finally:
            conn.close()

    # reorder must be registered before {column_id} routes to avoid capture
    @application.put("/api/boards/{board_id}/columns/reorder")
    async def api_reorder_columns(board_id: int, body: ReorderColumnsRequest, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not reorder_columns(conn, bid, body.column_ids):
                raise HTTPException(status_code=400, detail="Invalid column IDs for this board")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.put("/api/boards/{board_id}/columns/{column_id}")
    async def api_rename_column_by_board(board_id: int, column_id: str, body: RenameColumnRequest, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not rename_column(conn, bid, column_id, body.title):
                raise HTTPException(status_code=404, detail="Column not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.post("/api/boards/{board_id}/columns")
    async def api_create_column(board_id: int, body: CreateColumnRequest, username: str = Depends(require_auth)):
        if not body.title.strip():
            raise HTTPException(status_code=400, detail="Column title cannot be empty")
        conn, bid = _get_board_for_user(username, board_id)
        try:
            col_id = create_column(conn, bid, body.title.strip())
            if col_id is None:
                raise HTTPException(status_code=404, detail="Board not found")
            return {"id": col_id, "title": body.title.strip()}
        finally:
            conn.close()

    @application.delete("/api/boards/{board_id}/columns/{column_id}")
    async def api_delete_column(board_id: int, column_id: str, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not delete_column(conn, bid, column_id):
                raise HTTPException(status_code=404, detail="Column not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.post("/api/boards/{board_id}/cards")
    async def api_create_card_by_board(board_id: int, body: CreateCardRequest, username: str = Depends(require_auth)):
        if body.priority not in VALID_PRIORITIES:
            raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not create_card(conn, bid, body.column_id, body.id, body.title, body.details, body.due_date, body.priority):
                raise HTTPException(status_code=404, detail="Column not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.put("/api/boards/{board_id}/cards/{card_id}")
    async def api_update_card_by_board(board_id: int, card_id: str, body: UpdateCardRequest, username: str = Depends(require_auth)):
        if body.priority not in VALID_PRIORITIES:
            raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not update_card(conn, bid, card_id, body.title, body.details, body.due_date, body.priority):
                raise HTTPException(status_code=404, detail="Card not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.delete("/api/boards/{board_id}/cards/{card_id}")
    async def api_delete_card_by_board(board_id: int, card_id: str, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not delete_card(conn, bid, card_id):
                raise HTTPException(status_code=404, detail="Card not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.put("/api/boards/{board_id}/cards/{card_id}/move")
    async def api_move_card_by_board(board_id: int, card_id: str, body: MoveCardRequest, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not move_card(conn, bid, card_id, body.column_id, body.position):
                raise HTTPException(status_code=404, detail="Card or column not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.put("/api/boards/{board_id}/bulk")
    async def api_bulk_update_by_board(board_id: int, body: BulkUpdateRequest, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            bulk_update(conn, bid, body.model_dump())
            return {"status": "ok"}
        finally:
            conn.close()

    @application.post("/api/boards/{board_id}/ai/chat")
    async def ai_chat_by_board(board_id: int, body: ChatRequest, auth: tuple[str, str] = Depends(require_auth_with_token)):
        username, token = auth
        conn, bid = _get_board_for_user(username, board_id)
        chat_key = f"{token}:{bid}"
        try:
            board_state = get_board(conn, bid)
            history = _chat_history.get(chat_key, [])

            try:
                result = chat_with_board(board_state, body.message, history)
            except AINotConfiguredError:
                raise HTTPException(status_code=503, detail="AI service not configured")
            except AIServiceError as exc:
                raise HTTPException(status_code=502, detail=str(exc))

            applied = []
            try:
                for action in result.board_updates:
                    if action.action == "create_card":
                        create_card(conn, bid, action.column_id, action.card_id, action.title, action.details or "", action.due_date, action.priority or "none", commit=False)
                    elif action.action == "edit_card":
                        update_card(conn, bid, action.card_id, action.title, action.details or "", action.due_date, action.priority or "none", commit=False)
                    elif action.action == "delete_card":
                        delete_card(conn, bid, action.card_id, commit=False)
                    elif action.action == "move_card":
                        move_card(conn, bid, action.card_id, action.column_id, action.position, commit=False)
                    elif action.action == "rename_column":
                        rename_column(conn, bid, action.column_id, action.title, commit=False)
                    applied.append(action.model_dump(exclude_none=True))
                conn.commit()
            except Exception:
                conn.rollback()
                raise

            history.append({"role": "user", "content": body.message})
            history.append({"role": "assistant", "content": result.response})
            _chat_history[chat_key] = history

            return {"response": result.response, "board_updates": applied}
        finally:
            conn.close()

    @application.get("/api/boards/{board_id}/stats")
    async def api_board_stats(board_id: int, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            return get_board_stats(conn, bid)
        finally:
            conn.close()

    @application.get("/api/boards/{board_id}/search")
    async def api_search_cards(board_id: int, q: str = "", username: str = Depends(require_auth)):
        if not q.strip():
            return {"cards": []}
        conn, bid = _get_board_for_user(username, board_id)
        try:
            return {"cards": search_cards(conn, bid, q.strip())}
        finally:
            conn.close()

    @application.get("/api/boards/{board_id}/cards/{card_id}/comments")
    async def api_get_comments(board_id: int, card_id: str, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            comments = get_comments(conn, bid, card_id)
            if comments is None:
                raise HTTPException(status_code=404, detail="Card not found")
            return {"comments": comments}
        finally:
            conn.close()

    @application.post("/api/boards/{board_id}/cards/{card_id}/comments")
    async def api_add_comment(board_id: int, card_id: str, body: AddCommentRequest, username: str = Depends(require_auth)):
        if not body.body.strip():
            raise HTTPException(status_code=400, detail="Comment body cannot be empty")
        conn, bid = _get_board_for_user(username, board_id)
        try:
            user_id = get_user_id(conn, username)
            if user_id is None:
                raise HTTPException(status_code=404, detail="User not found")
            comment = add_comment(conn, bid, card_id, user_id, body.body.strip())
            if comment is None:
                raise HTTPException(status_code=404, detail="Card not found")
            return comment
        finally:
            conn.close()

    @application.delete("/api/boards/{board_id}/cards/{card_id}/comments/{comment_id}")
    async def api_delete_comment(board_id: int, card_id: str, comment_id: int, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            user_id = get_user_id(conn, username)
            if user_id is None:
                raise HTTPException(status_code=404, detail="User not found")
            if not delete_comment(conn, bid, card_id, comment_id, user_id):
                raise HTTPException(status_code=404, detail="Comment not found")
            return {"status": "ok"}
        finally:
            conn.close()

    # -- Label routes --

    @application.get("/api/boards/{board_id}/labels")
    async def api_get_labels(board_id: int, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            return {"labels": get_labels(conn, bid)}
        finally:
            conn.close()

    @application.post("/api/boards/{board_id}/labels")
    async def api_create_label(board_id: int, body: CreateLabelRequest, username: str = Depends(require_auth)):
        if not body.name.strip():
            raise HTTPException(status_code=400, detail="Label name cannot be empty")
        conn, bid = _get_board_for_user(username, board_id)
        try:
            return create_label(conn, bid, body.name.strip(), body.color)
        finally:
            conn.close()

    @application.delete("/api/boards/{board_id}/labels/{label_id}")
    async def api_delete_label(board_id: int, label_id: int, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not delete_label(conn, bid, label_id):
                raise HTTPException(status_code=404, detail="Label not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.get("/api/boards/{board_id}/cards/{card_id}/labels")
    async def api_get_card_labels(board_id: int, card_id: str, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            labels = get_card_labels(conn, bid, card_id)
            if labels is None:
                raise HTTPException(status_code=404, detail="Card not found")
            return {"labels": labels}
        finally:
            conn.close()

    @application.post("/api/boards/{board_id}/cards/{card_id}/labels/{label_id}")
    async def api_set_card_label(board_id: int, card_id: str, label_id: int, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not set_card_label(conn, bid, card_id, label_id):
                raise HTTPException(status_code=404, detail="Card or label not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.delete("/api/boards/{board_id}/cards/{card_id}/labels/{label_id}")
    async def api_remove_card_label(board_id: int, card_id: str, label_id: int, username: str = Depends(require_auth)):
        conn, bid = _get_board_for_user(username, board_id)
        try:
            if not remove_card_label(conn, bid, card_id, label_id):
                raise HTTPException(status_code=404, detail="Label not assigned to card")
            return {"status": "ok"}
        finally:
            conn.close()

    # -- Legacy single-board routes (keep for backward compat) --

    @application.get("/api/board")
    async def api_get_board(username: str = Depends(require_auth)):
        conn, board_id = _get_board_id(username)
        try:
            return get_board(conn, board_id)
        finally:
            conn.close()

    @application.put("/api/board/columns/{column_id}")
    async def api_rename_column(column_id: str, body: RenameColumnRequest, username: str = Depends(require_auth)):
        conn, board_id = _get_board_id(username)
        try:
            if not rename_column(conn, board_id, column_id, body.title):
                raise HTTPException(status_code=404, detail="Column not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.post("/api/board/cards")
    async def api_create_card(body: CreateCardRequest, username: str = Depends(require_auth)):
        if body.priority not in VALID_PRIORITIES:
            raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")
        conn, board_id = _get_board_id(username)
        try:
            if not create_card(conn, board_id, body.column_id, body.id, body.title, body.details, body.due_date, body.priority):
                raise HTTPException(status_code=404, detail="Column not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.put("/api/board/cards/{card_id}")
    async def api_update_card(card_id: str, body: UpdateCardRequest, username: str = Depends(require_auth)):
        if body.priority not in VALID_PRIORITIES:
            raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}")
        conn, board_id = _get_board_id(username)
        try:
            if not update_card(conn, board_id, card_id, body.title, body.details, body.due_date, body.priority):
                raise HTTPException(status_code=404, detail="Card not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.delete("/api/board/cards/{card_id}")
    async def api_delete_card(card_id: str, username: str = Depends(require_auth)):
        conn, board_id = _get_board_id(username)
        try:
            if not delete_card(conn, board_id, card_id):
                raise HTTPException(status_code=404, detail="Card not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.put("/api/board/cards/{card_id}/move")
    async def api_move_card(card_id: str, body: MoveCardRequest, username: str = Depends(require_auth)):
        conn, board_id = _get_board_id(username)
        try:
            if not move_card(conn, board_id, card_id, body.column_id, body.position):
                raise HTTPException(status_code=404, detail="Card or column not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.put("/api/board")
    async def api_bulk_update(body: BulkUpdateRequest, username: str = Depends(require_auth)):
        conn, board_id = _get_board_id(username)
        try:
            bulk_update(conn, board_id, body.model_dump())
            return {"status": "ok"}
        finally:
            conn.close()

    # -- Static frontend --

    if static_dir.is_dir():
        next_dir = static_dir / "_next"
        if next_dir.is_dir():
            application.mount(
                "/_next", StaticFiles(directory=next_dir), name="next-assets"
            )

        @application.get("/{path:path}")
        async def serve_frontend(path: str):
            file_path = static_dir / path
            if file_path.is_file():
                return FileResponse(file_path)
            index = static_dir / "index.html"
            if index.is_file():
                return FileResponse(index)
            return {"error": "not found"}

    return application


app = create_app()
