# Changelog

All notable changes to DenAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-03-20

### Added
- **Tool-specific icons & colors** — Each tool has unique emoji + accent color in the UI
  - Visual left border colors per tool type (blue=read, green=write, orange=exec, etc.)
  - Tool metadata map (`TOOL_META`) for consistent styling
- **Think tool inline rendering** — Reasoning scratchpad shows inline with dashed border
  - Always expanded, no collapse — transparent thinking for the user
  - Styled as italic "Raciocínio interno" with violet accent
- **Tool result improvements** — Better UX for tool output
  - Results > 2000 chars are truncated with "mostrar mais" toggle
  - Copy button on every tool result card
  - Results capped at 300px height with scroll
- **Plans UI panel** — Visual plan management in sidebar
  - Collapsible "📋 Planos" section with badge counter
  - Plan list with progress bars (done/total percentage)
  - Click-to-view modal with step status icons
  - Plans API: `GET /api/plans`, `GET /api/plans/{id}`, `DELETE /api/plans/{id}`
- **config.yaml support** — `~/.denai/config.yaml` for persistent configuration
  - Priority chain: CLI args > env vars > config.yaml > defaults
  - All settings supported: model, ollama_url, port, share, max_tool_rounds, max_context
  - `config.example.yaml` template included
  - Graceful fallback on malformed YAML (warning, not crash)
- **Parallel tool execution** — Read-only tools run concurrently via `asyncio.gather`
  - `file_read`, `grep`, `think`, `memory_search`, `rag_search`, `web_search` etc.
  - Write tools (`file_write`, `command_exec`, etc.) stay sequential for safety
  - Smart batching: consecutive parallel-safe tools are grouped automatically
  - Circuit breaker integration — failed tools excluded from parallel batches
- **13 new tests** — Plans routes (6), tool batching (7). Total: 295+

### Changed
- `renderToolCallCard` completely rewritten with per-tool styling
- SSE tool_result handler enhanced with copy/truncation support
- PyYAML added as dependency

## [0.3.0] - 2026-03-20

### Added
- **Core tools** — 7 new tools that transform DenAI from chatbot to assistant
  - `file_read` — Read files with line numbers, offset/limit for large files
  - `file_write` — Write files with auto directory creation
  - `list_files` — List directory contents with glob pattern support
  - `command_exec` — Execute shell commands with security sandbox
  - `memory_save` — Persistent memory across sessions (SQLite)
  - `memory_search` — Search past memories by keywords and type
  - `web_search` — Fetch web URLs with HTML stripping and SSRF protection
- **`file_edit` tool** — Search/replace in files with exact text matching, replace_all option, sandbox-safe
- **`question` tool** — Pause the LLM and ask the user for input (future-based async blocking, 5min timeout)
  - SSE `question` event sent to frontend before blocking
  - API routes: `GET /api/questions/pending`, `POST /api/questions/{id}/answer`
  - Frontend: interactive question cards with option buttons or free-form input
- **Multi-step planning** — LLM can create and track execution plans
  - `plan_create` — Define goal + numbered steps
  - `plan_update` — Mark steps as done/in_progress with results
  - Progress tracking with visual indicators (✅ ⬜ 🔄)
  - System prompt instructs LLM to plan before complex tasks
- **Model management** — Pull and delete models from the UI
  - `POST /api/models/pull` — Download models via SSE streaming progress
  - `DELETE /api/models/{name}` — Remove installed models
  - Consolidated models + ollama status routes into `models.py`
- **RAG local** — BM25-based document search, zero external dependencies
  - Index documents from `~/.denai/documents/` (30+ file formats)
  - Smart text chunking with overlap for large files
  - Bilingual stop words (PT-BR + EN)
  - Auto-inject relevant context into chat prompts
- **RAG tools** — `rag_search`, `rag_index`, `rag_stats` available to the LLM
- **RAG API routes** — Full CRUD for document management
  - `GET /api/rag/stats` — Index statistics
  - `POST /api/rag/index` — Reindex documents
  - `POST /api/rag/search` — Search documents
  - `GET /api/rag/documents` — List documents
  - `POST /api/rag/upload` — Upload document (with extension/size validation)
  - `DELETE /api/rag/documents/{name}` — Remove document
- **Plugin system** — Autodiscovery from `~/.denai/plugins/` (single-file + directory plugins)
- **Plugin API routes** — List and manage plugins via `/api/plugins`
- **51 new tests** — RAG unit tests, API integration tests, tool tests, prompt tests (237 total)
- **Dynamic context management** — Auto-scales context window 8k→32k→64k based on conversation length
  - Token estimation for messages (model-agnostic, ~4 chars/token heuristic)
  - Auto-summarization when context exceeds 60% capacity (compresses old messages)
  - Configurable via `DENAI_MAX_CONTEXT` (default: 65536)
- **Extended tool rounds** — Up to 25 tool call rounds per message (was 5)
  - Configurable via `DENAI_MAX_TOOL_ROUNDS` (default: 25)
  - Enables long multi-step sessions (file editing, planning, research workflows)
- **New env vars** — `DENAI_MAX_TOOL_ROUNDS`, `DENAI_MAX_CONTEXT` for power users
- **12 new tests** — Context management module (249 total)
- **Resilience improvements** — Error recovery, retry, circuit breaker
  - Retry com backoff para erros transientes do Ollama (429, 500-504)
  - Recovery hints injetados quando tools falham (ex: "use file_read antes de file_edit")
  - Circuit breaker: tool que falha 3x consecutivas é bloqueada automaticamente
- **System prompt reforçado** — Guias operacionais para modelos locais
  - Regra "read before edit" — SEMPRE ler arquivo antes de editar
  - Guidance de error recovery — parar após 2 falhas e perguntar ao usuário
  - Instrução para usar `think` antes de ações complexas
- **Planning persistido em SQLite** — Planos sobrevivem restart do servidor
- **File backup automático** — `file_write` e `file_edit` criam backup em `~/.denai/backups/`
- **`grep` tool** — Busca regex em arquivos com filtro por extensão, skip de diretórios comuns
- **`think` tool** — Scratchpad para raciocínio sem side-effects (melhora qualidade em modelos menores)
- **`web_search` com DuckDuckGo real** — Pesquisa por query (não só fetch de URL), retrocompatível
- **33 new tests** — grep, think, planning SQLite, file backup, recovery hints, circuit breaker (282 total)

## [0.2.0] - 2026-03-19

### Added
- **First-boot wizard** — 4-step guided setup: Welcome → Install Ollama → Pull Model → Ready
- **Dark/Light mode** — Toggle with `Ctrl+T`, persists in localStorage
- **Export conversations** — Download as JSON or Markdown via header button
- **Search conversations** — Search bar in sidebar, queries titles and message content
- **Ollama status badge** — Live indicator in header (polling every 15s)
- **Error handling** — Contextual error banners with retry button (classifies network, auth, rate limit, server errors)
- **Tool calling feedback** — CSS spinner, progress bar animation, completion flash, multi-tool counter
- **PyPI publish workflow** — GitHub Actions with trusted OIDC publishing
- **MANIFEST.in** — Ensures static files in sdist
- **23 integration tests** — Export, search, Ollama status (httpx AsyncClient + ASGI)

### Changed
- Migrated FastAPI startup from `on_event` to `lifespan` (eliminates deprecation warnings)
- Enriched pyproject.toml classifiers and metadata
- Added PyPI badge to README

## [0.1.1] - 2026-03-19

### Fixed
- DB connection leak — async context manager (`get_db()`)
- CDN dependencies bundled locally (marked.js, highlight.js, github-dark-dimmed.css)
- README badges pointing to correct repo
- Windows path separator in sandbox security check
- StaticFiles mount for vendor directory

### Added
- GitHub Actions CI (Ubuntu + Windows, Python 3.10/3.12)
- `[dev]` extras in pyproject.toml
- `requirements.txt` fallback for pip users

## [0.1.0] - 2026-03-19

### Added
- Initial release
- Modular Python package (33 files, ~2000 LOC)
- FastAPI web server with SSE streaming
- Ollama integration (chat, model switching, pull)
- Persistent memory (SQLite)
- Built-in tools: file I/O, shell commands, web search, memory
- Security: API key auth, rate limiting, command filtering, path sandboxing
- Web UI: chat interface, conversation management, code highlighting
- Share mode (`--compartilhar`) for local network access
- Windows installer scripts (BAT/PowerShell)
- 84 unit tests

[0.4.0]: https://github.com/rodrigogobbo/denai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/rodrigogobbo/denai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rodrigogobbo/denai/compare/v0.1.0...v0.2.0
[0.1.1]: https://github.com/rodrigogobbo/denai/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rodrigogobbo/denai/releases/tag/v0.1.0
