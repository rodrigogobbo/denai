# Requirements — v0.26.0 Electron UX

## REQ-1: Notificações nativas

1.1. WHEN Ollama becomes unavailable after being online, THE app SHALL send an OS notification: "Ollama offline — models unavailable". _(Event-driven)_
1.2. WHEN Ollama comes back online after being offline, THE app SHALL send: "Ollama online — ready to chat". _(Event-driven)_
1.3. WHEN a new update is available, THE app SHALL send a notification instead of only showing a dialog. _(Event-driven)_
1.4. Notifications SHALL use `new Notification()` from Electron, not the web Notification API. _(Ubiquitous)_
1.5. THE polling interval for Ollama status SHALL be 10s (health check already exists at 5s — share it). _(Ubiquitous)_

## REQ-2: Modelo por perfil

2.1. WHEN a profile is activated, THE app SHALL restore the last model used in that profile. _(Event-driven)_
2.2. WHEN the user selects a model, THE app SHALL persist it to `~/.denai/profiles/<name>/last_model` (or `~/.denai/last_model` for default). _(Event-driven)_
2.3. `GET /api/profiles/active/model` SHALL return the last model for the current profile. _(Ubiquitous)_
2.4. `POST /api/profiles/active/model` SHALL save the model for the current profile. _(Event-driven)_

## REQ-3: icon.icns real

3.1. THE macOS app icon SHALL be a valid `.icns` file with resolutions: 16, 32, 64, 128, 256, 512, 1024. _(Ubiquitous)_
3.2. THE icon SHALL be generated from `electron/assets/icon.png` (512×512) using `iconutil` or `sips`. _(Ubiquitous)_
3.3. THE CI SHALL generate the `.icns` before running `npm run make` on macOS runners. _(Ubiquitous)_
