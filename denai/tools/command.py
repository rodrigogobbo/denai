"""Execução de comandos no terminal — com filtro de segurança."""

import subprocess
import sys
from pathlib import Path

from ..security.command_filter import is_command_safe
from ..security.sandbox import is_path_allowed

SPEC = {
    "type": "function",
    "function": {
        "name": "command_exec",
        "description": "Executa um comando no terminal. Comandos destrutivos são bloqueados por segurança.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Comando para executar"},
                "workdir": {
                    "type": "string",
                    "description": "Diretório de trabalho (dentro do home, opcional)",
                },
            },
            "required": ["command"],
        },
    },
}

TOOLS = [(SPEC, "command_exec")]


async def command_exec(args: dict) -> str:
    cmd = args["command"]

    safe, reason = is_command_safe(cmd)
    if not safe:
        return f"🔒 {reason}"

    workdir = args.get("workdir", str(Path.home()))
    wd_ok, _ = is_path_allowed(workdir)
    if not wd_ok:
        workdir = str(Path.home())

    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=30, cwd=workdir,
            )
        else:
            result = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True, text=True, timeout=30, cwd=workdir,
            )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        if result.returncode != 0:
            output += f"\n(exit code: {result.returncode})"
        return (output.strip()[:5000]) or "(sem output)"

    except subprocess.TimeoutExpired:
        return "⚠️ Comando excedeu timeout de 30 segundos"
    except PermissionError:
        return f"🔒 Sem permissão para executar: {cmd[:80]}"
