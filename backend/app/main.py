from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.auth import get_user, login, logout

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


class UserResponse(BaseModel):
    username: str


def require_auth(authorization: str = Header()) -> str:
    """Dependency that extracts and validates the Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ")
    username = get_user(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return username


def create_app(static_dir: Path | None = None) -> FastAPI:
    if static_dir is None:
        static_dir = DEFAULT_STATIC_DIR

    application = FastAPI(title="Kanban Studio API")

    @application.get("/api/health")
    async def health():
        return {"status": "ok"}

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
