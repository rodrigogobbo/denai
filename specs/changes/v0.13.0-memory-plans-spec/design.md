# Design Document

## Overview

### Change Type
new-feature

### Design Goals
1. Adicionar `memory_list` complementando memory_save/memory_search existentes
2. Criar `plans_spec` como sistema de documentos distintos de `plan_create` (execução step-by-step)
3. Manter retrocompatibilidade total com tools existentes

### References
- REQ-1: memory_list Tool
- REQ-2: plans_spec Spec Documents

## System Architecture

### DES-1: memory_list

Adicionar ao `denai/tools/memory.py` um novo spec `MEMORY_LIST_SPEC` e executor `memory_list`. Reutiliza `_get_db()` existente. Query sem filtros retorna as N mais recentes por `created_at DESC`.

A rota `GET /api/memories` ganha parâmetros `?type=` e `?limit=` via FastAPI `Query()`.

### DES-2: plans_spec

Novo módulo `denai/tools/plans_spec.py` com:
- Storage: `~/.denai/plans/<slug>.md` (conteúdo) + `~/.denai/plan_specs.db` (metadados SQLite)
- Trash: `~/.denai/plans/.trash/` para soft delete
- `_slugify()`: normaliza título para slug URL-safe
- `_unique_id()`: garante unicidade consultando o DB

Dispatcher único `plans_spec(args)` com `action` como parâmetro. Nova rota `denai/routes/plans_spec.py`.

### DES-3: Distinção semântica

| Tool | Propósito | Persiste entre sessões |
|---|---|---|
| `plan_create/update` | Execução step-by-step de uma tarefa | Sim |
| `plans_spec` | Documento de referência (RFC, ADR, design) | Sim |
| `todowrite` | Rastreamento em tempo real da sessão | Sim |
