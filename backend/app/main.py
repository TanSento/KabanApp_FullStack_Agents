from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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


# -- Auth dependency --

def require_auth(authorization: str = Header()) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    username = get_user(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username


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
