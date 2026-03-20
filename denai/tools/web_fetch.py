"""Tool de busca web — pesquisa DuckDuckGo + fetch de URLs com extração de texto."""

from __future__ import annotations

import re
from ipaddress import ip_address
from urllib.parse import quote_plus, urlparse

import httpx

# ─── Specs ──────────────────────────────────────────────────────────────────

WEB_SEARCH_SPEC = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Busca na web via DuckDuckGo ou carrega conteúdo de uma URL específica. "
            "Se receber uma URL (começa com http), faz fetch e retorna o texto. "
            "Se receber texto livre, pesquisa no DuckDuckGo e retorna os resultados."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto para pesquisar OU URL para carregar",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Máximo de resultados de busca (padrão: 5, máx: 10)",
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Máximo de caracteres ao carregar URL (padrão: 5000)",
                },
            },
            "required": ["query"],
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
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#\d+;", "", text)
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

    try:
        ip = ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_reserved:
            return False, f"IP bloqueado (rede interna): {host}"
    except ValueError:
        pass

    if host in ("localhost", "0.0.0.0", "[::]", "[::1]"):  # noqa: S104 — checking, not binding
        return False, f"Host bloqueado: {host}"

    for prefix in BLOCKED_RANGES:
        if host.startswith(prefix):
            return False, f"IP bloqueado (rede interna): {host}"

    return True, ""


def _is_url(query: str) -> bool:
    """Heurística: é uma URL ou uma query de busca?"""
    q = query.strip()
    return q.startswith(("http://", "https://")) or ("." in q and " " not in q and len(q) < 200)


# ─── DuckDuckGo Search ────────────────────────────────────────────────────


async def _search_ddg(query: str, max_results: int = 5) -> str:
    """Pesquisa no DuckDuckGo via HTML (sem API key)."""
    max_results = min(max_results, 10)
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(TIMEOUT),
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html",
                },
            )
            resp.raise_for_status()

    except httpx.TimeoutException:
        return f"⏱️ Timeout na busca por: {query}"
    except httpx.HTTPStatusError as e:
        return f"❌ Erro HTTP {e.response.status_code} na busca"
    except httpx.ConnectError:
        return "❌ Sem conexão — busca requer internet"
    except Exception as e:
        return f"❌ Erro na busca: {type(e).__name__}: {e}"

    html = resp.text
    results = []

    # Parse dos resultados do DuckDuckGo HTML
    # Cada resultado está em <div class="result">
    result_blocks = re.findall(
        r'<a[^>]+class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
        r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    )

    if not result_blocks:
        # Fallback: tentar extrair links do resultado
        result_blocks = re.findall(
            r'<a[^>]+class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )
        for link, title in result_blocks[:max_results]:
            title_clean = _strip_html(title).strip()
            if title_clean and link:
                # DuckDuckGo redireciona via //duckduckgo.com/l/?uddg=...
                actual_url = link
                if "uddg=" in link:
                    from urllib.parse import parse_qs, unquote

                    try:
                        params = parse_qs(urlparse(link).query)
                        actual_url = unquote(params.get("uddg", [link])[0])
                    except Exception:
                        pass
                results.append(f"  🔗 **{title_clean}**\n     {actual_url}")
    else:
        for link, title, snippet in result_blocks[:max_results]:
            title_clean = _strip_html(title).strip()
            snippet_clean = _strip_html(snippet).strip()
            actual_url = link
            if "uddg=" in link:
                from urllib.parse import parse_qs, unquote

                try:
                    params = parse_qs(urlparse(link).query)
                    actual_url = unquote(params.get("uddg", [link])[0])
                except Exception:
                    pass
            results.append(f"  🔗 **{title_clean}**\n     {actual_url}\n     {snippet_clean}")

    if not results:
        return f"📭 Nenhum resultado encontrado para: {query}"

    header = f'🔍 {len(results)} resultado(s) para "{query}":\n'
    return header + "\n\n".join(results)


# ─── URL Fetch ─────────────────────────────────────────────────────────────


async def _fetch_url(url: str, max_chars: int = MAX_CHARS_DEFAULT) -> str:
    """Busca conteúdo de uma URL."""
    # Check for disallowed schemes first
    if "://" in url and not url.startswith(("http://", "https://")):
        scheme = url.split("://")[0]
        return f"🔒 URL bloqueada: Protocolo não permitido: {scheme}"

    # Auto-add https for bare hostnames
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # SSRF check
    safe, reason = _is_url_safe(url)
    if not safe:
        return f"🔒 URL bloqueada: {reason}"

    max_chars = min(max_chars, MAX_CHARS_LIMIT)

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

    if "json" in content_type:
        text = body
    elif "html" in content_type:
        text = _strip_html(body)
    else:
        text = body

    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n... (truncado)"

    return f"🌐 {url}\n\n{text}"


# ─── Main Executor ─────────────────────────────────────────────────────────


async def web_search(args: dict) -> str:
    """Busca web inteligente: detecta se é URL ou query."""
    query = args.get("query", "").strip()

    # Retrocompat: aceitar 'url' como parâmetro (versão anterior)
    if not query:
        query = args.get("url", "").strip()

    if not query:
        return "❌ Parâmetro 'query' é obrigatório."

    if _is_url(query):
        max_chars = min(int(args.get("max_chars", MAX_CHARS_DEFAULT)), MAX_CHARS_LIMIT)
        return await _fetch_url(query, max_chars)
    else:
        max_results = min(int(args.get("max_results", 5)), 10)
        return await _search_ddg(query, max_results)


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (WEB_SEARCH_SPEC, "web_search"),
]
