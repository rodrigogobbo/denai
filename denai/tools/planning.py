"""Tools de planejamento — criar e acompanhar planos multi-step, persistidos em SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from ..config import DATA_DIR

# ─── Database ─────────────────────────────────────────────────────────────

PLANS_DB = DATA_DIR / "plans.db"

_STATUS_ICON = {"pending": "⬜", "in_progress": "🔄", "done": "✅"}


def _get_db() -> sqlite3.Connection:
    """Abre (e inicializa se necessário) o banco de planos."""
    PLANS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(PLANS_DB))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            steps TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    )
    conn.commit()
    return conn


def _get_current_plan() -> dict | None:
    """Retorna o plano mais recente (ativo)."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM plans ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "goal": row["goal"],
        "steps": json.loads(row["steps"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _save_plan(plan: dict) -> None:
    """Salva/atualiza um plano no banco."""
    conn = _get_db()
    now = datetime.now(timezone.utc).isoformat()
    if "id" in plan and plan["id"]:
        conn.execute(
            "UPDATE plans SET goal = ?, steps = ?, updated_at = ? WHERE id = ?",
            (plan["goal"], json.dumps(plan["steps"]), now, plan["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO plans (goal, steps, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (plan["goal"], json.dumps(plan["steps"]), now, now),
        )
    conn.commit()
    conn.close()


def _format_plan(plan: dict) -> str:
    """Formata um plano como string legível."""
    lines = [f"📋 Plano: {plan['goal']}"]
    for i, step in enumerate(plan["steps"], 1):
        icon = _STATUS_ICON.get(step["status"], "⬜")
        line = f"{icon} {i}. {step['text']}"
        if step.get("result"):
            line += f" — {step['result']}"
        lines.append(line)
    done = sum(1 for s in plan["steps"] if s["status"] == "done")
    total = len(plan["steps"])
    lines.append(f"\nProgresso: {done}/{total}")
    return "\n".join(lines)


# ─── Specs ────────────────────────────────────────────────────────────────

PLAN_CREATE_SPEC = {
    "type": "function",
    "function": {
        "name": "plan_create",
        "description": (
            "Cria um plano de execução com passos numerados. "
            "Use para tarefas complexas que precisam de múltiplos passos. "
            "Planos são salvos permanentemente e sobrevivem a reinicializações."
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
    """Cria um novo plano de execução, persistido em SQLite."""
    goal = args.get("goal", "")
    steps = args.get("steps", [])
    if not goal:
        return "❌ Parâmetro 'goal' é obrigatório."
    if not steps:
        return "❌ Parâmetro 'steps' é obrigatório (lista não vazia)."
    plan = {
        "goal": goal,
        "steps": [{"text": s, "status": "pending", "result": ""} for s in steps],
    }
    _save_plan(plan)
    # Re-read to get the ID
    saved = _get_current_plan()
    if saved:
        return _format_plan(saved)
    return _format_plan(plan)


async def plan_update(args: dict) -> str:
    """Atualiza status de um passo do plano."""
    plan = _get_current_plan()
    if not plan:
        return "❌ Nenhum plano ativo. Crie um com plan_create."
    step_num = args.get("step", 0)
    status = args.get("status", "done")
    result = args.get("result", "")
    if step_num < 1 or step_num > len(plan["steps"]):
        return f"❌ Passo inválido: {step_num}. Plano tem {len(plan['steps'])} passos."
    step = plan["steps"][step_num - 1]
    step["status"] = status
    if result:
        step["result"] = result
    _save_plan(plan)
    return _format_plan(plan)


# ─── Registration ─────────────────────────────────────────────────────────

TOOLS = [
    (PLAN_CREATE_SPEC, "plan_create"),
    (PLAN_UPDATE_SPEC, "plan_update"),
]
