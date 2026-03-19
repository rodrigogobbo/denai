"""Tool de raciocínio — scratchpad para o LLM pensar antes de agir."""

from __future__ import annotations

# ─── Spec ──────────────────────────────────────────────────────────────────

THINK_SPEC = {
    "type": "function",
    "function": {
        "name": "think",
        "description": (
            "Use para raciocinar internamente antes de executar ações complexas. "
            "Não tem side-effects — é um scratchpad para organizar seus pensamentos. "
            "Ideal antes de editar múltiplos arquivos, planejar sequências de comandos, "
            "ou quando precisa analisar informações antes de responder."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "Seu raciocínio, análise ou plano interno",
                },
            },
            "required": ["thought"],
        },
    },
}


# ─── Executor ──────────────────────────────────────────────────────────────


async def think(args: dict) -> str:
    """Scratchpad — retorna o pensamento sem side effects."""
    thought = args.get("thought", "").strip()
    if not thought:
        return "❌ Parâmetro 'thought' é obrigatório."
    return f"💭 Raciocínio registrado.\n{thought}"


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (THINK_SPEC, "think"),
]
