# Requirements Document

## Introduction

DenAI v0.13.0 porta dois recursos do Wolf/HubAI Nitro: `memory_list` (listar memórias sem query) e `plans_spec` (spec documents markdown com lifecycle). O sistema de memória existente só tinha save/search; usuários não conseguiam listar o que foi salvo sem saber palavras-chave. O sistema de planos só tinha execução step-by-step; faltava um lugar para documentos de arquitetura e decisões que sobrevivem entre sessões.

## Glossary

| Term | Definition |
|------|------------|
| memory_list | Tool que lista memórias recentes sem query, com filtro por tipo e limite |
| plans_spec | Sistema de spec documents markdown com lifecycle (draft/active/done/archived) |
| slug | Identificador gerado a partir do título (ex: "Minha Feature" → "minha-feature") |
| soft_delete | Remoção que move o arquivo para .trash/ em vez de apagar permanentemente |

## Requirements

### REQ-1: memory_list Tool

**User Story:** Como usuário, quero listar as memórias recentes sem precisar de uma query específica, para revisar o contexto salvo entre sessões.

#### Acceptance Criteria

1.1. THE system SHALL provide a `memory_list` tool that returns the most recent memories without requiring a query parameter. _(Ubiquitous)_

1.2. WHEN `memory_list` is called with a `type` parameter, THE system SHALL filter results to only the specified type (fact/decision/preference/observation). _(Event-driven)_

1.3. WHEN `memory_list` is called with a `limit` parameter, THE system SHALL return at most that many memories, capped at 50. _(Event-driven)_

1.4. THE system SHALL default to returning 20 memories when no limit is specified. _(Ubiquitous)_

1.5. THE system SHALL display the total count as "X de Y memória(s)" to show how many exist vs. how many are shown. _(Ubiquitous)_

1.6. `GET /api/memories` SHALL accept optional `?type=` and `?limit=` query parameters and return a `total` field. _(Ubiquitous)_

### REQ-2: plans_spec Spec Documents

**User Story:** Como desenvolvedor, quero criar documentos de planejamento em markdown com lifecycle, para registrar decisões técnicas e specs que sobrevivam entre sessões.

#### Acceptance Criteria

2.1. THE system SHALL provide a `plans_spec` tool with actions: create, update, get, list, delete. _(Ubiquitous)_

2.2. WHEN a spec is created, THE system SHALL store the content as a markdown file in `~/.denai/plans/<slug>.md` and metadata in SQLite. _(Event-driven)_

2.3. THE system SHALL generate slug IDs from the title (lowercase, sem acentos, hifenizado), garantindo unicidade com sufixo numérico. _(Ubiquitous)_

2.4. WHEN a spec is deleted, THE system SHALL move the file to `~/.denai/plans/.trash/` instead of deleting permanently. _(Event-driven)_

2.5. THE spec lifecycle SHALL support transitions: draft → active → done → archived. _(Ubiquitous)_

2.6. THE system SHALL expose REST endpoints: GET/POST /api/plans-spec, GET/PATCH/DELETE /api/plans-spec/{id}. _(Ubiquitous)_
