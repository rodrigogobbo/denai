"""Rotas REST para spec documents — CRUD via HTTP."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from ..tools.plans_spec import (
    VALID_STATUSES,
    _create,
    _delete,
    _get_db,
    _plan_path,
    _update,
)

router = APIRouter(prefix="/api/plans-spec", tags=["plans-spec"])


class PlanSpecCreate(BaseModel):
    title: str
    content: str
    status: str = "draft"
    tags: str = ""


class PlanSpecUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None
    tags: str | None = None


@router.get("")
async def list_plan_specs(
    status: str | None = Query(None, description="Filtrar por status"),
) -> dict[str, Any]:
    """Lista todos os spec documents (metadados)."""
    conn = _get_db()
    if status and status in VALID_STATUSES:
        rows = conn.execute(
            "SELECT * FROM plan_specs WHERE status = ? ORDER BY updated_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM plan_specs ORDER BY updated_at DESC").fetchall()
    conn.close()

    return {
        "plans": [
            {
                "id": row["id"],
                "title": row["title"],
                "status": row["status"],
                "tags": row["tags"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
    }


@router.post("", status_code=201)
async def create_plan_spec(body: PlanSpecCreate) -> dict[str, Any]:
    """Cria um novo spec document."""
    result = await _create(
        {
            "title": body.title,
            "content": body.content,
            "status": body.status,
            "tags": body.tags,
        }
    )
    if result.startswith("❌"):
        raise HTTPException(status_code=400, detail=result)

    # Retorna o spec criado
    plan_id = result.split(": ", 1)[1].split("\n")[0].strip()
    conn = _get_db()
    row = conn.execute("SELECT * FROM plan_specs WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    return dict(row)


@router.get("/{plan_id}")
async def get_plan_spec(plan_id: str) -> dict[str, Any]:
    """Retorna um spec document com conteúdo completo."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM plan_specs WHERE id = ?", (plan_id,)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Spec não encontrado: {plan_id}")

    path = _plan_path(plan_id)
    content = path.read_text(encoding="utf-8") if path.exists() else ""

    return {
        "id": row["id"],
        "title": row["title"],
        "status": row["status"],
        "tags": row["tags"],
        "content": content,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.patch("/{plan_id}")
async def update_plan_spec(plan_id: str, body: PlanSpecUpdate) -> dict[str, Any]:
    """Atualiza um spec document."""
    update_args: dict[str, Any] = {"id": plan_id}
    if body.title is not None:
        update_args["title"] = body.title
    if body.content is not None:
        update_args["content"] = body.content
    if body.status is not None:
        update_args["status"] = body.status
    if body.tags is not None:
        update_args["tags"] = body.tags

    result = await _update(update_args)
    if result.startswith("❌"):
        status_code = 404 if "não encontrado" in result else 400
        raise HTTPException(status_code=status_code, detail=result)

    conn = _get_db()
    row = conn.execute("SELECT * FROM plan_specs WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    return dict(row)


@router.delete("/{plan_id}")
async def delete_plan_spec(plan_id: str) -> Response:
    """Move o spec para .trash/ (soft delete)."""
    result = await _delete({"id": plan_id})
    if result.startswith("❌"):
        raise HTTPException(status_code=404, detail=result)
    return Response(status_code=204)
