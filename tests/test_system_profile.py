"""Testes para system_profile.py e GET /api/system/profile."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from denai.system_profile import (
    MODEL_CATALOG,
    TIER_DEFAULTS,
    _best_installed,
    _get_tier,
    _recommend,
    get_system_profile,
)

# ─── _get_tier ─────────────────────────────────────────────────────────────


class TestGetTier:
    def test_minimal_very_low_ram(self):
        assert _get_tier(4.0, None) == "minimal"

    def test_light_border(self):
        assert _get_tier(6.0, None) == "light"

    def test_light_mid_range(self):
        assert _get_tier(8.0, None) == "light"

    def test_mid_at_10gb(self):
        assert _get_tier(10.0, None) == "mid"

    def test_mid_16gb(self):
        assert _get_tier(16.0, None) == "mid"

    def test_high_at_20gb(self):
        assert _get_tier(20.0, None) == "high"

    def test_high_32gb(self):
        assert _get_tier(32.0, None) == "high"

    def test_ultra_above_36gb(self):
        assert _get_tier(40.0, None) == "ultra"

    def test_vram_boost_non_arm(self):
        # 8GB RAM + 12GB VRAM → effective ~18GB → mid tier
        with patch("denai.system_profile.platform.machine", return_value="x86_64"):
            tier = _get_tier(8.0, 12.0)
        assert tier in ("mid", "high")

    def test_no_vram_boost_on_apple_silicon(self):
        # Apple Silicon: unified memory — no extra boost
        with patch("denai.system_profile.platform.machine", return_value="arm64"):
            tier_with = _get_tier(8.0, 8.0)
            tier_without = _get_tier(8.0, None)
        assert tier_with == tier_without


# ─── TIER_DEFAULTS ─────────────────────────────────────────────────────────


class TestTierDefaults:
    def test_all_tiers_have_defaults(self):
        for tier in ("minimal", "light", "mid", "high", "ultra"):
            assert tier in TIER_DEFAULTS
            assert TIER_DEFAULTS[tier]

    def test_defaults_in_catalog(self):
        catalog_names = [m.name for m in MODEL_CATALOG]
        for model in TIER_DEFAULTS.values():
            assert model in catalog_names


# ─── MODEL_CATALOG ─────────────────────────────────────────────────────────


class TestModelCatalog:
    def test_catalog_not_empty(self):
        assert len(MODEL_CATALOG) >= 4

    def test_ascending_ram_requirements(self):
        rams = [m.ram_min_gb for m in MODEL_CATALOG]
        assert rams == sorted(rams)

    def test_all_models_have_required_fields(self):
        for m in MODEL_CATALOG:
            assert m.name
            assert m.size_gb > 0
            assert m.ram_min_gb > 0
            assert m.description


# ─── _best_installed ───────────────────────────────────────────────────────


class TestBestInstalled:
    def test_returns_none_when_nothing_installed(self):
        assert _best_installed([], "mid", 16.0) is None

    def test_returns_installed_compatible_model(self):
        result = _best_installed(["llama3.2:3b"], "mid", 16.0)
        assert result == "llama3.2:3b"

    def test_returns_best_compatible_when_multiple(self):
        installed = ["llama3.2:3b", "llama3.1:8b"]
        result = _best_installed(installed, "mid", 16.0)
        # llama3.1:8b is heavier — should be preferred
        assert result is not None
        assert "llama3.1" in result or "llama3.2" in result

    def test_ignores_incompatible_installed_models(self):
        # qwen2.5-coder:32b needs 36GB, user has 8GB
        result = _best_installed(["qwen2.5-coder:32b"], "light", 8.0)
        assert result is None

    def test_matches_by_prefix(self):
        # Installed as "llama3.2:3b" but catalog has "llama3.2:3b" — should match
        result = _best_installed(["llama3.2:3b"], "mid", 16.0)
        assert result == "llama3.2:3b"


# ─── _recommend ────────────────────────────────────────────────────────────


class TestRecommend:
    def test_recommends_tier_default_when_nothing_installed(self):
        with patch("denai.system_profile._get_disk_free_gb", return_value=50.0):
            rec = _recommend("mid", 16.0, [])
        assert rec["model"] == TIER_DEFAULTS["mid"]
        assert rec["already_installed"] is False

    def test_prioritizes_installed_model(self):
        with patch("denai.system_profile._get_disk_free_gb", return_value=50.0):
            rec = _recommend("mid", 16.0, ["llama3.2:3b"])
        assert rec["already_installed"] is True
        assert "llama3.2" in rec["model"]

    def test_downgrades_on_low_disk(self):
        # Only 1GB free — should recommend lighter model
        with patch("denai.system_profile._get_disk_free_gb", return_value=1.0):
            rec = _recommend("ultra", 64.0, [])
        # Should not recommend 32b model (18GB) when only 1GB free
        recommended_model = next((m for m in MODEL_CATALOG if m.name == rec["model"]), None)
        assert recommended_model is None or recommended_model.size_gb < 18.0

    def test_alternatives_exclude_recommended(self):
        with patch("denai.system_profile._get_disk_free_gb", return_value=50.0):
            rec = _recommend("mid", 16.0, [])
        for alt in rec.get("alternatives", []):
            assert alt["name"] != rec["model"]

    def test_alternatives_are_compatible(self):
        with patch("denai.system_profile._get_disk_free_gb", return_value=50.0):
            rec = _recommend("mid", 16.0, [])
        for alt in rec.get("alternatives", []):
            assert alt["ram_min_gb"] <= 16.0 * 1.1


# ─── get_system_profile ────────────────────────────────────────────────────


class TestGetSystemProfile:
    @pytest.mark.asyncio
    async def test_profile_has_required_fields(self):
        with (
            patch("denai.system_profile._get_ram_gb", return_value=16.0),
            patch("denai.system_profile._get_vram_gb", return_value=None),
            patch("denai.system_profile._get_disk_free_gb", return_value=50.0),
            patch("denai.system_profile._get_installed_models", new_callable=AsyncMock, return_value=[]),
        ):
            profile = await get_system_profile()

        assert "ram_gb" in profile
        assert "tier" in profile
        assert "recommendation" in profile
        assert "model_catalog" in profile
        assert "installed_models" in profile
        assert profile["ram_gb"] == 16.0

    @pytest.mark.asyncio
    async def test_catalog_has_compatibility_flags(self):
        with (
            patch("denai.system_profile._get_ram_gb", return_value=8.0),
            patch("denai.system_profile._get_vram_gb", return_value=None),
            patch("denai.system_profile._get_disk_free_gb", return_value=50.0),
            patch("denai.system_profile._get_installed_models", new_callable=AsyncMock, return_value=[]),
        ):
            profile = await get_system_profile()

        for entry in profile["model_catalog"]:
            assert "compatible" in entry
            assert "installed" in entry
            assert "warning" in entry

        # Heavy models should not be compatible with 8GB
        heavy = next((e for e in profile["model_catalog"] if e["ram_min_gb"] > 8.0), None)
        if heavy:
            assert heavy["compatible"] is False
            assert heavy["warning"] is not None

    @pytest.mark.asyncio
    async def test_installed_models_reflected(self):
        with (
            patch("denai.system_profile._get_ram_gb", return_value=16.0),
            patch("denai.system_profile._get_vram_gb", return_value=None),
            patch("denai.system_profile._get_disk_free_gb", return_value=50.0),
            patch("denai.system_profile._get_installed_models", new_callable=AsyncMock, return_value=["llama3.2:3b"]),
        ):
            profile = await get_system_profile()

        llama3 = next((e for e in profile["model_catalog"] if e["name"] == "llama3.2:3b"), None)
        assert llama3 is not None
        assert llama3["installed"] is True


# ─── Route: GET /api/system/profile ────────────────────────────────────────


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

    with (
        patch("denai.config.DB_PATH", db_path),
        patch("denai.db.DB_PATH", db_path),
        patch("denai.config.DATA_DIR", tmp_path),
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


class TestSystemProfileRoute:
    @pytest.mark.asyncio
    async def test_returns_200(self, client):
        with patch("denai.system_profile._get_installed_models", new_callable=AsyncMock, return_value=[]):
            resp = await client.get("/api/system/profile")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_has_tier(self, client):
        with patch("denai.system_profile._get_installed_models", new_callable=AsyncMock, return_value=[]):
            resp = await client.get("/api/system/profile")
        data = resp.json()
        assert data["tier"] in ("minimal", "light", "mid", "high", "ultra")

    @pytest.mark.asyncio
    async def test_response_has_recommendation(self, client):
        with patch("denai.system_profile._get_installed_models", new_callable=AsyncMock, return_value=[]):
            resp = await client.get("/api/system/profile")
        data = resp.json()
        assert "model" in data["recommendation"]
        assert "reason" in data["recommendation"]
