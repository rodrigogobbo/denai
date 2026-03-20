"""
FastAPI application — monta middleware, rotas e startup.
Ponto central de wiring. Nenhuma lógica de negócio aqui.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from urllib.parse import parse_qs

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import DATA_DIR, DEFAULT_MODEL, HOST, OLLAMA_URL, PORT, SHARE_MODE, STATIC_DIR
from .db import init_db
from .logging_config import LOG_FILE, setup_logging
from .network import LOCAL_IP
from .routes import all_routers
from .security import API_KEY, PUBLIC_PATHS, rate_limiter, verify_api_key
from .version import VERSION

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_db()
    logger.info("DenAI v%s iniciado — model=%s, port=%s", VERSION, DEFAULT_MODEL, PORT)
    _print_banner()
    yield
    logger.info("DenAI encerrado.")


class AuthMiddleware:
    """ASGI middleware — não bufferiza StreamingResponse (ao contrário de @app.middleware)."""

    def __init__(self, app):  # noqa: ANN001
        self.app = app

    async def __call__(self, scope, receive, send):  # noqa: ANN001
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Rotas públicas e estáticas passam direto
        if path in PUBLIC_PATHS or path.startswith("/static"):
            await self.app(scope, receive, send)
            return

        # Rate limit por IP
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            await self._send_json(send, 429, {"error": "Rate limit excedido. Aguarde um momento."})
            return

        # Auth via header ou query param
        headers_list = scope.get("headers", [])
        api_key = ""
        for name, value in headers_list:
            if name == b"x-api-key":
                api_key = value.decode()
                break
        if not api_key:
            qs = scope.get("query_string", b"").decode()
            params = parse_qs(qs)
            api_key = params.get("key", [""])[0]

        if not verify_api_key(api_key):
            await self._send_json(send, 401, {"error": "API key inválida ou ausente."})
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _send_json(send, status: int, body: dict) -> None:  # noqa: ANN001
        payload = json.dumps(body).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"content-length", str(len(payload)).encode()],
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})


def create_app() -> FastAPI:
    app = FastAPI(title="DenAI", version=VERSION, lifespan=lifespan)

    # ── CORS ──
    cors_origins = [
        f"http://localhost:{PORT}",
        f"http://127.0.0.1:{PORT}",
    ]
    if SHARE_MODE:
        cors_origins.append(f"http://{LOCAL_IP}:{PORT}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    # ── Auth + Rate Limit (ASGI — preserva streaming) ──
    app.add_middleware(AuthMiddleware)

    # ── Health (público) ──
    @app.get("/api/health")
    async def health():
        ollama_ok = False
        ollama_version = None
        try:
            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{OLLAMA_URL}/api/version")
                if r.status_code == 200:
                    ollama_ok = True
                    ollama_version = r.json().get("version")
        except Exception:
            pass
        return {
            "status": "ok",
            "version": VERSION,
            "ollama": ollama_ok,
            "ollama_version": ollama_version,
            "model": DEFAULT_MODEL,
            "share_mode": SHARE_MODE,
            "local_ip": LOCAL_IP if SHARE_MODE else None,
        }

    # ── Static files ──
    # Mount vendor first (more specific), then catch-all /static
    vendor_dir = STATIC_DIR / "vendor"
    if vendor_dir.is_dir():
        app.mount("/static/vendor", StaticFiles(directory=str(vendor_dir)), name="vendor")
    if STATIC_DIR.is_dir():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # ── Registrar routers ──
    for router in all_routers:
        app.include_router(router)

    return app


def _print_banner():
    share_block = ""
    if SHARE_MODE:
        url = f"http://{LOCAL_IP}:{PORT}"
        share_block = f"""
  🌐 MODO COMPARTILHADO
  📱 URL:  {url}
  🔑 Key:  {API_KEY}
  Passe a URL + key pra quem quiser acessar."""
    else:
        share_block = """
  💡 Pra compartilhar: python -m denai --compartilhar"""

    print(f"""
  🐺 DenAI v{VERSION}
  ─────────────────────────────────────
  URL:     http://{HOST}:{PORT}
  Ollama:  {OLLAMA_URL}
  Dados:   {DATA_DIR}
  Logs:    {LOG_FILE}
  🔒 Auth + Sandbox + Rate Limit
{share_block}
  ─────────────────────────────────────
""")


# Instância global pra uvicorn importar
app = create_app()
