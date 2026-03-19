"""Logging centralizado — arquivo + console."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import DATA_DIR

# ─── Log directory ──────────────────────────────────────────────────────────

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "denai.log"

# ─── Formato ────────────────────────────────────────────────────────────────

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configura logging para arquivo (rotativo) + console.

    Logs ficam em ~/.denai/logs/denai.log (max 5 MB, 3 backups).
    """
    root = logging.getLogger("denai")

    # Evita configurar múltiplas vezes
    if root.handlers:
        return root

    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # ── Arquivo (rotativo: 5 MB, 3 backups) ──
    file_handler = RotatingFileHandler(
        str(LOG_FILE),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)  # Arquivo captura tudo
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    # ── Console (só WARNING+) ──
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    return root


def get_logger(name: str) -> logging.Logger:
    """Retorna um sub-logger. Uso: logger = get_logger(__name__)"""
    return logging.getLogger(f"denai.{name}")
