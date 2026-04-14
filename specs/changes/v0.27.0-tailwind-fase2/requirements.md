# Requirements — Tailwind Fase 2: chat.css + layout.css

## REQ-1: Extrair padrões repetidos para utilities.css
- REQ-1.1: Identificar blocos CSS repetidos 5+ vezes em `chat.css` e `layout.css`
- REQ-1.2: Criar classes compostas no `utilities.css` com `@apply` para cada padrão
- REQ-1.3: Substituir as ocorrências inline pelas classes compostas nos arquivos de origem

## REQ-2: Metas de redução
- REQ-2.1: `chat.css` deve reduzir de 616 para menos de 450 linhas (≥27%)
- REQ-2.2: `layout.css` deve reduzir de 860 para menos de 650 linhas (≥24%)
- REQ-2.3: `utilities.css` pode crescer para até 200 linhas

## REQ-3: Sem regressão visual
- REQ-3.1: Build Vite deve passar sem erros
- REQ-3.2: Nenhuma classe CSS existente deve ser removida — apenas consolidada
- REQ-3.3: Variáveis CSS (`var(--*)`) devem ser preservadas, não substituídas por valores hardcoded
