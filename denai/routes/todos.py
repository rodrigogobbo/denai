"""Rotas REST para todo list."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..tools.todowrite import _get_db, todowrite

router = APIRouter(prefix="/api/todos", tags=["todos"])


class TodoItem(BaseModel):
    id: str
    content: str
    status: str = "pending"
    priority: str = "medium"


class TodoWriteBody(BaseModel):
    todos: list[TodoItem]


@router.get("")
async def list_todos() -> dict[str, Any]:
    """Retorna a lista de todos atual."""
    conn = _get_db()
    rows = conn.execute("SELECT * FROM todos ORDER BY rowid").fetchall()
    conn.close()
    todos = [dict(r) for r in rows]
    done = sum(1 for t in todos if t["status"] == "completed")
    return {"todos": todos, "total": len(todos), "done": done}


@router.put("")
async def write_todos(body: TodoWriteBody) -> dict[str, Any]:
    """Substitui a lista inteira de todos."""
    result = await todowrite({"todos": [t.model_dump() for t in body.todos]})
    if result.startswith("❌"):
        raise HTTPException(status_code=400, detail=result)
    conn = _get_db()
    rows = conn.execute("SELECT * FROM todos ORDER BY rowid").fetchall()
    conn.close()
    todos = [dict(r) for r in rows]
    done = sum(1 for t in todos if t["status"] == "completed")
    return {"todos": todos, "total": len(todos), "done": done}


@router.delete("")
async def clear_todos() -> dict[str, Any]:
    """Limpa toda a lista de todos."""
    conn = _get_db()
    conn.execute("DELETE FROM todos")
    conn.commit()
    conn.close()
    return {"ok": True}
