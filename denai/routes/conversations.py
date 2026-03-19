"""CRUD de conversas e mensagens."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Request

from ..config import DEFAULT_MODEL
from ..db import get_db

router = APIRouter()


@router.get("/api/conversations")
async def list_conversations():
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, title, model, created_at, updated_at "
            "FROM conversations ORDER BY updated_at DESC LIMIT 50"
        )
        return {"conversations": [dict(r) for r in rows]}


@router.post("/api/conversations")
async def create_conversation(request: Request):
    body = await request.json()
    conv_id = str(uuid.uuid4())[:12]
    model = body.get("model", DEFAULT_MODEL)
    now = datetime.now().isoformat()
    async with get_db() as db:
        await db.execute(
            "INSERT INTO conversations (id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conv_id, "Nova conversa", model, now, now),
        )
        await db.commit()
    return {"id": conv_id, "model": model}


@router.get("/api/conversations/{conv_id}/messages")
async def get_messages(conv_id: str):
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, role, content, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY created_at",
            (conv_id,),
        )
        return {"messages": [dict(r) for r in rows]}


@router.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        await db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        await db.commit()
    return {"ok": True}
