# Design Document

## Overview
### Change Type: new-feature
### Design Goals
1. Substituição total da lista a cada chamada elimina dessincronias de estado
2. IDs explícitos permitem referência direta nos prompts
3. Prioridade visível via ícones (🔵🟡🔴)

### DES-1: Storage
SQLite em `~/.denai/todos.db`. `DELETE todos` + INSERT a cada chamada — operação atômica.

### DES-2: Distinção do plan_create
- `todowrite`: substitui tudo, IDs, prioridade → rastreamento em tempo real
- `plan_create`: UPSERT incremental → planos longos multi-sessão
