"""Rotas de project analysis (/init) e context persistente."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..project import analyze_project, load_context, save_context

router = APIRouter()


def _project_to_dict(info) -> dict:
    """Convert ProjectInfo to API response dict."""
    return {
        "name": info.name,
        "path": info.path,
        "languages": info.languages,
        "ecosystems": info.ecosystems,
        "frameworks": info.frameworks,
        "key_files": info.key_files,
        "file_count": info.file_count,
        "dir_count": info.dir_count,
        "description": info.description,
        "git": info.git_info,
        "tree": info.tree,
    }


@router.post("/api/project/init")
async def init_project(body: dict | None = None):
    """Analyze a project directory, persist context, and return results."""
    path = None
    if body and body.get("path"):
        path = body["path"]

    info = analyze_project(path)
    save_context(info)

    return {
        "ok": True,
        "project": _project_to_dict(info),
        "context": info.to_context(),
    }


@router.get("/api/project/init")
async def init_project_get(path: str | None = None):
    """GET variant for convenience."""
    info = analyze_project(path)
    save_context(info)

    return {
        "ok": True,
        "project": _project_to_dict(info),
        "context": info.to_context(),
    }


@router.get("/api/project/context")
async def get_project_context(path: str | None = None):
    """Return persisted project context, or 404 if not found."""
    ctx = load_context(path)
    if ctx is None:
        return JSONResponse(
            {"error": "No project context found. Run /init first."},
            status_code=404,
        )
    return {"ok": True, "context": ctx}
