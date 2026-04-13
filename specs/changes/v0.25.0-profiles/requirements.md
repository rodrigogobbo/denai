# Requirements Document

## Introduction

Usuários que usam o DenAI para múltiplos contextos (trabalho, pessoal, projetos diferentes) compartilham todas as memórias, providers e configurações em um único diretório `~/.denai/`. Isso gera ruído: memórias de trabalho aparecem em conversas pessoais, providers de API paga ficam ativos quando não são necessários.

Perfis resolvem isso: cada perfil é um namespace independente com `denai.db`, `config.yaml`, `providers.yaml` e memórias próprios. O perfil padrão é `default` (comportamento atual, retrocompatível).

## Glossary

| Term | Definition |
|---|---|
| profile | Namespace isolado com DB, config e memórias próprios |
| active_profile | Perfil atualmente selecionado na sessão |
| profile_dir | `~/.denai/profiles/<name>/` — dados do perfil |
| default profile | Perfil `default` — compatível com dados existentes em `~/.denai/` |

## Requirements

### REQ-1: Estrutura de perfis

1.1. THE system SHALL support named profiles stored at `~/.denai/profiles/<name>/`. _(Ubiquitous)_

1.2. THE default profile SHALL use the existing `~/.denai/` data directly — zero migration required for existing users. _(Ubiquitous)_

1.3. WHEN a non-default profile is active, THE system SHALL use `~/.denai/profiles/<name>/denai.db`, `config.yaml`, `providers.yaml` and `memories`. _(Ubiquitous)_

1.4. THE active profile SHALL be stored in `~/.denai/active_profile` (plain text file with profile name). _(Ubiquitous)_

### REQ-2: CLI e API

2.1. `python -m denai --profile <name>` SHALL activate the named profile for that session. _(Event-driven)_

2.2. `GET /api/profiles` SHALL list available profiles with name and creation date. _(Ubiquitous)_

2.3. `POST /api/profiles` SHALL create a new profile (body: `{name}`). _(Event-driven)_

2.4. `POST /api/profiles/<name>/activate` SHALL switch to the named profile (requires restart or session reload). _(Event-driven)_

2.5. `DELETE /api/profiles/<name>` SHALL delete a non-active profile and its data. _(Event-driven)_

2.6. `GET /api/profiles/active` SHALL return the current active profile name. _(Ubiquitous)_

### REQ-3: UI — seletor no header

3.1. THE header SHALL show the active profile name next to the model label. _(Ubiquitous)_

3.2. Clicking the profile name SHALL open a dropdown to switch profiles or create new ones. _(Event-driven)_

3.3. WHEN switching profiles, THE system SHALL reload the page (new session with new profile's data). _(Event-driven)_

3.4. THE profile selector SHALL show a `+` button to create a new profile inline. _(Ubiquitous)_

### REQ-4: Isolamento de dados

4.1. Conversations SHALL be isolated per profile. _(Ubiquitous)_

4.2. Memories SHALL be isolated per profile. _(Ubiquitous)_

4.3. Providers SHALL be isolated per profile (each profile has its own `providers.yaml`). _(Ubiquitous)_

4.4. Skills and personas are shared across profiles (they live in `~/.denai/skills/` and `~/.denai/personas/`). _(Ubiquitous)_

4.5. The RAG index is shared across profiles. _(Ubiquitous)_
