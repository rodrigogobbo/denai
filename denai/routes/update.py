"""Rotas de auto-atualização — verifica PyPI, instala com streaming e reinicia."""

from __future__ import annotations

import asyncio
import json
import sys

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..logging_config import get_logger
from ..version import VERSION

log = get_logger("routes.update")

router = APIRouter()

# Flag global para evitar restart duplo
_restart_scheduled = False


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse version string to tuple for comparison."""
    return tuple(int(x) for x in v.split(".")[:3] if x.isdigit())


# ── Check ────────────────────────────────────────────────────────


@router.get("/api/update/check")
async def check_update():
    """Compara versão local vs PyPI e busca notas de release do GitHub."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("https://pypi.org/pypi/denai/json")
            if resp.status_code != 200:
                return {
                    "update_available": False,
                    "current_version": VERSION,
                    "error": "Não foi possível verificar PyPI",
                }
            data = resp.json()
            latest = data["info"]["version"]
            current_t = _parse_version(VERSION)
            latest_t = _parse_version(latest)
            update_available = latest_t > current_t

            result: dict = {
                "current_version": VERSION,
                "latest_version": latest,
                "update_available": update_available,
            }

            # Buscar notas de release do GitHub quando há atualização
            if update_available:
                notes = await _fetch_release_notes(client, latest)
                if notes:
                    result["release_notes"] = notes

            return result
    except Exception as e:
        log.error("Erro ao verificar atualização no PyPI: %s", e)
        return {
            "update_available": False,
            "current_version": VERSION,
            "error": "Não foi possível verificar atualizações",
        }


async def _fetch_release_notes(client: httpx.AsyncClient, version: str) -> str | None:
    """Busca as notas da release no GitHub Releases."""
    try:
        tag = f"v{version}"
        url = f"https://api.github.com/repos/rodrigogobbo/denai/releases/tags/{tag}"
        resp = await client.get(url, headers={"Accept": "application/vnd.github+json"})
        if resp.status_code == 200:
            body = resp.json().get("body", "").strip()
            if body:
                return body
    except Exception:
        pass

    # Fallback: extrair do CHANGELOG.md bundled
    return _extract_changelog(version)


def _extract_changelog(version: str) -> str | None:
    """Extrai notas de uma versão do CHANGELOG.md local."""
    import re
    from pathlib import Path

    changelog_path = Path(__file__).parent.parent.parent / "CHANGELOG.md"
    if not changelog_path.exists():
        return None
    try:
        content = changelog_path.read_text(encoding="utf-8")
        pattern = rf"## \[{re.escape(version)}\].*?(?=\n## \[|\Z)"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(0).strip()
    except Exception:
        pass
    return None


# ── Install (SSE streaming) ──────────────────────────────────────


@router.post("/api/update/install")
async def install_update():
    """Instala atualização via pip, enviando progresso por SSE em tempo real.

    Eventos SSE:
    - {"type": "progress", "line": "..."}  — linha do pip
    - {"type": "success", "version": "x.y.z", "message": "..."}
    - {"type": "error", "message": "..."}
    """

    async def generate():
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "denai",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # stderr junto com stdout
            )

            # Ler linha a linha em tempo real
            while True:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").rstrip()
                if line:
                    yield f"data: {json.dumps({'type': 'progress', 'line': line})}\n\n"

            await proc.wait()

            if proc.returncode == 0:
                # Descobrir a versão instalada
                new_version = await _get_installed_version()
                event = json.dumps(
                    {
                        "type": "success",
                        "version": new_version,
                        "message": f"DenAI {new_version} instalado com sucesso!",
                    }
                )
                yield f"data: {event}\n\n"
            else:
                event = json.dumps({"type": "error", "message": "Erro durante a instalação. Verifique os logs."})
                yield f"data: {event}\n\n"

        except Exception as e:
            log.error("Erro durante instalação: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Erro interno durante a instalação.'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _get_installed_version() -> str:
    """Lê a versão do denai instalado via pip show."""
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pip",
            "show",
            "denai",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        for line in stdout.decode().splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return VERSION


# ── Restart ──────────────────────────────────────────────────────


@router.post("/api/update/restart")
async def restart_server():
    """Reinicia o servidor DenAI.

    Inicia uma nova instância com os mesmos argumentos e encerra a atual.
    Se não conseguir iniciar a nova instância, retorna erro com instruções
    para reiniciar manualmente.
    """
    global _restart_scheduled  # noqa: PLW0603
    if _restart_scheduled:
        return {"ok": False, "error": "Reinicialização já agendada."}

    _restart_scheduled = True

    # Agendar restart em background (após resposta ser enviada)
    asyncio.create_task(_do_restart())

    return {
        "ok": True,
        "message": "Reinicialização iniciada. Aguarde alguns segundos...",
        "reconnect_delay_ms": 3000,
    }


async def _do_restart() -> None:
    """Inicia nova instância e encerra a atual."""
    import subprocess

    await asyncio.sleep(0.5)  # Garante que a resposta HTTP foi enviada

    cmd = [sys.executable, "-m", "denai"] + sys.argv[1:]

    try:
        subprocess.Popen(cmd)  # noqa: S603 — cmd é [sys.executable, "-m", "denai", ...]
        log.info("Nova instância do DenAI iniciada: %s", " ".join(cmd))
    except Exception as e:
        log.error("Falha ao iniciar nova instância: %s", e)

    await asyncio.sleep(1)
    log.info("Encerrando processo atual para reinicialização...")
    sys.exit(0)
