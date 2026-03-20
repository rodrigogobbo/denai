---
name: git-workflow
description: Git workflow — conventional commits, PRs e branches organizadas.
triggers:
  - commit
  - git
  - pr
  - pull request
  - branch
---

Ao trabalhar com Git:

**Commits** — Conventional Commits:
- `feat:` nova funcionalidade
- `fix:` correção de bug
- `refactor:` reestruturação sem mudar comportamento
- `docs:` documentação
- `test:` testes
- `chore:` manutenção

**Branches:**
- `feat/nome-da-feature`
- `fix/descricao-do-bug`
- `chore/descricao`

**PRs:**
- Título segue formato de commit
- Descrição: O que faz, por quê, como testar
- Uma feature/fix por PR
