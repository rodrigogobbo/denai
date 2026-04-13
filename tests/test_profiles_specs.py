"""Testes para profile_manager, /api/profiles e /api/specs."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from denai.profile_manager import (
    create_profile,
    delete_profile,
    get_active_profile,
    get_profile_dir,
    list_profiles,
    set_active_profile,
)

# ─── profile_manager ───────────────────────────────────────────────────────


class TestProfileManager:
    def test_default_profile_returns_base_dir(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            assert get_profile_dir("default") == tmp_path

    def test_named_profile_returns_profiles_subdir(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
        ):
            result = get_profile_dir("work")
            assert result == tmp_path / "profiles" / "work"

    def test_get_active_profile_defaults_to_default(self, tmp_path):
        with patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"):
            assert get_active_profile() == "default"

    def test_set_and_get_active_profile(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
        ):
            set_active_profile("work")
            assert get_active_profile() == "work"

    def test_create_profile(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            p = create_profile("personal")
            assert p.exists()
            assert p.name == "personal"

    def test_create_duplicate_profile_raises(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            create_profile("dup")
            with pytest.raises(ValueError, match="já existe"):
                create_profile("dup")

    def test_cannot_create_default(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            with pytest.raises(ValueError, match="default"):
                create_profile("default")

    def test_delete_profile(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            create_profile("todelete")
            result = delete_profile("todelete")
            assert result is True
            assert not (tmp_path / "profiles" / "todelete").exists()

    def test_cannot_delete_active_profile(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            create_profile("active-one")
            set_active_profile("active-one")
            with pytest.raises(ValueError, match="ativo"):
                delete_profile("active-one")

    def test_cannot_delete_default(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            with pytest.raises(ValueError, match="default"):
                delete_profile("default")

    def test_list_profiles_always_includes_default(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            profiles = list_profiles()
            names = [p["name"] for p in profiles]
            assert "default" in names

    def test_list_profiles_includes_created(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            create_profile("work")
            create_profile("personal")
            profiles = list_profiles()
            names = [p["name"] for p in profiles]
            assert "work" in names
            assert "personal" in names

    def test_invalid_profile_name_raises(self, tmp_path):
        with (
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            with pytest.raises(ValueError, match="inválido"):
                create_profile("invalid name!")


# ─── /api/profiles routes ──────────────────────────────────────────────────


@pytest.fixture
async def client(tmp_path):
    import aiosqlite

    from denai.app import create_app
    from denai.db import SCHEMA_SQL

    db_path = tmp_path / "test.db"
    db = await aiosqlite.connect(str(db_path))
    await db.executescript(SCHEMA_SQL)
    await db.execute("INSERT OR IGNORE INTO _schema_version (version) VALUES (1)")
    await db.commit()
    await db.close()

    profiles_dir = tmp_path / "profiles"
    active_file = tmp_path / "active_profile"

    with (
        patch("denai.config.DB_PATH", db_path),
        patch("denai.db.DB_PATH", db_path),
        patch("denai.config.DATA_DIR", tmp_path),
        patch("denai.profile_manager._BASE_DIR", tmp_path),
        patch("denai.profile_manager._PROFILES_DIR", profiles_dir),
        patch("denai.profile_manager._ACTIVE_FILE", active_file),
    ):
        _app = create_app()
        from denai.security.auth import API_KEY
        from denai.security.rate_limit import rate_limiter

        rate_limiter.reset()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app),
            base_url="http://testserver",
            headers={"X-API-Key": API_KEY},
        ) as c:
            yield c


class TestProfileRoutes:
    @pytest.mark.asyncio
    async def test_list_profiles_returns_default(self, client):
        resp = await client.get("/api/profiles")
        assert resp.status_code == 200
        data = resp.json()
        names = [p["name"] for p in data["profiles"]]
        assert "default" in names

    @pytest.mark.asyncio
    async def test_create_profile(self, client, tmp_path):
        with (
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            resp = await client.post("/api/profiles", json={"name": "work"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "work"

    @pytest.mark.asyncio
    async def test_activate_profile(self, client, tmp_path):
        with (
            patch("denai.profile_manager._PROFILES_DIR", tmp_path / "profiles"),
            patch("denai.profile_manager._BASE_DIR", tmp_path),
            patch("denai.profile_manager._ACTIVE_FILE", tmp_path / "active_profile"),
        ):
            await client.post("/api/profiles", json={"name": "myprofile"})
            resp = await client.post("/api/profiles/myprofile/activate")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["reload"] is True

    @pytest.mark.asyncio
    async def test_get_active(self, client):
        resp = await client.get("/api/profiles/active")
        assert resp.status_code == 200
        assert "active" in resp.json()


# ─── /api/specs routes ─────────────────────────────────────────────────────


class TestSpecsRoutes:
    @pytest.mark.asyncio
    async def test_list_specs_no_context(self, client):
        resp = await client.post("/api/specs/list", json={"conversation_id": "no-ctx"})
        assert resp.status_code == 400
        assert "context" in resp.json()["error"].lower()

    @pytest.mark.asyncio
    async def test_list_specs_with_context(self, client, tmp_path):
        # Criar estrutura de specs
        specs_dir = tmp_path / "myproject" / "specs" / "changes"
        (specs_dir / "v0.1.0-feature").mkdir(parents=True)
        (specs_dir / "v0.2.0-bugfix").mkdir(parents=True)
        (specs_dir / "v0.1.0-feature" / "requirements.md").write_text("# Requirements")

        from denai.context_store import _contexts

        _contexts["spec-conv-1"] = {
            "path": str(tmp_path / "myproject"),
            "project_name": "myproject",
            "summary": "## Projeto: myproject",
            "index": {"docs": [], "df": {}, "avg_len": 0, "n": 0, "k1": 1.5, "b": 0.75},
            "file_count": 1,
        }

        resp = await client.post("/api/specs/list", json={"conversation_id": "spec-conv-1"})
        assert resp.status_code == 200
        data = resp.json()
        assert "v0.1.0-feature" in data["specs"]
        assert "v0.2.0-bugfix" in data["specs"]

        del _contexts["spec-conv-1"]

    @pytest.mark.asyncio
    async def test_read_spec(self, client, tmp_path):
        specs_dir = tmp_path / "proj" / "specs" / "changes" / "v0.1.0-test"
        specs_dir.mkdir(parents=True)
        (specs_dir / "requirements.md").write_text("# Requirements\nREQ-1: Something")
        (specs_dir / "tasks.md").write_text("# Tasks\n- [x] Done\n- [ ] Todo")

        from denai.context_store import _contexts

        _contexts["spec-conv-2"] = {
            "path": str(tmp_path / "proj"),
            "project_name": "proj",
            "summary": "",
            "index": {"docs": [], "df": {}, "avg_len": 0, "n": 0, "k1": 1.5, "b": 0.75},
            "file_count": 2,
        }

        resp = await client.post(
            "/api/specs/read",
            json={
                "conversation_id": "spec-conv-2",
                "slug": "v0.1.0-test",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "REQ-1" in data["content"]
        assert "[ ] Todo" in data["content"]

        del _contexts["spec-conv-2"]

    @pytest.mark.asyncio
    async def test_read_spec_not_found(self, client, tmp_path):
        specs_dir = tmp_path / "proj2" / "specs" / "changes"
        specs_dir.mkdir(parents=True)

        from denai.context_store import _contexts

        _contexts["spec-conv-3"] = {
            "path": str(tmp_path / "proj2"),
            "project_name": "proj2",
            "summary": "",
            "index": {"docs": [], "df": {}, "avg_len": 0, "n": 0, "k1": 1.5, "b": 0.75},
            "file_count": 0,
        }

        resp = await client.post(
            "/api/specs/read",
            json={
                "conversation_id": "spec-conv-3",
                "slug": "nonexistent",
            },
        )
        assert resp.status_code == 404

        del _contexts["spec-conv-3"]


class TestProfileModel:
    @pytest.mark.asyncio
    async def test_get_model_no_saved(self, client):
        resp = await client.get("/api/profiles/active/model")
        assert resp.status_code == 200
        assert resp.json()["model"] is None

    @pytest.mark.asyncio
    async def test_save_and_get_model(self, client, tmp_path):
        with (
            patch("denai.profile_manager.get_active_profile", return_value="default"),
            patch("denai.profile_manager.get_profile_dir", return_value=tmp_path),
        ):
            resp = await client.post("/api/profiles/active/model", json={"model": "llama3.1:8b"})
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

            resp2 = await client.get("/api/profiles/active/model")
            assert resp2.json()["model"] == "llama3.1:8b"

    @pytest.mark.asyncio
    async def test_save_empty_model_returns_error(self, client):
        resp = await client.post("/api/profiles/active/model", json={"model": ""})
        assert resp.status_code == 400
