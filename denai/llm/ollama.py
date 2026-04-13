"""Integração com Ollama — streaming chat com tool calling."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import AsyncGenerator

import httpx

from ..config import DEFAULT_MODEL, MAX_CONTEXT, MAX_TOOL_ROUNDS, OLLAMA_URL
from ..logging_config import get_logger
from ..rag import get_rag_context
from ..tools import TOOLS_SPEC, execute_tool
from .context import estimate_messages_tokens, llm_summarize, pick_context_size, summarize_old_messages
from .prompt import build_system_prompt

_SUGGESTION_PREFIX = "__SUGGESTION__:"


def _maybe_suggestion_event(result: str) -> str | None:
    """Se result é uma sugestão, retorna o evento SSE; caso contrário None."""
    if result.startswith(_SUGGESTION_PREFIX):
        payload = result[len(_SUGGESTION_PREFIX) :]
        try:
            data = json.loads(payload)
            return json.dumps({"suggestion": data})
        except json.JSONDecodeError:
            pass
    return None


log = get_logger("llm")

# ─── Config ────────────────────────────────────────────────────────────────

CONTEXT_SUMMARIZE_THRESHOLD = 20000  # Tokens — comprimir acima disso
MAX_RETRIES = 2  # Retries para erros transientes do Ollama
CIRCUIT_BREAKER_LIMIT = 3  # Falhas consecutivas na mesma tool → para

# Tools que são read-only e podem rodar em paralelo
PARALLEL_SAFE_TOOLS = frozenset(
    {
        "file_read",
        "list_files",
        "grep",
        "think",
        "memory_search",
        "rag_search",
        "rag_stats",
        "web_search",
    }
)


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
        return "\n💡 Dica: O arquivo não existe. Use list_files para verificar quais arquivos existem no diretório."
    if tool_name == "command_exec" and ("permissão" in error_msg.lower() or "permission" in error_msg.lower()):
        return "\n💡 Dica: Sem permissão para executar este comando. Tente uma abordagem alternativa."
    if "🔒" in error_msg:
        return "\n💡 Dica: Este caminho está bloqueado por segurança. Não tente acessá-lo novamente."
    return ""


def _batch_tool_calls(tool_calls: list[dict], tool_failures: Counter) -> list[list[dict]]:
    """Agrupa tool calls consecutivas em batches para execução paralela.

    Tools parallel-safe consecutivas são agrupadas. Qualquer tool não-parallel-safe
    ou com circuit breaker ativo quebra o batch e fica sozinha.
    """
    batches: list[list[dict]] = []
    current_batch: list[dict] = []
    current_is_parallel = False

    for tc in tool_calls:
        fn = tc.get("function", {})
        name = fn.get("name", "unknown")
        is_parallel = name in PARALLEL_SAFE_TOOLS and tool_failures[name] < CIRCUIT_BREAKER_LIMIT

        if not current_batch:
            current_batch = [tc]
            current_is_parallel = is_parallel
        elif is_parallel and current_is_parallel:
            current_batch.append(tc)
        else:
            batches.append(current_batch)
            current_batch = [tc]
            current_is_parallel = is_parallel

    if current_batch:
        batches.append(current_batch)

    return batches


async def stream_chat(
    messages: list,
    model: str = DEFAULT_MODEL,
    use_tools: bool = True,
    *,
    tools_spec: list[dict] | None = None,
    prompt_prefix: str = "",
    system_override: str | None = None,
    conversation_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream de chat com Ollama, com suporte a tool calling iterativo.

    Features:
    - max_tool_rounds configurável (padrão 25) — suporta sessões longas
    - Context auto-sizing — 8k→16k→32k→64k conforme a conversa cresce
    - Summarization automática — comprime histórico antigo quando excede threshold
    - Retry com backoff para erros transientes do Ollama
    - Circuit breaker — para tool que falha 3x consecutivas
    - Recovery hints — dicas de recuperação injetadas no contexto
    - tools_spec: override da lista de tools (None = usa TOOLS_SPEC global)
    - prompt_prefix: texto prefixado ao system prompt (ex: modo plano)
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

    # Buscar skills ativas/triggered
    skills_context = ""
    try:
        from ..skills import get_skills_context

        skills_context = get_skills_context(message=user_query or "")
    except Exception:
        pass  # Skills são best-effort

    if system_override is not None:
        system_content = system_override
    else:
        system_content = build_system_prompt(rag_context, skills_context=skills_context)
    if prompt_prefix:
        system_content = prompt_prefix + system_content

    # Injetar contexto de repositório se ativo para esta conversa
    if conversation_id:
        try:
            from ..context_store import get_context as get_repo_context

            ctx = get_repo_context(conversation_id)
            if ctx:
                system_content += (
                    f"\n\n---\n\n{ctx['summary']}\n\n> Use rag_search para buscar código e arquivos neste repositório."
                )
        except Exception:
            pass

    system_msg = {"role": "system", "content": system_content}
    full_messages = [system_msg] + messages

    # Resolve effective tools list (override or global)
    effective_tools = tools_spec if tools_spec is not None else TOOLS_SPEC

    # Circuit breaker: conta falhas consecutivas por tool
    tool_failures: Counter = Counter()

    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
        for round_num in range(MAX_TOOL_ROUNDS):
            # Auto-summarize se contexto ficou grande demais
            if estimate_messages_tokens(full_messages) > CONTEXT_SUMMARIZE_THRESHOLD:
                yield f"data: {json.dumps({'progress': {'status': 'summarizing'}})}\n\n"
                llm_summary = None
                try:
                    # Separar mensagens antigas pra resumir via LLM
                    _sys = full_messages[0] if full_messages[0].get("role") == "system" else None
                    _rest = full_messages[1:] if _sys else full_messages
                    if len(_rest) > 12:
                        _old = _rest[:-12]
                        llm_summary = await llm_summarize(_old, model=model, ollama_url=OLLAMA_URL)
                except Exception:
                    pass  # Fallback silencioso pra summarization manual
                full_messages = summarize_old_messages(full_messages, keep_recent=12, llm_summary=llm_summary)

            # Context size dinâmico baseado no tamanho real
            num_ctx = pick_context_size(full_messages, max_context=MAX_CONTEXT)

            payload = {
                "model": model,
                "messages": full_messages,
                "stream": True,
                "options": {"temperature": 0.7, "num_ctx": num_ctx},
            }
            if use_tools and effective_tools:
                payload["tools"] = effective_tools

            accumulated = ""
            tool_calls = []

            # Retry para erros transientes do Ollama
            last_error = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as resp:
                        if resp.status_code != 200:
                            error_text = await resp.aread()
                            err_msg = error_text.decode()

                            # Erro de memória insuficiente — mensagem amigável
                            if "model requires more system memory" in err_msg:
                                log.error("OOM: modelo requer mais RAM — %s", err_msg)
                                friendly = (
                                    "⚠️ **Memória insuficiente para este modelo.**\n\n"
                                    f"Erro do Ollama: {err_msg}\n\n"
                                    "**Soluções:**\n"
                                    "1. Use um modelo menor: "
                                    "`ollama pull llama3.2:3b` (precisa ~2 GB)\n"
                                    "2. Feche outros programas para liberar RAM\n"
                                    "3. Troque o modelo no menu dropdown da interface\n\n"
                                    "💡 Dica: com 8 GB de RAM, use modelos de até 3-4B. "
                                    "Com 16 GB, modelos de 7-8B funcionam bem."
                                )
                                yield f"data: {json.dumps({'error': friendly})}\n\n"
                                return

                            err_msg = f"Ollama error {resp.status_code}: {err_msg}"
                            log.error("Ollama HTTP %d: %s", resp.status_code, err_msg)

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
                    log.warning("Ollama connection error (tentativa %d/%d): %s", attempt + 1, MAX_RETRIES + 1, e)
                    if attempt < MAX_RETRIES:
                        last_error = str(e)
                        import asyncio

                        await asyncio.sleep(attempt + 1)
                        continue
                    err = f"Ollama não respondeu após {MAX_RETRIES + 1} tentativas: {e}"
                    log.error(err)
                    yield f"data: {json.dumps({'error': err})}\n\n"
                    return

            if last_error:
                yield f"data: {json.dumps({'error': last_error})}\n\n"
                return

            if not tool_calls:
                break

            # Executar tool calls (com paralelismo para tools read-only)
            full_messages.append(
                {
                    "role": "assistant",
                    "content": accumulated,
                    "tool_calls": tool_calls,
                }
            )

            # Separar em batches: tools parallelizable vs sequenciais
            # Mantém a ordem original — agrupa consecutivas que são parallel-safe
            batches = _batch_tool_calls(tool_calls, tool_failures)

            for batch in batches:
                if len(batch) == 1 or not all(
                    tc.get("function", {}).get("name", "") in PARALLEL_SAFE_TOOLS for tc in batch
                ):
                    # Execução sequencial
                    for tc in batch:
                        fn = tc.get("function", {})
                        tool_name = fn.get("name", "unknown")
                        tool_args = fn.get("arguments", {})

                        # Injetar conv_id nas tool_args para tools que precisam de contexto de sessão
                        if conversation_id:
                            tool_args["_conv_id"] = conversation_id

                        if tool_failures[tool_name] >= CIRCUIT_BREAKER_LIMIT:
                            skip_msg = (
                                f"⚠️ Tool '{tool_name}' falhou {CIRCUIT_BREAKER_LIMIT} vezes consecutivas. "
                                "Parando tentativas automáticas. Peça ajuda ao usuário ou tente outra abordagem."
                            )
                            yield f"data: {json.dumps({'tool_result': {'name': tool_name, 'result': skip_msg}})}\n\n"
                            full_messages.append({"role": "tool", "content": skip_msg})
                            continue

                        yield f"data: {json.dumps({'tool_call': {'name': tool_name, 'args': tool_args}})}\n\n"

                        if tool_name == "question":
                            q_text = tool_args.get("question", "")
                            q_options = tool_args.get("options", [])
                            from ..tools.question import _next_id

                            q_id = _next_id()
                            q_event = {"question": {"id": q_id, "text": q_text, "options": q_options}}
                            yield f"data: {json.dumps(q_event)}\n\n"
                            tool_args["_question_id"] = q_id

                        result = await execute_tool(tool_name, tool_args)

                        is_error = result.startswith("❌") or result.startswith("🔒")
                        if is_error:
                            tool_failures[tool_name] += 1
                            hint = _build_recovery_hint(tool_name, result)
                            if hint:
                                result += hint
                        else:
                            tool_failures[tool_name] = 0

                        suggestion_event = _maybe_suggestion_event(result)
                        if suggestion_event:
                            yield f"data: {suggestion_event}\n\n"
                        else:
                            yield f"data: {json.dumps({'tool_result': {'name': tool_name, 'result': result[:2000]}})}\n\n"
                        full_messages.append({"role": "tool", "content": result})

                else:
                    # Execução paralela — emitir todos tool_call events primeiro
                    tc_infos = []
                    for tc in batch:
                        fn = tc.get("function", {})
                        tool_name = fn.get("name", "unknown")
                        tool_args = fn.get("arguments", {})
                        # Injetar conv_id nas tool_args para tools que precisam de contexto de sessão
                        if conversation_id:
                            tool_args["_conv_id"] = conversation_id
                        yield f"data: {json.dumps({'tool_call': {'name': tool_name, 'args': tool_args}})}\n\n"
                        tc_infos.append((tool_name, tool_args))

                    # Executar em paralelo
                    import asyncio

                    tasks = [execute_tool(name, args) for name, args in tc_infos]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Emitir resultados na mesma ordem
                    for (tool_name, _), result in zip(tc_infos, results, strict=False):
                        if isinstance(result, Exception):
                            result = f"❌ Erro interno: {result}"

                        is_error = result.startswith("❌") or result.startswith("🔒")
                        if is_error:
                            tool_failures[tool_name] += 1
                            hint = _build_recovery_hint(tool_name, result)
                            if hint:
                                result += hint
                        else:
                            tool_failures[tool_name] = 0

                        suggestion_event = _maybe_suggestion_event(result)
                        if suggestion_event:
                            yield f"data: {suggestion_event}\n\n"
                        else:
                            yield f"data: {json.dumps({'tool_result': {'name': tool_name, 'result': result[:2000]}})}\n\n"
                        full_messages.append({"role": "tool", "content": result})

            # Emitir progresso do round pra UI saber que ainda tá trabalhando
            if round_num > 0 and round_num % 5 == 0:
                yield f"data: {json.dumps({'progress': {'round': round_num + 1, 'max': MAX_TOOL_ROUNDS}})}\n\n"

            tool_calls = []
            accumulated = ""

        yield 'data: {"done": true}\n\n'
