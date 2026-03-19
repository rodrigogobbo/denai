"""Rota UI — serve interface web + tela de login."""

import secrets

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..config import STATIC_DIR, SHARE_MODE
from ..security.auth import API_KEY

router = APIRouter()

LOGIN_HTML = STATIC_DIR / "login.html"
UI_HTML = STATIC_DIR / "ui.html"


@router.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    """Serve a interface web.
    - Local (127.0.0.1): injeta API key automaticamente
    - Remoto (rede): mostra login ou valida cookie
    """
    if not UI_HTML.exists():
        return HTMLResponse(
            "<h1>ui.html não encontrado</h1>"
            "<p>Coloque o arquivo em denai/static/ui.html</p>"
        )

    client_ip = request.client.host if request.client else "unknown"
    is_local = client_ip in ("127.0.0.1", "::1", "localhost")

    # Acesso local: key automática
    if is_local:
        return _serve_with_key()

    # Acesso remoto: verificar cookie
    cookie_key = request.cookies.get("denai_key", "")
    if cookie_key and secrets.compare_digest(cookie_key, API_KEY):
        return _serve_with_key()

    # Sem auth: mostrar login
    if LOGIN_HTML.exists():
        return HTMLResponse(LOGIN_HTML.read_text(encoding="utf-8"))
    return HTMLResponse(_FALLBACK_LOGIN)


def _serve_with_key() -> HTMLResponse:
    html = UI_HTML.read_text(encoding="utf-8")
    inject = f'<script>window.__DENAI_API_KEY__ = "{API_KEY}";</script>'
    html = html.replace("</head>", f"{inject}\n</head>")
    return HTMLResponse(html)


_FALLBACK_LOGIN = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🐺 DenAI — Login</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0a0a0f;color:#e4e4e7;display:flex;align-items:center;justify-content:center;min-height:100vh}
.card{background:#16161e;border:1px solid #27272a;border-radius:16px;padding:48px 40px;max-width:400px;width:90%;text-align:center}
.wolf{font-size:64px;margin-bottom:16px}
h1{font-size:22px;margin-bottom:8px}
.sub{color:#71717a;font-size:14px;margin-bottom:32px;line-height:1.5}
input{width:100%;padding:12px 16px;background:#0a0a0f;border:1px solid #3f3f46;border-radius:8px;color:#e4e4e7;font-size:15px;outline:none;margin-bottom:16px}
input:focus{border-color:#21c25e}
button{width:100%;padding:12px;background:#21c25e;color:#000;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer}
button:hover{background:#1da94f}
.err{color:#ef4444;font-size:13px;margin-top:12px;display:none}
.hint{color:#52525b;font-size:12px;margin-top:24px;line-height:1.6}
code{background:#27272a;padding:2px 6px;border-radius:4px;font-size:11px}
</style></head><body>
<div class="card">
<div class="wolf">🐺</div><h1>DenAI</h1>
<p class="sub">Assistente de IA local. Digite a chave de acesso.</p>
<form onsubmit="return doLogin()">
<input type="password" id="k" placeholder="Cole a chave aqui..." autofocus>
<button type="submit">Entrar</button>
<p class="err" id="e">Chave incorreta.</p>
</form>
<p class="hint">A chave está em <code>~/.denai/api.key</code></p>
</div>
<script>
async function doLogin(){
  const k=document.getElementById('k').value.trim();
  if(!k)return false;
  try{
    const r=await fetch('/api/models',{headers:{'X-API-Key':k}});
    if(r.ok){document.cookie='denai_key='+encodeURIComponent(k)+';path=/;max-age=31536000;SameSite=Strict';location.reload()}
    else document.getElementById('e').style.display='block';
  }catch(e){document.getElementById('e').style.display='block'}
  return false;
}
</script></body></html>"""
