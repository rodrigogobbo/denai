# 🐺 DenAI

**Your private AI den.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/rodrigogobbo/denai?style=social)](https://github.com/rodrigogobbo/denai)
[![Tests](https://github.com/rodrigogobbo/denai/actions/workflows/ci.yml/badge.svg)](https://github.com/rodrigogobbo/denai/actions/workflows/ci.yml)

A fully local AI assistant with tools, memory, and **zero cloud dependency**. Chat with LLMs on your machine — your data never leaves your computer.

---

## ✨ Features

- 🔒 **100% Private** — Everything runs locally. No data leaves your machine. Ever.
- 🧠 **Persistent Memory** — Remembers context across conversations
- 🛠️ **Built-in Tools** — File I/O, web search, shell commands, and more
- 🌐 **Web UI** — Clean chat interface served automatically at `localhost:4078`
- 🔄 **Model Switching** — Swap between Ollama models on the fly
- 📡 **Share Mode** — Expose your instance with authentication via `--share`
- ⚡ **Streaming** — Real-time token-by-token responses
- 🧩 **Extensible** — Drop a Python file in `denai/tools/` and it's auto-discovered
- 🌍 **Offline First** — Works without internet after initial setup

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                  Browser                    │
│              localhost:4078                  │
└────────────────────┬────────────────────────┘
                     │ HTTP / WebSocket
┌────────────────────▼────────────────────────┐
│              DenAI Server                   │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ FastAPI   │ │  Tools   │ │   Memory    │ │
│  │ (routes)  │ │ (auto-   │ │ (SQLite /   │ │
│  │           │ │ discover)│ │  JSON)      │ │
│  └─────┬────┘ └────┬─────┘ └──────┬──────┘ │
│        │           │              │         │
│        └───────────┼──────────────┘         │
│                    │                        │
└────────────────────┼────────────────────────┘
                     │ Ollama API (:11434)
┌────────────────────▼────────────────────────┐
│               Ollama                        │
│         LLM Models (local)                  │
└─────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows — download from https://ollama.com/download
```

### 2. Pull a model

```bash
ollama pull llama3.1:8b
```

### 3. Install DenAI

```bash
pip install denai
```

### 4. Run

```bash
denai
```

Open your browser at **http://localhost:4078** — that's it! 🎉

> **Screenshot placeholder**  
> ![DenAI Screenshot](docs/screenshot.png)

---

## 🛠️ Available Tools

| Tool | Description | Requires Internet |
|------|-------------|:-:|
| `read_file` | Read files from the local filesystem | ❌ |
| `write_file` | Create or overwrite files | ❌ |
| `list_files` | List directory contents | ❌ |
| `run_command` | Execute shell commands (sandboxed) | ❌ |
| `web_search` | Search the web via DuckDuckGo | ✅ |
| `web_fetch` | Fetch and parse a URL | ✅ |
| `memory_save` | Save a persistent memory | ❌ |
| `memory_search` | Search saved memories | ❌ |

Tools are auto-discovered from `denai/tools/`. Drop a new `.py` file and it just works.

---

## 🧠 AI Models

| Model | Size | RAM | Best For | Recommendation |
|-------|------|-----|----------|:-:|
| `llama3.2:3b` | ~2 GB | 8 GB | Quick questions, light tasks | 🟢 Low-end PCs |
| `llama3.1:8b` | ~4.7 GB | 10 GB | General use, good balance | ⭐ **Recommended** |
| `qwen2.5-coder:7b` | ~4.4 GB | 10 GB | Code generation & debugging | 🔵 Developers |
| `deepseek-r1:8b` | ~4.9 GB | 10 GB | Reasoning & math | 🟣 Complex problems |
| `mistral:7b` | ~4.1 GB | 10 GB | Versatile, multilingual | 🟡 Good all-rounder |
| `gemma3:4b` | ~3.3 GB | 8 GB | Lightweight yet capable | 🟢 Alternative |

```bash
# Install any model
ollama pull <model-name>

# List installed models
ollama list
```

---

## 🔗 Share Mode

Expose your local DenAI to others on the network (or via tunnel):

```bash
denai --share
```

- Generates a login page with API key authentication
- Only authenticated users can access the chat
- All traffic stays in your local network by default

---

## 🔐 Security

| Layer | Description |
|-------|-------------|
| **API Key** | Required for share mode; auto-generated or set via `DENAI_API_KEY` |
| **Command Sandbox** | Dangerous commands (`rm -rf /`, `format`, etc.) are blocked |
| **Command Filter** | Allowlist/blocklist for shell commands |
| **Rate Limiting** | Configurable requests-per-minute to prevent abuse |
| **Local Only** | By default, binds to `127.0.0.1` — no external access |

---

## ⚙️ Configuration

All configuration is via environment variables or a `.env` file in `~/.denai/`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DENAI_HOST` | `127.0.0.1` | Bind address |
| `DENAI_PORT` | `4078` | Server port |
| `DENAI_MODEL` | `llama3.1:8b` | Default Ollama model |
| `DENAI_OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `DENAI_API_KEY` | *(auto-generated)* | API key for share mode |
| `DENAI_DATA_DIR` | `~/.denai` | Data directory (memory, history) |
| `DENAI_LOG_LEVEL` | `info` | Logging level |
| `DENAI_RATE_LIMIT` | `30` | Max requests per minute |

---

## 🧑‍💻 Development

```bash
# Clone the repo
git clone https://github.com/your-org/denai.git
cd denai

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .

# Run locally
python -m denai
```

### Project Structure

```
denai/
├── denai/
│   ├── __init__.py
│   ├── __main__.py          # CLI entrypoint
│   ├── server.py            # FastAPI app
│   ├── chat.py              # Ollama chat logic
│   ├── memory.py            # Persistent memory
│   ├── config.py            # Settings & env vars
│   ├── security.py          # Auth, rate limiting
│   ├── static/              # Web UI assets
│   └── tools/               # Auto-discovered tools
│       ├── __init__.py
│       ├── file_tools.py
│       ├── web_tools.py
│       ├── command_tools.py
│       └── memory_tools.py
├── tests/
│   ├── test_chat.py
│   ├── test_tools.py
│   └── test_memory.py
├── docs/
│   └── GUIA-COMPLETO.md
├── pyproject.toml
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 🤝 Contributing

We'd love your help! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

[MIT](LICENSE) — use it, fork it, ship it.

---

## 🙏 Credits

Built on the shoulders of giants:

- **[Ollama](https://ollama.com)** — Local LLM runtime
- **[FastAPI](https://fastapi.tiangolo.com)** — High-performance Python web framework
- **[DuckDuckGo](https://duckduckgo.com)** — Privacy-first web search

---

> 🐺 *Your den, your data, your AI.*
