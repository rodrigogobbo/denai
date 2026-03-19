"""CRUD de memórias."""

from fastapi import APIRouter

from ..db import get_db

router = APIRouter()


@router.get("/api/memories")
async def list_memories():
    db = await get_db()
    rows = await db.execute_fetchall(
        "SELECT id, type, content, tags, created_at FROM memories ORDER BY created_at DESC LIMIT 50"
    )
    await db.close()
    return {"memories": [dict(r) for r in rows]}


@router.delete("/api/memories/{mem_id}")
async def delete_memory(mem_id: str):
    db = await get_db()
    await db.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
    await db.commit()
    await db.close()
    return {"ok": True}
