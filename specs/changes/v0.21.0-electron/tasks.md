# Implementation Tasks

## Overview

Implementação do DenAI Desktop (Electron) em 5 fases.

**Pré-requisitos:**
- Node.js ≥ 18 instalado
- `uv` binaries baixados para cada plataforma e colocados em `electron/bin/`
- Ícones criados: `icon.png` (512×512), `icon.ico`, `icon.icns`

---

## Phase 1: Scaffold do Electron

- [ ] 1.1 Criar `electron/package.json` com electron-forge e electron-updater
  - _Implements: DES-1, REQ-1.1, REQ-1.5_

- [ ] 1.2 Criar `electron/forge.config.js` com makers para win32/darwin/linux
  - Configurar extraResource para empacotar `bin/` com uv binaries
  - _Implements: DES-2, REQ-1.2_

- [ ] 1.3 Baixar uv binaries para `electron/bin/`
  - `uv-win32-x64.exe`, `uv-darwin-arm64`, `uv-darwin-x64`, `uv-linux-x64`
  - Source: https://github.com/astral-sh/uv/releases
  - _Implements: DES-2, REQ-2.1_

- [ ] 1.4 Criar assets: `electron/assets/icon.png`, `icon.ico`, `icon.icns`
  - Usar o logo 🐺 do DenAI — criar versão em 512×512 px
  - _Implements: REQ-3.1_

---

## Phase 2: Backend Process Management

- [ ] 2.1 Criar `electron/src/main.js` — estrutura base
  - `createSplashWindow()` — janela 400×300, frameless, sempre no topo
  - `setupTray()` — tray icon com menu contextual
  - `createMainWindow()` — 900×600 mínimo, lembra posição/tamanho
  - _Implements: DES-3, REQ-3.4, REQ-4.1, REQ-4.2_

- [ ] 2.2 Implementar `detectUv()` em main.js
  - Localiza o binário uv correto para a plataforma atual via `process.platform + process.arch`
  - Usa `path.join(process.resourcesPath, 'bin', uvName)` em produção
  - Fallback para `which uv` em desenvolvimento
  - _Implements: DES-4, REQ-2.1_

- [ ] 2.3 Implementar `ensureVenv(uvPath, sendStatus)` em main.js
  - Verifica existência de `~/.denai/electron-venv/`
  - Se não existe: `uv venv` + `uv pip install denai=={VERSION}` com callback de progresso
  - Se existe mas versão diferente: `uv pip install --upgrade denai=={VERSION}`
  - _Implements: DES-5, REQ-2.2, REQ-2.3_

- [ ] 2.4 Implementar `spawnBackend(uvPath)` em main.js
  - Spawna `uv run --python {venvPath} python -m denai`
  - Captura stdout/stderr em buffer para logs de erro
  - Define `backendProcess` global para cleanup no quit
  - _Implements: DES-4, REQ-2.4_

- [ ] 2.5 Implementar `waitForHealth(timeoutMs)` em main.js
  - Poll `GET http://localhost:4078/api/health` a cada 500ms
  - Resolve ao receber 200, rejeita após timeout
  - _Implements: DES-4, REQ-2.5_

- [ ] 2.6 Implementar shutdown gracioso em `app.on('before-quit')`
  - `backendProcess.kill('SIGTERM')` + Promise com timeout 5s
  - _Implements: DES-3, REQ-2.6_

- [ ] 2.7 Tratar falha de inicialização do backend
  - `dialog.showErrorBox()` com mensagem + últimas linhas do log
  - Botão "Tentar novamente" chama `startBackend()` novamente
  - _Implements: REQ-2.7_

---

## Phase 3: UX — Splash, Tray, Janela Principal

- [ ] 3.1 Criar `electron/src/splash.html` e `splash.js`
  - Fundo dark (#0d1117), logo DenAI SVG, barra de progresso CSS
  - Recebe status via IPC: `ipcRenderer.on('splash-status', (e, msg) => ...)`
  - _Implements: DES-6, REQ-3.1, REQ-3.2_

- [ ] 3.2 Criar `electron/src/preload.js`
  - Expõe `contextBridge.exposeInMainWorld('electron', {...})` com canais IPC
  - _Implements: DES-3_

- [ ] 3.3 Implementar comportamento de fechar → minimizar para tray
  - `mainWindow.on('close', e => { e.preventDefault(); mainWindow.hide() })`
  - Exceto quando `app.isQuitting = true`
  - _Implements: REQ-4.3_

- [ ] 3.4 Implementar tray menu completo
  - "Abrir DenAI" → `mainWindow.show() + mainWindow.focus()`
  - "Status" → item disabled com texto dinâmico (online/offline)
  - "Sair" → `app.isQuitting = true; app.quit()`
  - Double-click → toggle window
  - _Implements: DES-7, REQ-4.2, REQ-4.4, REQ-4.5, REQ-4.6_

- [ ] 3.5 Detecção do Ollama e notificação
  - Poll `http://localhost:11434/api/version` no startup
  - Se offline: `new Notification('DenAI', { body: 'Ollama não encontrado. ...' })`
  - Poll periódico para detectar quando Ollama inicia
  - _Implements: DES-3, REQ-5.1, REQ-5.2, REQ-5.3, REQ-5.4_

---

## Phase 4: Auto-update e Build Final

- [ ] 4.1 Configurar electron-updater em main.js
  - `autoUpdater.setFeedURL({ provider: 'github', owner: 'rodrigogobbo', repo: 'denai' })`
  - `autoUpdater.checkForUpdatesAndNotify()` no startup
  - Handler para mostrar notificação de update disponível
  - _Implements: DES-9, REQ-6.1, REQ-6.2, REQ-6.3, REQ-6.4_

- [ ] 4.2 Testar build local: `cd electron && npm run make`
  - Verificar tamanho dos installers (< 150MB)
  - Verificar que uv está nos recursos empacotados
  - _Implements: REQ-7.4_

- [ ] 4.3 Adicionar `electron/` ao `.gitignore` adequadamente
  - Ignorar: `node_modules/`, `out/`, `.webpack/`
  - Incluir: `src/`, `assets/`, `forge.config.js`, `package.json`

---

## Phase 5: CI — build-electron job

- [ ] 5.1 Criar `.github/workflows/electron.yml`
  - Trigger: `on: release: types: [published]` (dispara junto com o PyPI publish)
  - Matrix: windows-latest, macos-latest (arm64 runner se disponível), ubuntu-latest
  - Steps: checkout, node setup, npm ci, npm run make, upload artifacts to release
  - _Implements: DES-8, REQ-1.3, REQ-1.4, REQ-7.1, REQ-7.2, REQ-7.3_

- [ ] 5.2 Injetar `BUNDLED_VERSION` no build
  - Script `electron/scripts/sync-version.js` que lê `denai/version.py` e atualiza `electron/package.json`
  - Chamado antes do `npm run make` no CI
  - _Implements: DES-5_

- [ ] 5.3 Documentar setup de desenvolvimento em `electron/README.md`
  - Pré-requisitos, como rodar em dev, como fazer build local
  - _Implements: REQ-1.1_
