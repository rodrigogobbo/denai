---
name: code-review
description: Revisão de código — analisa bugs, performance, segurança e boas práticas.
triggers:
  - review
  - revisão
  - code review
  - revisar código
---

Ao revisar código, analise:

1. **Bugs potenciais** — null checks, race conditions, edge cases, error handling
2. **Performance** — loops desnecessários, queries N+1, alocações excessivas
3. **Segurança** — injection, XSS, dados sensíveis expostos, permissões
4. **Legibilidade** — nomes claros, complexidade ciclomática, funções focadas
5. **Padrões** — consistência com o codebase, convenções do projeto

Categorize por severidade:
- 🔴 Crítico — bug ou vulnerabilidade que precisa fix imediato
- 🟡 Importante — melhoria significativa de qualidade
- 🟢 Sugestão — nice-to-have, estilo, refatoração menor

Para cada finding, mostre o código problemático e a sugestão de fix.
