"""Testes para providers_store e rotas de providers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from denai.providers_store import (
    add_or_update_provider,
    load_providers,
    mask_api_key,
    remove_provider,
    save_providers,
)

# ─── providers_store ───────────────────────────────────────────────────────


class TestMaskApiKey:
    def test_empty_key(self):
        assert mask_api_key("") == ""

    def test_short_key(self):
        assert mask_api_key("abc") == "***"

    def test_normal_key(self):
        result = mask_api_key("sk-abcdefghij1234")
        assert result.startswith("sk-a")
        assert "***" in result
        assert "abcdefghij1234" not in result

    def test_long_key_ends_correctly(self):
        key = "sk-" + "x" * 30 + "99"
        result = mask_api_key(key)
        assert result.endswith("99")
        assert "***" in result


class TestLoadSaveProviders:
    def test_load_empty_when_no_file(self, tmp_path):
        fake_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            result = load_providers()
        assert result == []

    def test_save_and_load_roundtrip(self, tmp_path):
        fake_path = tmp_path / "providers.yaml"
        providers = [
            {"name": "OpenAI", "kind": "openai", "base_url": "https://api.openai.com", "api_key": "sk-test"},
            {"name": "LM Studio", "kind": "openai", "base_url": "http://localhost:1234", "api_key": ""},
        ]
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            save_providers(providers)
            result = load_providers()
        assert len(result) == 2
        assert result[0]["name"] == "OpenAI"
        assert result[1]["name"] == "LM Studio"

    def test_save_creates_file(self, tmp_path):
        fake_path = tmp_path / "subdir" / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            save_providers([{"name": "Test", "kind": "openai", "base_url": "http://x", "api_key": ""}])
        assert fake_path.exists()

    def test_load_handles_corrupt_file(self, tmp_path):
        fake_path = tmp_path / "providers.yaml"
        fake_path.write_text("not: valid: yaml: ][")
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            result = load_providers()
        assert result == []


class TestAddOrUpdateProvider:
    def test_add_new_provider(self, tmp_path):
        fake_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            add_or_update_provider({"name": "TestProv", "kind": "openai", "base_url": "http://x", "api_key": ""})
            result = load_providers()
        assert len(result) == 1
        assert result[0]["name"] == "TestProv"

    def test_update_existing_provider(self, tmp_path):
        fake_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            add_or_update_provider({"name": "TestProv", "kind": "openai", "base_url": "http://old", "api_key": ""})
            add_or_update_provider({"name": "TestProv", "kind": "openai", "base_url": "http://new", "api_key": "key2"})
            result = load_providers()
        assert len(result) == 1
        assert result[0]["base_url"] == "http://new"

    def test_update_case_insensitive(self, tmp_path):
        fake_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            add_or_update_provider({"name": "OpenAI", "kind": "openai", "base_url": "http://x", "api_key": ""})
            add_or_update_provider({"name": "openai", "kind": "openai", "base_url": "http://y", "api_key": ""})
            result = load_providers()
        assert len(result) == 1


class TestRemoveProvider:
    def test_remove_existing(self, tmp_path):
        fake_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            save_providers([{"name": "ToRemove", "kind": "openai", "base_url": "http://x", "api_key": ""}])
            removed = remove_provider("ToRemove")
            result = load_providers()
        assert removed is True
        assert len(result) == 0

    def test_remove_nonexistent(self, tmp_path):
        fake_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            removed = remove_provider("Ghost")
        assert removed is False

    def test_remove_case_insensitive(self, tmp_path):
        fake_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", fake_path):
            save_providers([{"name": "OpenAI", "kind": "openai", "base_url": "http://x", "api_key": ""}])
            removed = remove_provider("openai")
        assert removed is True


# ─── routes/models.py ──────────────────────────────────────────────────────


@pytest.fixture
async def client(tmp_path):
    """App client com DB e store temporários."""
    import aiosqlite

    from denai.app import create_app
    from denai.db import SCHEMA_SQL
    from denai.security.auth import API_KEY
    from denai.security.rate_limit import rate_limiter

    db_path = tmp_path / "test.db"
    db = await aiosqlite.connect(str(db_path))
    await db.executescript(SCHEMA_SQL)
    await db.execute("INSERT OR IGNORE INTO _schema_version (version) VALUES (1)")
    await db.commit()
    await db.close()

    providers_path = tmp_path / "providers.yaml"

    import httpx

    with (
        patch("denai.config.DB_PATH", db_path),
        patch("denai.db.DB_PATH", db_path),
        patch("denai.providers_store.PROVIDERS_FILE", providers_path),
        patch("denai.config.DATA_DIR", tmp_path),
    ):
        _app = create_app()
        rate_limiter.reset()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app),
            base_url="http://testserver",
            headers={"X-API-Key": API_KEY},
        ) as c:
            yield c


class TestProviderRoutes:
    @pytest.mark.asyncio
    async def test_list_providers_returns_ollama(self, client):
        resp = await client.get("/api/providers")
        assert resp.status_code == 200
        data = resp.json()
        names = [p["name"] for p in data["providers"]]
        assert "Ollama" in names

    @pytest.mark.asyncio
    async def test_list_templates(self, client):
        resp = await client.get("/api/providers/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["templates"]) >= 5
        ids = [t["id"] for t in data["templates"]]
        assert "openai" in ids
        assert "groq" in ids

    @pytest.mark.asyncio
    async def test_add_provider(self, client, tmp_path):
        providers_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", providers_path):
            resp = await client.post(
                "/api/providers",
                json={
                    "name": "TestLM",
                    "kind": "openai",
                    "base_url": "http://localhost:1234",
                    "api_key": "",
                    "models": ["test-model"],
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["provider"]["name"] == "TestLM"

    @pytest.mark.asyncio
    async def test_add_provider_cannot_override_ollama(self, client):
        resp = await client.post(
            "/api/providers",
            json={
                "name": "Ollama",
                "kind": "ollama",
                "base_url": "http://localhost:11434",
            },
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_providers_api_key_masked(self, client, tmp_path):
        providers_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", providers_path):
            await client.post(
                "/api/providers",
                json={
                    "name": "SecretProv",
                    "kind": "openai",
                    "base_url": "http://x",
                    "api_key": "sk-supersecretkey123",
                },
            )
            resp = await client.get("/api/providers")
        data = resp.json()
        prov = next((p for p in data["providers"] if p["name"] == "SecretProv"), None)
        assert prov is not None
        assert prov["has_key"] is True
        # A key real NUNCA deve aparecer
        assert "sk-supersecretkey123" not in str(data)

    @pytest.mark.asyncio
    async def test_delete_provider(self, client, tmp_path):
        providers_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", providers_path):
            await client.post(
                "/api/providers",
                json={
                    "name": "ToDelete",
                    "kind": "openai",
                    "base_url": "http://x",
                    "api_key": "",
                },
            )
            resp = await client.delete("/api/providers/ToDelete")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    @pytest.mark.asyncio
    async def test_delete_ollama_forbidden(self, client):
        resp = await client.delete("/api/providers/ollama")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client, tmp_path):
        providers_path = tmp_path / "providers.yaml"
        with patch("denai.providers_store.PROVIDERS_FILE", providers_path):
            resp = await client.delete("/api/providers/Ghost")
        assert resp.status_code == 404


class TestProviderTemplates:
    def test_all_templates_have_required_fields(self):
        from denai.providers_store import PROVIDER_TEMPLATES

        for t in PROVIDER_TEMPLATES:
            assert "id" in t
            assert "label" in t
            assert "kind" in t
            assert "base_url" in t
            assert "requires_key" in t

    def test_templates_have_unique_ids(self):
        from denai.providers_store import PROVIDER_TEMPLATES

        ids = [t["id"] for t in PROVIDER_TEMPLATES]
        assert len(ids) == len(set(ids))

    def test_known_templates_present(self):
        from denai.providers_store import PROVIDER_TEMPLATES

        ids = {t["id"] for t in PROVIDER_TEMPLATES}
        for expected in ("openai", "anthropic", "gemini", "groq", "openrouter", "lmstudio"):
            assert expected in ids
