"""Tool de sugestões proativas — suggest_skill e suggest_plugin.

Emite um evento SSE especial 'suggestion' que o frontend renderiza
como um card interativo (1-click install).

Diferente de executar algo, suggest_* apenas sinaliza ao frontend
que existe um recurso relevante — o usuário decide se instala.
"""

from __future__ import annotations

# ─── Specs ─────────────────────────────────────────────────────────────────

SUGGEST_SKILL_SPEC = {
    "type": "function",
    "function": {
        "name": "suggest_skill",
        "description": (
            "Sugere proativamente uma skill ao usuário quando o tópico da conversa "
            "é coberto por uma skill disponível. Exibe um card interativo no chat. "
            "Use quando o usuário mencionar tópicos relacionados a uma skill — "
            "não espere ele pedir explicitamente. "
            "Só sugira skills que realmente agreguem valor ao contexto atual."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "Nome ou slug da skill a sugerir",
                },
                "reason": {
                    "type": "string",
                    "description": "Explicação curta de por que esta skill é útil para o que o usuário pediu",
                },
            },
            "required": ["skill_name", "reason"],
        },
    },
}

SUGGEST_PLUGIN_SPEC = {
    "type": "function",
    "function": {
        "name": "suggest_plugin",
        "description": (
            "Sugere proativamente um plugin ao usuário quando a tarefa se beneficiaria "
            "de uma integração externa. Exibe um card interativo no chat. "
            "Use quando o usuário mencionar tópicos relacionados a um plugin disponível. "
            "Só sugira plugins que realmente agreguem valor ao contexto atual."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "plugin_id": {
                    "type": "string",
                    "description": "ID do plugin a sugerir",
                },
                "reason": {
                    "type": "string",
                    "description": "Explicação curta de por que este plugin é útil para o que o usuário pediu",
                },
            },
            "required": ["plugin_id", "reason"],
        },
    },
}

# ─── Executors ─────────────────────────────────────────────────────────────

# Prefixo mágico — o chat route detecta e converte em evento SSE 'suggestion'
_SUGGESTION_PREFIX = "__SUGGESTION__:"


async def suggest_skill(args: dict) -> str:
    """Emite uma sugestão de skill via evento SSE."""
    skill_name = args.get("skill_name", "").strip()
    reason = args.get("reason", "").strip()

    if not skill_name:
        return "❌ 'skill_name' é obrigatório."
    if not reason:
        return "❌ 'reason' é obrigatório."

    import json

    payload = json.dumps(
        {
            "type": "skill",
            "id": skill_name,
            "reason": reason,
        }
    )
    return f"{_SUGGESTION_PREFIX}{payload}"


async def suggest_plugin(args: dict) -> str:
    """Emite uma sugestão de plugin via evento SSE."""
    plugin_id = args.get("plugin_id", "").strip()
    reason = args.get("reason", "").strip()

    if not plugin_id:
        return "❌ 'plugin_id' é obrigatório."
    if not reason:
        return "❌ 'reason' é obrigatório."

    import json

    payload = json.dumps(
        {
            "type": "plugin",
            "id": plugin_id,
            "reason": reason,
        }
    )
    return f"{_SUGGESTION_PREFIX}{payload}"


# ─── Registration ───────────────────────────────────────────────────────────

TOOLS = [
    (SUGGEST_SKILL_SPEC, "suggest_skill"),
    (SUGGEST_PLUGIN_SPEC, "suggest_plugin"),
]
