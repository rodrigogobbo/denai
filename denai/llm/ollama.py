"""Integração com Ollama — streaming chat com tool calling."""

from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx

from ..config import DEFAULT_MODEL, MAX_CONTEXT, MAX_TOOL_ROUNDS, OLLAMA_URL
from ..rag import get_rag_context
from ..tools import TOOLS_SPEC, execute_tool
from .context import estimate_messages_tokens, pick_context_size, summarize_old_messages
from .prompt import build_system_prompt

# ─── Config ────────────────────────────────────────────────────────────────

CONTEXT_SUMMARIZE_THRESHOLD = 20000  # Tokens — comprimir acima disso


async def stream_chat(
    messages: list,
    model: str = DEFAULT_MODEL,
    use_tools: bool = True,
) -> AsyncGenerator[str, None]:
    """Stream de chat com Ollama, com suporte a tool calling iterativo.

    Melhorias sobre a versão anterior:
    - max_tool_rounds=25 (era 5) — suporta sessões longas
    - Context auto-sizing — 8k→16k→32k→64k conforme a conversa cresce
    - Summarization automática — comprime histórico antigo quando excede threshold
    """

    # Extrair última mensagem do usuário para RAG context
    user_query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_query = msg.get("content", "")
            break

    # Buscar contexto RAG relevante (não bloqueia se não houver docs)
    rag_context = ""
    if user_query:
        try:
            rag_context = get_rag_context(user_query, max_chars=3000)
        except Exception:
            pass  # RAG é best-effort — não quebra o chat

    system_msg = {"role": "system", "content": build_system_prompt(rag_context)}
    full_messages = [system_msg] + messages

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        for round_num in range(MAX_TOOL_ROUNDS):
            # Auto-summarize se contexto ficou grande demais
            if estimate_messages_tokens(full_messages) > CONTEXT_SUMMARIZE_THRESHOLD:
                full_messages = summarize_old_messages(full_messages, keep_recent=12)

            # Context size dinâmico baseado no tamanho real
            num_ctx = pick_context_size(full_messages, max_context=MAX_CONTEXT)

            payload = {
                "model": model,
                "messages": full_messages,
                "stream": True,
                "options": {"temperature": 0.7, "num_ctx": num_ctx},
            }
            if use_tools and TOOLS_SPEC:
                payload["tools"] = TOOLS_SPEC

            accumulated = ""
            tool_calls = []

            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
                if resp.status_code != 200:
                    error_text = await resp.aread()
                    err_msg = f"Ollama error {resp.status_code}: {error_text.decode()}"
                    yield f"data: {json.dumps({'error': err_msg})}\n\n"
                    return

                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if "message" in chunk:
                        msg = chunk["message"]
                        if msg.get("content"):
                            accumulated += msg["content"]
                            yield f"data: {json.dumps({'content': msg['content']})}\n\n"
                        if msg.get("tool_calls"):
                            tool_calls.extend(msg["tool_calls"])

                    if chunk.get("done"):
                        break

            if not tool_calls:
                break

            # Executar tool calls
            full_messages.append(
                {
                    "role": "assistant",
                    "content": accumulated,
                    "tool_calls": tool_calls,
                }
            )

            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "unknown")
                tool_args = fn.get("arguments", {})

                yield f"data: {json.dumps({'tool_call': {'name': tool_name, 'args': tool_args}})}\n\n"

                # Se for question, enviar evento especial antes de executar
                if tool_name == "question":
                    q_text = tool_args.get("question", "")
                    q_options = tool_args.get("options", [])
                    from ..tools.question import _next_id

                    q_id = _next_id()
                    yield f"data: {json.dumps({'question': {'id': q_id, 'text': q_text, 'options': q_options}})}\n\n"
                    tool_args["_question_id"] = q_id

                result = await execute_tool(tool_name, tool_args)

                yield f"data: {json.dumps({'tool_result': {'name': tool_name, 'result': result[:2000]}})}\n\n"

                full_messages.append({"role": "tool", "content": result})

            # Emitir progresso do round pra UI saber que ainda tá trabalhando
            if round_num > 0 and round_num % 5 == 0:
                yield f"data: {json.dumps({'progress': {'round': round_num + 1, 'max': MAX_TOOL_ROUNDS}})}\n\n"

            tool_calls = []
            accumulated = ""

        yield 'data: {"done": true}\n\n'
