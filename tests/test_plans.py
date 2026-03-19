"""Testes para rotas de planos (/api/plans)."""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from denai.app import create_app
from denai.db import SCHEMA_SQL


@pytest.fixture
async def client(tmp_path):
    """Cria app com DB temporário e client autenticado."""
    db_path = tmp_path / "test_plans.db"
    plans_db_path = tmp_path / "plans.db"

    import aiosqlite

    db = await aiosqlite.connect(str(db_path))
    await db.executescript(SCHEMA_SQL)
    await db.execute("INSERT OR IGNORE INTO _schema_version (version) VALUES (1)")
    await db.commit()
    await db.close()

    with (
        patch("denai.config.DB_PATH", db_path),
        patch("denai.db.DB_PATH", db_path),
        patch("denai.config.DATA_DIR", tmp_path),
        patch("denai.tools.planning.PLANS_DB", plans_db_path),
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


def _create_plan(tmp_path, goal: str, steps: list[dict]) -> int:
    """Helper: insere um plano direto no DB."""
    import sqlite3
    from datetime import datetime, timezone

    plans_db = tmp_path / "plans.db"
    plans_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(plans_db))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            steps TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO plans (goal, steps, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (goal, json.dumps(steps), now, now),
    )
    conn.commit()
    plan_id = cursor.lastrowid
    conn.close()
    return plan_id


@pytest.mark.asyncio
async def test_list_plans_empty(client):
    resp = await client.get("/api/plans")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_plans(client, tmp_path):
    steps = [
        {"text": "Step 1", "status": "done", "result": "ok"},
        {"text": "Step 2", "status": "pending", "result": ""},
    ]
    _create_plan(tmp_path, "Test Goal", steps)

    resp = await client.get("/api/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["goal"] == "Test Goal"
    assert data[0]["step_count"] == 2
    assert data[0]["done_count"] == 1


@pytest.mark.asyncio
async def test_get_plan(client, tmp_path):
    steps = [{"text": "Do thing", "status": "in_progress", "result": ""}]
    pid = _create_plan(tmp_path, "My Plan", steps)

    resp = await client.get(f"/api/plans/{pid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["goal"] == "My Plan"
    assert len(data["steps"]) == 1
    assert data["steps"][0]["text"] == "Do thing"


@pytest.mark.asyncio
async def test_get_plan_not_found(client):
    resp = await client.get("/api/plans/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_plan(client, tmp_path):
    pid = _create_plan(tmp_path, "Delete Me", [{"text": "x", "status": "pending", "result": ""}])

    resp = await client.delete(f"/api/plans/{pid}")
    assert resp.status_code == 204

    # Confirm deleted
    resp2 = await client.get(f"/api/plans/{pid}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_plan_not_found(client):
    resp = await client.delete("/api/plans/9999")
    assert resp.status_code == 404
