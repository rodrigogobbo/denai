"""Rota /api/chat — streaming SSE."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..config import DEFAULT_MODEL
from ..db import get_db
from ..llm import stream_chat
from ..modes import filter_tools_for_mode, get_system_prompt_prefix
from ..tools import TOOLS_SPEC
from ..undo import commit_changeset, start_changeset

router = APIRouter()


@router.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    conv_id = body.get("conversation_id")
    user_message = body.get("message", "")
    model = body.get("model", DEFAULT_MODEL)
    mode = body.get("mode", "build")

    if not user_message.strip():
        return JSONResponse({"error": "Mensagem vazia"}, status_code=400)
    if len(user_message) > 50_000:
        return JSONResponse({"error": "Mensagem muito longa (máx 50000 chars)"}, status_code=400)

    async with get_db() as db:
        # Criar conversa se necessário
        if not conv_id:
            conv_id = str(uuid.uuid4())[:12]
            now = datetime.now().isoformat()
            await db.execute(
                "INSERT INTO conversations (id, title, model, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (conv_id, user_message[:50], model, now, now),
            )
        else:
            rows = await db.execute_fetchall("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv_id,))
            if rows[0][0] == 0:
                await db.execute(
                    "UPDATE conversations SET title = ? WHERE id = ?",
                    (user_message[:50], conv_id),
                )

        # Salvar mensagem do usuário
        msg_id = str(uuid.uuid4())[:12]
        now = datetime.now().isoformat()
        await db.execute(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (msg_id, conv_id, "user", user_message, now),
        )
        await db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conv_id))
        await db.commit()

        # Histórico
        rows = await db.execute_fetchall(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conv_id,),
        )
        messages = [{"role": r[0], "content": r[1]} for r in rows]

    # Memórias
    async with get_db() as db:
        mem_rows = await db.execute_fetchall("SELECT type, content FROM memories ORDER BY created_at DESC LIMIT 20")
        if mem_rows:
            mem_text = "\n".join(f"- [{r[0]}] {r[1]}" for r in mem_rows)
            messages.insert(0, {"role": "system", "content": f"Memórias persistentes:\n{mem_text}"})

    # Filter tools and get prompt prefix based on mode
    filtered_tools = filter_tools_for_mode(TOOLS_SPEC, mode)
    prompt_prefix = get_system_prompt_prefix(mode)

    async def generate():
        full_response = []
        start_changeset(f"chat:{conv_id}")
        yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"

        async for chunk in stream_chat(
            messages,
            model,
            tools_spec=filtered_tools,
            prompt_prefix=prompt_prefix,
        ):
            yield chunk
            try:
                line = chunk.strip()
                if line.startswith("data: "):
                    line = line[6:]
                data = json.loads(line)
                if "content" in data:
                    full_response.append(data["content"])
            except Exception:
                pass

        # Salvar resposta
        response_text = "".join(full_response)
        if response_text.strip():
            async with get_db() as db:
                resp_id = str(uuid.uuid4())[:12]
                now2 = datetime.now().isoformat()
                await db.execute(
                    "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                    (resp_id, conv_id, "assistant", response_text, now2),
                )
                await db.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now2, conv_id))
                await db.commit()

        # Commit undo changeset após streaming completo
        commit_changeset()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
