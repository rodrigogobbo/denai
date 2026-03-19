"""Filtro de comandos perigosos — blocklist por regex."""

import re

BLOCKED_COMMANDS = [
    # Destrutivos
    r"\brm\s+(-rf?|--recursive)\s+[/\\]",
    r"\brmdir\s+/s\s+/q\b",
    r"\bformat\s+[a-zA-Z]:",
    r"\bdel\s+/[sfq]",
    r"\bmkfs\b",
    r"\bdd\s+if=.*of=.*/dev/",
    r">\s*/dev/sd[a-z]",
    # Exfiltração / execução remota
    r"\bcurl\b.*\|\s*(bash|sh|python)",
    r"\bwget\b.*\|\s*(bash|sh|python)",
    r"\bpowershell\b.*-enc",
    r"\biex\b.*\(.*downloadstring",
    r"\bInvoke-WebRequest\b.*\|\s*iex\b",
    # Rede suspeita
    r"\bnc\s+-[el]",
    r"\bncat\s+-[el]",
    # Registro/sistema Windows
    r"\breg\s+(delete|add)\b.*\\\\HKLM\\\\",
    r"\bbcdedit\b",
    r"\bschtasks\b.*/create\b",
    # Crypto / ofuscação
    r"base64\s+(-d|--decode)\b.*\|\s*(bash|sh|python)",
    r"\beval\b.*\$\(",
]


def is_command_safe(cmd: str) -> tuple:
    """Verifica se o comando é seguro.

    Returns:
        (safe, reason) — reason vazio se seguro.
    """
    for pattern in BLOCKED_COMMANDS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return False, f"Comando bloqueado por segurança (padrão: {pattern[:40]})"
    return True, ""
