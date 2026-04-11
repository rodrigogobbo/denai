# Requirements Document

## Introduction

O DenAI hoje exige que o usuário: instale Python 3.10+, instale Ollama, execute `python -m denai` no terminal, e abra o browser manualmente. Essa sequência de 4 passos é a maior barreira de adoção para usuários não-técnicos.

Este change transforma o DenAI em uma aplicação desktop nativa usando Electron, distribuída como instalador binário (.exe no Windows, .dmg no macOS, .AppImage no Linux). O backend Python/FastAPI continua sendo o core — o Electron atua como shell gráfico que:
1. Gerencia o ciclo de vida do processo Python
2. Abre uma janela de browser nativa apontando para o servidor local
3. Providencia ícone na bandeja do sistema com menu de contexto
4. Detecta e guia a instalação do Ollama se necessário

A estratégia de empacotamento usa **uv** (gerenciador de pacotes Python ultra-rápido, 4MB) bundled dentro do pacote Electron. O uv instala Python e o denai em um ambiente isolado na primeira execução (~30s), e depois apenas inicia o servidor em <2s nas execuções seguintes.

O pacote Python no PyPI continua existindo e funcionando para usuários técnicos. O Electron é uma distribuição alternativa, não um replacement.

## Glossary

| Term | Definition |
|------|------------|
| electron_shell | A camada Electron que gerencia a janela e o processo Python |
| backend_process | O processo uvicorn/FastAPI spawned pelo Electron |
| uv | Gerenciador de pacotes Python ultra-rápido (astral-sh/uv), bundled no app Electron |
| venv_dir | Ambiente virtual isolado criado pelo uv em `~/.denai/electron-venv/` |
| tray_icon | Ícone do DenAI na bandeja do sistema com menu (Abrir, Configurações, Sair) |
| ipc | Inter-process communication entre Electron main process e renderer |
| splash_screen | Tela de loading exibida enquanto o backend Python inicializa |

## Requirements

### REQ-1: Estrutura do Monorepo Electron

**User Story:** Como mantenedor, quero que o código Electron viva dentro do repositório denai com build integrado ao CI, para manter um único repositório com distribuições Python (PyPI) e desktop (Electron).

#### Acceptance Criteria

1.1. THE repository SHALL contain an `electron/` directory with: `main.js`, `preload.js`, `package.json`, `forge.config.js`. _(Ubiquitous)_

1.2. THE `electron/` build SHALL be independent of the Python package build — `npm run make` in `electron/` produces installers without touching `pyproject.toml`. _(Ubiquitous)_

1.3. THE CI pipeline SHALL build Electron distributables on push to `main` for: Windows (x64), macOS (arm64, x64), Linux (x64). _(Ubiquitous)_

1.4. Electron distributables SHALL be attached to the GitHub Release created by the existing auto-release job. _(Event-driven)_

1.5. THE `electron/` directory SHALL have its own `package.json` with `@electron/forge` as the build tool. _(Ubiquitous)_

### REQ-2: Gerenciamento do Backend Python

**User Story:** Como usuário, quero que o app instale e gerencie o Python e o DenAI automaticamente, sem precisar abrir o terminal.

#### Acceptance Criteria

2.1. THE Electron app SHALL bundle `uv` binary for the target platform inside `electron/bin/uv-{platform}`. _(Ubiquitous)_

2.2. ON first launch, IF `~/.denai/electron-venv/` does not exist, THE app SHALL create a virtual environment and install `denai` via uv, showing progress in the splash screen. _(Event-driven)_

2.3. WHEN the installed `denai` version differs from the bundled expected version, THE app SHALL offer to upgrade automatically. _(Event-driven)_

2.4. THE backend SHALL be spawned as a child process: `uv run --python ~/.denai/electron-venv python -m denai`. _(Ubiquitous)_

2.5. THE app SHALL wait for `GET /api/health` to return 200 before showing the main window (max 30s timeout). _(Event-driven)_

2.6. WHEN the Electron app closes, THE app SHALL send SIGTERM to the backend process and wait up to 5s for graceful shutdown. _(Event-driven)_

2.7. IF the backend fails to start, THE app SHALL show an error dialog with logs and a "Try again" button. _(Unwanted behavior)_

### REQ-3: Janela Principal e Splash Screen

**User Story:** Como usuário, quero ver uma tela de loading enquanto o app inicializa, e depois a interface do DenAI em uma janela nativa.

#### Acceptance Criteria

3.1. THE app SHALL show a splash screen during backend initialization with: DenAI logo, version, status message, and progress indicator. _(Ubiquitous)_

3.2. ON first launch only, THE splash screen SHALL show installation progress with step labels (Configurando Python... Instalando DenAI... Iniciando servidor...). _(Event-driven)_

3.3. WHEN the backend is ready, THE app SHALL transition from splash to the main BrowserWindow loading `http://localhost:4078`. _(Event-driven)_

3.4. THE main window SHALL have: minimum size 900×600, remember last position/size, and show native title bar with "DenAI" title. _(Ubiquitous)_

3.5. THE main window SHALL open DevTools only in development mode (not in production builds). _(Ubiquitous)_

### REQ-4: Tray Icon

**User Story:** Como usuário, quero que o DenAI continue rodando quando fecho a janela, acessível pelo ícone na bandeja do sistema.

#### Acceptance Criteria

4.1. THE app SHALL create a system tray icon with the DenAI logo. _(Ubiquitous)_

4.2. THE tray icon context menu SHALL contain: "Abrir DenAI", separator, "Status do servidor" (enabled/disabled indicator), separator, "Sair". _(Ubiquitous)_

4.3. WHEN the main window is closed via the X button, THE app SHALL hide the window instead of quitting (minimize to tray). _(Event-driven)_

4.4. WHEN "Abrir DenAI" is clicked in the tray menu, THE app SHALL show and focus the main window. _(Event-driven)_

4.5. WHEN "Sair" is clicked, THE app SHALL quit completely, including stopping the backend. _(Event-driven)_

4.6. Double-clicking the tray icon SHALL toggle the main window visibility. _(Event-driven)_

### REQ-5: Detecção e Guia do Ollama

**User Story:** Como usuário novo, quero que o app detecte se o Ollama está instalado e me guia para instalá-lo se necessário.

#### Acceptance Criteria

5.1. ON startup, THE app SHALL check if Ollama is running by calling `GET http://localhost:11434/api/version`. _(Event-driven)_

5.2. IF Ollama is not running, THE app SHALL show a non-blocking notification with a link to `https://ollama.com/download`. _(Event-driven)_

5.3. THE notification SHALL not block the main window — user can still open DenAI and see the setup wizard. _(Ubiquitous)_

5.4. WHEN Ollama becomes available after the initial check, THE app SHALL automatically dismiss the notification. _(Event-driven)_

### REQ-6: Auto-update do App Electron

**User Story:** Como usuário, quero receber atualizações automáticas do app Electron sem precisar baixar manualmente.

#### Acceptance Criteria

6.1. THE Electron app SHALL check for new GitHub Releases on startup using `electron-updater`. _(Event-driven)_

6.2. WHEN an update is available, THE app SHALL show a non-intrusive notification: "Nova versão disponível. Baixar e instalar?" _(Event-driven)_

6.3. IF the user accepts, THE app SHALL download the update in background and install on next restart. _(Event-driven)_

6.4. The auto-update SHALL work for: Windows (NSIS), macOS (dmg), Linux (AppImage). _(Ubiquitous)_

### REQ-7: Distribuição e CI

**User Story:** Como mantenedor, quero que os builds Electron sejam gerados automaticamente no CI junto com a release do PyPI.

#### Acceptance Criteria

7.1. THE CI SHALL have a `build-electron` job triggered by the same version bump that triggers the Python release. _(Event-driven)_

7.2. THE build SHALL produce signed installers for macOS (when signing cert is available) and unsigned for Windows/Linux. _(Ubiquitous)_

7.3. THE GitHub Release SHALL contain download links for: `.exe` (Windows), `.dmg` (macOS arm64), `.dmg` (macOS x64), `.AppImage` (Linux). _(Ubiquitous)_

7.4. THE total installer size SHALL not exceed 150MB for any platform. _(Ubiquitous)_
