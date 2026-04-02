"""Rotas de modelos — listar, baixar, deletar e gerenciar providers."""

from __future__ import annotations

import json
import time

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from ..config import DEFAULT_MODEL, OLLAMA_URL
from ..llm.providers import (
    Provider,
    get_all_providers,
    get_provider,
    list_models_for_provider,
    register_provider,
)
from ..logging_config import get_logger
from ..providers_store import (
    PROVIDER_TEMPLATES,
    add_or_update_provider,
    mask_api_key,
    remove_provider,
)
from ..security.url_validator import ProviderURLError, validate_provider_url

log = get_logger("routes.models")

router = APIRouter()

_TIMEOUT = httpx.Timeout(3600.0, connect=10.0)
_TEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


# ── Providers — CRUD ──────────────────────────────────────────────


@router.get("/api/providers")
async def list_providers():
    """Lista providers configurados (API keys mascaradas)."""
    providers = get_all_providers()
    return {
        "providers": [
            {
                "name": p.name,
                "kind": p.kind,
                "base_url": p.base_url,
                "has_key": bool(p.api_key),
                "api_key_masked": mask_api_key(p.api_key) if p.api_key else "",
                "models": p.models,
                "default_model": p.default_model,
                "is_default": p.name.lower() == "ollama",
            }
            for p in providers
        ]
    }


@router.get("/api/providers/templates")
async def list_templates():
    """Lista templates pré-configurados de providers."""
    return {"templates": PROVIDER_TEMPLATES}


class ProviderBody(BaseModel):
    name: str
    kind: str = "openai"
    base_url: str
    api_key: str = ""
    models: list[str] = []
    default_model: str = ""


@router.post("/api/providers")
async def add_provider(body: ProviderBody):
    """Adiciona ou atualiza um provider e persiste em ~/.denai/providers.yaml."""
    if body.name.lower() == "ollama":
        return JSONResponse({"error": "O provider Ollama padrão não pode ser substituído."}, status_code=400)

    provider = Provider(
        name=body.name,
        kind=body.kind,
        base_url=body.base_url.rstrip("/"),
        api_key=body.api_key,
        models=body.models,
        default_model=body.default_model,
    )
    register_provider(provider)

    # Persistir (sem expor a API key no retorno)
    add_or_update_provider(
        {
            "name": body.name,
            "kind": body.kind,
            "base_url": body.base_url.rstrip("/"),
            "api_key": body.api_key,
            "models": body.models,
            "default_model": body.default_model,
        }
    )

    return {
        "ok": True,
        "provider": {
            "name": provider.name,
            "kind": provider.kind,
            "base_url": provider.base_url,
            "has_key": bool(provider.api_key),
        },
    }


@router.delete("/api/providers/{name}")
async def delete_provider(name: str):
    """Remove um provider persistido."""
    if name.lower() == "ollama":
        return JSONResponse({"error": "O provider Ollama padrão não pode ser removido."}, status_code=400)

    removed = remove_provider(name)
    if not removed:
        return JSONResponse({"error": f"Provider '{name}' não encontrado."}, status_code=404)

    # Remove da memória também
    from ..llm.providers import _providers

    _providers.pop(name.lower(), None)

    return {"ok": True}


class TestProviderBody(BaseModel):
    kind: str = "openai"
    base_url: str
    api_key: str = ""


@router.post("/api/providers/test")
async def test_provider(body: TestProviderBody):
    """Testa conexão com um provider antes de salvar."""
    # Validação anti-SSRF: parse + blocklist + reconstrução quebra o taint
    # allow_localhost=True para suportar LM Studio / LocalAI em desenvolvimento
    try:
        base_url = validate_provider_url(body.base_url, allow_localhost=True)
    except ProviderURLError:
        return JSONResponse({"ok": False, "error": "URL inválida ou bloqueada por segurança."}, status_code=400)

    start = time.monotonic()

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if body.api_key:
        headers["Authorization"] = f"Bearer {body.api_key}"

    try:
        async with httpx.AsyncClient(timeout=_TEST_TIMEOUT) as client:
            if body.kind == "ollama":
                resp = await client.get(f"{base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
            else:
                # OpenAI-compat: tenta listar modelos
                resp = await client.get(f"{base_url}/v1/models", headers=headers)
                if resp.status_code == 401:
                    return {"ok": False, "error": "API key inválida ou ausente.", "latency_ms": None}
                if resp.status_code == 404:
                    # Alguns providers não têm /v1/models — tenta /api/tags
                    resp2 = await client.get(f"{base_url}/api/tags")
                    models = [m["name"] for m in resp2.json().get("models", [])] if resp2.status_code == 200 else []
                else:
                    resp.raise_for_status()
                    data = resp.json()
                    models = [m["id"] for m in data.get("data", [])]

        latency_ms = round((time.monotonic() - start) * 1000)
        return {
            "ok": True,
            "latency_ms": latency_ms,
            "models_found": len(models),
            "models": models[:10],
        }

    except httpx.ConnectError:
        return {"ok": False, "error": "Não foi possível conectar. Verifique a URL.", "latency_ms": None}
    except httpx.TimeoutException:
        return {"ok": False, "error": "Timeout ao conectar (>10s).", "latency_ms": None}
    except Exception as e:
        log.warning("Teste de provider falhou: %s", e)
        return {"ok": False, "error": "Falha ao testar conexão. Verifique a URL e a API key.", "latency_ms": None}


# ── Models (multi-provider) ──────────────────────────────────────


@router.get("/api/models")
async def list_models(provider: str | None = None):
    """Lista modelos de todos os providers (ou de um específico)."""
    if provider:
        prov = get_provider(provider)
        if not prov:
            return {"models": [], "default": DEFAULT_MODEL, "error": f"Provider '{provider}' não encontrado"}
        models = await list_models_for_provider(prov)
        return {"models": models, "default": DEFAULT_MODEL, "provider": prov.name}

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
            async with (
                httpx.AsyncClient(timeout=_TIMEOUT) as client,
                client.stream("POST", f"{OLLAMA_URL}/api/pull", json={"name": model_name}) as resp,
            ):
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
