# Requirements Document

## Introduction

`todowrite` porta o modelo de todo list do Wolf/HubAI Nitro. O sistema `plan_create/update` existente opera incrementalmente — cria um plano e atualiza step a step, o que causa dessincronias quando o LLM perde o estado. `todowrite` substitui a lista inteira a cada chamada, com IDs explícitos e prioridade.

## Requirements

### REQ-1: todowrite Tool

1.1. THE system SHALL provide a `todowrite` tool that **replaces the entire todo list** on each call. _(Ubiquitous)_
1.2. EACH todo item SHALL have: `id` (string, unique), `content` (string), `status` (pending/in_progress/completed), `priority` (low/medium/high, default medium). _(Ubiquitous)_
1.3. THE system SHALL reject duplicate IDs, missing `id`, missing `content`, or invalid `status`. _(Unwanted behavior)_
1.4. THE system SHALL provide a `todoread` tool that returns the current list without modifying it. _(Ubiquitous)_
1.5. `todoread` SHALL be available in Plan mode (read-only). _(Ubiquitous)_
1.6. THE system SHALL expose GET/PUT/DELETE /api/todos. _(Ubiquitous)_
1.7. THE system prompt SHALL distinguish: todowrite (sessão atual) vs plan_create (sessões longas) vs plans_spec (documentação). _(Ubiquitous)_
