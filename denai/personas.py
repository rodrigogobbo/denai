"""Personas — system prompts especializados para sub-agentes.

Personas podem ser:
1. Bundled — definidas no pacote (denai/personas_bundled/)
2. Customizadas — em ~/.denai/personas/*.md

Formato dos arquivos .md:
---
name: security
description: AppSec specialist with offensive mindset
---
Você é um especialista em segurança...
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import DATA_DIR
from .logging_config import get_logger

log = get_logger("personas")

PERSONAS_DIR = DATA_DIR / "personas"
PERSONAS_DIR.mkdir(parents=True, exist_ok=True)

# Personas bundled ficam junto ao pacote
_BUNDLED_DIR = Path(__file__).parent / "personas_bundled"


@dataclass
class Persona:
    """Uma persona — identidade e system prompt de um sub-agente."""

    name: str
    description: str
    system_prompt: str
    source: str = "bundled"  # "bundled" | "custom"


def _parse_persona_file(path: Path, source: str = "bundled") -> Persona | None:
    """Parseia um arquivo .md com frontmatter YAML."""
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    name = path.stem
    description = ""
    system_prompt = raw

    if raw.startswith("---"):
        parts = re.split(r"^---\s*$", raw, maxsplit=2, flags=re.MULTILINE)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
                name = str(meta.get("name", name))
                description = str(meta.get("description", ""))
                system_prompt = parts[2].strip()
            except yaml.YAMLError as e:
                log.warning("Erro no frontmatter de %s: %s", path.name, e)

    if not system_prompt:
        return None

    return Persona(name=name, description=description, system_prompt=system_prompt, source=source)


def discover_personas() -> list[Persona]:
    """Descobre todas as personas disponíveis (bundled + custom).

    Personas custom sobrescrevem bundled com mesmo nome.
    """
    personas: dict[str, Persona] = {}

    # 1. Bundled
    if _BUNDLED_DIR.exists():
        for f in sorted(_BUNDLED_DIR.glob("*.md")):
            try:
                p = _parse_persona_file(f, source="bundled")
                if p:
                    personas[p.name] = p
            except Exception as e:
                log.warning("Erro ao carregar persona bundled %s: %s", f.name, e)

    # 2. Custom (sobrescreve bundled)
    for f in sorted(PERSONAS_DIR.glob("*.md")):
        try:
            p = _parse_persona_file(f, source="custom")
            if p:
                personas[p.name] = p
        except Exception as e:
            log.warning("Erro ao carregar persona custom %s: %s", f.name, e)

    return list(personas.values())


def get_persona(name: str) -> Persona | None:
    """Retorna uma persona pelo nome (case-insensitive)."""
    name_lower = name.lower().strip()
    for p in discover_personas():
        if p.name.lower() == name_lower:
            return p
    return None
