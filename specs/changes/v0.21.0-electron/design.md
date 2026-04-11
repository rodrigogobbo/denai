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
  scripts/
    sync-version.js             ← lê denai/version.py → atualiza package.json
  src/
    main.js                     ← main process: lifecycle, tray, IPC
    preload.js                  ← bridge segura renderer↔main
    splash.html                 ← tela de loading
    splash.js
  bin/
    uv-win32-x64.exe
    uv-darwin-arm64
    uv-darwin-x64
    uv-linux-x64
  assets/
    icon.png / icon.ico / icon.icns
```

### DES-1: electron/package.json

```json
{
  "name": "denai",
  "version": "0.21.0",
  "main": "src/main.js",
  "scripts": {
    "start": "electron-forge start",
    "make": "electron-forge make",
    "sync-version": "node scripts/sync-version.js"
  },
  "devDependencies": {
    "@electron-forge/cli": "^7.x",
    "@electron-forge/maker-dmg": "^7.x",
    "@electron-forge/maker-nsis": "^7.x",
    "@electron-forge/maker-appimage": "^7.x",
    "electron": "^33.x"
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
    extraResource: ['bin/'],
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
  └── requestSingleInstanceLock()
  └── createSplashWindow()
  └── setupTray()
  └── startBackend()
        ├── detectUv()
        ├── ensureVenv()        → uv venv + uv pip install denai=={VERSION}
        ├── spawnBackend()
        └── waitForService(url, 30000, 500)
              ├── OK  → closeSplash() + createMainWindow()
              └── FAIL → showErrorDialog()

app.on('window-all-closed')  → hideToTray()

powerMonitor.on('resume')    → dispatchEvent('denai:wake') no renderer

app.on('before-quit')        → killProcessCrossPlatform(backendProcess)
```

### DES-4: Backend Process Management

```js
function startDenaiBackend() {
  const child = spawn(uvPath, ['run', '--python', venvPython, '-m', 'denai'], {
    env: { ...process.env, DENAI_PORT: '4078' },
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
  });

  child.on('exit', (code) => {
    const unexpected = code !== 0 && !isQuitting;
    if (unexpected && backendRestartCount < MAX_RESTARTS) {
      backendRestartCount++;
      const delay = 1500 * Math.pow(2, backendRestartCount - 1);
      setTimeout(startDenaiBackend, delay);
    }
  });
}
```

MAX_RESTARTS = 3. Backoff: 1.5s → 3s → 6s.

### DES-5: killProcessCrossPlatform

```js
function killProcessCrossPlatform(proc) {
  if (!proc || proc.killed || proc.pid == null) return;
  if (process.platform === 'win32') {
    try { execSync(`taskkill /F /T /PID ${proc.pid}`, { stdio: 'ignore' }); }
    catch {}
  } else {
    proc.kill('SIGTERM');
  }
}
```

### DES-6: Single Instance

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

### DES-7: Window Bounds Persistence

```js
const BOUNDS_FILE = path.join(app.getPath('userData'), 'window-bounds.json');
// save on 'resize' + 'move', load on createMainWindow()
```

### DES-8: powerMonitor → Reconectar após sleep

```js
powerMonitor.on('resume', () => {
  mainWindow?.webContents.executeJavaScript(
    'window.dispatchEvent(new CustomEvent("denai:wake"))'
  );
});
```

### DES-9: uv Bootstrap

```bash
# First run only (~30s)
uv venv ~/.denai/electron-venv
uv pip install --python ~/.denai/electron-venv denai=={BUNDLED_VERSION}

# Subsequent runs (<2s)
uv run --python ~/.denai/electron-venv python -m denai
```

`BUNDLED_VERSION` injetado pelo `scripts/sync-version.js` no build.

### DES-10: Splash Screen

`splash.html` — HTML puro, fundo `#0d1117`, logo SVG, barra de progresso CSS.

Estados via IPC:
1. `"Verificando instalação..."`
2. `"Configurando Python..."` ← só first run
3. `"Instalando DenAI..."` ← só first run
4. `"Iniciando servidor..."`

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

### DES-12: Auto-update

```js
autoUpdater.setFeedURL({ provider: 'github', owner: 'rodrigogobbo', repo: 'denai' });
autoUpdater.checkForUpdatesAndNotify();
```

### DES-13: Crash Handlers

```js
process.on('uncaughtException', err => console.error('[DenAI]', err));
process.on('unhandledRejection', r => console.error('[DenAI]', r));
```

### DES-14: CI build-electron

```yaml
build-electron:
  needs: [release]
  strategy:
    matrix:
      os: [windows-latest, macos-latest, ubuntu-latest]
  steps:
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
