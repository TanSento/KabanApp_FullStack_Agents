from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DEFAULT_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(static_dir: Path | None = None) -> FastAPI:
    if static_dir is None:
        static_dir = DEFAULT_STATIC_DIR

    application = FastAPI(title="Kanban Studio API")

    @application.get("/api/health")
    async def health():
        return {"status": "ok"}

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
