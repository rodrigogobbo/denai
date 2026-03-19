"""
FastAPI application — monta middleware, rotas e startup.
Ponto central de wiring. Nenhuma lógica de negócio aqui.
"""

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import DATA_DIR, DEFAULT_MODEL, HOST, OLLAMA_URL, PORT, SHARE_MODE, STATIC_DIR
from .db import init_db
from .network import LOCAL_IP
from .routes import all_routers
from .security import API_KEY, PUBLIC_PATHS, rate_limiter, verify_api_key


def create_app() -> FastAPI:
    app = FastAPI(title="DenAI", version="0.1.0")

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

    # ── Auth + Rate Limit middleware ──
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path

        if path in PUBLIC_PATHS or path.startswith("/static"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                {"error": "Rate limit excedido. Aguarde um momento."},
                status_code=429,
            )

        provided_key = (
            request.headers.get("X-API-Key")
            or request.query_params.get("key")
        )
        if not verify_api_key(provided_key):
            return JSONResponse(
                {"error": "API key inválida ou ausente."},
                status_code=401,
            )

        return await call_next(request)

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
            "version": "0.1.0",
            "ollama": ollama_ok,
            "ollama_version": ollama_version,
            "model": DEFAULT_MODEL,
            "share_mode": SHARE_MODE,
            "local_ip": LOCAL_IP if SHARE_MODE else None,
        }

    # ── Static files (vendor JS/CSS) ──
    vendor_dir = STATIC_DIR / "vendor"
    if vendor_dir.is_dir():
        app.mount("/static/vendor", StaticFiles(directory=str(vendor_dir)), name="vendor")

    # ── Registrar routers ──
    for router in all_routers:
        app.include_router(router)

    # ── Startup ──
    @app.on_event("startup")
    async def startup():
        await init_db()
        _print_banner()

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
  🐺 DenAI v0.1.0
  ─────────────────────────────────────
  URL:     http://{HOST}:{PORT}
  Ollama:  {OLLAMA_URL}
  Dados:   {DATA_DIR}
  🔒 Auth + Sandbox + Rate Limit
{share_block}
  ─────────────────────────────────────
""")


# Instância global pra uvicorn importar
app = create_app()
