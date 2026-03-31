"""Tool de sub-agente — delega um goal para um agente especializado com persona própria.

O sub-agente roda uma sessão LLM isolada com system prompt customizado (persona).
Resultado retorna como string para o agente pai continuar.

Proteções:
- Sem recursão: subagent não pode chamar outro subagent
- Max tool calls reduzido (padrão: 20)
- Timeout: 120s
- Sessão isolada do histórico do pai
"""

from __future__ import annotations

import asyncio
import json

from ..config import DEFAULT_MODEL
from ..logging_config import get_logger

log = get_logger("tools.subagent")

MAX_SUBAGENT_TOOL_CALLS = 20
SUBAGENT_TIMEOUT = 120  # segundos

# ─── Spec ──────────────────────────────────────────────────────────────────

SUBAGENT_SPEC = {
    "type": "function",
    "function": {
        "name": "subagent",
        "description": (
            "Delega um sub-goal para um agente especializado com persona própria. "
            "O sub-agente roda em sessão isolada com system prompt customizado e retorna o resultado. "
            "Use para tarefas que se beneficiam de expertise específica: "
            "'security' para análise de vulnerabilidades, "
            "'reviewer' para code review, "
            "'writer' para documentação, "
            "'data' para análise de dados. "
            "Pode usar persona customizada via system_prompt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "O que o sub-agente deve fazer (seja específico)",
                },
                "persona": {
                    "type": "string",
                    "description": (
                        "Persona pré-definida: 'security', 'reviewer', 'writer', 'data'. "
                        "Ignorado se system_prompt for fornecido."
                    ),
                },
                "system_prompt": {
                    "type": "string",
                    "description": "System prompt customizado (opcional, sobrescreve persona)",
                },
                "model": {
                    "type": "string",
                    "description": "Modelo LLM a usar (opcional, herda o padrão)",
                },
            },
            "required": ["goal"],
        },
    },
}

# ─── Executor ──────────────────────────────────────────────────────────────


async def subagent(args: dict) -> str:
    """Executa um sub-agente especializado e retorna o resultado."""
    goal = args.get("goal", "").strip()
    if not goal:
        return "❌ 'goal' é obrigatório."

    persona_name = args.get("persona", "").strip()
    system_prompt_override = args.get("system_prompt", "").strip()
    model = args.get("model", DEFAULT_MODEL)

    # Resolver system prompt
    system_prompt = _resolve_system_prompt(persona_name, system_prompt_override)

    log.info("Subagent iniciado — persona=%s, goal=%s", persona_name or "custom", goal[:50])

    try:
        result = await asyncio.wait_for(
            _run_subagent(goal=goal, system_prompt=system_prompt, model=model),
            timeout=SUBAGENT_TIMEOUT,
        )
        return result
    except asyncio.TimeoutError:
        return f"❌ Sub-agente excedeu o timeout de {SUBAGENT_TIMEOUT}s."
    except Exception as e:
        log.error("Subagent falhou: %s", e)
        return f"❌ Sub-agente falhou: {type(e).__name__}"


def _resolve_system_prompt(persona_name: str, system_prompt_override: str) -> str:
    """Resolve o system prompt: override > persona nomeada > padrão."""
    if system_prompt_override:
        return system_prompt_override

    if persona_name:
        try:
            from ..personas import get_persona

            persona = get_persona(persona_name)
            if persona:
                return persona.system_prompt
            log.warning("Persona '%s' não encontrada — usando prompt padrão", persona_name)
        except Exception as e:
            log.warning("Erro ao carregar persona '%s': %s", persona_name, e)

    # Fallback: prompt genérico de sub-agente
    return (
        "Você é um assistente especializado. "
        "Execute o objetivo dado com precisão, usando as ferramentas disponíveis. "
        "Seja direto e retorne um resultado claro e completo."
    )


async def _run_subagent(goal: str, system_prompt: str, model: str) -> str:
    """Roda o mini-loop LLM do sub-agente e coleta o resultado final."""
    from ..tools.registry import TOOLS_SPEC

    # Tools disponíveis para o sub-agente: tudo exceto subagent (sem recursão)
    subagent_tools = [t for t in TOOLS_SPEC if t.get("function", {}).get("name") != "subagent"]

    messages: list[dict] = [{"role": "user", "content": goal}]
    tool_calls_count = 0
    final_response = ""

    try:
        from ..llm.ollama import stream_chat

        chunks: list[str] = []
        async for chunk in stream_chat(
            messages,
            model=model,
            use_tools=True,
            tools_spec=subagent_tools,
            system_override=system_prompt,
        ):
            chunk = chunk.strip()
            if not chunk.startswith("data: "):
                continue
            raw = chunk[6:]
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            # Acumular conteúdo de texto
            if "content" in data:
                chunks.append(data["content"])

            # Contar tool calls (para não ultrapassar o limite)
            if "tool_result" in data:
                tool_calls_count += 1
                if tool_calls_count >= MAX_SUBAGENT_TOOL_CALLS:
                    log.warning("Subagent atingiu limite de %d tool calls", MAX_SUBAGENT_TOOL_CALLS)
                    break

        final_response = "".join(chunks).strip()

    except Exception as e:
        log.error("Erro no mini-loop do sub-agente: %s", e)
        return f"❌ Erro durante execução: {type(e).__name__}: {e}"

    if not final_response:
        return "⚠️ Sub-agente não produziu resposta."

    return final_response


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (SUBAGENT_SPEC, "subagent"),
]
