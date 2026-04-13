# Implementation Tasks

## Status: 🔄 IN PROGRESS

## Feature 1: Tailwind + Vite

- [ ] 1.1 Criar `frontend/package.json` com Tailwind v3 + Vite
  - _Implements: DES-2, REQ-1.1_

- [ ] 1.2 Criar `frontend/tailwind.config.js` com design tokens do DenAI
  - _Implements: DES-3, REQ-2.1, REQ-2.2_

- [ ] 1.3 Criar `frontend/vite.config.js`
  - _Implements: DES-1, REQ-1.2_

- [ ] 1.4 Criar `frontend/src/input.css` com imports
  - _Implements: DES-4, REQ-3.1, REQ-3.2_

- [ ] 1.5 Mover CSS variables e animations para `frontend/src/custom/`
  - _Implements: DES-5, REQ-3.3, REQ-3.4_

- [ ] 1.6 Migrar classes duplicadas dos 5 CSS para `@apply` em `frontend/src/custom/`
  - _Implements: DES-5, REQ-3.3_

- [ ] 1.7 Build → gerar `denai/static/css/tailwind.css` e commitar
  - _Implements: DES-6, REQ-1.4_

- [ ] 1.8 Atualizar `ui.html` — remover 5 links CSS, adicionar 1 link `tailwind.css`
  - _Implements: DES-6, REQ-1.4_

- [ ] 1.9 Documentar em `frontend/README.md`
  - _Implements: REQ-4.2_

## Feature 2: /context command

- [ ] 2.1 Criar `denai/context_store.py` — estado em memória + indexação
  - _Implements: DES-1, DES-2, REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4_

- [ ] 2.2 Criar `denai/routes/context.py` — POST /api/context/activate, DELETE /api/context/{conv_id}
  - _Implements: DES-5, REQ-1.1, REQ-1.2, REQ-1.3, REQ-1.5_

- [ ] 2.3 Atualizar `llm/ollama.py` — injetar project summary quando contexto ativo
  - _Implements: DES-3, REQ-1.4, REQ-3.1, REQ-3.2, REQ-3.3_

- [ ] 2.4 Atualizar `tools/rag_search.py` — usar índice da sessão quando ativo
  - _Implements: DES-4, REQ-2.5_

- [ ] 2.5 Frontend: interceptar `/context <path>` no chat
  - _Implements: DES-6, REQ-1.1_

- [ ] 2.6 Frontend: badge no input quando contexto ativo
  - _Implements: DES-7, REQ-4.1_

- [ ] 2.7 Testes para context_store e rota

- [ ] 2.8 Bump 0.23.0, PR
