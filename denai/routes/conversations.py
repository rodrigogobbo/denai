"""CRUD de conversas e mensagens."""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, Response

from ..config import DEFAULT_MODEL
from ..db import get_db

router = APIRouter()


@router.get("/api/conversations")
async def list_conversations():
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id, title, model, created_at, updated_at FROM conversations ORDER BY updated_at DESC LIMIT 50"
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
            "SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at",
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


@router.get("/api/conversations/search")
async def search_conversations(q: str = Query(..., min_length=1)):
    term = f"%{q}%"
    async with get_db() as db:
        # Search in conversation titles and message content
        rows = await db.execute_fetchall(
            """
            SELECT DISTINCT
                c.id, c.title, c.model, c.created_at, c.updated_at,
                m.content AS snippet
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            WHERE c.title LIKE ? OR m.content LIKE ?
            ORDER BY c.updated_at DESC
            LIMIT 20
            """,
            (term, term),
        )
        results = []
        seen = set()
        for r in rows:
            r = dict(r)
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            snippet = r.pop("snippet", None)
            if snippet and q.lower() in snippet.lower():
                # Extract ~80 chars around the match
                idx = snippet.lower().index(q.lower())
                start = max(0, idx - 40)
                end = min(len(snippet), idx + len(q) + 40)
                r["snippet"] = ("…" if start > 0 else "") + snippet[start:end] + ("…" if end < len(snippet) else "")
            else:
                r["snippet"] = None
            results.append(r)
        return {"results": results}


@router.get("/api/conversations/{conv_id}/export")
async def export_conversation(conv_id: str, format: str = Query("json", pattern="^(json|markdown)$")):
    async with get_db() as db:
        conv_row = await db.execute_fetchall(
            "SELECT id, title, model, created_at, updated_at FROM conversations WHERE id = ?",
            (conv_id,),
        )
        if not conv_row:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
        conv = dict(conv_row[0])

        msg_rows = await db.execute_fetchall(
            "SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conv_id,),
        )
        messages = [dict(m) for m in msg_rows]

    safe_title = conv["title"].replace(" ", "_")[:40]

    if format == "markdown":
        lines = [
            f"# {conv['title']}",
            "",
            f"- **Modelo:** {conv['model']}",
            f"- **Criada em:** {conv['created_at']}",
            f"- **Atualizada em:** {conv['updated_at']}",
            "",
            "---",
            "",
        ]
        for msg in messages:
            role_label = "### 👤 Usuário" if msg["role"] == "user" else "### 🐺 DenAI"
            lines.append(role_label)
            lines.append("")
            lines.append(msg["content"])
            lines.append("")
        content = "\n".join(lines)
        return PlainTextResponse(
            content,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{safe_title}.md"'},
        )

    # JSON export
    payload = {**conv, "messages": messages}
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.json"'},
    )
