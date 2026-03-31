"""Spec Documents — planos/especificações persistentes em markdown com lifecycle rico.

Diferente de plan_create/plan_update (execução step-by-step), os spec documents
são documentos vivos de planejamento e arquitetura — equivalente ao `plans` tool
do Wolf/HubAI Nitro.

Armazenamento:
- Conteúdo: ~/.denai/plans/<id>.md
- Metadados: SQLite (tabela plan_specs)
- Deletados: ~/.denai/plans/.trash/<id>.md
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ..config import DATA_DIR

# ─── Paths ─────────────────────────────────────────────────────────────────

PLANS_DIR = DATA_DIR / "plans"
PLANS_TRASH_DIR = PLANS_DIR / ".trash"
PLANS_DB = DATA_DIR / "plan_specs.db"

PLANS_DIR.mkdir(parents=True, exist_ok=True)
PLANS_TRASH_DIR.mkdir(parents=True, exist_ok=True)

# ─── Status ────────────────────────────────────────────────────────────────

VALID_STATUSES = ("draft", "active", "done", "archived")

# ─── Database ──────────────────────────────────────────────────────────────


def _get_db() -> sqlite3.Connection:
    PLANS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(PLANS_DB))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS plan_specs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


# ─── Helpers ───────────────────────────────────────────────────────────────


def _slugify(title: str) -> str:
    """Converte título em slug válido para nome de arquivo."""
    slug = title.lower()
    slug = re.sub(r"[àáâãäå]", "a", slug)
    slug = re.sub(r"[èéêë]", "e", slug)
    slug = re.sub(r"[ìíîï]", "i", slug)
    slug = re.sub(r"[òóôõö]", "o", slug)
    slug = re.sub(r"[ùúûü]", "u", slug)
    slug = re.sub(r"[ç]", "c", slug)
    slug = re.sub(r"[ñ]", "n", slug)
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:80] or "plan"


def _unique_id(title: str, conn: sqlite3.Connection) -> str:
    """Gera ID único baseado no slug, adicionando sufixo numérico se necessário."""
    base = _slugify(title)
    candidate = base
    counter = 2
    while conn.execute("SELECT 1 FROM plan_specs WHERE id = ?", (candidate,)).fetchone():
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def _plan_path(plan_id: str) -> Path:
    return PLANS_DIR / f"{plan_id}.md"


def _format_plan_summary(row: sqlite3.Row) -> str:
    tags_str = f" [{row['tags']}]" if row["tags"] else ""
    status_icon = {"draft": "📝", "active": "🔄", "done": "✅", "archived": "📦"}.get(row["status"], "📄")
    date = row["updated_at"][:10]
    return f"{status_icon} [{row['status']}] {row['id']}{tags_str} — {row['title']} (atualizado: {date})"


# ─── Spec ──────────────────────────────────────────────────────────────────

PLANS_SPEC_SPEC = {
    "type": "function",
    "function": {
        "name": "plans_spec",
        "description": (
            "Gerencia spec documents — planos, especificações e documentos de arquitetura "
            "persistidos em markdown com lifecycle (draft→active→done→archived). "
            "Use para planejar features, documentar decisões técnicas, e acompanhar progresso "
            "de trabalhos complexos que precisam sobreviver entre sessões. "
            "Diferente de plan_create (execução step-by-step), specs são documentos vivos "
            "de referência e planejamento."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "update", "get", "list", "delete"],
                    "description": (
                        "create: cria novo spec. "
                        "update: atualiza conteúdo/status/title/tags. "
                        "get: retorna conteúdo completo de um spec. "
                        "list: lista todos os specs (metadados). "
                        "delete: move para .trash/ (reversível)."
                    ),
                },
                "id": {
                    "type": "string",
                    "description": "ID do spec (slug). Obrigatório para update/get/delete.",
                },
                "title": {
                    "type": "string",
                    "description": "Título do spec. Obrigatório para create.",
                },
                "content": {
                    "type": "string",
                    "description": "Conteúdo em markdown. Obrigatório para create, opcional para update.",
                },
                "status": {
                    "type": "string",
                    "enum": ["draft", "active", "done", "archived"],
                    "description": "Status do lifecycle. Padrão: draft.",
                },
                "tags": {
                    "type": "string",
                    "description": "Tags separadas por vírgula para categorização.",
                },
            },
            "required": ["action"],
        },
    },
}

# ─── Executors ─────────────────────────────────────────────────────────────


async def plans_spec(args: dict) -> str:
    """Dispatcher para operações de spec documents."""
    action = args.get("action", "").strip()
    dispatch = {
        "create": _create,
        "update": _update,
        "get": _get,
        "list": _list,
        "delete": _delete,
    }
    handler = dispatch.get(action)
    if not handler:
        return f"❌ Ação inválida: '{action}'. Use: create, update, get, list, delete."
    return await handler(args)


async def _create(args: dict) -> str:
    title = args.get("title", "").strip()
    if not title:
        return "❌ 'title' é obrigatório para criar um spec."

    content = args.get("content", "").strip()
    if not content:
        return "❌ 'content' é obrigatório para criar um spec."

    status = args.get("status", "draft")
    if status not in VALID_STATUSES:
        status = "draft"

    tags = args.get("tags", "")
    now = datetime.now(timezone.utc).isoformat()

    conn = _get_db()
    plan_id = _unique_id(title, conn)

    conn.execute(
        "INSERT INTO plan_specs (id, title, status, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (plan_id, title, status, tags, now, now),
    )
    conn.commit()
    conn.close()

    _plan_path(plan_id).write_text(content, encoding="utf-8")

    return f"✅ Spec criado: {plan_id}\nStatus: {status}\nArquivo: {_plan_path(plan_id)}"


async def _update(args: dict) -> str:
    plan_id = args.get("id", "").strip()
    if not plan_id:
        return "❌ 'id' é obrigatório para atualizar."

    conn = _get_db()
    row = conn.execute("SELECT * FROM plan_specs WHERE id = ?", (plan_id,)).fetchone()
    if not row:
        conn.close()
        return f"❌ Spec não encontrado: '{plan_id}'. Use plans_spec action=list para ver os disponíveis."

    now = datetime.now(timezone.utc).isoformat()
    fields: list[str] = ["updated_at = ?"]
    values: list = [now]

    new_title = args.get("title", "").strip()
    if new_title:
        fields.append("title = ?")
        values.append(new_title)

    new_status = args.get("status", "").strip()
    if new_status:
        if new_status not in VALID_STATUSES:
            conn.close()
            return f"❌ Status inválido: '{new_status}'. Use: draft, active, done, archived."
        fields.append("status = ?")
        values.append(new_status)

    new_tags = args.get("tags")
    if new_tags is not None:
        fields.append("tags = ?")
        values.append(new_tags)

    values.append(plan_id)
    conn.execute(f"UPDATE plan_specs SET {', '.join(fields)} WHERE id = ?", values)  # noqa: S608
    conn.commit()
    conn.close()

    new_content = args.get("content", "").strip()
    if new_content:
        _plan_path(plan_id).write_text(new_content, encoding="utf-8")

    updated_row = _get_db().execute("SELECT * FROM plan_specs WHERE id = ?", (plan_id,)).fetchone()
    return f"✅ Spec atualizado.\n{_format_plan_summary(updated_row)}"


async def _get(args: dict) -> str:
    plan_id = args.get("id", "").strip()
    if not plan_id:
        return "❌ 'id' é obrigatório."

    conn = _get_db()
    row = conn.execute("SELECT * FROM plan_specs WHERE id = ?", (plan_id,)).fetchone()
    conn.close()

    if not row:
        return f"❌ Spec não encontrado: '{plan_id}'. Use plans_spec action=list para ver os disponíveis."

    path = _plan_path(plan_id)
    content = path.read_text(encoding="utf-8") if path.exists() else "(arquivo de conteúdo não encontrado)"

    tags_str = f"\nTags: {row['tags']}" if row["tags"] else ""
    return (
        f"📄 {row['title']}\n"
        f"ID: {row['id']}\n"
        f"Status: {row['status']}{tags_str}\n"
        f"Criado: {row['created_at'][:10]} | Atualizado: {row['updated_at'][:10]}\n"
        f"─────────────────────────\n"
        f"{content}"
    )


async def _list(args: dict) -> str:
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM plan_specs ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()

    if not rows:
        return "📭 Nenhum spec document criado ainda."

    status_filter = args.get("status", "").strip()
    if status_filter:
        rows = [r for r in rows if r["status"] == status_filter]
        if not rows:
            return f"📭 Nenhum spec com status '{status_filter}'."

    parts = [f"📋 {len(rows)} spec(s):\n"]
    for row in rows:
        parts.append(_format_plan_summary(row))

    return "\n".join(parts)


async def _delete(args: dict) -> str:
    plan_id = args.get("id", "").strip()
    if not plan_id:
        return "❌ 'id' é obrigatório."

    conn = _get_db()
    row = conn.execute("SELECT * FROM plan_specs WHERE id = ?", (plan_id,)).fetchone()
    if not row:
        conn.close()
        return f"❌ Spec não encontrado: '{plan_id}'."

    conn.execute("DELETE FROM plan_specs WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()

    src = _plan_path(plan_id)
    if src.exists():
        dst = PLANS_TRASH_DIR / src.name
        src.rename(dst)

    return f"🗑️ Spec '{plan_id}' movido para .trash/ (reversível)."


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (PLANS_SPEC_SPEC, "plans_spec"),
]
