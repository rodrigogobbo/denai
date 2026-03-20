"""Tests for skills system."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from denai.app import app
from denai.routes.skills import router as skills_router
from denai.security import API_KEY
from denai.skills import (
    Skill,
    _active_skills,
    _parse_skill_file,
    activate_skill,
    clear_active_skills,
    deactivate_skill,
    discover_skills,
    get_active_skills,
    get_skill,
    get_skills_context,
    match_skills,
)

# ─── Unit tests ───


class TestSkill:
    """Test Skill dataclass."""

    def test_basic(self):
        s = Skill(name="test", description="A test skill")
        assert s.name == "test"
        assert s.triggers == []
        assert s.content == ""

    def test_with_triggers(self):
        s = Skill(name="test", triggers=["foo", "bar"])
        assert len(s.triggers) == 2


class TestParseSkillFile:
    """Test skill file parsing."""

    def test_simple_md(self, tmp_path: Path):
        f = tmp_path / "review.md"
        f.write_text("Just review the code carefully.")
        skill = _parse_skill_file(f)
        assert skill is not None
        assert skill.name == "review"
        assert skill.content == "Just review the code carefully."

    def test_with_frontmatter(self, tmp_path: Path):
        f = tmp_path / "debug.md"
        content = (
            "---\nname: debugger\ndescription: Debug skill\n"
            "triggers:\n  - debug\n  - bug\n---\nDebug instructions here."
        )
        f.write_text(content)
        skill = _parse_skill_file(f)
        assert skill is not None
        assert skill.name == "debugger"
        assert skill.description == "Debug skill"
        assert skill.triggers == ["debug", "bug"]
        assert skill.content == "Debug instructions here."

    def test_triggers_as_string(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("---\ntriggers: foo, bar, baz\n---\nContent.")
        skill = _parse_skill_file(f)
        assert skill is not None
        assert skill.triggers == ["foo", "bar", "baz"]

    def test_auto_activate(self, tmp_path: Path):
        f = tmp_path / "always.md"
        f.write_text("---\nauto_activate: true\ndescription: Always on\n---\nAlways active.")
        skill = _parse_skill_file(f)
        assert skill is not None
        assert skill.auto_activate is True

    def test_empty_file(self, tmp_path: Path):
        f = tmp_path / "empty.md"
        f.write_text("")
        assert _parse_skill_file(f) is None

    def test_no_content_after_frontmatter(self, tmp_path: Path):
        f = tmp_path / "nocontent.md"
        f.write_text("---\nname: test\n---\n")
        assert _parse_skill_file(f) is None

    def test_invalid_yaml(self, tmp_path: Path):
        f = tmp_path / "bad.md"
        f.write_text("---\n: invalid: yaml: [[\n---\nStill has content.")
        skill = _parse_skill_file(f)
        # Should fall back to using raw content
        assert skill is not None


class TestDiscoverSkills:
    """Test skill discovery."""

    def test_discover_empty(self, tmp_path: Path):
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            skills = discover_skills()
            assert skills == []

    def test_discover_skills(self, tmp_path: Path):
        (tmp_path / "alpha.md").write_text("Alpha skill content.")
        (tmp_path / "beta.md").write_text("---\ndescription: Beta\n---\nBeta content.")
        (tmp_path / "not-a-skill.txt").write_text("Ignored")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            skills = discover_skills()
            assert len(skills) == 2
            names = [s.name for s in skills]
            assert "alpha" in names
            assert "beta" in names

    def test_discover_sorted(self, tmp_path: Path):
        (tmp_path / "zebra.md").write_text("Z")
        (tmp_path / "alpha.md").write_text("A")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            skills = discover_skills()
            assert skills[0].name == "alpha"
            assert skills[1].name == "zebra"


class TestMatchSkills:
    """Test trigger matching."""

    def test_match_by_trigger(self, tmp_path: Path):
        (tmp_path / "review.md").write_text("---\ntriggers:\n  - code review\n  - revisar\n---\nReview.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            matched = match_skills("pode fazer um code review?")
            assert len(matched) == 1
            assert matched[0].name == "review"

    def test_no_match(self, tmp_path: Path):
        (tmp_path / "review.md").write_text("---\ntriggers:\n  - code review\n---\nReview.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            matched = match_skills("hello world")
            assert matched == []

    def test_case_insensitive(self, tmp_path: Path):
        (tmp_path / "test.md").write_text("---\ntriggers:\n  - DEBUG\n---\nDebug.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            matched = match_skills("help me debug this")
            assert len(matched) == 1

    def test_auto_activate_always_matches(self, tmp_path: Path):
        (tmp_path / "always.md").write_text("---\nauto_activate: true\n---\nAlways on.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            matched = match_skills("random text")
            assert len(matched) == 1

    def test_empty_text(self, tmp_path: Path):
        assert match_skills("") == []


class TestActivation:
    """Test manual skill activation."""

    def setup_method(self):
        _active_skills.clear()

    def test_activate(self, tmp_path: Path):
        (tmp_path / "test.md").write_text("Test skill.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            assert activate_skill("test") is True
            assert "test" in _active_skills

    def test_activate_nonexistent(self, tmp_path: Path):
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            assert activate_skill("nope") is False

    def test_deactivate(self, tmp_path: Path):
        _active_skills.add("test")
        assert deactivate_skill("test") is True
        assert "test" not in _active_skills

    def test_deactivate_not_active(self):
        assert deactivate_skill("nope") is False

    def test_clear(self):
        _active_skills.update({"a", "b", "c"})
        clear_active_skills()
        assert len(_active_skills) == 0


class TestGetActiveSkills:
    """Test getting active skills."""

    def setup_method(self):
        _active_skills.clear()

    def test_empty(self, tmp_path: Path):
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            assert get_active_skills() == []

    def test_manual_active(self, tmp_path: Path):
        (tmp_path / "review.md").write_text("Review content.")
        _active_skills.add("review")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            active = get_active_skills()
            assert len(active) == 1
            assert active[0].name == "review"

    def test_auto_activate_included(self, tmp_path: Path):
        (tmp_path / "auto.md").write_text("---\nauto_activate: true\n---\nAuto skill.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            active = get_active_skills()
            assert len(active) == 1


class TestGetSkillsContext:
    """Test context generation."""

    def setup_method(self):
        _active_skills.clear()

    def test_no_skills(self, tmp_path: Path):
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            ctx = get_skills_context()
            assert ctx == ""

    def test_with_active_skill(self, tmp_path: Path):
        (tmp_path / "review.md").write_text("---\ndescription: Code review\n---\nReview instructions.")
        _active_skills.add("review")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            ctx = get_skills_context()
            assert "review" in ctx
            assert "Review instructions" in ctx
            assert "Skills Ativas" in ctx

    def test_triggered_by_message(self, tmp_path: Path):
        (tmp_path / "debug.md").write_text("---\ntriggers:\n  - debug\n---\nDebug guide.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            ctx = get_skills_context(message="help me debug this error")
            assert "Debug guide" in ctx

    def test_no_duplicates(self, tmp_path: Path):
        (tmp_path / "skill1.md").write_text("---\ntriggers:\n  - test\nauto_activate: true\n---\nContent.")
        _active_skills.add("skill1")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            ctx = get_skills_context(message="test something")
            assert ctx.count("Content.") == 1  # no duplicate


class TestGetSkill:
    """Test getting skill by name."""

    def test_found(self, tmp_path: Path):
        (tmp_path / "myskill.md").write_text("My skill content.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            s = get_skill("myskill")
            assert s is not None
            assert s.name == "myskill"

    def test_not_found(self, tmp_path: Path):
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            assert get_skill("nope") is None


# ─── API tests ───

# Register the skills router on the app (not yet in routes/__init__.py)
app.include_router(skills_router)

_AUTH = {"X-API-Key": API_KEY}


@pytest.mark.asyncio
class TestSkillsAPI:
    """Test skills API endpoints."""

    def setup_method(self):
        _active_skills.clear()

    async def test_list_skills(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/skills", headers=_AUTH)
            assert resp.status_code == 200
            data = resp.json()
            assert "skills" in data

    async def test_activate_skill(self, tmp_path: Path):
        (tmp_path / "test.md").write_text("Test skill.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/skills/activate",
                    json={"name": "test"},
                    headers=_AUTH,
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data.get("ok") is True

    async def test_activate_missing_name(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/skills/activate", json={}, headers=_AUTH)
            data = resp.json()
            assert "error" in data

    async def test_deactivate_skill(self):
        _active_skills.add("test")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/skills/deactivate",
                json={"name": "test"},
                headers=_AUTH,
            )
            assert resp.status_code == 200

    async def test_match_skills(self, tmp_path: Path):
        (tmp_path / "review.md").write_text("---\ntriggers:\n  - review\n---\nReview.")
        with patch("denai.skills.SKILLS_DIR", tmp_path):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/skills/match",
                    json={"text": "do a review"},
                    headers=_AUTH,
                )
                assert resp.status_code == 200
                data = resp.json()
                assert len(data["matched"]) == 1

    async def test_clear_skills(self):
        _active_skills.update({"a", "b"})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/skills/clear", headers=_AUTH)
            assert resp.status_code == 200
            assert len(_active_skills) == 0
