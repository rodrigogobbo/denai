"""Rotas de auto-atualização — verifica PyPI e oferece upgrade."""

from __future__ import annotations

import asyncio
import sys

import httpx
from fastapi import APIRouter

from ..logging_config import get_logger
from ..version import VERSION

log = get_logger("routes.update")

router = APIRouter()


def _parse_version(v: str) -> tuple[int, ...]:
    """Parse version string to tuple for comparison.

    Handles semver-like strings (e.g. "0.6.1", "1.2.3.4").
    Non-numeric segments are ignored.
    """
    return tuple(int(x) for x in v.split(".")[:3] if x.isdigit())


@router.get("/api/update/check")
async def check_update():
    """Compara versão local vs PyPI."""
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

            return {
                "current_version": VERSION,
                "latest_version": latest,
                "update_available": latest_t > current_t,
            }
    except Exception as e:
        log.error("Erro ao verificar atualização no PyPI: %s", e)
        return {
            "update_available": False,
            "current_version": VERSION,
            "error": "Não foi possível verificar atualizações",
        }


@router.post("/api/update/install")
async def install_update():
    """Roda pip install --upgrade denai em background."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "denai",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    success = proc.returncode == 0
    return {
        "success": success,
        "output": stdout.decode() if success else stderr.decode(),
        "message": "✅ Atualizado! Reinicie o DenAI para aplicar." if success else "❌ Erro na atualização",
    }
