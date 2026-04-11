# DenAI Desktop — Electron

App desktop para o DenAI. Gerencia o backend Python/FastAPI como processo filho e expõe a UI em uma janela nativa.

## Desenvolvimento

### Pré-requisitos

- Node.js ≥ 18
- `uv` instalado globalmente (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Setup

```bash
cd electron
npm install
```

### Rodar em dev

```bash
# Na raiz do repo (inicia o backend Python)
python -m denai &

# Em electron/
npm start
```

### Build local

```bash
# Baixar binários uv (necessário para empacotar)
# Ver .github/workflows/electron.yml para os URLs corretos
# Colocar em electron/bin/

# Sincronizar versão do Python
node scripts/sync-version.js

# Gerar instalador para a plataforma atual
npm run make
# Output em: electron/out/make/
```

## Estrutura

```
electron/
├── forge.config.js     ← configuração do electron-forge
├── package.json
├── scripts/
│   └── sync-version.js ← lê denai/version.py → atualiza package.json
├── src/
│   ├── main.js         ← main process
│   ├── preload.js      ← contextBridge
│   ├── splash.html     ← tela de loading
│   └── splash.js
├── bin/                ← binários uv (não comitados, baixados no CI)
│   ├── uv-darwin-arm64
│   ├── uv-darwin-x64
│   ├── uv-linux-x64
│   └── uv-win32-x64.exe
└── assets/
    ├── icon.png        ← 512×512px
    ├── icon.ico        ← Windows
    └── icon.icns       ← macOS
```

## Como funciona

1. Electron detecta o binário `uv` correto para a plataforma
2. No primeiro run: cria venv em `~/.denai/electron-venv/` e instala o `denai` via uv
3. Spawna `python -m denai` como processo filho
4. Aguarda `GET /api/health` responder (máx 30s)
5. Abre a janela principal apontando para `http://127.0.0.1:4078`
6. Tray icon fica na bandeja — fechar a janela minimiza, não encerra
