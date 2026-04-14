"""Tool specs_analyze — analisa status de implementação de uma spec SDS."""

from __future__ import annotations

import os as _os
from pathlib import Path

from ..context_store import get_context

# ─── Spec ──────────────────────────────────────────────────────────────────

SPECS_ANALYZE_SPEC = {
    "type": "function",
    "function": {
        "name": "specs_analyze",
        "description": (
            "Lê e retorna o conteúdo completo de uma spec SDS (requirements.md, design.md, tasks.md) "
            "do projeto ativo. Use para analisar o status de implementação de uma feature planejada, "
            "verificar quais tasks estão concluídas ou pendentes, ou entender o design de uma mudança. "
            "Requer que um repositório esteja ativo via /context."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "Nome da spec (ex: 'v0.27.0-specs-analyze'). Use specs_list primeiro para ver as disponíveis.",
                },
                "conversation_id": {
                    "type": "string",
                    "description": "ID da conversa atual, para localizar o contexto de projeto ativo.",
                },
            },
            "required": ["slug", "conversation_id"],
        },
    },
}


# ─── Executor ──────────────────────────────────────────────────────────────


async def specs_analyze(args: dict) -> str:
    """Carrega e retorna o conteúdo de uma spec SDS para análise."""
    slug = args.get("slug", "").strip()
    conv_id = args.get("conversation_id", "").strip()

    if not slug:
        return "❌ Parâmetro 'slug' é obrigatório."

    ctx = get_context(conv_id) if conv_id else None
    if not ctx:
        return "❌ Nenhum repositório ativo. Use `/context <caminho>` primeiro."

    try:
        safe_path = _os.path.realpath(_os.path.abspath(ctx["path"]))
    except (ValueError, OSError):
        return "❌ Caminho do projeto inválido."

    specs_dir = Path(safe_path) / "specs" / "changes"
    if not specs_dir.exists():
        return (
            f"❌ O projeto **{ctx['project_name']}** não tem `specs/changes/`.\n"
            "Este comando funciona com projetos que usam Spec-Driven Development (SDS)."
        )

    safe_slug = _os.path.basename(_os.path.normpath(slug))
    spec_dir = specs_dir / safe_slug

    if not spec_dir.exists():
        available = sorted(d.name for d in specs_dir.iterdir() if d.is_dir() and not d.name.startswith("."))
        return (
            f"❌ Spec `{safe_slug}` não encontrada.\n"
            f"Specs disponíveis: {', '.join(available) if available else 'nenhuma'}"
        )

    parts = []
    for fname in ("requirements.md", "design.md", "tasks.md"):
        fpath = spec_dir / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8", errors="replace")
            parts.append(f"## 📄 {fname}\n\n{content}")

    if not parts:
        return f"❌ Spec `{safe_slug}` está vazia (nenhum arquivo encontrado)."

    project_info = f"**Projeto:** {ctx['project_name']} (`{safe_path}`)\n**Spec:** {safe_slug}\n\n"
    return project_info + "\n\n---\n\n".join(parts)


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (SPECS_ANALYZE_SPEC, "specs_analyze"),
]
