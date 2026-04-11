# Implementation Tasks

## Status: ✅ DONE (PR #54, v0.21.0)

## Phase 1: Scaffold ✅

- [x] 1.1 `electron/package.json` com electron-forge e electron-updater
  - _Implements: DES-1, REQ-1.1, REQ-1.5_

- [x] 1.2 `electron/forge.config.js` — makers win32/darwin/linux, extraResource bin/
  - _Implements: DES-2, REQ-1.2_

- [x] 1.3 `electron/bin/` — placeholder (.gitignore), baixados no CI
  - _Implements: REQ-2.1_

- [x] 1.4 `electron/assets/` — estrutura criada (ícones a serem adicionados)
  - _Implements: REQ-3.1_

- [x] 1.5 `electron/.gitignore` — node_modules, out, bin
  - _Implements: REQ-1.1_

- [x] 1.6 `electron/README.md` — setup dev, build local, estrutura
  - _Implements: REQ-1.1_

## Phase 2: Backend Process Management ✅

- [x] 2.1 `getUvPath()` — detecta uv por platform/arch, fallback global
  - _Implements: DES-3, REQ-2.1_

- [x] 2.2 `ensureVenv()` — cria venv + instala/atualiza denai via uv
  - _Implements: DES-9, REQ-2.2, REQ-2.3_

- [x] 2.3 `spawnBackend()` — spawn com env DENAI_PORT + stdout/stderr logging
  - _Implements: DES-4, REQ-2.4_

- [x] 2.4 `waitForService()` — poll HTTP com timeout 30s
  - _Implements: DES-4, REQ-2.5_

- [x] 2.5 `killProcessCrossPlatform()` — taskkill Windows / SIGTERM Unix
  - _Implements: DES-5, REQ-2.6_

- [x] 2.6 Restart com backoff exponencial (1.5s/3s/6s, máx 3x)
  - _Implements: DES-4, REQ-2.7_

- [x] 2.7 `app.on('before-quit')` — killProcessCrossPlatform
  - _Implements: REQ-2.6_

## Phase 3: UX ✅

- [x] 3.1 `splash.html` + `splash.js` — dark theme, logo, barra de progresso, IPC
  - _Implements: DES-10, REQ-3.1, REQ-3.2_

- [x] 3.2 `preload.js` — contextBridge seguro
  - _Implements: DES-3_

- [x] 3.3 `createMainWindow()` — bounds persistidos, fechar→hide, min 900×600
  - _Implements: DES-7, REQ-3.3, REQ-3.4, REQ-4.3_

- [x] 3.4 `setupTray()` — menu Abrir/Status/Sair, double-click toggle, status poll 5s
  - _Implements: DES-11, REQ-4.1, REQ-4.2, REQ-4.4, REQ-4.5, REQ-4.6_

- [x] 3.5 `checkOllama()` — poll 11434, notificação não-bloqueante, retry 30s
  - _Implements: REQ-5.1, REQ-5.2, REQ-5.3, REQ-5.4_

- [x] 3.6 `requestSingleInstanceLock()` — foco na janela existente
  - _Implements: DES-6_

- [x] 3.7 `powerMonitor.resume` → dispatchEvent('denai:wake')
  - _Implements: DES-8_

## Phase 4: Auto-update e Build ✅

- [x] 4.1 `setupAutoUpdate()` — electron-updater com GitHub provider
  - _Implements: DES-12, REQ-6.1, REQ-6.2, REQ-6.3, REQ-6.4_

- [x] 4.2 Crash handlers — uncaughtException + unhandledRejection
  - _Implements: DES-13_

## Phase 5: CI ✅

- [x] 5.1 `.github/workflows/electron.yml` — matrix win/mac/linux, download uv, make, upload release
  - _Implements: DES-14, REQ-1.3, REQ-1.4, REQ-7.1, REQ-7.2, REQ-7.3_

- [x] 5.2 `electron/scripts/sync-version.js` — lê version.py, atualiza package.json
  - _Implements: DES-9, REQ-1.4_

## Pendente (próximas iterações)

- [ ] Ícones reais: icon.png (512×512), icon.ico, icon.icns
  - _Implements: REQ-3.1_

- [ ] Testar build local em macOS + Windows
  - _Implements: REQ-7.4_

- [ ] Code signing macOS (requer Apple Developer account)
  - _Implements: REQ-7.2_
