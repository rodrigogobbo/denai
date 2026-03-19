"""Tool de busca web — fetch de URLs com extração de texto."""

from __future__ import annotations

import re
from ipaddress import ip_address
from urllib.parse import urlparse

import httpx

# ─── Spec ──────────────────────────────────────────────────────────────────

WEB_SEARCH_SPEC = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Busca conteúdo de uma URL na web e retorna o texto extraído. "
            "Use para pesquisar informações, ler documentação online, ou "
            "buscar dados de APIs públicas."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL completa para buscar (ex: https://example.com)",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Máximo de caracteres no resultado (padrão: 5000)",
                },
            },
            "required": ["url"],
        },
    },
}


# ─── Constants ─────────────────────────────────────────────────────────────

MAX_CHARS_DEFAULT = 5000
MAX_CHARS_LIMIT = 20000
TIMEOUT = 15  # seconds

# IPs internos bloqueados (SSRF protection)
BLOCKED_RANGES = [
    "10.",
    "172.16.",
    "172.17.",
    "172.18.",
    "172.19.",
    "172.20.",
    "172.21.",
    "172.22.",
    "172.23.",
    "172.24.",
    "172.25.",
    "172.26.",
    "172.27.",
    "172.28.",
    "172.29.",
    "172.30.",
    "172.31.",
    "192.168.",
    "127.",
    "0.",
    "169.254.",
]


# ─── Helpers ───────────────────────────────────────────────────────────────


def _strip_html(html: str) -> str:
    """Remove tags HTML e retorna texto limpo."""
    # Remove script e style blocks
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#\d+;", "", text)
    # Normalizar whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_url_safe(url: str) -> tuple[bool, str]:
    """Verifica se a URL é segura (anti-SSRF)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL inválida"

    if parsed.scheme not in ("http", "https"):
        return False, f"Protocolo não permitido: {parsed.scheme}"

    host = parsed.hostname or ""

    # Check for IP addresses
    try:
        ip = ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            return False, f"IP bloqueado (rede interna): {host}"
    except ValueError:
        pass  # Not an IP — it's a hostname, which is fine

    # Check hostname patterns
    if host in ("localhost", "0.0.0.0", "[::]", "[::1]"):
        return False, f"Host bloqueado: {host}"

    # Additional check for IP-like hostnames
    for prefix in BLOCKED_RANGES:
        if host.startswith(prefix):
            return False, f"IP bloqueado (rede interna): {host}"

    return True, ""


# ─── Executor ──────────────────────────────────────────────────────────────


async def web_search(args: dict) -> str:
    """Busca conteúdo de uma URL."""
    url = args.get("url", "").strip()
    if not url:
        return "❌ Parâmetro 'url' é obrigatório."

    # Check for disallowed schemes first (ftp://, file://, etc)
    if "://" in url and not url.startswith(("http://", "https://")):
        scheme = url.split("://")[0]
        return f"🔒 URL bloqueada: Protocolo não permitido: {scheme}"

    # Auto-add https for bare hostnames
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # SSRF check (IP ranges, localhost, etc)
    safe, reason = _is_url_safe(url)
    if not safe:
        return f"🔒 URL bloqueada: {reason}"

    max_chars = min(int(args.get("max_chars", MAX_CHARS_DEFAULT)), MAX_CHARS_LIMIT)

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(TIMEOUT),
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "DenAI/1.0 (Local AI Assistant)",
                    "Accept": "text/html,application/json,text/plain,*/*",
                },
            )
            resp.raise_for_status()

    except httpx.TimeoutException:
        return f"⏱️ Timeout ao acessar {url} ({TIMEOUT}s)"
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP {e.response.status_code}: {url}"
    except httpx.ConnectError:
        return f"❌ Não foi possível conectar a {url}"
    except Exception as e:
        return f"❌ Erro: {type(e).__name__}: {e}"

    content_type = resp.headers.get("content-type", "")
    body = resp.text

    # Extrair texto baseado no content-type
    if "json" in content_type:
        text = body  # JSON já é texto
    elif "html" in content_type:
        text = _strip_html(body)
    else:
        text = body

    # Truncar
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n... (truncado)"

    return f"🌐 {url}\n\n{text}"


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (WEB_SEARCH_SPEC, "web_search"),
]
