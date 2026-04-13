# Implementation Tasks

## Status: ✅ DONE

## Feature 1: Múltiplos Perfis

- [x] 1.1 Criar `denai/profile_manager.py` — get/set/list/create/delete profiles
  - _Implements: DES-2, REQ-1.1, REQ-1.2, REQ-1.3, REQ-1.4_

- [x] 1.2 Atualizar `denai/config.py` — DATA_DIR e DB_PATH dinâmicos via profile_manager
  - _Implements: DES-3, REQ-1.2, REQ-1.3_

- [x] 1.3 Atualizar `denai/__main__.py` — argumento --profile
  - _Implements: DES-4, REQ-2.1_

- [x] 1.4 Criar `denai/routes/profiles.py` — CRUD de perfis
  - _Implements: DES-5, REQ-2.2, REQ-2.3, REQ-2.4, REQ-2.5, REQ-2.6_

- [x] 1.5 Frontend: seletor de perfil no header (ui.html + ui.js + CSS)
  - _Implements: DES-6, REQ-3.1, REQ-3.2, REQ-3.3, REQ-3.4_

- [x] 1.6 Testes para profile_manager e rotas

## Feature 2: Comando /specs

- [x] 2.1 Criar `denai/routes/specs.py` — POST /api/specs/list + /api/specs/read
  - _Implements: DES-1, REQ-3.1, REQ-3.2_

- [x] 2.2 Frontend: interceptar /specs no chat.js
  - _Implements: DES-2, DES-3, DES-4, REQ-1.1, REQ-1.2, REQ-1.3_

- [x] 2.3 Testes para as rotas specs

## Fase final

- [x] 3.1 Bump 0.25.0, CHANGELOG, PR
