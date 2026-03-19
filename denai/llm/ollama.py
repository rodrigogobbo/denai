"""Integração com Ollama — streaming chat com tool calling."""

from __future__ import annotations

import json
from collections import Counter
from typing import AsyncGenerator

import httpx

from ..config import DEFAULT_MODEL, MAX_CONTEXT, MAX_TOOL_ROUNDS, OLLAMA_URL
from ..rag import get_rag_context
from ..tools import TOOLS_SPEC, execute_tool
from .context import estimate_messages_tokens, pick_context_size, summarize_old_messages
from .prompt import build_system_prompt

# ─── Config ────────────────────────────────────────────────────────────────

CONTEXT_SUMMARIZE_THRESHOLD = 20000  # Tokens — comprimir acima disso
MAX_RETRIES = 2  # Retries para erros transientes do Ollama
CIRCUIT_BREAKER_LIMIT = 3  # Falhas consecutivas na mesma tool → para


def _is_transient_error(status_code: int) -> bool:
    """Erros que podem ser resolvidos com retry."""
    return status_code in (429, 500, 502, 503, 504)


def _build_recovery_hint(tool_name: str, error_msg: str) -> str:
    """Gera uma dica de recuperação baseada no tipo de erro e tool."""
    if tool_name == "file_edit" and "não encontrado" in error_msg.lower():
        return (
            "\n💡 Dica: O texto que você procurou não existe no arquivo. "
            "Use file_read para ver o conteúdo atual antes de tentar file_edit novamente."
        )
    if tool_name == "file_read" and "não encontrado" in error_msg.lower():
        return (
            "\n💡 Dica: O arquivo não existe. Use list_files para verificar "
            "quais arquivos existem no diretório."
        )
    if tool_name == "command_exec" and ("permissão" in error_msg.lower() or "permission" in error_msg.lower()):
        return "\n💡 Dica: Sem permissão para executar este comando. Tente uma abordagem alternativa."
    if "🔒" in error_msg:
        return "\n💡 Dica: Este caminho está bloqueado por segurança. Não tente acessá-lo novamente."
    return ""


async def stream_chat(
    messages: list,
    model: str = DEFAULT_MODEL,
    use_tools: bool = True,
) -> AsyncGenerator[str, None]:
    """Stream de chat com Ollama, com suporte a tool calling iterativo.

    Features:
    - max_tool_rounds configurável (padrão 25) — suporta sessões longas
    - Context auto-sizing — 8k→16k→32k→64k conforme a conversa cresce
    - Summarization automática — comprime histórico antigo quando excede threshold
    - Retry com backoff para erros transientes do Ollama
    - Circuit breaker — para tool que falha 3x consecutivas
    - Recovery hints — dicas de recuperação injetadas no contexto
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

    # Circuit breaker: conta falhas consecutivas por tool
    tool_failures: Counter = Counter()

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

            # Retry para erros transientes do Ollama
            last_error = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
                        if resp.status_code != 200:
                            error_text = await resp.aread()
                            err_msg = f"Ollama error {resp.status_code}: {error_text.decode()}"

                            if _is_transient_error(resp.status_code) and attempt < MAX_RETRIES:
                                last_error = err_msg
                                # Backoff simples: 1s, 2s
                                import asyncio

                                await asyncio.sleep(attempt + 1)
                                continue

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

                    last_error = None
                    break  # Sucesso — sai do retry loop

                except (httpx.ConnectError, httpx.ReadTimeout) as e:
                    if attempt < MAX_RETRIES:
                        last_error = str(e)
                        import asyncio

                        await asyncio.sleep(attempt + 1)
                        continue
                    err = f"Ollama não respondeu após {MAX_RETRIES + 1} tentativas: {e}"
                    yield f"data: {json.dumps({'error': err})}\n\n"
                    return

            if last_error:
                yield f"data: {json.dumps({'error': last_error})}\n\n"
                return

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

                # Circuit breaker: se tool falhou demais, pular
                if tool_failures[tool_name] >= CIRCUIT_BREAKER_LIMIT:
                    skip_msg = (
                        f"⚠️ Tool '{tool_name}' falhou {CIRCUIT_BREAKER_LIMIT} vezes consecutivas. "
                        "Parando tentativas automáticas. Peça ajuda ao usuário ou tente outra abordagem."
                    )
                    yield f"data: {json.dumps({'tool_result': {'name': tool_name, 'result': skip_msg}})}\n\n"
                    full_messages.append({"role": "tool", "content": skip_msg})
                    continue

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

                # Detectar erro e adicionar recovery hint
                is_error = result.startswith("❌") or result.startswith("🔒")
                if is_error:
                    tool_failures[tool_name] += 1
                    hint = _build_recovery_hint(tool_name, result)
                    if hint:
                        result += hint
                else:
                    # Reset circuit breaker se tool funcionou
                    tool_failures[tool_name] = 0

                yield f"data: {json.dumps({'tool_result': {'name': tool_name, 'result': result[:2000]}})}\n\n"

                full_messages.append({"role": "tool", "content": result})

            # Emitir progresso do round pra UI saber que ainda tá trabalhando
            if round_num > 0 and round_num % 5 == 0:
                yield f"data: {json.dumps({'progress': {'round': round_num + 1, 'max': MAX_TOOL_ROUNDS}})}\n\n"

            tool_calls = []
            accumulated = ""

        yield 'data: {"done": true}\n\n'
