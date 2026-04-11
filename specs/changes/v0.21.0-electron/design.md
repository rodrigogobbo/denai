# Design Document

## Overview

### Change Type
new-feature (distribuição desktop)

### Design Goals
1. Electron como shell mínimo — zero lógica de negócio no JS, tudo no Python
2. uv bundled elimina dependência de Python pré-instalado sem o peso do PyInstaller
3. Manter paridade total com a distribuição PyPI — mesmo código Python, mesma API
4. Build reproduzível via CI sem segredos de signing obrigatórios (exceto macOS App Store)

### References
- REQ-1: Estrutura do Monorepo
- REQ-2: Gerenciamento do Backend Python
- REQ-3: Janela e Splash Screen
- REQ-4: Tray Icon
- REQ-5: Detecção Ollama
- REQ-6: Auto-update
- REQ-7: CI/CD

### Learnings do HubAI Nitro

Analisado o `main.js` compilado do Nitro (v0.0.58) em produção. Padrões aproveitados diretamente:

| Pattern Nitro | Aplicação no DenAI |
|---|---|
| `killProcessCrossPlatform()` | `taskkill /F /T /PID` no Windows, `SIGTERM` em Unix |
| `requestSingleInstanceLock()` | Evitar duas instâncias do DenAI abertas |
| `loadWindowBounds()` + `BOUNDS_FILE` | `window-bounds.json` no userData |
| Restart com backoff exponencial (`1500 * 2^n`, máx 3x) | Restartar backend Python se crashar |
| `waitForService(url, timeout, interval)` | Poll de health com timeout |
| `powerMonitor` → reconectar após sleep | Reconectar SSE do DenAI ao acordar |
| `uncaughtException` + `unhandledRejection` | Capturar crashes do Electron main process |
| `electron-updater` com GitHub provider | Auto-update — confirmado funcional no Nitro |

Nitro usa **Go binary bundled** (`wolf-server`). DenAI usa **uv + Python** — arquitetura diferente mas o padrão de spawn/monitor/restart é idêntico.

---

## System Architecture

```
denai/                          ← Python package (existente, não muda)
  __main__.py
  app.py
  ...

electron/                       ← NOVO — Electron shell
  package.json
  forge.config.js
  src/
    main.js                     ← main process: lifecycle, tray, IPC
    preload.js                  ← bridge segura renderer↔main
    splash.html                 ← tela de loading (HTML estático)
    splash.js
  bin/
    uv-win32-x64.exe            ← uv bundled por plataforma
    uv-darwin-arm64
    uv-darwin-x64
    uv-linux-x64
  assets/
    icon.png / icon.ico / icon.icns
```

### DES-1: Estrutura Electron (electron/package.json)

```json
{
  "name": "denai",
  "version": "0.21.0",
  "main": "src/main.js",
  "scripts": {
    "start": "electron-forge start",
    "make": "electron-forge make"
  },
  "devDependencies": {
    "@electron-forge/cli": "^7.x",
    "@electron-forge/maker-dmg": "^7.x",
    "@electron-forge/maker-nsis": "^7.x",
    "@electron-forge/maker-appimage": "^7.x"
  },
  "dependencies": {
    "electron-updater": "^6.x"
  }
}
```

### DES-2: forge.config.js

```js
module.exports = {
  packagerConfig: {
    extraResource: ['bin/'],   // empacota uv binaries
    icon: 'assets/icon',
    appBundleId: 'dev.gobbo.denai',
  },
  makers: [
    { name: '@electron-forge/maker-nsis', platforms: ['win32'] },
    { name: '@electron-forge/maker-dmg',  platforms: ['darwin'] },
    { name: '@electron-forge/maker-appimage', platforms: ['linux'] },
  ]
}
```

### DES-3: main.js — Lifecycle

```
app.whenReady()
  └── requestSingleInstanceLock()   ← padrão Nitro
  └── createSplashWindow()
  └── setupTray()
  └── startBackend()
        ├── detectUv()              → path do uv bundled
        ├── ensureVenv()            → uv venv + uv pip install denai=={VERSION}
        ├── spawnBackend()          → child_process.spawn
        └── waitForService(url, 30000, 500)   ← padrão Nitro
              ├── OK → closeSplash() + createMainWindow()
              └── FAIL → showErrorDialog()

app.on('window-all-closed')
  └── hideToTray()   (NÃO quit — minimize to tray)

powerMonitor.on('resume')          ← padrão Nitro
  └── reconnectSSE()               → backend já está rodando, só reconectar

tray.on('double-click')
  └── toggleMainWindow()

app.on('before-quit')
  └── killProcessCrossPlatform(backendProcess)   ← padrão Nitro
```

### DES-4: Backend Process Management

```js
// Padrão adaptado do Nitro startWolfServer()
function startDenaiBackend() {
  const child = spawn(uvPath, ['run', '--python', venvPython, '-m', 'denai'], {
    env: { ...process.env, DENAI_PORT: '4078' },
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
  });

  child.stdout?.on('data', d => console.log(`[DenAI] ${d.toString().trim()}`));
  child.stderr?.on('data', d => console.warn(`[DenAI:err] ${d.toString().trim()}`));

  child.on('exit', (code, signal) => {
    backendProcess = null;
    const unexpected = code !== 0 && !isQuitting;
    if (unexpected) {
      backendRestartCount++;
      if (backendRestartCount <= MAX_RESTARTS) {  // MAX_RESTARTS = 3
        const delay = 1500 * Math.pow(2, backendRestartCount - 1);  // backoff Nitro
        setTimeout(startDenaiBackend, delay);
      }
    }
  });
}
```

### DES-5: killProcessCrossPlatform (padrão Nitro)

```js
function killProcessCrossPlatform(proc, name) {
  if (proc.killed || proc.pid == null) return;
  if (process.platform === 'win32') {
    try { execSync(`taskkill /F /T /PID ${proc.pid}`, { stdio: 'ignore' }); }
    catch {}
  } else {
    proc.kill('SIGTERM');
  }
}
```

### DES-6: Single Instance (padrão Nitro)

```js
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) { mainWindow.show(); mainWindow.focus(); }
  });
}
```

### DES-7: Window Bounds Persistence (padrão Nitro)

```js
const BOUNDS_FILE = path.join(app.getPath('userData'), 'window-bounds.json');

function loadWindowBounds() {
  try {
    const data = JSON.parse(fs.readFileSync(BOUNDS_FILE, 'utf-8'));
    if (data.width >= WIN_MIN_WIDTH && data.height >= WIN_MIN_HEIGHT) return data;
  } catch {}
  return { width: 1100, height: 700 };
}

function saveWindowBounds(win) {
  fs.writeFileSync(BOUNDS_FILE, JSON.stringify(win.getBounds()));
}
```

### DES-8: powerMonitor → Reconectar SSE (padrão Nitro)

```js
powerMonitor.on('resume', () => {
  // O backend Python continua rodando; reconectar SSE no frontend
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.executeJavaScript(
      'window.dispatchEvent(new CustomEvent("denai:wake"))'
    );
  }
});
```

### DES-9: uv Bootstrap

Na primeira execução (sem `~/.denai/electron-venv/`):
```
uv venv ~/.denai/electron-venv
uv pip install --python ~/.denai/electron-venv denai=={BUNDLED_VERSION}
```

`BUNDLED_VERSION` é injetado em `main.js` durante o build a partir de `denai/version.py`.

### DES-10: Splash Screen

`splash.html` — HTML simples com fundo dark (#0d1117), logo SVG do DenAI, mensagem de status dinâmica e barra de progresso CSS.

Estados:
1. "Verificando instalação..." (checkVenv)
2. "Configurando Python..." (uv venv) — só no first run
3. "Instalando DenAI..." (uv pip install) — só no first run
4. "Iniciando servidor..." (waitForService)

### DES-11: Tray Menu

```
┌─────────────────────────┐
│  🐺 Abrir DenAI         │
├─────────────────────────┤
│  ● Servidor: online     │
├─────────────────────────┤
│  Sair                   │
└─────────────────────────┘
```

### DES-12: Auto-update (padrão Nitro)

```js
autoUpdater.setFeedURL({ provider: 'github', owner: 'rodrigogobbo', repo: 'denai' });
autoUpdater.checkForUpdatesAndNotify();
```

### DES-13: Crash Handlers (padrão Nitro)

```js
process.on('uncaughtException', err => {
  console.error('[DenAI] Uncaught exception:', err);
  // log local — sem telemetria (privacidade)
});
process.on('unhandledRejection', reason => {
  console.error('[DenAI] Unhandled rejection:', reason);
});
```

### DES-14: CI — build-electron job

```yaml
build-electron:
  needs: [release]
  strategy:
    matrix:
      os: [windows-latest, macos-latest, ubuntu-latest]
  steps:
    - npm ci
    - node scripts/sync-version.js
    - npm run make
    - upload artifacts to GitHub Release
```

---

## O que NÃO muda

- `denai/` Python package — sem alterações
- `pip install denai` continua funcionando
- `python -m denai` continua funcionando
- Toda a API REST — idêntica
- Testes Python — sem alterações


---

## System Architecture

```
denai/                          ← Python package (existente, não muda)
  __main__.py
  app.py
  ...

electron/                       ← NOVO — Electron shell
  package.json
  forge.config.js
  src/
    main.js                     ← main process: lifecycle, tray, IPC
    preload.js                  ← bridge segura renderer↔main
    splash.html                 ← tela de loading (HTML estático)
    splash.js
  bin/
    uv-win32-x64.exe            ← uv bundled por plataforma
    uv-darwin-arm64
    uv-darwin-x64
    uv-linux-x64
  assets/
    icon.png / icon.ico / icon.icns
```

### DES-1: Estrutura Electron (electron/package.json)

```json
{
  "name": "denai",
  "version": "0.21.0",
  "main": "src/main.js",
  "scripts": {
    "start": "electron-forge start",
    "make": "electron-forge make"
  },
  "devDependencies": {
    "@electron-forge/cli": "^7.x",
    "@electron-forge/maker-dmg": "^7.x",
    "@electron-forge/maker-nsis": "^7.x",
    "@electron-forge/maker-appimage": "^7.x"
  },
  "dependencies": {
    "electron-updater": "^6.x"
  }
}
```

### DES-2: forge.config.js

```js
module.exports = {
  packagerConfig: {
    extraResource: ['bin/'],   // empacota uv binaries
    icon: 'assets/icon',
    appBundleId: 'dev.gobbo.denai',
  },
  makers: [
    { name: '@electron-forge/maker-nsis', platforms: ['win32'] },
    { name: '@electron-forge/maker-dmg',  platforms: ['darwin'] },
    { name: '@electron-forge/maker-appimage', platforms: ['linux'] },
  ]
}
```

### DES-3: main.js — Lifecycle

```
app.whenReady()
  └── createSplashWindow()
  └── setupTray()
  └── startBackend()
        ├── detectUv()           → path do uv bundled
        ├── ensureVenv()         → uv venv + uv pip install denai=={VERSION}
        ├── spawnBackend()       → child_process.spawn('uv run python -m denai')
        └── waitForHealth(30s)
              ├── OK → closeSplash() + createMainWindow()
              └── FAIL → showErrorDialog()

app.on('window-all-closed')
  └── hideToTray()   (NÃO quit — minimize to tray)

tray.on('double-click')
  └── toggleMainWindow()

app.on('before-quit')
  └── backend.kill('SIGTERM') + await(5s)
```

### DES-4: Backend Process Management

O backend é spawned com:
```js
const proc = spawn(uvPath, ['run', '--python', venvPython, '-m', 'denai'], {
  env: { ...process.env, DENAI_PORT: '4078' },
  detached: false,
})
```

stdout/stderr são capturados e armazenados para exibição em caso de erro.

Health check: poll `GET http://localhost:4078/api/health` a cada 500ms por até 30s.

### DES-5: uv Bootstrap

Na primeira execução (sem `~/.denai/electron-venv/`):
```
uv venv ~/.denai/electron-venv
uv pip install --python ~/.denai/electron-venv denai=={BUNDLED_VERSION}
```

O `BUNDLED_VERSION` é injetado em `main.js` durante o build a partir de `denai/version.py`.

### DES-6: Splash Screen

`splash.html` — HTML simples com fundo dark (#0d1117), logo SVG do DenAI, mensagem de status dinâmica e barra de progresso CSS. Sem bundler, sem framework.

Estados da splash:
1. "Verificando instalação..." (checkVenv)
2. "Configurando Python..." (uv venv) — só no first run
3. "Instalando DenAI..." (uv pip install) — só no first run
4. "Iniciando servidor..." (waitForHealth)

### DES-7: Tray Menu

```
┌─────────────────────────┐
│  🐺 Abrir DenAI         │
├─────────────────────────┤
│  ● Servidor: online     │  (ou ○ offline)
├─────────────────────────┤
│  Sair                   │
└─────────────────────────┘
```

### DES-8: CI — build-electron job

Novo job no `.github/workflows/ci.yml` (ou arquivo separado `electron.yml`):

```yaml
build-electron:
  needs: [release]  # roda APÓS release do Python
  strategy:
    matrix:
      os: [windows-latest, macos-latest, ubuntu-latest]
  steps:
    - npm ci
    - npm run make
    - upload artifacts para GitHub Release
```

### DES-9: Auto-update via electron-updater

`electron-updater` usa o GitHub Releases como feed. Configuração mínima:
```js
autoUpdater.setFeedURL({
  provider: 'github',
  owner: 'rodrigogobbo',
  repo: 'denai',
})
autoUpdater.checkForUpdatesAndNotify()
```

---

## Decisões técnicas

### Por que uv e não PyInstaller?

| | uv bundled | PyInstaller |
|---|---|---|
| Tamanho do installer | ~50MB (uv 4MB + app) | ~120-200MB |
| Compatibilidade | Qualquer Python 3.10+ via uv | Bundla um Python específico |
| Debugging | Processo Python normal, logs reais | Difícil de debugar |
| Updates do denai | `uv pip install --upgrade denai` | Rebuild do binário inteiro |

### Por que não empacotar o Python junto?

Porque o `denai/routes/update.py` já tem a lógica de `pip install --upgrade denai`. Com uv, o update do DenAI continua funcionando da mesma forma — apenas substitui o pacote no venv. Com PyInstaller, seria necessário baixar um novo binário inteiro.

### Tamanho estimado dos installers

- Windows (.exe NSIS): ~55MB
- macOS (.dmg): ~60MB
- Linux (.AppImage): ~65MB

Todos abaixo do limite de 150MB (REQ-7.4).

### O que NÃO muda

- `denai/` Python package — sem alterações
- `pip install denai` continua funcionando
- `python -m denai` continua funcionando
- Toda a API REST — idêntica
- Testes Python — sem alterações
