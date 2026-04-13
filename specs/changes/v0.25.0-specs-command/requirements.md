# Requirements Document

## Introduction

Desenvolvedores que usam o DenAI com `/context <caminho>` para trabalhar em repositórios frequentemente querem revisitar as specs de mudança documentadas (`specs/changes/`) sem sair do chat. O comando `/specs` lista as specs do projeto atual e permite abrir o conteúdo de uma spec diretamente na conversa.

É diferente de `plans_spec` (docs criados pelo LLM em `~/.denai/plans/`) — o `/specs` lista as specs SDS commitadas no repositório ativo via `/context`.

## Glossary

| Term | Definition |
|---|---|
| spec_file | Arquivo `requirements.md`, `design.md` ou `tasks.md` em `specs/changes/<slug>/` |
| specs_dir | Diretório `specs/changes/` na raiz do projeto ativo via `/context` |
| context_path | Path do projeto indexado pela sessão atual via `/context` |

## Requirements

### REQ-1: Comando /specs

1.1. WHEN the user types `/specs` in the chat and a context is active, THE system SHALL list all spec directories found in `specs/changes/` of the active project. _(Event-driven)_

1.2. WHEN the user types `/specs <slug>`, THE system SHALL display the contents of `specs/changes/<slug>/` (requirements.md + design.md + tasks.md). _(Event-driven)_

1.3. IF no context is active, THE system SHALL reply: "Nenhum repositório ativo. Use `/context <caminho>` primeiro." _(Unwanted behavior)_

1.4. IF `specs/changes/` does not exist in the project, THE system SHALL reply informing and suggest running `/context` on a DenAI project. _(Unwanted behavior)_

1.5. THE `/specs` command SHALL appear in `GET /api/commands`. _(Ubiquitous)_

### REQ-2: Conteúdo exibido

2.1. `/specs` (sem argumento) SHALL show a numbered list: `[1] v0.12.0-agentic-workflows`, `[2] v0.13.0-memory-plans-spec`, etc. _(Ubiquitous)_

2.2. `/specs <slug>` SHALL render the markdown content of the three spec files concatenados com separadores. _(Ubiquitous)_

2.3. THE task checkboxes in `tasks.md` SHALL be preserved (`[x]` e `[ ]`). _(Ubiquitous)_

### REQ-3: Backend

3.1. `POST /api/specs/list` SHALL accept `{conversation_id}` and return the list of specs from the active context. _(Ubiquitous)_

3.2. `POST /api/specs/read` SHALL accept `{conversation_id, slug}` and return the concatenated content. _(Ubiquitous)_
