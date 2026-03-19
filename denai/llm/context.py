"""Context management — estimativa de tokens, auto-sizing e summarization."""

from __future__ import annotations

import httpx


def estimate_tokens(text: str) -> int:
    """Estimativa rápida de tokens (~4 chars por token em inglês, ~3 em PT)."""
    return max(1, len(text) // 3)


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Estima tokens totais de uma lista de mensagens."""
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("content", ""))
        # Tool calls adicionam ~100 tokens por call
        for tc in msg.get("tool_calls", []):
            total += 100
    return total


def pick_context_size(messages: list[dict], max_context: int = 65536) -> int:
    """Escolhe num_ctx baseado no tamanho real da conversa.

    Começa em 8k, escala automaticamente conforme necessário.
    Evita desperdiçar VRAM em conversas curtas.
    Nunca excede max_context.
    """
    tokens = estimate_messages_tokens(messages)

    if tokens < 4000:
        size = 8192
    elif tokens < 12000:
        size = 16384
    elif tokens < 24000:
        size = 32768
    else:
        size = 65536

    return min(size, max_context)


_SUMMARIZE_PROMPT = (
    "Resuma a conversa anterior em um parágrafo conciso, preservando: "
    "decisões tomadas, fatos importantes, e contexto necessário para continuar."
)


async def llm_summarize(
    messages: list[dict],
    model: str,
    ollama_url: str,
) -> str:
    """Chama Ollama para gerar um resumo das mensagens antigas.

    Usa uma chamada não-streaming ao /api/chat com temperatura baixa
    e contexto pequeno (4096) para ser rápido e determinístico.

    Timeout de 15s — se Ollama demorar, levanta exceção pro caller
    fazer fallback à summarization manual.
    """
    # Monta transcript das mensagens pra resumir
    transcript_parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if content:
            transcript_parts.append(f"[{role}] {content}")

    transcript = "\n".join(transcript_parts)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SUMMARIZE_PROMPT},
            {"role": "user", "content": transcript},
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_ctx": 4096,
        },
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        resp = await client.post(f"{ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

    return data.get("message", {}).get("content", "").strip()


def summarize_old_messages(
    messages: list[dict],
    keep_recent: int = 10,
    llm_summary: str | None = None,
) -> list[dict]:
    """Comprime mensagens antigas num resumo quando o contexto fica grande.

    Mantém as `keep_recent` mensagens mais recentes intactas.
    Se `llm_summary` for fornecido, usa ele no lugar do resumo manual.
    As anteriores são comprimidas num único resumo de sistema.
    """
    if len(messages) <= keep_recent + 2:  # system + poucas msgs = não precisa
        return messages

    # Separar system prompt (sempre o primeiro)
    system = messages[0] if messages[0].get("role") == "system" else None
    rest = messages[1:] if system else messages

    if len(rest) <= keep_recent:
        return messages

    recent = rest[-keep_recent:]

    if llm_summary:
        # Usar resumo gerado pelo LLM
        summary_text = "--- Resumo da conversa anterior (gerado por IA) ---\n" + llm_summary + "\n--- Fim do resumo ---"
    else:
        # Fallback: resumo manual por truncação
        old = rest[:-keep_recent]
        summary_parts = []
        for msg in old:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            if role == "tool":
                # Tool results: só a primeira linha
                first_line = content.split("\n")[0][:200]
                summary_parts.append(f"[tool] {first_line}")
            elif role == "assistant":
                # Assistant: primeiras 2 linhas
                lines = content.split("\n")[:2]
                summary_parts.append(f"[assistant] {' '.join(lines)[:300]}")
            elif role == "user":
                summary_parts.append(f"[user] {content[:200]}")

        summary_text = "--- Resumo do histórico anterior ---\n" + "\n".join(summary_parts) + "\n--- Fim do resumo ---"

    result = []
    if system:
        result.append(system)
    result.append({"role": "system", "content": summary_text})
    result.extend(recent)

    return result
