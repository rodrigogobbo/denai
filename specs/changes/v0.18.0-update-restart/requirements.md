# Requirements Document

## Introduction

O update existente instalava em background sem feedback e exigia reinicialização manual. Este change transforma o install em SSE streaming linha-a-linha e adiciona restart automático com reconexão inteligente. Também adiciona pipeline de auto-release no CI.

## Requirements

### REQ-1: Streaming Install
1.1. `POST /api/update/install` SHALL stream pip output line-by-line via SSE with events: `progress`, `success`, `error`. _(Event-driven)_
1.2. ON success, THE system SHALL call `pip show denai` to get the installed version. _(Event-driven)_

### REQ-2: Auto-restart
2.1. `POST /api/update/restart` SHALL start a new instance with `subprocess.Popen([sys.executable, "-m", "denai"] + argv[1:])` and exit after 1s. _(Event-driven)_
2.2. A `_restart_scheduled` flag SHALL prevent double restart. _(Ubiquitous)_
2.3. THE frontend SHALL poll `GET /api/health` after restart and reload when server responds. _(Event-driven)_

### REQ-3: Auto-release Pipeline
3.1. ON push to main, AFTER test + lint pass, THE CI SHALL read VERSION from `denai/version.py`. _(Event-driven)_
3.2. IF no tag `v{VERSION}` exists, THE CI SHALL create tag, GitHub Release (with CHANGELOG notes) and publish to PyPI via trusted publishing. _(Event-driven)_
3.3. IF tag already exists, THE CI SHALL skip silently (idempotent). _(Ubiquitous)_

### REQ-4: Frontend Modal
4.1. THE update modal SHALL show current → new version with real-time pip log. _(Ubiquitous)_
4.2. AFTER success, THE modal SHALL show "Reiniciar agora" and "Reiniciar depois" buttons. _(Ubiquitous)_
4.3. THE update check SHALL run every 6h (in addition to startup check). _(Ubiquitous)_
