"""RAG local — indexa documentos e busca por similaridade.

Usa BM25 (term frequency) para busca sem dependências externas.
Não precisa de embeddings nem GPU — funciona 100% offline.

Diretório de documentos: ~/.denai/documents/
Formatos suportados: .txt, .md, .py, .json, .csv, .log, .yaml, .yml, .toml, .ini, .cfg, .html, .xml
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from ..config import DATA_DIR

DOCS_DIR = DATA_DIR / "documents"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".json",
    ".csv",
    ".log",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".html",
    ".xml",
    ".js",
    ".ts",
    ".sh",
    ".bat",
    ".ps1",
    ".sql",
    ".r",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
}

# ── Tokenizer simples ─────────────────────────────────────────────

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_STOP_WORDS = {
    "a",
    "o",
    "e",
    "de",
    "da",
    "do",
    "em",
    "um",
    "uma",
    "para",
    "com",
    "por",
    "que",
    "se",
    "na",
    "no",
    "os",
    "as",
    "é",
    "the",
    "and",
    "or",
    "in",
    "of",
    "to",
    "is",
    "it",
    "this",
    "that",
    "for",
    "on",
    "with",
    "as",
    "at",
    "by",
    "an",
    "be",
}


def tokenize(text: str) -> list[str]:
    """Tokeniza texto em palavras lowercase, removendo stop words."""
    words = _WORD_RE.findall(text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


# ── Chunker ─────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Divide texto em chunks com overlap."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap

    return chunks


# ── BM25 Index ─────────────────────────────────────────────────────

class BM25Index:
    """Índice BM25 simples para busca por similaridade textual."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: list[dict] = []  # [{text, source, tokens}]
        self.doc_count = 0
        self.avg_doc_len = 0
        self.df: dict[str, int] = {}  # document frequency per term
        self.indexed = False

    def add_document(self, text: str, source: str = ""):
        """Adiciona um documento ao índice."""
        tokens = tokenize(text)
        self.documents.append({
            "text": text,
            "source": source,
            "tokens": tokens,
        })

    def build(self):
        """Constrói o índice (calcular df, avg_doc_len)."""
        self.doc_count = len(self.documents)
        if self.doc_count == 0:
            self.indexed = True
            return

        total_len = 0
        self.df = {}

        for doc in self.documents:
            tokens = doc["tokens"]
            total_len += len(tokens)
            seen = set(tokens)
            for term in seen:
                self.df[term] = self.df.get(term, 0) + 1

        self.avg_doc_len = total_len / self.doc_count
        self.indexed = True

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Busca documentos mais relevantes para a query.

        Returns:
            Lista de {text, source, score} ordenada por relevância.
        """
        if not self.indexed:
            self.build()

        if self.doc_count == 0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = []
        for i, doc in enumerate(self.documents):
            score = self._score_document(doc["tokens"], query_tokens)
            if score > 0:
                scores.append((i, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scores[:top_k]:
            doc = self.documents[idx]
            results.append({
                "text": doc["text"],
                "source": doc["source"],
                "score": round(score, 4),
            })

        return results

    def _score_document(self, doc_tokens: list[str], query_tokens: list[str]) -> float:
        """Calcula score BM25 de um documento para uma query."""
        doc_len = len(doc_tokens)
        score = 0.0

        # Count term frequency in document
        tf_map: dict[str, int] = {}
        for t in doc_tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        for term in query_tokens:
            if term not in self.df:
                continue

            tf = tf_map.get(term, 0)
            if tf == 0:
                continue

            df = self.df[term]
            idf = math.log((self.doc_count - df + 0.5) / (df + 0.5) + 1)

            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)

            score += idf * numerator / denominator

        return score


# ── Global Index ─────────────────────────────────────────────────────

_index = BM25Index()
_indexed_files: set[str] = set()


def index_documents(directory: Path | None = None) -> dict:
    """Indexa todos os documentos do diretório.

    Returns:
        Metadados: {files_indexed, chunks, directory}
    """
    global _index, _indexed_files

    dir_path = directory or DOCS_DIR
    if not dir_path.exists():
        return {"files_indexed": 0, "chunks": 0, "directory": str(dir_path)}

    _index = BM25Index()
    _indexed_files = set()
    total_chunks = 0

    for file_path in sorted(dir_path.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if file_path.name.startswith("."):
            continue

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                continue

            # Chunk large files
            chunks = chunk_text(text)
            for chunk in chunks:
                _index.add_document(
                    text=chunk,
                    source=str(file_path.relative_to(dir_path)),
                )
                total_chunks += 1

            _indexed_files.add(str(file_path))
        except Exception:
            continue

    _index.build()

    return {
        "files_indexed": len(_indexed_files),
        "chunks": total_chunks,
        "directory": str(dir_path),
    }


def search_documents(query: str, top_k: int = 5) -> list[dict]:
    """Busca documentos relevantes para a query."""
    if not _index.indexed or _index.doc_count == 0:
        index_documents()

    return _index.search(query, top_k=top_k)


def get_rag_context(query: str, max_chars: int = 3000) -> str:
    """Retorna contexto RAG formatado para injetar no prompt.

    Busca documentos relevantes e formata como contexto para o LLM.
    """
    results = search_documents(query, top_k=5)
    if not results:
        return ""

    context_parts = []
    total_chars = 0

    for r in results:
        text = r["text"]
        if total_chars + len(text) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 100:
                text = text[:remaining] + "..."
            else:
                break

        source = r["source"]
        context_parts.append(f"[Fonte: {source}]\n{text}")
        total_chars += len(text)

    if not context_parts:
        return ""

    return (
        "Contexto de documentos locais (use para responder):\n\n"
        + "\n\n---\n\n".join(context_parts)
    )


def get_index_stats() -> dict:
    """Retorna estatísticas do índice."""
    return {
        "indexed": _index.indexed,
        "documents": _index.doc_count,
        "files": len(_indexed_files),
        "directory": str(DOCS_DIR),
    }
