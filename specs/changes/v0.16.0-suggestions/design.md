# Design Document

## Overview
### Change Type: new-feature

### DES-1: Prefixo mágico
`denai/tools/suggestions.py` — retorna `"__SUGGESTION__:{json}"`.

### DES-2: Interceptação no SSE
`llm/ollama.py` — `_maybe_suggestion_event(result)` detecta prefixo e emite `{"suggestion": data}`. Aplicado nos dois paths (serial e paralelo).

### DES-3: Frontend
`chat.js` — handler para `event.suggestion` renderiza card azul. `installSuggestion()` e `dismissSuggestion()` em `chat.js`. CSS em `chat.css`.
