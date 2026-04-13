# Implementation Tasks

## Status: ✅ DONE

## Fase 1: profile_manager

- [x] 1.1 Criar `denai/profile_manager.py`
  - get_active_profile() — lê ~/.denai/active_profile, default='default'
  - set_active_profile(name) — grava ~/.denai/active_profile
  - get_profile_dir(name) — 'default' → ~/.denai, outros → ~/.denai/profiles/<name>/
  - list_profiles() — lê ~/.denai/profiles/ + adiciona 'default'
  - create_profile(name) — mkdir ~/.denai/profiles/<name>/
  - delete_profile(name) — rmdir se não for 'default' e não for ativo
  - _Implements: DES-2, REQ-1.1, REQ-1.2, REQ-1.3, REQ-1.4_

## Fase 2: config.py

- [x] 2.1 Atualizar DATA_DIR e DB_PATH para usar get_profile_dir() no boot
  - _Implements: DES-3, REQ-1.2, REQ-1.3_

## Fase 3: CLI

- [x] 3.1 Adicionar --profile ao argparse em __main__.py
  - _Implements: DES-4, REQ-2.1_

## Fase 4: API

- [x] 4.1 Criar `denai/routes/profiles.py`
  - GET /api/profiles — list_profiles()
  - POST /api/profiles — create_profile(name)
  - POST /api/profiles/{name}/activate — set_active_profile + {reload: true}
  - DELETE /api/profiles/{name} — delete_profile(name)
  - GET /api/profiles/active — get_active_profile()
  - _Implements: DES-5, REQ-2.2–2.6_

## Fase 5: Frontend

- [x] 5.1 Badge de perfil no header (ui.html)
  - _Implements: DES-6, REQ-3.1_

- [x] 5.2 Dropdown de perfis com troca e criação inline (ui.js + CSS)
  - _Implements: DES-6, REQ-3.2, REQ-3.3, REQ-3.4_

## Fase 6: Testes

- [x] 6.1 Testes para profile_manager e rotas /api/profiles
