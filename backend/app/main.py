from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.ai import AINotConfiguredError, AIServiceError, chat, chat_with_board
from app.auth import get_user, login, logout
from app.db import (
    bulk_update,
    create_card,
    delete_card,
    ensure_board,
    ensure_user,
    get_board,
    get_connection,
    init_db,
    move_card,
    rename_column,
    update_card,
)

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# -- Pydantic models --

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


class UserResponse(BaseModel):
    username: str


class RenameColumnRequest(BaseModel):
    title: str


class CreateCardRequest(BaseModel):
    column_id: str
    id: str
    title: str
    details: str = ""


class UpdateCardRequest(BaseModel):
    title: str
    details: str


class MoveCardRequest(BaseModel):
    column_id: str
    position: int


class BulkUpdateRequest(BaseModel):
    columns: list[dict]
    cards: dict[str, dict]


class ChatRequest(BaseModel):
    message: str


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
        init_db(conn)  # idempotent -- ensures tables exist
        user_id = ensure_user(conn, username, "password")
        board_id = ensure_board(conn, user_id)
        return conn, board_id

    # -- Health --

    @application.get("/api/health")
    async def health():
        return {"status": "ok"}

    # -- Auth --

    @application.post("/api/auth/login")
    async def auth_login(body: LoginRequest) -> LoginResponse:
        token = login(body.username, body.password)
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
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
    async def auth_me(username: str = Header(alias="authorization", default="")) -> UserResponse:
        if not username.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        token = username.removeprefix("Bearer ")
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

            # Apply board updates atomically — commit once after all actions succeed
            applied = []
            try:
                for action in result.board_updates:
                    if action.action == "create_card":
                        create_card(conn, board_id, action.column_id, action.card_id, action.title, action.details or "", commit=False)
                    elif action.action == "edit_card":
                        update_card(conn, board_id, action.card_id, action.title, action.details or "", commit=False)
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

            # Update conversation history
            history.append({"role": "user", "content": body.message})
            history.append({"role": "assistant", "content": result.response})
            _chat_history[token] = history

            return {"response": result.response, "board_updates": applied}
        finally:
            conn.close()

    # -- Board CRUD --

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
        conn, board_id = _get_board_id(username)
        try:
            if not create_card(conn, board_id, body.column_id, body.id, body.title, body.details):
                raise HTTPException(status_code=404, detail="Column not found")
            return {"status": "ok"}
        finally:
            conn.close()

    @application.put("/api/board/cards/{card_id}")
    async def api_update_card(card_id: str, body: UpdateCardRequest, username: str = Depends(require_auth)):
        conn, board_id = _get_board_id(username)
        try:
            if not update_card(conn, board_id, card_id, body.title, body.details):
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
