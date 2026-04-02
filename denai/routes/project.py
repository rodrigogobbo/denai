"""Rotas de project analysis (/init) e context persistente."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..project import ProjectInfo, analyze_project, load_context, save_context
from ..security.sandbox import get_safe_path, is_path_allowed

router = APIRouter()


def _project_to_dict(info: ProjectInfo) -> dict:
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


def _validate_path(path: str | None) -> tuple[str | None, JSONResponse | None]:
    """Validate user-supplied path against sandbox. Returns (safe_path, error_response).

    safe_path é reconstruído internamente pelo sandbox (get_safe_path) a partir
    de Path.home() como âncora — não flui diretamente do input do usuário.
    """
    if not path:
        return None, None

    allowed, reason = is_path_allowed(path)
    if not allowed:
        return None, JSONResponse({"error": f"Caminho não permitido: {reason}"}, status_code=403)

    safe_path = get_safe_path(path)
    if safe_path is None:
        return None, JSONResponse({"error": "Caminho não permitido."}, status_code=403)

    return safe_path, None


def _analyze_and_persist(path: str | None) -> dict:
    """Shared logic for POST/GET init — analyze, save, return response."""
    info = analyze_project(path)
    save_context(info)
    return {
        "ok": True,
        "project": _project_to_dict(info),
        "context": info.to_context(),
    }


@router.post("/api/project/init")
async def init_project(body: dict | None = None):
    """Analyze a project directory, persist context, and return results."""
    raw_path = body.get("path") if body else None
    safe_path, err = _validate_path(raw_path)
    if err:
        return err
    return _analyze_and_persist(safe_path)


@router.get("/api/project/init")
async def init_project_get(path: str | None = None):
    """GET variant for convenience."""
    safe_path, err = _validate_path(path)
    if err:
        return err
    return _analyze_and_persist(safe_path)


@router.get("/api/project/context")
async def get_project_context(path: str | None = None):
    """Return persisted project context, or 404 if not found."""
    safe_path, err = _validate_path(path)
    if err:
        return err
    ctx = load_context(safe_path)
    if ctx is None:
        return JSONResponse(
            {"error": "No project context found. Run /init first."},
            status_code=404,
        )
    return {"ok": True, "context": ctx}
