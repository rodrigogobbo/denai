"""Pesquisa web via DuckDuckGo — sem API key."""

import re

import httpx

SPEC = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Pesquisa na web usando DuckDuckGo. Use para buscar informações atualizadas.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Termo de pesquisa"}
            },
            "required": ["query"],
        },
    },
}

TOOLS = [(SPEC, "web_search")]


async def web_search(args: dict) -> str:
    query = args["query"]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DenAI/1.0"
            },
        )

    text = resp.text
    snippets = re.findall(r'class="result__snippet">(.*?)</a>', text, re.DOTALL)
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', text, re.DOTALL)
    urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', text, re.DOTALL)

    results = []
    for i in range(min(5, len(snippets))):
        title = re.sub(r"<[^>]+>", "", titles[i] if i < len(titles) else "")
        snippet = re.sub(r"<[^>]+>", "", snippets[i])
        url = re.sub(r"<[^>]+>", "", urls[i] if i < len(urls) else "").strip()
        results.append(f"**{title}**\n{url}\n{snippet}\n")

    return "\n".join(results) if results else "Sem resultados encontrados."
