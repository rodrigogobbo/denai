"""Custom commands — prompts reutilizáveis em arquivos .md."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import DATA_DIR
from .logging_config import get_logger

log = get_logger("commands")

COMMANDS_DIR = DATA_DIR / "commands"
COMMANDS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Command:
    """A custom command definition."""

    name: str
    description: str = ""
    template: str = ""
    model: str = ""
    file_path: str = ""


def discover_commands() -> list[Command]:
    """Discover commands from ~/.denai/commands/*.md."""
    commands: list[Command] = []

    if not COMMANDS_DIR.exists():
        return commands

    for f in sorted(COMMANDS_DIR.glob("*.md")):
        try:
            cmd = _parse_command_file(f)
            if cmd:
                commands.append(cmd)
        except Exception as e:
            log.warning("Erro ao carregar comando %s: %s", f.name, e)

    return commands


def _parse_command_file(path: Path) -> Command | None:
    """Parse a command .md file with optional YAML frontmatter."""
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return None

    name = path.stem
    description = ""
    model = ""
    template = content

    # Parse YAML frontmatter (---\n...\n---)
    frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if frontmatter_match:
        try:
            meta = yaml.safe_load(frontmatter_match.group(1)) or {}
            description = meta.get("description", "")
            model = meta.get("model", "")
            template = frontmatter_match.group(2).strip()
        except yaml.YAMLError:
            template = content

    if not template:
        return None

    return Command(
        name=name,
        description=description,
        template=template,
        model=model,
        file_path=str(path),
    )


def render_command(cmd: Command, arguments: str = "") -> str:
    """Render a command template with arguments substituted."""
    result = cmd.template

    # Replace $ARGUMENTS with the full argument string
    result = result.replace("$ARGUMENTS", arguments)

    # Replace $1, $2, $3, etc. with positional args
    parts = _split_arguments(arguments)
    for i, part in enumerate(parts, 1):
        result = result.replace(f"${i}", part)

    # Clean up unreplaced positional vars
    result = re.sub(r"\$\d+", "", result)
    result = re.sub(r"\$ARGUMENTS", "", result)

    return result.strip()


def _split_arguments(args: str) -> list[str]:
    """Split arguments respecting quoted strings."""
    if not args.strip():
        return []

    parts: list[str] = []
    current = ""
    in_quotes = False
    quote_char = ""

    for ch in args:
        if ch in ('"', "'") and not in_quotes:
            in_quotes = True
            quote_char = ch
        elif ch == quote_char and in_quotes:
            in_quotes = False
            quote_char = ""
        elif ch == " " and not in_quotes:
            if current:
                parts.append(current)
                current = ""
        else:
            current += ch

    if current:
        parts.append(current)

    return parts


def get_command(name: str) -> Command | None:
    """Get a command by name."""
    commands = discover_commands()
    return next((c for c in commands if c.name == name), None)
