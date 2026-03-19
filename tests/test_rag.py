"""Testes do sistema RAG — indexação, busca, tools, rotas."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import aiosqlite
import httpx
import pytest

from denai.app import create_app
from denai.db import SCHEMA_SQL
from denai.rag import (
    BM25Index,
    chunk_text,
    get_index_stats,
    get_rag_context,
    index_documents,
    search_documents,
    tokenize,
)
from denai.tools.rag_search import rag_index, rag_search, rag_stats

# ── Tokenizer ──────────────────────────────────────────────────────────────


class TestTokenize:
    def test_basic_tokenization(self):
        tokens = tokenize("Hello World Python")
        assert "hello" in tokens
        assert "world" in tokens
        assert "python" in tokens

    def test_removes_stop_words(self):
        tokens = tokenize("the quick and brown fox is in the park")
        assert "the" not in tokens
        assert "and" not in tokens
        assert "is" not in tokens
        assert "in" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens

    def test_removes_single_char(self):
        tokens = tokenize("I a o x big")
        assert "big" in tokens
        assert "x" not in tokens  # single char, not stop word, but len <= 1

    def test_empty_string(self):
        assert tokenize("") == []

    def test_portuguese_stop_words(self):
        tokens = tokenize("o gato de casa para a rua")
        assert "gato" in tokens
        assert "casa" in tokens
        assert "rua" in tokens
        assert "de" not in tokens
        assert "para" not in tokens

    def test_unicode(self):
        tokens = tokenize("café résumé naïve")
        assert "café" in tokens
        assert "résumé" in tokens
        assert "naïve" in tokens


# ── Chunker ────────────────────────────────────────────────────────────────


class TestChunker:
    def test_small_text_single_chunk(self):
        text = "hello world foo bar"
        chunks = chunk_text(text, chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_large_text_multiple_chunks(self):
        words = ["word"] * 1000
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=200, overlap=50)
        assert len(chunks) > 1
        # Each chunk should have roughly 200 words (except last)
        for c in chunks[:-1]:
            word_count = len(c.split())
            assert word_count == 200

    def test_overlap_creates_shared_content(self):
        words = [f"w{i}" for i in range(600)]
        text = " ".join(words)
        chunks = chunk_text(text, chunk_size=300, overlap=100)
        assert len(chunks) >= 2
        # Words at the overlap boundary should appear in both chunks
        first_words = set(chunks[0].split())
        second_words = set(chunks[1].split())
        overlap_words = first_words & second_words
        assert len(overlap_words) > 0


# ── BM25 Index ─────────────────────────────────────────────────────────────


class TestBM25Index:
    def test_empty_index(self):
        idx = BM25Index()
        idx.build()
        assert idx.search("anything") == []

    def test_single_document(self):
        idx = BM25Index()
        idx.add_document("python programming language", source="doc1.txt")
        idx.build()
        results = idx.search("python")
        assert len(results) == 1
        assert results[0]["source"] == "doc1.txt"
        assert results[0]["score"] > 0

    def test_multiple_documents_ranking(self):
        idx = BM25Index()
        idx.add_document("python is great for data science", source="data.md")
        idx.add_document("java is used for enterprise apps", source="java.md")
        idx.add_document("python python python everywhere", source="py3.txt")
        idx.build()

        results = idx.search("python")
        assert len(results) == 2  # Only 2 docs mention python
        # Doc with more python mentions should score higher
        assert results[0]["source"] == "py3.txt"

    def test_no_match(self):
        idx = BM25Index()
        idx.add_document("cats and dogs", source="animals.txt")
        idx.build()
        results = idx.search("quantum physics")
        assert results == []

    def test_top_k_limit(self):
        idx = BM25Index()
        for i in range(20):
            idx.add_document(f"document about testing number {i}", source=f"doc{i}.txt")
        idx.build()

        results = idx.search("testing", top_k=3)
        assert len(results) == 3

    def test_auto_build_on_search(self):
        idx = BM25Index()
        idx.add_document("hello world", source="hw.txt")
        # Don't call build() explicitly
        results = idx.search("hello")
        assert len(results) == 1
        assert idx.indexed

    def test_score_is_float(self):
        idx = BM25Index()
        idx.add_document("machine learning deep neural networks", source="ml.txt")
        idx.build()
        results = idx.search("machine learning")
        assert isinstance(results[0]["score"], float)

    def test_empty_query(self):
        idx = BM25Index()
        idx.add_document("some content", source="f.txt")
        idx.build()
        results = idx.search("")
        assert results == []

    def test_stop_words_only_query(self):
        idx = BM25Index()
        idx.add_document("some content here", source="f.txt")
        idx.build()
        results = idx.search("the and or is")
        assert results == []


# ── Index Documents ────────────────────────────────────────────────────────


class TestIndexDocuments:
    def test_index_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = index_documents(Path(tmpdir))
            assert result["files_indexed"] == 0
            assert result["chunks"] == 0

    def test_index_nonexistent_directory(self):
        result = index_documents(Path("/nonexistent/path/xyz"))
        assert result["files_indexed"] == 0

    def test_index_with_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "readme.md").write_text("# Hello\nThis is a test document about Python")
            (d / "notes.txt").write_text("Notes about machine learning and AI")
            result = index_documents(d)
            assert result["files_indexed"] == 2
            assert result["chunks"] >= 2

    def test_index_skips_unsupported_extensions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "image.png").write_bytes(b"\x89PNG...")
            (d / "doc.txt").write_text("valid text")
            result = index_documents(d)
            assert result["files_indexed"] == 1

    def test_index_skips_dotfiles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / ".hidden").write_text("secret")
            (d / "visible.txt").write_text("public")
            result = index_documents(d)
            assert result["files_indexed"] == 1

    def test_index_skips_empty_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "empty.txt").write_text("")
            (d / "content.txt").write_text("has content")
            result = index_documents(d)
            assert result["files_indexed"] == 1

    def test_index_recursive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            sub = d / "subdir"
            sub.mkdir()
            (d / "root.txt").write_text("root file")
            (sub / "nested.md").write_text("nested file")
            result = index_documents(d)
            assert result["files_indexed"] == 2


# ── Search Documents ───────────────────────────────────────────────────────


class TestSearchDocuments:
    def test_search_with_indexed_docs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "python.md").write_text("Python is a great programming language for beginners")
            (d / "rust.md").write_text("Rust is a systems programming language focused on safety")
            index_documents(d)
            results = search_documents("Python programming")
            assert len(results) >= 1
            assert any("python" in r["source"].lower() for r in results)

    def test_search_empty_query(self):
        results = search_documents("")
        assert results == []


# ── RAG Context ────────────────────────────────────────────────────────────


class TestRAGContext:
    def test_rag_context_with_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "guide.md").write_text("DenAI is a local AI assistant that runs on your machine")
            index_documents(d)
            ctx = get_rag_context("DenAI assistant")
            assert "Contexto de documentos locais" in ctx
            assert "guide.md" in ctx

    def test_rag_context_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index_documents(Path(tmpdir))
            ctx = get_rag_context("something completely unrelated xyz123")
            assert ctx == ""

    def test_rag_context_max_chars(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            # Create many large docs
            for i in range(10):
                (d / f"doc{i}.md").write_text(f"testing content number {i} " * 200)
            index_documents(d)
            ctx = get_rag_context("testing content", max_chars=500)
            # Context should be trimmed
            assert len(ctx) < 1000  # some overhead from headers


# ── Index Stats ────────────────────────────────────────────────────────────


class TestIndexStats:
    def test_stats_structure(self):
        stats = get_index_stats()
        assert "indexed" in stats
        assert "documents" in stats
        assert "files" in stats
        assert "directory" in stats


# ── RAG Tools (Executors) ──────────────────────────────────────────────────


class TestRAGTools:
    def test_rag_search_tool_empty_query(self):
        result = asyncio.get_event_loop().run_until_complete(rag_search({"query": ""}))
        assert "❌" in result

    def test_rag_search_tool_no_docs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index_documents(Path(tmpdir))
            result = asyncio.get_event_loop().run_until_complete(rag_search({"query": "xyz"}))
            assert "📭" in result

    def test_rag_search_tool_with_results(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            d = Path(tmpdir)
            (d / "test.txt").write_text("FastAPI is a modern Python web framework for APIs")
            index_documents(d)
            result = asyncio.get_event_loop().run_until_complete(rag_search({"query": "FastAPI Python"}))
            assert "resultado" in result
            assert "test.txt" in result

    def test_rag_index_tool_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("denai.tools.rag_search.index_documents") as mock_idx:
                mock_idx.return_value = {"files_indexed": 0, "chunks": 0, "directory": tmpdir}
                result = asyncio.get_event_loop().run_until_complete(rag_index({}))
                assert "📭" in result

    def test_rag_index_tool_with_files(self):
        with patch("denai.tools.rag_search.index_documents") as mock_idx:
            mock_idx.return_value = {"files_indexed": 5, "chunks": 12, "directory": "/tmp/docs"}
            result = asyncio.get_event_loop().run_until_complete(rag_index({}))
            assert "✅" in result
            assert "5" in result
            assert "12" in result

    def test_rag_stats_tool(self):
        result = asyncio.get_event_loop().run_until_complete(rag_stats({}))
        assert "RAG Index Stats" in result


# ── RAG Routes (API) ──────────────────────────────────────────────────────


@pytest.fixture
async def rag_client(tmp_path):
    """Cria app com DB temporário e client autenticado para testes RAG."""
    db_path = tmp_path / "test_rag.db"

    db = await aiosqlite.connect(str(db_path))
    await db.executescript(SCHEMA_SQL)
    await db.execute("INSERT OR IGNORE INTO _schema_version (version) VALUES (1)")
    await db.commit()
    await db.close()

    with (
        patch("denai.config.DB_PATH", db_path),
        patch("denai.db.DB_PATH", db_path),
    ):
        _app = create_app()
        from denai.security.auth import API_KEY

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app),
            base_url="http://testserver",
            headers={"X-API-Key": API_KEY},
        ) as client:
            yield client


class TestRAGRoutes:
    """Testes de integração das rotas RAG."""

    @pytest.mark.asyncio
    async def test_rag_stats_endpoint(self, rag_client):
        resp = await rag_client.get("/api/rag/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "indexed" in data
        assert "documents" in data

    @pytest.mark.asyncio
    async def test_rag_index_endpoint(self, rag_client):
        resp = await rag_client.post("/api/rag/index")
        assert resp.status_code == 200
        data = resp.json()
        assert "files_indexed" in data

    @pytest.mark.asyncio
    async def test_rag_search_endpoint_empty_query(self, rag_client):
        resp = await rag_client.post("/api/rag/search", json={"query": ""})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rag_search_endpoint_valid(self, rag_client):
        resp = await rag_client.post("/api/rag/search", json={"query": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_rag_documents_list(self, rag_client):
        resp = await rag_client.get("/api/rag/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert "documents" in data
        assert "directory" in data

    @pytest.mark.asyncio
    async def test_rag_upload_no_file(self, rag_client):
        resp = await rag_client.post("/api/rag/upload")
        # FastAPI returns 422 when required file param is missing
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_rag_upload_unsupported_extension(self, rag_client):
        resp = await rag_client.post(
            "/api/rag/upload",
            files={"file": ("image.png", b"fake png", "image/png")},
        )
        assert resp.status_code == 400
        assert "não suportada" in resp.json()["error"]

    @pytest.mark.asyncio
    async def test_rag_upload_valid_file(self, rag_client):
        content = b"This is a test document about Python programming"
        resp = await rag_client.post(
            "/api/rag/upload",
            files={"file": ("test_upload.txt", content, "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["file"] == "test_upload.txt"

    @pytest.mark.asyncio
    async def test_rag_delete_nonexistent(self, rag_client):
        resp = await rag_client.delete("/api/rag/documents/nonexistent.txt")
        assert resp.status_code == 404


# ── Prompt Integration ─────────────────────────────────────────────────────


class TestPromptIntegration:
    def test_prompt_without_rag(self):
        from denai.llm.prompt import build_system_prompt

        prompt = build_system_prompt()
        assert "DenAI" in prompt
        assert "Contexto de documentos" not in prompt

    def test_prompt_with_rag_context(self):
        from denai.llm.prompt import build_system_prompt

        ctx = "Contexto de documentos locais (use para responder):\n\n[Fonte: test.md]\nHello world"
        prompt = build_system_prompt(rag_context=ctx)
        assert "DenAI" in prompt
        assert "Contexto de documentos locais" in prompt
        assert "test.md" in prompt

    def test_prompt_mentions_rag_capability(self):
        from denai.llm.prompt import build_system_prompt

        prompt = build_system_prompt()
        assert "RAG" in prompt or "documentos locais" in prompt


# ── Tool Specs ─────────────────────────────────────────────────────────────


class TestRAGToolSpecs:
    def test_tools_registered(self):
        from denai.tools.rag_search import TOOLS

        assert len(TOOLS) == 3
        names = [t[0]["function"]["name"] for t in TOOLS]
        assert "rag_search" in names
        assert "rag_index" in names
        assert "rag_stats" in names

    def test_spec_structure(self):
        from denai.tools.rag_search import RAG_SEARCH_SPEC

        assert RAG_SEARCH_SPEC["type"] == "function"
        fn = RAG_SEARCH_SPEC["function"]
        assert fn["name"] == "rag_search"
        assert "query" in fn["parameters"]["properties"]
        assert "query" in fn["parameters"]["required"]
