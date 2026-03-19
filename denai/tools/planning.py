"""Tools de planejamento — criar e acompanhar planos multi-step."""

from __future__ import annotations

# ─── State ────────────────────────────────────────────────────────────────

_current_plan: dict | None = None  # {"goal": str, "steps": [{"text": str, "status": str, "result": str}]}

_STATUS_ICON = {"pending": "⬜", "in_progress": "🔄", "done": "✅"}


def _format_plan() -> str:
    """Formata o plano atual como string legível."""
    if not _current_plan:
        return "❌ Nenhum plano ativo."
    lines = [f"📋 Plano: {_current_plan['goal']}"]
    for i, step in enumerate(_current_plan["steps"], 1):
        icon = _STATUS_ICON.get(step["status"], "⬜")
        line = f"{icon} {i}. {step['text']}"
        if step["result"]:
            line += f" — {step['result']}"
        lines.append(line)
    done = sum(1 for s in _current_plan["steps"] if s["status"] == "done")
    total = len(_current_plan["steps"])
    lines.append(f"\nProgresso: {done}/{total}")
    return "\n".join(lines)


# ─── Specs ────────────────────────────────────────────────────────────────

PLAN_CREATE_SPEC = {
    "type": "function",
    "function": {
        "name": "plan_create",
        "description": (
            "Cria um plano de execução com passos numerados. "
            "Use para tarefas complexas que precisam de múltiplos passos."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Objetivo do plano",
                },
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de passos a executar",
                },
            },
            "required": ["goal", "steps"],
        },
    },
}

PLAN_UPDATE_SPEC = {
    "type": "function",
    "function": {
        "name": "plan_update",
        "description": ("Atualiza o status de um passo do plano. Use após executar cada passo para marcar progresso."),
        "parameters": {
            "type": "object",
            "properties": {
                "step": {
                    "type": "integer",
                    "description": "Número do passo (1-based)",
                },
                "status": {
                    "type": "string",
                    "description": "Novo status: pending, in_progress, done",
                },
                "result": {
                    "type": "string",
                    "description": "Resultado ou observação sobre o passo",
                },
            },
            "required": ["step", "status"],
        },
    },
}

# ─── Executors ────────────────────────────────────────────────────────────


async def plan_create(args: dict) -> str:
    """Cria um novo plano de execução."""
    global _current_plan
    goal = args.get("goal", "")
    steps = args.get("steps", [])
    if not goal:
        return "❌ Parâmetro 'goal' é obrigatório."
    if not steps:
        return "❌ Parâmetro 'steps' é obrigatório (lista não vazia)."
    _current_plan = {
        "goal": goal,
        "steps": [{"text": s, "status": "pending", "result": ""} for s in steps],
    }
    return _format_plan()


async def plan_update(args: dict) -> str:
    """Atualiza status de um passo do plano."""
    if not _current_plan:
        return "❌ Nenhum plano ativo. Crie um com plan_create."
    step_num = args.get("step", 0)
    status = args.get("status", "done")
    result = args.get("result", "")
    if step_num < 1 or step_num > len(_current_plan["steps"]):
        return f"❌ Passo inválido: {step_num}. Plano tem {len(_current_plan['steps'])} passos."
    step = _current_plan["steps"][step_num - 1]
    step["status"] = status
    if result:
        step["result"] = result
    return _format_plan()


# ─── Registration ─────────────────────────────────────────────────────────

TOOLS = [
    (PLAN_CREATE_SPEC, "plan_create"),
    (PLAN_UPDATE_SPEC, "plan_update"),
]
