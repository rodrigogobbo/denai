"""Modos de operação — Build (padrão) vs Plan (read-only)."""

from __future__ import annotations

# Tools allowed in Plan mode (read-only)
PLAN_MODE_TOOLS = frozenset(
    {
        "file_read",
        "list_files",
        "grep",
        "think",
        "memory_search",
        "rag_search",
        "rag_stats",
        "web_search",
        "web_fetch",
        "question",
    }
)

# All possible modes
MODES = {"build", "plan"}

PLAN_PROMPT_PREFIX = (
    "⚠️ MODO PLANO ATIVO — Você está apenas analisando e planejando. "
    "NÃO modifique arquivos, NÃO execute comandos, NÃO crie documentos. "
    "Apenas leia, analise, sugira e planeje.\n\n"
)


def filter_tools_for_mode(tools_spec: list[dict], mode: str) -> list[dict]:
    """Filter tools based on the active mode.

    In 'build' mode, all tools are available.
    In 'plan' mode, only read-only tools are available.
    """
    if mode != "plan":
        return tools_spec

    return [tool for tool in tools_spec if tool.get("function", {}).get("name") in PLAN_MODE_TOOLS]


def get_system_prompt_prefix(mode: str) -> str:
    """Get a system prompt prefix for the given mode."""
    if mode == "plan":
        return PLAN_PROMPT_PREFIX
    return ""
