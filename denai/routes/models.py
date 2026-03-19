"""Rotas de modelos — listar e baixar."""

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..config import DEFAULT_MODEL, OLLAMA_URL

router = APIRouter()


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


@router.post("/api/pull")
async def pull_model(request: Request):
    body = await request.json()
    model_name = body.get("model", DEFAULT_MODEL)

    async def generate():
        async with httpx.AsyncClient(timeout=httpx.Timeout(3600.0, connect=10.0)) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/pull", json={"name": model_name}) as resp:
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield f"data: {line}\n\n"
        yield 'data: {"done": true}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/api/ollama/status")
async def ollama_status():
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            # Get version
            ver_resp = await c.get(f"{OLLAMA_URL}/api/version")
            version = ver_resp.json().get("version", "unknown") if ver_resp.status_code == 200 else "unknown"

            # Get model count
            tags_resp = await c.get(f"{OLLAMA_URL}/api/tags")
            models_count = len(tags_resp.json().get("models", [])) if tags_resp.status_code == 200 else 0

            return {"status": "online", "version": version, "models_count": models_count}
    except Exception:
        return {"status": "offline", "version": None, "models_count": 0}
