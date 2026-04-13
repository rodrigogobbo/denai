# Design — v0.26.0 Electron UX

### DES-1: Notificações — main.js

```js
// Reutilizar o poll de Ollama já existente (checkOllama())
// Adicionar estado para detectar transições online↔offline

let _ollamaWasOnline = null;

function notifyOllamaStatus(isOnline) {
  if (_ollamaWasOnline === isOnline) return; // sem mudança
  const prev = _ollamaWasOnline;
  _ollamaWasOnline = isOnline;
  if (prev === null) return; // primeiro check, não notificar

  if (!isOnline) {
    new Notification({ title: 'DenAI', body: 'Ollama offline — modelos indisponíveis.' }).show();
  } else {
    new Notification({ title: 'DenAI', body: 'Ollama online — pronto para conversar.' }).show();
  }
}
```

### DES-2: Modelo por perfil — routes/profiles.py + frontend

Backend:
```python
# GET /api/profiles/active/model → lê ~/.denai/[profiles/<name>/]last_model
# POST /api/profiles/active/model body:{model} → salva o arquivo
```

Frontend: ao trocar de modelo, chamar `POST /api/profiles/active/model`. Ao carregar a UI, buscar `GET /api/profiles/active/model` e setar o modelo.

### DES-3: icon.icns real — CI + iconutil

No step `Make distributables (arm64)` do macos-latest:
```bash
# Gerar iconset e converter para icns
mkdir -p /tmp/DenAI.iconset
sips -z 16 16   icon.png -o /tmp/DenAI.iconset/icon_16x16.png
sips -z 32 32   icon.png -o /tmp/DenAI.iconset/icon_16x16@2x.png
sips -z 32 32   icon.png -o /tmp/DenAI.iconset/icon_32x32.png
sips -z 64 64   icon.png -o /tmp/DenAI.iconset/icon_32x32@2x.png
sips -z 128 128 icon.png -o /tmp/DenAI.iconset/icon_128x128.png
sips -z 256 256 icon.png -o /tmp/DenAI.iconset/icon_128x128@2x.png
sips -z 256 256 icon.png -o /tmp/DenAI.iconset/icon_256x256.png
sips -z 512 512 icon.png -o /tmp/DenAI.iconset/icon_256x256@2x.png
sips -z 512 512 icon.png -o /tmp/DenAI.iconset/icon_512x512.png
cp icon.png      /tmp/DenAI.iconset/icon_512x512@2x.png
iconutil -c icns /tmp/DenAI.iconset -o assets/icon.icns
```

`sips` e `iconutil` estão disponíveis nativamente no macOS — sem deps extras.
