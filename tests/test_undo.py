"""Testes do sistema de undo/redo."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from denai.app import create_app
from denai.security.auth import API_KEY
from denai.undo import (
    _redo_stack,
    _undo_stack,
    clear,
    commit_changeset,
    get_status,
    redo,
    save_snapshot,
    start_changeset,
    undo,
)


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": API_KEY},
    ) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_stacks():
    """Reset undo/redo stacks between tests."""
    clear()
    yield
    clear()


# ── Snapshots ────────────────────────────────────────────────────


def test_save_snapshot_existing_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("original content")

    start_changeset("test")
    save_snapshot(str(f))
    commit_changeset()

    assert len(_undo_stack) == 1
    assert _undo_stack[0].snapshots[0].content == "original content"
    assert _undo_stack[0].snapshots[0].existed is True


def test_save_snapshot_nonexistent_file(tmp_path):
    f = tmp_path / "new.txt"

    start_changeset("test")
    save_snapshot(str(f))
    commit_changeset()

    assert _undo_stack[0].snapshots[0].existed is False
    assert _undo_stack[0].snapshots[0].content is None


def test_no_duplicate_snapshots(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("content")

    start_changeset("test")
    save_snapshot(str(f))
    save_snapshot(str(f))  # Duplicate — should be ignored
    commit_changeset()

    assert len(_undo_stack[0].snapshots) == 1


def test_empty_changeset_not_saved():
    start_changeset("empty")
    commit_changeset()
    assert len(_undo_stack) == 0


# ── Undo ─────────────────────────────────────────────────────────


def test_undo_restores_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("original")

    start_changeset("edit")
    save_snapshot(str(f))
    commit_changeset()

    f.write_text("modified")
    assert f.read_text() == "modified"

    result = undo()
    assert result["ok"] is True
    assert f.read_text() == "original"


def test_undo_deletes_new_file(tmp_path):
    f = tmp_path / "new.txt"

    start_changeset("create")
    save_snapshot(str(f))  # File didn't exist
    commit_changeset()

    f.write_text("new content")
    assert f.exists()

    result = undo()
    assert result["ok"] is True
    assert not f.exists()


def test_undo_empty_stack():
    result = undo()
    assert "error" in result


def test_undo_populates_redo(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("v1")

    start_changeset("edit")
    save_snapshot(str(f))
    commit_changeset()
    f.write_text("v2")

    undo()
    assert len(_redo_stack) == 1


# ── Redo ─────────────────────────────────────────────────────────


def test_redo_after_undo(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("v1")

    start_changeset("edit")
    save_snapshot(str(f))
    commit_changeset()
    f.write_text("v2")

    undo()  # back to v1
    assert f.read_text() == "v1"

    redo()  # back to v2
    assert f.read_text() == "v2"


def test_redo_empty_stack():
    result = redo()
    assert "error" in result


def test_new_change_clears_redo(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("v1")

    start_changeset("edit1")
    save_snapshot(str(f))
    commit_changeset()
    f.write_text("v2")

    undo()
    assert len(_redo_stack) == 1

    # New change should clear redo
    start_changeset("edit2")
    save_snapshot(str(f))
    commit_changeset()
    assert len(_redo_stack) == 0


# ── Status ───────────────────────────────────────────────────────


def test_get_status():
    status = get_status()
    assert status["undo_available"] == 0
    assert status["redo_available"] == 0


def test_get_status_with_history(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("content")

    start_changeset("test")
    save_snapshot(str(f))
    commit_changeset()

    status = get_status()
    assert status["undo_available"] == 1


# ── Stack limit ──────────────────────────────────────────────────


def test_stack_limit(tmp_path):
    from denai.undo import MAX_UNDO_STACK

    f = tmp_path / "test.txt"
    for i in range(MAX_UNDO_STACK + 10):
        f.write_text(f"version {i}")
        start_changeset(f"edit {i}")
        save_snapshot(str(f))
        commit_changeset()

    assert len(_undo_stack) == MAX_UNDO_STACK


# ── API Endpoints ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_undo_status(client):
    resp = await client.get("/api/undo/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "undo_available" in data
    assert "redo_available" in data


@pytest.mark.asyncio
async def test_api_undo_empty(client):
    resp = await client.post("/api/undo")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_api_redo_empty(client):
    resp = await client.post("/api/redo")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
