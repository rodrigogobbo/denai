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
