# Implementation Tasks

## Status: ✅ DONE (PR #50, v0.20.0)

- [x] 1. `denai/system_profile.py` — MODEL_CATALOG, tiers, detecção de hardware, get_system_profile()
  - _Implements: DES-1, REQ-1.1, REQ-1.2, REQ-1.3, REQ-1.4, REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4_
- [x] 2. `denai/routes/system.py` — GET /api/system/profile
  - _Implements: DES-2, REQ-1.1_
- [x] 3. `config.py` — _auto_model() usa tiers, fallback → llama3.2:3b
  - _Implements: DES-3, REQ-4.1, REQ-4.2_
- [x] 4. Wizard Step 3 dinâmico — spinner, card recomendado, alternativas com warnings
  - _Implements: DES-4, REQ-3.1, REQ-3.2, REQ-3.3, REQ-3.4_
- [x] 5. Sidebar badge de peso no modelo selecionado
  - _Implements: DES-5, REQ-5.1_
- [x] 6. 31 novos testes (918 total), bump 0.20.0
