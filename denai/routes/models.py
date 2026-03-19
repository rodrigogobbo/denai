"""Rotas de modelos — listar, baixar e deletar."""

from __future__ import annotations

import json

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import DEFAULT_MODEL, OLLAMA_URL

router = APIRouter()

_TIMEOUT = httpx.Timeout(3600.0, connect=10.0)


@router.get("/api/models")
async def list_models():
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                data = r.json()
                models = [m["name"] for m in data.get("models", [])]
                return {"models": models, "default": DEFAULT_MODEL}
    except Exception:
        pass
    return {"models": [], "default": DEFAULT_MODEL, "error": "Ollama não acessível"}


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
            yield f"data: {json.dumps({'status': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
