"""Tool de execução de comandos — subprocess com sandbox e filtro."""

from __future__ import annotations

import asyncio
import platform
import subprocess

from ..security.command_filter import is_command_safe
from ..security.sandbox import is_path_allowed

# ─── Spec ──────────────────────────────────────────────────────────────────

COMMAND_EXEC_SPEC = {
    "type": "function",
    "function": {
        "name": "command_exec",
        "description": (
            "Executa um comando no terminal (bash no Linux/macOS, cmd no Windows). "
            "Use para rodar scripts, instalar pacotes, consultar informações do sistema, "
            "executar git, etc. Comandos destrutivos são bloqueados automaticamente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Comando a executar",
                },
                "workdir": {
                    "type": "string",
                    "description": "Diretório de trabalho (padrão: home do usuário)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout em segundos (padrão: 30, máximo: 120)",
                },
            },
            "required": ["command"],
        },
    },
}


# ─── Constants ─────────────────────────────────────────────────────────────

MAX_OUTPUT = 4000  # chars
MAX_TIMEOUT = 120


# ─── Executor ──────────────────────────────────────────────────────────────


async def command_exec(args: dict) -> str:
    """Executa um comando no shell."""
    command = args.get("command", "").strip()
    if not command:
        return "❌ Parâmetro 'command' é obrigatório."

    # 1. Filtro de segurança
    safe, reason = is_command_safe(command)
    if not safe:
        return f"🔒 Comando bloqueado: {reason}"

    # 2. Workdir (sandbox check)
    workdir = args.get("workdir")
    if workdir:
        from pathlib import Path

        workdir_path = Path(workdir).expanduser().resolve()
        allowed, reason = is_path_allowed(str(workdir_path))
        if not allowed:
            return f"🔒 Diretório bloqueado: {reason}"
        if not workdir_path.is_dir():
            return f"❌ Diretório não encontrado: {workdir_path}"
        cwd = str(workdir_path)
    else:
        from pathlib import Path

        cwd = str(Path.home())

    # 3. Timeout
    timeout = min(int(args.get("timeout", 30)), MAX_TIMEOUT)

    # 4. Montar comando pra shell
    is_windows = platform.system() == "Windows"
    if is_windows:
        shell_cmd = ["cmd", "/c", command]
    else:
        shell_cmd = ["/bin/sh", "-c", command]

    # 5. Executar
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *shell_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
            ),
            timeout=5,  # timeout pra criar o processo
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            return f"⏱️ Comando excedeu o timeout de {timeout}s e foi cancelado."

    except FileNotFoundError:
        return f"❌ Shell não encontrado: {shell_cmd[0]}"
    except asyncio.TimeoutError:
        return "❌ Timeout ao criar o processo."
    except Exception as e:
        return f"❌ Erro ao executar: {type(e).__name__}: {e}"

    # 6. Montar resultado
    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
    exit_code = proc.returncode

    parts = []
    if stdout:
        text = stdout if len(stdout) <= MAX_OUTPUT else stdout[:MAX_OUTPUT] + "\n... (truncado)"
        parts.append(text)
    if stderr:
        text = stderr if len(stderr) <= MAX_OUTPUT else stderr[:MAX_OUTPUT] + "\n... (truncado)"
        parts.append(f"⚠️ stderr:\n{text}")

    if exit_code != 0:
        parts.append(f"❌ Exit code: {exit_code}")
    elif not parts:
        parts.append("✅ Comando executado (sem output).")

    return "\n".join(parts)


# ─── Registration ──────────────────────────────────────────────────────────

TOOLS = [
    (COMMAND_EXEC_SPEC, "command_exec"),
]
