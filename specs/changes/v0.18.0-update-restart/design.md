# Design Document

## Overview
### Change Type: new-feature + ci/cd

### DES-1: routes/update.py
`install_update()` — `asyncio.create_subprocess_exec` com `stdout=PIPE`, `readline()` em loop, yield SSE. `_get_installed_version()` via `pip show`.

`restart_server()` — `asyncio.create_task(_do_restart())` para resposta imediata. `_do_restart()` — Popen + sleep(1) + sys.exit(0).

### DES-2: Frontend
`ui.js` — `openUpdateModal()`, `startInstallUpdate()` (SSE reader), `restartServer()`, `_waitForReconnect()` (poll /api/health com retry).

Modal HTML em `ui.html`. CSS em `components.css` (`.update-log`, `.btn-restart-now`).

### DES-3: CI Auto-release
`ci.yml` — job `Auto Release` com `needs: [test, lint]`, `if: push to main`. Steps: ler VERSION, checar tag, extrair CHANGELOG, criar tag, criar Release, build, `pypa/gh-action-pypi-publish`. Environment `pypi` para trusted publishing OIDC.
