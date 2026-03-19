# Changelog

All notable changes to DenAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/rodrigogobbo/denai/compare/v0.1.0...v0.2.0
[0.1.1]: https://github.com/rodrigogobbo/denai/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rodrigogobbo/denai/releases/tag/v0.1.0
