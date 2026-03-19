"""Rotas de planos — CRUD de plans persistidos em SQLite."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..tools.planning import _get_db

router = APIRouter(prefix="/api", tags=["plans"])


@router.get("/plans")
async def list_plans() -> list[dict[str, Any]]:
    """Lista todos os planos (sem steps completos)."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT id, goal, steps, created_at, updated_at FROM plans ORDER BY id DESC"
    ).fetchall()
    conn.close()

    result = []
    for row in rows:
        steps = json.loads(row["steps"]) if row["steps"] else []
        done_count = sum(1 for s in steps if s.get("status") == "done")
        result.append(
            {
                "id": row["id"],
                "goal": row["goal"],
                "step_count": len(steps),
                "done_count": done_count,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
    return result


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: int) -> dict[str, Any]:
    """Retorna um plano com steps completos."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")

    return {
        "id": row["id"],
        "goal": row["goal"],
        "steps": json.loads(row["steps"]) if row["steps"] else [],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: int) -> Response:
    """Remove um plano."""
    conn = _get_db()
    conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    conn.commit()
    affected = conn.execute("SELECT changes()").fetchone()[0]
    conn.close()

    if not affected:
        raise HTTPException(status_code=404, detail="Plano não encontrado.")

    return Response(status_code=204)
