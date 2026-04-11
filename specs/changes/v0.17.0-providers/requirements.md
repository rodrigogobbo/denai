# Requirements Document

## Introduction

Providers adicionados via UI eram efêmeros (perdidos ao reiniciar). A UI usava `prompt()` nativo sem feedback. Este change adiciona persistência, CRUD completo, 8 templates pré-configurados, teste de conexão e proteção SSRF.

## Requirements

### REQ-1: Persistência
1.1. Providers adicionados via UI SHALL be persisted in `~/.denai/providers.yaml` (chmod 600). _(Ubiquitous)_
1.2. Providers SHALL be loaded from the store on server boot. _(Ubiquitous)_
1.3. `GET /api/providers` SHALL never expose API keys (masked as `sk-ab***99`). _(Ubiquitous)_

### REQ-2: Templates
2.1. THE system SHALL provide 8 pre-configured templates: OpenAI, Anthropic, Gemini, OpenRouter, Groq, LM Studio, LocalAI, Ollama remote. _(Ubiquitous)_
2.2. `GET /api/providers/templates` SHALL return templates with label, description, base_url, requires_key, default_models. _(Ubiquitous)_

### REQ-3: CRUD + Test
3.1. `POST /api/providers` SHALL add/update provider and persist. _(Ubiquitous)_
3.2. `DELETE /api/providers/{name}` SHALL remove provider (Ollama default protected). _(Ubiquitous)_
3.3. `POST /api/providers/test` SHALL test connection returning latency_ms and models list. _(Event-driven)_

### REQ-4: SSRF Protection
4.1. `POST /api/providers/test` SHALL validate the URL against a blocklist before any HTTP request. _(Ubiquitous)_
4.2. THE blocklist SHALL include: 169.254.0.0/16, loopback (in production), reserved RFC ranges. _(Ubiquitous)_
4.3. DNS resolution SHALL be checked against the same blocklist (DNS rebinding prevention). _(Ubiquitous)_

### REQ-5: UI Modal
5.1. A ⚙ button in the sidebar SHALL open a provider management modal. _(Ubiquitous)_
5.2. THE modal SHALL allow: add (with template dropdown), edit, remove, test connection. _(Ubiquitous)_
