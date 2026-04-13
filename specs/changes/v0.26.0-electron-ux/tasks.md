# Implementation Tasks

## Status: ✅ DONE (PR #78, v0.26.0)

- [x] 1.1 `electron/src/main.js` — refazer `checkOllama()` para detectar transições online↔offline
  - `_ollamaOnline` state, `_handleOllamaTransition()`, `_sendNotification()`
  - Poll a cada 10s em vez de one-shot
  - _Implements: DES-1, REQ-1.1, REQ-1.2, REQ-1.5_

- [x] 1.2 `setupAutoUpdate()` — notificação nativa ao detectar update disponível
  - `_sendNotification()` antes do dialog
  - _Implements: REQ-1.3_

- [x] 2.1 `routes/profiles.py` — `GET/POST /api/profiles/active/model`
  - Lê/grava `<profile_dir>/last_model`
  - _Implements: DES-2, REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4_

- [x] 2.2 `models.js` — restaurar modelo do perfil ao carregar, salvar ao trocar
  - `GET /api/profiles/active/model` no `loadModels()`
  - `POST /api/profiles/active/model` no `change` listener
  - _Implements: REQ-2.1, REQ-2.2_

- [x] 3.1 `electron.yml` — step `Generate icon.icns` antes do build arm64
  - `sips` + `iconutil` (nativos no macOS, sem deps)
  - _Implements: DES-3, REQ-3.1, REQ-3.2, REQ-3.3_

- [x] 4. 3 novos testes, bump 0.26.0, PR
