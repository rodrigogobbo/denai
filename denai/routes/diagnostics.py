"""Rota de diagnóstico — logs e info do sistema."""

from __future__ import annotations

from fastapi import APIRouter

from ..logging_config import LOG_FILE

router = APIRouter(prefix="/api", tags=["diagnostics"])


@router.get("/logs")
async def get_logs(lines: int = 100):
    """Retorna as últimas N linhas do arquivo de log.

    Query params:
        lines (int): Número de linhas a retornar (default 100, max 1000).
    """
    lines = min(lines, 1000)

    if not LOG_FILE.exists():
        return {"logs": "", "lines": 0, "path": str(LOG_FILE)}

    try:
        text = LOG_FILE.read_text(encoding="utf-8", errors="replace")
        all_lines = text.strip().splitlines()
        tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {
            "logs": "\n".join(tail),
            "lines": len(tail),
            "total_lines": len(all_lines),
            "path": str(LOG_FILE),
        }
    except Exception as e:
        return {"error": str(e), "path": str(LOG_FILE)}


@router.get("/diagnostics")
async def diagnostics():
    """Informações de diagnóstico do sistema."""
    import platform
    import sys

    from ..config import DATA_DIR, DEFAULT_MODEL, OLLAMA_URL, PORT

    # RAM info
    ram_gb = _get_ram_gb()

    # Tamanho do banco
    db_path = DATA_DIR / "denai.db"
    db_size_mb = round(db_path.stat().st_size / (1024 * 1024), 1) if db_path.exists() else 0

    # Log size
    log_size_mb = round(LOG_FILE.stat().st_size / (1024 * 1024), 2) if LOG_FILE.exists() else 0

    return {
        "system": {
            "os": platform.system(),
            "os_version": platform.version(),
            "arch": platform.machine(),
            "python": sys.version.split()[0],
            "ram_gb": ram_gb,
        },
        "denai": {
            "model": DEFAULT_MODEL,
            "ollama_url": OLLAMA_URL,
            "port": PORT,
            "data_dir": str(DATA_DIR),
            "db_size_mb": db_size_mb,
            "log_file": str(LOG_FILE),
            "log_size_mb": log_size_mb,
        },
    }


def _get_ram_gb() -> float | None:
    """Tenta obter RAM total em GB."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return round(int(line.split()[1]) / (1024 * 1024), 1)
    except Exception:
        pass
    try:
        import subprocess

        out = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
        return round(int(out.strip()) / (1024**3), 1)
    except Exception:
        pass
    return None
