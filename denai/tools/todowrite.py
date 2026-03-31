"""Tool de todo list — substitui a lista inteira a cada chamada.

Diferente de plan_create/plan_update (que operam incrementalmente),
todowrite recebe a lista COMPLETA a cada chamada e substitui o estado.
Isso elimina dessincronias e dá ao LLM controle total sobre o estado.

Uso correto:
- Para iniciar: chamar com todos os todos em status 'pending'
- Para marcar progresso: chamar com a lista completa + status atualizado
- Para completar: chamar com o item em status 'completed'
- NUNCA fazer batch de updates — marcar completed logo após concluir cada item

Armazenamento: SQLite (mesma tabela, schema diferente do plans)
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from ..config import DATA_DIR

# ─── Database ──────────────────────────────────────────────────────────────

TODOS_DB = DATA_DIR / "todos.db"

VALID_STATUSES = ("pending", "in_progress", "completed")
VALID_PRIORITIES = ("low", "medium", "high")

_STATUS_ICON = {
    "pending": "⬜",
    "in_progress": "🔄",
    "completed": "✅",
}

_PRIORITY_ICON = {
    "low": "🔵",
    "medium": "🟡",
    "high": "🔴",
}


def _get_db() -> sqlite3.Connection:
    TODOS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(TODOS_DB))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            priority TEXT NOT NULL DEFAULT 'medium',
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _format_todos(todos: list[dict]) -> str:
    if not todos:
        return "📋 Lista de todos vazia."

    done = sum(1 for t in todos if t["status"] == "completed")
    total = len(todos)

    lines = [f"📋 Todos ({done}/{total} concluídos):\n"]
    for todo in todos:
        status_icon = _STATUS_ICON.get(todo["status"], "⬜")
        priority_icon = _PRIORITY_ICON.get(todo.get("priority", "medium"), "🟡")
        lines.append(f"{status_icon} {priority_icon} [{todo['id']}] {todo['content']}")

    return "\n".join(lines)


# ─── Spec ──────────────────────────────────────────────────────────────────

TODOWRITE_SPEC = {
    "type": "function",
    "function": {
        "name": "todowrite",
        "description": (
            "Gerencia a lista de todos — SUBSTITUI a lista inteira a cada chamada. "
            "Use para rastrear tarefas de trabalhos complexos (3+ passos) em tempo real. "
            "SEMPRE envie a lista completa: todos os itens, com os status atualizados. "
            "Nunca faça batch de updates — marque 'completed' logo após concluir cada item. "
            "Fluxo correto: criar todos em 'pending' → marcar 'in_progress' ao começar → "
            "marcar 'completed' logo após terminar (na mesma chamada de tool, não depois)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "description": "Lista COMPLETA de todos (substitui o estado atual).",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "ID único do todo (ex: '1', 'setup-db', 'fix-auth')",
                            },
                            "content": {
                                "type": "string",
                                "description": "Descrição da tarefa",
                            },
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "completed"],
                                "description": "Status atual da tarefa",
                            },
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "Prioridade (padrão: medium)",
                            },
                        },
                        "required": ["id", "content", "status"],
                    },
                }
            },
            "required": ["todos"],
        },
    },
}

# ─── Executor ──────────────────────────────────────────────────────────────


async def todowrite(args: dict) -> str:
    """Substitui a lista de todos inteira."""
    raw_todos = args.get("todos", [])

    if not isinstance(raw_todos, list):
        return "❌ 'todos' deve ser uma lista."

    # Validar e normalizar cada todo
    todos: list[dict] = []
    seen_ids: set[str] = set()

    for i, item in enumerate(raw_todos):
        if not isinstance(item, dict):
            return f"❌ Item {i} não é um objeto válido."

        todo_id = str(item.get("id", "")).strip()
        if not todo_id:
            return f"❌ Item {i} não tem 'id'."
        if todo_id in seen_ids:
            return f"❌ ID duplicado: '{todo_id}'."
        seen_ids.add(todo_id)

        content = str(item.get("content", "")).strip()
        if not content:
            return f"❌ Item '{todo_id}' não tem 'content'."

        status = item.get("status", "pending")
        if status not in VALID_STATUSES:
            return f"❌ Status inválido em '{todo_id}': '{status}'. Use: pending, in_progress, completed."

        priority = item.get("priority", "medium")
        if priority not in VALID_PRIORITIES:
            priority = "medium"

        todos.append(
            {
                "id": todo_id,
                "content": content,
                "status": status,
                "priority": priority,
            }
        )

    # Substituir lista inteira no banco
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    conn.execute("DELETE FROM todos")
    for todo in todos:
        conn.execute(
            "INSERT INTO todos (id, content, status, priority, updated_at) VALUES (?, ?, ?, ?, ?)",
            (todo["id"], todo["content"], todo["status"], todo["priority"], now),
        )
    conn.commit()
    conn.close()

    return _format_todos(todos)


async def todoread(args: dict) -> str:  # noqa: ARG001
    """Lê a lista de todos atual."""
    conn = _get_db()
    rows = conn.execute("SELECT * FROM todos ORDER BY rowid").fetchall()
    conn.close()

    todos = [dict(r) for r in rows]
    return _format_todos(todos)


# ─── Registration ──────────────────────────────────────────────────────────

TODOREAD_SPEC = {
    "type": "function",
    "function": {
        "name": "todoread",
        "description": (
            "Lê a lista de todos atual. Use para checar o estado das tarefas "
            "antes de continuar um trabalho em andamento."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
}

TOOLS = [
    (TODOWRITE_SPEC, "todowrite"),
    (TODOREAD_SPEC, "todoread"),
]
