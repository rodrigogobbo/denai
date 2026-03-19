# Changelog

All notable changes to DenAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **51 new tests** — RAG unit tests, API integration tests, tool tests, prompt tests (227 total)

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

[0.3.0]: https://github.com/rodrigogobbo/denai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rodrigogobbo/denai/compare/v0.1.0...v0.2.0
[0.1.1]: https://github.com/rodrigogobbo/denai/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rodrigogobbo/denai/releases/tag/v0.1.0
