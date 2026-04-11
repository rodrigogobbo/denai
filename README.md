# 🐺 DenAI

**Your private AI den.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/denai.svg)](https://pypi.org/project/denai/)
[![GitHub stars](https://img.shields.io/github/stars/rodrigogobbo/denai?style=social)](https://github.com/rodrigogobbo/denai)
[![Tests](https://github.com/rodrigogobbo/denai/actions/workflows/ci.yml/badge.svg)](https://github.com/rodrigogobbo/denai/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/rodrigogobbo/denai/graph/badge.svg)](https://codecov.io/gh/rodrigogobbo/denai)

A fully local AI assistant with tools, memory, and **zero cloud dependency**. Chat with LLMs on your machine — your data never leaves your computer.

---

## ✨ Features

- 🔒 **100% Private** — Everything runs locally. No data leaves your machine. Ever.
- 🧠 **Persistent Memory** — Remembers context across conversations (SQLite)
- 🛠️ **26 Built-in Tools** — File I/O, grep, web search, git, planning, sub-agents and more
- 🌐 **Web UI** — Clean chat interface at `localhost:4078`
- 🔄 **Model Switching** — Ollama + OpenAI, Anthropic, Gemini, Groq, LM Studio and more
- 🤖 **Agentic Workflows** — Autonomous multi-step execution with checkpoints
- 🤝 **Sub-agents** — Delegate to specialized agents (security, reviewer, writer, data)
- 💡 **Smart Model Selection** — Auto-detects your hardware and recommends the best model
- 🔌 **MCP Support** — Connect external tools via Model Context Protocol
- 🖥️ **Desktop App** — Native installer (.exe/.dmg/.zip), no Python required
- 🔁 **Auto Update** — Streaming install progress + one-click restart
- 💬 **In-app Feedback** — Report bugs and suggestions without leaving DenAI
- 🚀 **Auto Release** — Every version bump triggers CI → GitHub Release → PyPI
- 🌍 **Offline First** — Works without internet after initial setup

---

## 🚀 Quickstart

### Option A — Desktop installer (recommended for non-developers)

Download the installer for your platform from the [latest release](https://github.com/rodrigogobbo/denai/releases/latest):

| Platform | File |
|---|---|
| Windows | `DenAI-*.Setup.exe` |
| macOS | `DenAI.dmg` |
| Linux | `DenAI-linux-x64-*.zip` |

The app manages Python automatically via `uv` — no setup required.

### Option B — pip

```bash
# 1. Install Ollama — https://ollama.com/download
# 2. Pull a model
ollama pull llama3.2:3b

# 3. Install and run DenAI
pip install denai
python -m denai
```

Open **http://localhost:4078** — that's it! 🎉

> 💡 DenAI auto-detects your RAM and recommends the best model on first run.

---

## 🏗️ Architecture

```
Browser (localhost:4078)
        │ HTTP / SSE
DenAI Server (FastAPI + uvicorn)
  ├── 26 Tools (file, git, web, memory, planning, sub-agents...)
  ├── SQLite (conversations, memory, plans, todos)
  └── Ollama API (:11434) — or any OpenAI-compatible provider
```

The `electron/` shell wraps the Python server in a native desktop app. The PyPI package works standalone without Electron.

---

## 📚 Documentation

| Document | Description |
|---|---|
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | System requirements, models, Docker, uninstall |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Share mode, MCP, security, config.yaml |
| [docs/TOOLS.md](docs/TOOLS.md) | All 26 tools with parameters and examples |
| [docs/PROVIDERS.md](docs/PROVIDERS.md) | OpenAI, Anthropic, Gemini, Groq, LM Studio setup |
| [docs/PERSONAS.md](docs/PERSONAS.md) | Sub-agents and custom personas |
| [docs/SECURITY.md](docs/SECURITY.md) | Sandbox, SSRF protection, auth, OWASP |
| [docs/API.md](docs/API.md) | Full REST API reference |
| [docs/GUIA-COMPLETO.md](docs/GUIA-COMPLETO.md) | Complete guide for beginners (PT-BR) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup, tests, PR workflow |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## 🗂️ Project Structure

```
denai/                    ← Python package
  routes/                 ← FastAPI routers (26 endpoints)
  tools/                  ← 26 auto-discovered tools
  llm/                    ← Ollama + provider adapters
  static/                 ← Web UI (HTML/CSS/JS)
  security/               ← Sandbox, auth, SSRF validation
electron/                 ← Desktop app (Electron + uv)
specs/changes/            ← SDS specs per version
tests/                    ← 918 tests
docs/                     ← Documentation
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, coding standards and PR workflow.

```bash
git clone https://github.com/rodrigogobbo/denai.git
cd denai
pip install -e ".[dev]"
pytest
```

---

## 📄 License

MIT — [rodrigogobbo/denai](https://github.com/rodrigogobbo/denai)
