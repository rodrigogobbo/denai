# Requirements Document

## Introduction

Desenvolvedores que usam o DenAI para trabalhar em um repositório precisam repetidamente explicar o contexto do projeto ao LLM: "é um projeto FastAPI em Python, usa SQLite, tem esse estrutura de diretórios...". O comando `/context <caminho>` resolve isso: indexa o projeto uma vez e mantém o contexto ativo na sessão.

O RAG (BM25) já existe e funciona via `~/.denai/documents/`. O `/context` é uma abstração de nível mais alto que:
1. Copia/indexa temporariamente arquivos de um diretório externo
2. Injeta um resumo do projeto no system prompt da sessão
3. Responde perguntas sobre o código usando busca BM25

## Glossary

| Term | Definition |
|------|------------|
| context_session | Estado da sessão com diretório indexado e metadados do projeto |
| project_summary | Texto gerado pelo `analyze_project()` existente, injetado no system prompt |
| context_index | Índice BM25 temporário dos arquivos do diretório (separado de `~/.denai/documents/`) |
| /context | Comando de chat que ativa o modo de análise de repositório |

## Requirements

### REQ-1: Comando /context

1.1. WHEN the user types `/context <path>` in the chat, THE system SHALL index the directory at `<path>` and activate repository context mode for the current session. _(Event-driven)_

1.2. THE command SHALL validate: path exists, path is within sandbox, path is a directory. _(Ubiquitous)_

1.3. WHEN activated, THE system SHALL display a confirmation: "✅ Contexto ativado: <n> arquivos indexados em <project>". _(Event-driven)_

1.4. WHILE context mode is active, THE system SHALL prepend a project summary to every LLM request (similar to how `plans_spec` uses system prompt injection). _(State-driven)_

1.5. THE command `/context off` SHALL deactivate context mode and clear the temporary index. _(Event-driven)_

1.6. THE command `/context` (without path) SHALL show the current active context or "nenhum contexto ativo". _(Event-driven)_

### REQ-2: Indexação

2.1. THE indexer SHALL respect `.gitignore` patterns if present in the directory. _(Ubiquitous)_

2.2. THE indexer SHALL skip: `node_modules/`, `.git/`, `__pycache__/`, `*.pyc`, `dist/`, `build/`, `*.lock`, binary files. _(Ubiquitous)_

2.3. THE indexer SHALL limit to 500 files and 50MB total to prevent hangs. _(Ubiquitous)_

2.4. THE index SHALL be stored in memory (not persisted) — cleared on session end or `/context off`. _(Ubiquitous)_

2.5. WHEN the user asks about the codebase, THE system SHALL use BM25 search on the context index to find relevant files before answering. _(Event-driven)_

### REQ-3: Project summary injection

3.1. THE system SHALL use the existing `analyze_project()` function to generate a project summary. _(Ubiquitous)_

3.2. THE summary SHALL be injected as a prefix in the system prompt while context mode is active. _(Ubiquitous)_

3.3. THE summary SHALL include: project name, languages, frameworks, directory tree (depth 2), file count. _(Ubiquitous)_

### REQ-4: UX

4.1. THE chat input SHALL show a badge "📁 <project>" when context mode is active. _(Ubiquitous)_

4.2. THE `/context` command SHALL appear in the commands list (`GET /api/commands`). _(Ubiquitous)_

4.3. IF indexing takes > 2s, THE system SHALL show a loading indicator. _(Event-driven)_
