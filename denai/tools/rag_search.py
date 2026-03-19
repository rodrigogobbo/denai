"""Tool de busca RAG — pesquisa documentos locais indexados."""

from __future__ import annotations

from ..rag import get_index_stats, index_documents, search_documents

# ─── Specs ─────────────────────────────────────────────────────────────────

RAG_SEARCH_SPEC = {
    "type": "function",
    "function": {
        "name": "rag_search",
        "description": (
            "Pesquisa documentos locais do usuário em ~/.denai/documents/ "
            "usando busca por similaridade (BM25). Use quando o usuário "
            "perguntar sobre conteúdo de seus documentos ou quiser "
            "encontrar informações em seus arquivos indexados."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto para buscar nos documentos",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Número máximo de resultados (padrão: 5)",
                },
            },
            "required": ["query"],
        },
    },
}

RAG_INDEX_SPEC = {
    "type": "function",
    "function": {
        "name": "rag_index",
        "description": (
            "Reindexa os documentos locais em ~/.denai/documents/. "
            "Use quando o usuário adicionar novos documentos e quiser "
            "que eles sejam encontrados nas buscas."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}

RAG_STATS_SPEC = {
    "type": "function",
    "function": {
        "name": "rag_stats",
        "description": "Mostra estatísticas do índice RAG (documentos indexados, chunks, etc).",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}


# ─── Executors ─────────────────────────────────────────────────────────────


async def rag_search(args: dict) -> str:
    """Busca nos documentos indexados."""
    query = args.get("query", "")
    top_k = args.get("top_k", 5)

    if not query.strip():
        return "❌ Query vazia. Informe o que deseja buscar."

    results = search_documents(query, top_k=int(top_k))

    if not results:
        return "📭 Nenhum documento encontrado. Coloque arquivos em ~/.denai/documents/ e use rag_index para indexar."

    parts = [f'📄 {len(results)} resultado(s) para "{query}":\n']
    for i, r in enumerate(results, 1):
        score = r["score"]
        source = r["source"]
        text = r["text"]
        # Truncar texto longo
        if len(text) > 500:
            text = text[:500] + "..."
        parts.append(f"**[{i}] {source}** (score: {score})\n{text}\n")

    return "\n".join(parts)


async def rag_index(args: dict) -> str:
    """Reindexa os documentos."""
    stats = index_documents()
    files = stats["files_indexed"]
    chunks = stats["chunks"]
    directory = stats["directory"]

    if files == 0:
        return (
            f"📭 Nenhum documento encontrado em {directory}\n"
            "Coloque arquivos .txt, .md, .py etc nessa pasta e rode novamente."
        )

    return f"✅ Indexados {files} arquivo(s) → {chunks} chunk(s)\n📁 Diretório: {directory}"


async def rag_stats(args: dict) -> str:
    """Retorna estatísticas do índice."""
    stats = get_index_stats()
    return (
        f"📊 RAG Index Stats\n"
        f"  Indexado: {'sim' if stats['indexed'] else 'não'}\n"
        f"  Documentos (chunks): {stats['documents']}\n"
        f"  Arquivos: {stats['files']}\n"
        f"  Diretório: {stats['directory']}"
    )


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (RAG_SEARCH_SPEC, "rag_search"),
    (RAG_INDEX_SPEC, "rag_index"),
    (RAG_STATS_SPEC, "rag_stats"),
]
