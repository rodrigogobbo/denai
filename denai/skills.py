"""Skills — specialized instructions loaded from .md files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import DATA_DIR
from .logging_config import get_logger

log = get_logger("skills")

SKILLS_DIR = DATA_DIR / "skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

# Track which skills are currently active
_active_skills: set[str] = set()


@dataclass
class Skill:
    """A skill definition."""

    name: str
    description: str = ""
    triggers: list[str] = field(default_factory=list)
    content: str = ""
    file_path: str = ""
    auto_activate: bool = False


def discover_skills() -> list[Skill]:
    """Discover skills from ~/.denai/skills/*.md."""
    skills: list[Skill] = []

    if not SKILLS_DIR.exists():
        return skills

    for f in sorted(SKILLS_DIR.glob("*.md")):
        try:
            skill = _parse_skill_file(f)
            if skill:
                skills.append(skill)
        except Exception as e:
            log.warning("Erro ao carregar skill %s: %s", f.name, e)

    return skills


def _parse_skill_file(path: Path) -> Skill | None:
    """Parse a skill .md file with YAML frontmatter."""
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None

    name = path.stem
    description = ""
    triggers: list[str] = []
    content = raw
    auto_activate = False

    # Parse YAML frontmatter (---\n...\n---)
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", raw, re.DOTALL)
    if frontmatter_match:
        try:
            meta = yaml.safe_load(frontmatter_match.group(1)) or {}
            name = meta.get("name", name)
            description = meta.get("description", "")
            auto_activate = bool(meta.get("auto_activate", False))

            # Triggers can be string or list
            t = meta.get("triggers", [])
            if isinstance(t, str):
                triggers = [x.strip() for x in t.split(",") if x.strip()]
            elif isinstance(t, list):
                triggers = [str(x).strip() for x in t if x]
            else:
                triggers = []

            content = frontmatter_match.group(2).strip()
        except yaml.YAMLError:
            content = raw

    if not content:
        return None

    return Skill(
        name=name,
        description=description,
        triggers=triggers,
        content=content,
        file_path=str(path),
        auto_activate=auto_activate,
    )


def match_skills(text: str) -> list[Skill]:
    """Find skills whose triggers match the given text."""
    if not text:
        return []

    text_lower = text.lower()
    matched: list[Skill] = []

    for skill in discover_skills():
        if skill.auto_activate:
            matched.append(skill)
            continue
        for trigger in skill.triggers:
            if trigger.lower() in text_lower:
                matched.append(skill)
                break

    return matched


def get_skill(name: str) -> Skill | None:
    """Get a skill by name."""
    skills = discover_skills()
    return next((s for s in skills if s.name == name), None)


def activate_skill(name: str) -> bool:
    """Manually activate a skill for the session."""
    skill = get_skill(name)
    if skill:
        _active_skills.add(name)
        log.info("Skill ativada: %s", name)
        return True
    return False


def deactivate_skill(name: str) -> bool:
    """Deactivate a skill."""
    if name in _active_skills:
        _active_skills.discard(name)
        log.info("Skill desativada: %s", name)
        return True
    return False


def get_active_skills() -> list[Skill]:
    """Get all currently active skills (manually activated + auto-activate)."""
    result: list[Skill] = []
    all_skills = discover_skills()

    for skill in all_skills:
        if skill.name in _active_skills or skill.auto_activate:
            result.append(skill)

    return result


def get_skills_context(message: str = "") -> str:
    """Generate the skills context block for the system prompt.

    Includes manually activated skills + auto-triggered skills based on message.
    """
    active = get_active_skills()

    # Also check message triggers
    if message:
        triggered = match_skills(message)
        seen = {s.name for s in active}
        for skill in triggered:
            if skill.name not in seen:
                active.append(skill)
                seen.add(skill.name)

    if not active:
        return ""

    parts = ["\n## Skills Ativas\n"]
    for skill in active:
        parts.append(f"### {skill.name}")
        if skill.description:
            parts.append(f"*{skill.description}*\n")
        parts.append(skill.content)
        parts.append("")  # blank line between skills

    return "\n".join(parts)


def clear_active_skills() -> None:
    """Clear all manually activated skills."""
    _active_skills.clear()
