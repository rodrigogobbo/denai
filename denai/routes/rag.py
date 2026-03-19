"""Rotas de gerenciamento de documentos RAG — /api/rag/*."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import JSONResponse

from ..rag import (
    DOCS_DIR,
    SUPPORTED_EXTENSIONS,
    get_index_stats,
    index_documents,
    search_documents,
)

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.get("/api/rag/stats")
async def rag_stats():
    """Estatísticas do índice RAG."""
    return get_index_stats()


@router.post("/api/rag/index")
async def rag_index():
    """(Re)indexa todos os documentos."""
    result = index_documents()
    return result


@router.post("/api/rag/search")
async def rag_search(request: Request):
    """Busca nos documentos indexados."""
    body = await request.json()
    query = body.get("query", "")
    top_k = body.get("top_k", 5)

    if not query.strip():
        return JSONResponse({"error": "Query vazia"}, status_code=400)

    results = search_documents(query, top_k=int(top_k))
    return {"query": query, "results": results, "total": len(results)}


@router.get("/api/rag/documents")
async def list_documents():
    """Lista documentos no diretório de documentos."""
    if not DOCS_DIR.exists():
        return {"documents": [], "directory": str(DOCS_DIR)}

    docs = []
    for f in sorted(DOCS_DIR.rglob("*")):
        if not f.is_file():
            continue
        if f.name.startswith("."):
            continue
        if f.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            stat = f.stat()
            docs.append(
                {
                    "name": f.name,
                    "path": str(f.relative_to(DOCS_DIR)),
                    "size": stat.st_size,
                    "extension": f.suffix.lower(),
                }
            )
        except Exception:
            continue

    return {"documents": docs, "directory": str(DOCS_DIR), "total": len(docs)}


@router.post("/api/rag/upload")
async def upload_document(file: UploadFile):
    """Upload de documento para indexação."""
    if not file.filename:
        return JSONResponse({"error": "Nome de arquivo ausente"}, status_code=400)

    # Validar extensão
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return JSONResponse(
            {"error": f"Extensão {ext} não suportada. Suportados: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"},
            status_code=400,
        )

    # Sanitizar nome do arquivo (evitar path traversal)
    safe_name = Path(file.filename).name
    if ".." in safe_name or "/" in safe_name or "\\" in safe_name:
        return JSONResponse({"error": "Nome de arquivo inválido"}, status_code=400)

    # Ler conteúdo com limite de tamanho
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return JSONResponse(
            {"error": f"Arquivo muito grande (máx {MAX_FILE_SIZE // 1024 // 1024}MB)"},
            status_code=400,
        )

    # Salvar
    dest = DOCS_DIR / safe_name
    dest.write_bytes(content)

    # Reindexar
    stats = index_documents()

    return {
        "ok": True,
        "file": safe_name,
        "size": len(content),
        "index": stats,
    }


@router.delete("/api/rag/documents/{filename:path}")
async def delete_document(filename: str):
    """Remove um documento do diretório."""
    # Sanitizar
    safe_path = DOCS_DIR / filename
    try:
        safe_path = safe_path.resolve()
        docs_resolved = DOCS_DIR.resolve()
        if not str(safe_path).startswith(str(docs_resolved)):
            return JSONResponse({"error": "Caminho inválido"}, status_code=400)
    except Exception:
        return JSONResponse({"error": "Caminho inválido"}, status_code=400)

    if not safe_path.exists():
        return JSONResponse({"error": "Arquivo não encontrado"}, status_code=404)

    safe_path.unlink()

    # Reindexar
    stats = index_documents()
    return {"ok": True, "deleted": filename, "index": stats}
