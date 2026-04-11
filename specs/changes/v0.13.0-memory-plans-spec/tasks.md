# Implementation Tasks

## Status: ✅ DONE (mergeado em PR #31, v0.13.0)

- [x] 1. Adicionar `memory_list` em `denai/tools/memory.py`
  - _Implements: DES-1, REQ-1.1, REQ-1.2, REQ-1.3, REQ-1.4, REQ-1.5_

- [x] 2. Atualizar `GET /api/memories` com `?type=` e `?limit=`, retornar `total`
  - _Implements: DES-1, REQ-1.6_

- [x] 3. Criar `denai/tools/plans_spec.py` — CRUD com actions dispatcher
  - _Implements: DES-2, REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4, REQ-2.5_

- [x] 4. Criar `denai/routes/plans_spec.py` — REST endpoints
  - _Implements: DES-2, REQ-2.6_

- [x] 5. Registrar router em `routes/__init__.py`

- [x] 6. Atualizar system prompt com instruções sobre plans_spec vs plan_create

- [x] 7. 39 novos testes (771 total)

- [x] 8. Bump version 0.13.0
