"""Rotas de project analysis (/init)."""

from __future__ import annotations

from fastapi import APIRouter

from ..project import analyze_project

router = APIRouter()


@router.post("/api/project/init")
async def init_project(body: dict | None = None):
    """Analyze a project directory and return context."""
    path = None
    if body and body.get("path"):
        path = body["path"]

    info = analyze_project(path)
    return {
        "ok": True,
        "project": {
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
        },
        "context": info.to_context(),
    }


@router.get("/api/project/init")
async def init_project_get(path: str | None = None):
    """GET variant for convenience."""
    info = analyze_project(path)
    return {
        "ok": True,
        "project": {
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
        },
        "context": info.to_context(),
    }
