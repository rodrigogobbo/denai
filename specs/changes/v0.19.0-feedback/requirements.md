# Requirements Document

## Introduction

Usuários não tinham forma de reportar bugs ou sugerir melhorias sem sair do DenAI e criar conta no GitHub. Este change adiciona feedback in-app que abre GitHub Issues via API ou salva localmente como fallback.

## Requirements

1.1. `POST /api/feedback` SHALL accept `type` (bug/improvement), `title` (≥3 chars), `description` (≥10 chars), `include_context` (bool). _(Ubiquitous)_
1.2. IF `feedback.github_token` is configured, THE system SHALL open a GitHub Issue via REST API with automatic labels (bug+user-feedback or enhancement+user-feedback). _(Event-driven)_
1.3. IF no token is configured, THE system SHALL save feedback locally in `~/.denai/feedback/<timestamp>_<type>.json`. _(Event-driven)_
1.4. WHEN `include_context` is true, THE system SHALL collect: DenAI version, OS, Python, Ollama status, recent logs. _(Event-driven)_
1.5. Logs SHALL only be included for bug reports (not improvements). _(Ubiquitous)_
1.6. `GET /api/feedback/config` SHALL return method (github/local) and has_token. _(Ubiquitous)_
1.7. A 💬 button SHALL be visible in the header, with Ctrl+Shift+F shortcut. _(Ubiquitous)_
1.8. THE modal SHALL have two tabs: 🐛 Bug and 💡 Improvement. _(Ubiquitous)_
1.9. ON success, THE modal SHALL show the GitHub issue link when available. _(Event-driven)_
