"""Rotas de leitura de specs SDS do projeto ativo via /context."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..context_store import get_context

router = APIRouter(prefix="/api/specs", tags=["specs"])


class SpecsBody(BaseModel):
    conversation_id: str


class SpecsReadBody(BaseModel):
    conversation_id: str
    slug: str


def _get_specs_dir(conv_id: str) -> tuple[Path | None, str | None]:
    """Retorna o diretório specs/changes/ do projeto ativo, ou erro."""
    ctx = get_context(conv_id)
    if not ctx:
        return None, "Nenhum repositório ativo. Use `/context <caminho>` primeiro."

    # Usar os.path para sanitizar o path (padrão reconhecido pelo CodeQL)
    import os as _os

    try:
        safe_path = _os.path.realpath(_os.path.abspath(ctx["path"]))
    except (ValueError, OSError):
        return None, "Caminho do projeto inválido."

    specs_dir = Path(safe_path) / "specs" / "changes"

    if not specs_dir.exists():
        return None, (
            f"O projeto **{ctx['project_name']}** não tem `specs/changes/`.\n"
            "Este comando funciona com projetos que usam Spec-Driven Development (SDS)."
        )

    return specs_dir, None


@router.post("/list")
async def list_specs(body: SpecsBody):
    """Lista as specs disponíveis no projeto ativo."""
    specs_dir, error = _get_specs_dir(body.conversation_id)
    if error:
        return JSONResponse({"error": error}, status_code=400)

    slugs = sorted(d.name for d in specs_dir.iterdir() if d.is_dir() and not d.name.startswith("."))

    if not slugs:
        return {"specs": [], "message": "Nenhuma spec encontrada em `specs/changes/`."}

    return {
        "specs": slugs,
        "project": get_context(body.conversation_id)["project_name"],
    }


@router.post("/read")
async def read_spec(body: SpecsReadBody):
    """Retorna o conteúdo de uma spec (requirements + design + tasks)."""
    specs_dir, error = _get_specs_dir(body.conversation_id)
    if error:
        return JSONResponse({"error": error}, status_code=400)

    slug = body.slug.strip().strip("/")
    spec_dir = specs_dir / slug

    if not spec_dir.exists():
        available = [d.name for d in specs_dir.iterdir() if d.is_dir()]
        return JSONResponse(
            {"error": f"Spec `{slug}` não encontrada.", "available": available},
            status_code=404,
        )

    parts = []
    for fname in ("requirements.md", "design.md", "tasks.md"):
        fpath = spec_dir / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8", errors="replace")
            parts.append(f"## 📄 {fname}\n\n{content}")

    if not parts:
        return JSONResponse({"error": f"Spec `{slug}` está vazia."}, status_code=404)

    return {
        "slug": slug,
        "content": "\n\n---\n\n".join(parts),
    }
