"""
Configuração centralizada do DenAI.
Todas as constantes, env vars, paths e CLI args.

Prioridade: CLI args > env vars > config.yaml > defaults
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ─── YAML Config ──────────────────────────────────────────────────────────


def _load_yaml_config(path: Path) -> dict:
    """Load config from YAML file. Returns empty dict on any error."""
    if not path.is_file():
        return {}
    try:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"⚠️  Warning: Failed to parse {path}: {exc}")
        return {}


# ─── CLI ───────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        prog="denai",
        description="🐺 DenAI — Your private AI den",
    )
    parser.add_argument(
        "--compartilhar",
        action="store_true",
        help="Ativa modo rede local — permite acesso de outros dispositivos",
    )
    parser.add_argument("--host", default=None, help="Endereço de bind")
    parser.add_argument("--port", type=int, default=None, help="Porta (padrão: 4078)")
    parser.add_argument("--model", default=None, help="Modelo padrão do Ollama")

    if "uvicorn" not in sys.modules.get("__main__", "").__class__.__name__:
        try:
            return parser.parse_args()
        except SystemExit:
            pass

    # Fallback pra env vars (quando importado pelo uvicorn)
    class _EnvArgs:
        compartilhar = os.getenv("DENAI_SHARE", "").lower() in ("1", "true", "yes")
        host = os.getenv("DENAI_HOST")
        port = int(os.getenv("DENAI_PORT", "0")) or None
        model = os.getenv("DENAI_MODEL")

    return _EnvArgs()


CLI = parse_args()

# ─── Paths ─────────────────────────────────────────────────────────────────

DATA_DIR = Path.home() / ".denai"
DB_PATH = DATA_DIR / "denai.db"
API_KEY_PATH = DATA_DIR / "api.key"
STATIC_DIR = Path(__file__).parent / "static"
CONFIG_YAML_PATH = DATA_DIR / "config.yaml"

DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Load YAML defaults ───────────────────────────────────────────────────

_yaml_cfg = _load_yaml_config(CONFIG_YAML_PATH)

# ─── Server ────────────────────────────────────────────────────────────────
# Priority: CLI args > env vars > config.yaml > hardcoded defaults

OLLAMA_URL = os.getenv("DENAI_OLLAMA_URL") or _yaml_cfg.get("ollama_url") or "http://localhost:11434"

DEFAULT_MODEL = CLI.model or os.getenv("DENAI_MODEL") or _yaml_cfg.get("model") or "llama3.1:8b"

PORT = CLI.port or int(os.getenv("DENAI_PORT", "0")) or None or _yaml_cfg.get("port") or 4078

SHARE_MODE = (
    CLI.compartilhar or os.getenv("DENAI_SHARE", "").lower() in ("1", "true", "yes") or _yaml_cfg.get("share", False)
)

# ─── LLM Tuning ───────────────────────────────────────────────────────────

MAX_TOOL_ROUNDS = int(os.getenv("DENAI_MAX_TOOL_ROUNDS") or _yaml_cfg.get("max_tool_rounds") or 25)

MAX_CONTEXT = int(os.getenv("DENAI_MAX_CONTEXT") or _yaml_cfg.get("max_context") or 65536)

# ─── Host ──────────────────────────────────────────────────────────────────

if CLI.host:
    HOST = CLI.host
elif SHARE_MODE:
    HOST = "0.0.0.0"
else:
    HOST = "127.0.0.1"
