"""Tests for granular permissions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from denai.app import create_app
from denai.permissions import (
    _DEFAULTS,
    PermissionResult,
    _load_yaml_perms,
    check_permission,
    get_all_permissions,
    reset_permissions,
    set_permission,
)

# ─── Unit tests ───


class TestDefaults:
    """Test default permission levels."""

    def test_read_tools_are_allow(self):
        for tool in ("file_read", "list_files", "grep", "think"):
            assert _DEFAULTS[tool] == "allow"

    def test_write_tools_are_ask(self):
        for tool in ("file_write", "file_edit", "command_exec"):
            assert _DEFAULTS[tool] == "ask"

    def test_all_defaults_valid(self):
        for tool, level in _DEFAULTS.items():
            assert level in ("allow", "ask", "deny"), f"{tool} has invalid level: {level}"


class TestLoadYamlPerms:
    """Test the _load_yaml_perms helper."""

    def test_load_with_section_key(self, tmp_path: Path):
        f = tmp_path / "perms.yaml"
        f.write_text("permissions:\n  grep: deny\n  file_read: allow\n")
        result = _load_yaml_perms(f, section_key="permissions")
        assert result == {"grep": "deny", "file_read": "allow"}

    def test_load_root_level(self, tmp_path: Path):
        f = tmp_path / "perms.yaml"
        f.write_text("grep: deny\nfile_write: allow\n")
        result = _load_yaml_perms(f)
        assert result == {"grep": "deny", "file_write": "allow"}

    def test_load_filters_invalid_levels(self, tmp_path: Path):
        f = tmp_path / "perms.yaml"
        f.write_text("grep: deny\nfile_read: banana\n")
        result = _load_yaml_perms(f)
        assert result == {"grep": "deny"}

    def test_load_nonexistent_file(self, tmp_path: Path):
        result = _load_yaml_perms(tmp_path / "nope.yaml")
        assert result == {}

    def test_load_invalid_yaml(self, tmp_path: Path):
        f = tmp_path / "bad.yaml"
        f.write_text(": : : invalid {{{\n")
        result = _load_yaml_perms(f)
        assert result == {}

    def test_load_non_dict_yaml(self, tmp_path: Path):
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2\n")
        result = _load_yaml_perms(f)
        assert result == {}

    def test_load_section_key_non_dict(self, tmp_path: Path):
        f = tmp_path / "perms.yaml"
        f.write_text("permissions: not_a_dict\n")
        result = _load_yaml_perms(f, section_key="permissions")
        assert result == {}

    def test_fallback_to_root_when_section_missing(self, tmp_path: Path):
        f = tmp_path / "perms.yaml"
        f.write_text("grep: deny\nfile_read: allow\n")
        result = _load_yaml_perms(f, section_key="permissions")
        assert result == {"grep": "deny", "file_read": "allow"}


class TestCheckPermission:
    """Test permission checking."""

    def test_allow_tool(self):
        result = check_permission("file_read")
        assert result.allowed is True
        assert result.level == "allow"

    def test_ask_tool(self):
        result = check_permission("file_write")
        assert result.allowed is False
        assert result.level == "ask"
        assert "confirmação" in result.reason

    def test_unknown_tool_defaults_ask(self):
        result = check_permission("unknown_tool_xyz")
        assert result.allowed is False
        assert result.level == "ask"

    def test_result_has_tool_name(self):
        result = check_permission("grep")
        assert result.tool == "grep"


class TestSetPermission:
    """Test setting permissions."""

    def test_set_and_check(self, tmp_path: Path):
        fake_perms = tmp_path / "permissions.yaml"
        with patch("denai.permissions.PERMISSIONS_FILE", fake_perms):
            set_permission("file_read", "deny")
            # Verify the file was written with the correct override
            assert fake_perms.is_file()
            import yaml

            data = yaml.safe_load(fake_perms.read_text())
            assert data["permissions"]["file_read"] == "deny"

    def test_set_invalid_level(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Nível inválido"):
            set_permission("file_read", "invalid")

    def test_set_creates_file(self, tmp_path: Path):
        fake_perms = tmp_path / "sub" / "permissions.yaml"
        with patch("denai.permissions.PERMISSIONS_FILE", fake_perms):
            set_permission("grep", "deny")
            assert fake_perms.is_file()


class TestResetPermissions:
    """Test resetting permissions."""

    def test_reset_removes_file(self, tmp_path: Path):
        fake_perms = tmp_path / "permissions.yaml"
        fake_perms.write_text("permissions:\n  file_read: deny\n")
        with patch("denai.permissions.PERMISSIONS_FILE", fake_perms):
            reset_permissions()
            assert not fake_perms.is_file()

    def test_reset_nonexistent_ok(self, tmp_path: Path):
        fake_perms = tmp_path / "nope.yaml"
        with patch("denai.permissions.PERMISSIONS_FILE", fake_perms):
            reset_permissions()  # Should not raise


class TestGetAllPermissions:
    """Test merged permissions."""

    def test_returns_defaults_without_overrides(self):
        with patch("denai.permissions._load_overrides", return_value={}):
            with patch("denai.permissions._load_from_config_yaml", return_value={}):
                perms = get_all_permissions()
                assert perms["file_read"] == "allow"
                assert perms["file_write"] == "ask"

    def test_overrides_merge(self):
        with patch("denai.permissions._load_overrides", return_value={"file_read": "deny"}):
            with patch("denai.permissions._load_from_config_yaml", return_value={}):
                perms = get_all_permissions()
                assert perms["file_read"] == "deny"
                assert perms["file_write"] == "ask"  # unchanged

    def test_config_yaml_overrides_defaults(self):
        with (
            patch("denai.permissions._load_overrides", return_value={}),
            patch(
                "denai.permissions._load_from_config_yaml",
                return_value={"command_exec": "allow"},
            ),
        ):
            perms = get_all_permissions()
            assert perms["command_exec"] == "allow"

    def test_permissions_yaml_wins_over_config(self):
        with (
            patch("denai.permissions._load_overrides", return_value={"grep": "deny"}),
            patch(
                "denai.permissions._load_from_config_yaml",
                return_value={"grep": "allow"},
            ),
        ):
            perms = get_all_permissions()
            assert perms["grep"] == "deny"  # permissions.yaml wins


class TestPermissionResult:
    """Test PermissionResult dataclass."""

    def test_basic(self):
        r = PermissionResult(allowed=True, level="allow", tool="test")
        assert r.allowed is True
        assert r.reason == ""

    def test_with_reason(self):
        r = PermissionResult(allowed=False, level="deny", tool="rm", reason="Blocked!")
        assert r.reason == "Blocked!"


# ─── API tests ───


@pytest.fixture
async def client(tmp_path):
    """Cria app com client autenticado e router de permissions incluído."""
    with patch("denai.config.DATA_DIR", tmp_path):
        _app = create_app()

        # Inclui o router de permissions (não registrado no __init__.py ainda)
        from denai.routes.permissions import router as perms_router

        _app.include_router(perms_router)

        from denai.security.auth import API_KEY
        from denai.security.rate_limit import rate_limiter

        rate_limiter.reset()

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=_app),
            base_url="http://testserver",
            headers={"X-API-Key": API_KEY},
        ) as c:
            yield c


@pytest.mark.asyncio
class TestPermissionsAPI:
    """Test permissions API endpoints."""

    async def test_list_permissions(self, client):
        resp = await client.get("/api/permissions")
        assert resp.status_code == 200
        data = resp.json()
        assert "permissions" in data
        assert "file_read" in data["permissions"]
        assert data["permissions"]["file_read"]["level"] in ("allow", "ask", "deny")

    async def test_check_permission(self, client):
        resp = await client.post("/api/permissions/check", json={"tool": "grep"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["tool"] == "grep"
        assert data["allowed"] is True

    async def test_check_missing_tool(self, client):
        resp = await client.post("/api/permissions/check", json={})
        data = resp.json()
        assert "error" in data

    async def test_update_permission(self, client):
        resp = await client.put("/api/permissions", json={"tool": "test_tool", "level": "deny"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("ok") is True or "error" not in data

    async def test_update_invalid_level(self, client):
        resp = await client.put("/api/permissions", json={"tool": "grep", "level": "banana"})
        data = resp.json()
        assert "error" in data

    async def test_reset_permissions(self, client):
        resp = await client.post("/api/permissions/reset")
        assert resp.status_code == 200
