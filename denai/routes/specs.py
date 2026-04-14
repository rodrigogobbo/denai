"""Rotas de leitura de specs SDS do projeto ativo via /context."""

from __future__ import annotations

import json
import os as _os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from ..config import DEFAULT_MODEL
from ..context_store import get_context
from ..llm import stream_chat

router = APIRouter(prefix="/api/specs", tags=["specs"])


class SpecsBody(BaseModel):
    conversation_id: str


class SpecsReadBody(BaseModel):
    conversation_id: str
    slug: str


class SpecsAnalyzeBody(BaseModel):
    conversation_id: str
    slug: str
    model: str = DEFAULT_MODEL
    question: str = (
        "Qual o status atual desta implementação no repositório? "
        "Aponte tasks concluídas (✅) e pendentes (⬜), cite arquivos relevantes "
        "encontrados e faça um resumo de 2-3 linhas."
    )


def _get_specs_dir(conv_id: str) -> tuple[Path | None, str | None]:
    """Retorna o diretório specs/changes/ do projeto ativo, ou erro."""
    ctx = get_context(conv_id)
    if not ctx:
        return None, "Nenhum repositório ativo. Use `/context <caminho>` primeiro."

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


def _load_spec_content(specs_dir: Path, slug: str) -> tuple[str | None, str | None]:
    """Carrega e concatena os arquivos de uma spec. Retorna (content, error)."""
    safe_slug = _os.path.basename(_os.path.normpath(slug))
    spec_dir = specs_dir / safe_slug

    if not spec_dir.exists():
        available = [d.name for d in specs_dir.iterdir() if d.is_dir()]
        return None, f"Spec `{safe_slug}` não encontrada. Disponíveis: {', '.join(available) or 'nenhuma'}"

    parts = []
    for fname in ("requirements.md", "design.md", "tasks.md"):
        fpath = spec_dir / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8", errors="replace")
            parts.append(f"## 📄 {fname}\n\n{content}")

    if not parts:
        return None, f"Spec `{safe_slug}` está vazia."

    return "\n\n---\n\n".join(parts), None


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

    content, err = _load_spec_content(specs_dir, body.slug)
    if err:
        return JSONResponse({"error": err}, status_code=404)

    safe_slug = _os.path.basename(_os.path.normpath(body.slug.strip().strip("/")))
    return {"slug": safe_slug, "content": content}


@router.post("/analyze")
async def analyze_spec(body: SpecsAnalyzeBody):
    """Analisa o status de implementação de uma spec usando o LLM. Streaming SSE."""
    specs_dir, error = _get_specs_dir(body.conversation_id)
    if error:
        return JSONResponse({"error": error}, status_code=400)

    spec_content, err = _load_spec_content(specs_dir, body.slug)
    if err:
        return JSONResponse({"error": err}, status_code=404)

    ctx = get_context(body.conversation_id)
    project_name = ctx["project_name"] if ctx else "projeto"
    project_path = ctx["path"] if ctx else ""

    safe_slug = _os.path.basename(_os.path.normpath(body.slug.strip().strip("/")))

    system_prompt = (
        f"Você é um assistente de engenharia de software especialista em "
        f"Spec-Driven Development (SDS). "
        f"Você está analisando a spec **{safe_slug}** do projeto **{project_name}** "
        f"localizado em `{project_path}`. "
        f"Use suas ferramentas (bash, read_file, glob) para inspecionar o repositório "
        f"e verificar o que já foi implementado. Seja objetivo e preciso."
    )

    user_message = f"Analise a spec abaixo e responda: {body.question}\n\n---\n\n{spec_content}"

    messages = [{"role": "user", "content": user_message}]

    sse_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    async def generate():
        yield f"data: {json.dumps({'slug': safe_slug, 'analyzing': True})}\n\n"
        async for chunk in stream_chat(
            messages,
            body.model,
            system_override=system_prompt,
            conversation_id=body.conversation_id,
        ):
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream", headers=sse_headers)
