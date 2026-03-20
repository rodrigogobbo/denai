"""Rotas de modelos — listar, baixar e deletar (multi-provider)."""

from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import DEFAULT_MODEL, OLLAMA_URL
from ..llm.providers import (
    Provider,
    get_all_providers,
    get_provider,
    list_models_for_provider,
    register_provider,
)
from ..logging_config import get_logger

log = get_logger("routes.models")

router = APIRouter()

_TIMEOUT = httpx.Timeout(3600.0, connect=10.0)


# ── Providers ─────────────────────────────────────────────────────


@router.get("/api/providers")
async def list_providers():
    """Lista providers configurados."""
    providers = get_all_providers()
    return {
        "providers": [
            {
                "name": p.name,
                "kind": p.kind,
                "base_url": p.base_url,
                "has_key": bool(p.api_key),
            }
            for p in providers
        ]
    }


@router.post("/api/providers")
async def add_provider(request: Request):
    """Adiciona um provider OpenAI-compatible."""
    body = await request.json()
    try:
        provider = Provider(
            name=body["name"],
            kind=body.get("kind", "openai"),
            base_url=body["base_url"],
            api_key=body.get("api_key", ""),
        )
        register_provider(provider)
        return {"ok": True, "provider": provider.name}
    except (KeyError, TypeError) as e:
        log.error("Erro ao adicionar provider: %s", e)
        return {"error": "Parâmetros inválidos para o provider"}


# ── Models (multi-provider) ──────────────────────────────────────


@router.get("/api/models")
async def list_models(provider: str | None = None):
    """Lista modelos de todos os providers (ou de um específico)."""
    if provider:
        # Single provider
        prov = get_provider(provider)
        if not prov:
            return {"models": [], "default": DEFAULT_MODEL, "error": f"Provider '{provider}' não encontrado"}
        models = await list_models_for_provider(prov)
        return {"models": models, "default": DEFAULT_MODEL, "provider": prov.name}

    # All providers — collect from each
    all_models: list[dict] = []
    errors: list[str] = []

    for prov in get_all_providers():
        try:
            models = await list_models_for_provider(prov)
            all_models.extend(models)
        except Exception as e:
            log.error("Erro ao listar modelos do provider '%s': %s", prov.name, e)
            errors.append(f"{prov.name}: erro ao listar modelos")

    result: dict = {"models": all_models, "default": DEFAULT_MODEL}
    if errors:
        result["errors"] = errors
    return result


# ── Pull (Ollama only) ───────────────────────────────────────────


@router.post("/api/models/pull")
async def pull_model(request: Request):
    body = await request.json()
    model_name = body.get("model")
    if not model_name:
        return JSONResponse({"error": "campo 'model' obrigatório"}, status_code=400)

    async def generate():
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                async with client.stream("POST", f"{OLLAMA_URL}/api/pull", json={"name": model_name}) as resp:
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        parsed = json.loads(line)
                        event = {
                            "status": parsed.get("status", ""),
                            "completed": parsed.get("completed"),
                            "total": parsed.get("total"),
                            "digest": parsed.get("digest"),
                        }
                        # Remove None values for cleaner output
                        event = {k: v for k, v in event.items() if v is not None}
                        yield f"data: {json.dumps(event)}\n\n"
            yield f"data: {json.dumps({'status': 'success'})}\n\n"
        except httpx.ConnectError:
            yield f"data: {json.dumps({'status': 'error', 'error': 'Ollama não acessível'})}\n\n"
        except Exception as e:
            log.error("Erro ao baixar modelo '%s': %s", model_name, e)
            yield f"data: {json.dumps({'status': 'error', 'error': 'Erro interno ao baixar modelo'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Delete (Ollama only) ─────────────────────────────────────────


@router.delete("/api/models/{name:path}")
async def delete_model(name: str):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.delete(f"{OLLAMA_URL}/api/delete", json={"name": name})
            if resp.status_code == 200:
                return {"status": "deleted", "model": name}
            return JSONResponse(
                {"error": resp.text or "Falha ao deletar modelo"},
                status_code=resp.status_code,
            )
    except httpx.ConnectError:
        return JSONResponse({"error": "Ollama não acessível"}, status_code=502)


# ── Ollama status ─────────────────────────────────────────────────


@router.get("/api/ollama/status")
async def ollama_status():
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            ver_resp = await c.get(f"{OLLAMA_URL}/api/version")
            version = ver_resp.json().get("version", "unknown") if ver_resp.status_code == 200 else "unknown"
            tags_resp = await c.get(f"{OLLAMA_URL}/api/tags")
            models_count = len(tags_resp.json().get("models", [])) if tags_resp.status_code == 200 else 0
            return {"status": "online", "version": version, "models_count": models_count}
    except Exception:
        return {"status": "offline", "version": None, "models_count": 0}
