# Implementation Tasks

## Status: ✅ DONE (PR #34, v0.16.0)

- [x] 1. `denai/tools/suggestions.py` — suggest_skill + suggest_plugin com prefixo __SUGGESTION__
  - _Implements: DES-1, REQ-1.1_
- [x] 2. `llm/ollama.py` — _maybe_suggestion_event() intercepta prefixo (serial + paralelo)
  - _Implements: DES-2, REQ-1.2_
- [x] 3. Frontend: card azul com install/dismiss em chat.js e chat.css
  - _Implements: DES-3, REQ-1.3, REQ-1.4_
- [x] 4. PLAN_MODE_TOOLS — suggest tools excluídas
  - _Implements: REQ-1.5_
- [x] 5. System prompt atualizado
  - _Implements: REQ-1.6_
- [x] 6. 18 novos testes (842 total), bump 0.16.0
