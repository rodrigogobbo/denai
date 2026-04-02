"""Rotas de feedback in-app — reportar bugs e sugerir melhorias.

O feedback é enviado como GitHub Issue via API REST se um token estiver
configurado em ~/.denai/config.yaml (feedback.github_token).
Fallback: salvo localmente em ~/.denai/feedback/.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..config import DATA_DIR
from ..logging_config import LOG_FILE, get_logger
from ..version import VERSION

log = get_logger("routes.feedback")

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

FEEDBACK_DIR = DATA_DIR / "feedback"

# Repo padrão para issues
DEFAULT_REPO = "rodrigogobbo/denai"

# Labels por tipo
LABELS: dict[str, list[str]] = {
    "bug": ["bug", "user-feedback"],
    "improvement": ["enhancement", "user-feedback"],
}


# ── Config ───────────────────────────────────────────────────────────────


def _get_feedback_config() -> dict:
    """Lê configuração de feedback do config.yaml."""
    try:
        from ..config import _yaml_cfg

        return _yaml_cfg.get("feedback", {})
    except Exception:
        return {}


# ── Models ───────────────────────────────────────────────────────────────


class FeedbackBody(BaseModel):
    type: str = "bug"  # "bug" | "improvement"
    title: str
    description: str
    include_context: bool = True


# ── Context collection ───────────────────────────────────────────────────


def _collect_context() -> dict:
    """Coleta contexto do sistema para incluir na issue."""
    ctx: dict = {
        "denai_version": VERSION,
        "os": f"{platform.system()} {platform.machine()}",
        "python": sys.version.split()[0],
    }

    # Ollama status
    try:
        import asyncio

        async def _check_ollama():
            from ..config import OLLAMA_URL

            async with httpx.AsyncClient(timeout=3) as c:
                r = await c.get(f"{OLLAMA_URL}/api/version")
                if r.status_code == 200:
                    return f"online v{r.json().get('version', '?')}"
                return "offline"

        ctx["ollama"] = asyncio.get_event_loop().run_until_complete(_check_ollama())
    except Exception:
        ctx["ollama"] = "unknown"

    return ctx


def _get_recent_logs(lines: int = 20) -> str:
    """Lê as últimas N linhas do log."""
    try:
        if LOG_FILE.exists():
            text = LOG_FILE.read_text(encoding="utf-8", errors="replace")
            tail = text.strip().splitlines()[-lines:]
            return "\n".join(tail)
    except Exception:
        pass
    return "(logs não disponíveis)"


def _format_issue_body(
    description: str,
    feedback_type: str,
    context: dict | None,
    logs: str | None,
) -> str:
    """Formata o corpo da GitHub Issue em markdown."""
    parts = ["## Descrição\n", description, "\n"]

    if context:
        parts.append("\n## Contexto\n")
        parts.append(f"- **DenAI:** v{context.get('denai_version', '?')}")
        parts.append(f"- **OS:** {context.get('os', '?')}")
        parts.append(f"- **Python:** {context.get('python', '?')}")
        parts.append(f"- **Ollama:** {context.get('ollama', '?')}")
        parts.append("")

    if logs and feedback_type == "bug":
        parts.append("\n## Logs recentes\n")
        parts.append("```")
        parts.append(logs)
        parts.append("```\n")

    parts.append("\n---")
    parts.append("*Reportado via DenAI in-app feedback*")

    return "\n".join(parts)


# ── Submission ───────────────────────────────────────────────────────────


async def _submit_to_github(
    token: str,
    repo: str,
    title: str,
    body: str,
    labels: list[str],
) -> dict:
    """Abre uma GitHub Issue via API REST."""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"title": title, "body": body, "labels": labels}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload, headers=headers)

    if resp.status_code == 201:
        data = resp.json()
        return {
            "method": "github",
            "issue_number": data["number"],
            "issue_url": data["html_url"],
            "message": f"Issue #{data['number']} aberta com sucesso!",
        }

    log.error("GitHub API error %s: %s", resp.status_code, resp.text[:200])
    raise RuntimeError(f"GitHub API retornou {resp.status_code}")


def _save_locally(title: str, body: str, feedback_type: str) -> dict:
    """Salva feedback localmente como fallback."""
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = FEEDBACK_DIR / f"{ts}_{feedback_type}.json"
    data = {
        "type": feedback_type,
        "title": title,
        "body": body,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "method": "local",
        "file": str(path),
        "message": "Feedback salvo localmente (configure feedback.github_token para enviar ao GitHub).",
    }


# ── Routes ───────────────────────────────────────────────────────────────


@router.get("/config")
async def feedback_config():
    """Retorna configuração de feedback disponível."""
    cfg = _get_feedback_config()
    has_token = bool(cfg.get("github_token", "").strip())
    return {
        "enabled": True,
        "method": "github" if has_token else "local",
        "repo": cfg.get("repo", DEFAULT_REPO),
        "has_token": has_token,
    }


@router.post("")
async def submit_feedback(body: FeedbackBody):
    """Envia feedback como GitHub Issue ou salva localmente."""
    # Validação
    title = body.title.strip()
    description = body.description.strip()

    if len(title) < 3:
        return JSONResponse({"error": "Título muito curto (mínimo 3 caracteres)."}, status_code=400)
    if len(description) < 10:
        return JSONResponse({"error": "Descrição muito curta (mínimo 10 caracteres)."}, status_code=400)
    if body.type not in ("bug", "improvement"):
        return JSONResponse({"error": "Tipo inválido. Use 'bug' ou 'improvement'."}, status_code=400)

    # Coletar contexto
    context = _collect_context() if body.include_context else None
    logs = _get_recent_logs() if (body.include_context and body.type == "bug") else None

    # Formatar body da issue
    issue_body = _format_issue_body(description, body.type, context, logs)
    labels = LABELS.get(body.type, ["user-feedback"])

    # Tentar enviar via GitHub
    cfg = _get_feedback_config()
    token = cfg.get("github_token", "").strip()
    repo = cfg.get("repo", DEFAULT_REPO)

    if token:
        try:
            result = await _submit_to_github(token, repo, title, issue_body, labels)
            return result
        except Exception as e:
            log.warning("Falha ao enviar para GitHub (%s), salvando localmente.", e)

    # Fallback local
    return _save_locally(title, issue_body, body.type)


@router.get("/list")
async def list_local_feedback():
    """Lista feedbacks salvos localmente (fallback)."""
    if not FEEDBACK_DIR.exists():
        return {"feedbacks": []}
    items = []
    for f in sorted(FEEDBACK_DIR.glob("*.json"), reverse=True)[:20]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items.append(
                {
                    "file": f.name,
                    "type": data.get("type"),
                    "title": data.get("title"),
                    "created_at": data.get("created_at"),
                }
            )
        except Exception:
            pass
    return {"feedbacks": items}
