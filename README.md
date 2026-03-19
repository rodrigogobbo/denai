# 🐺 DenAI

**Your private AI den.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/denai.svg)](https://pypi.org/project/denai/)
[![GitHub stars](https://img.shields.io/github/stars/rodrigogobbo/denai?style=social)](https://github.com/rodrigogobbo/denai)
[![Tests](https://github.com/rodrigogobbo/denai/actions/workflows/ci.yml/badge.svg)](https://github.com/rodrigogobbo/denai/actions/workflows/ci.yml)

A fully local AI assistant with tools, memory, and **zero cloud dependency**. Chat with LLMs on your machine — your data never leaves your computer.

---

## ✨ Features

- 🔒 **100% Private** — Everything runs locally. No data leaves your machine. Ever.
- 🧠 **Persistent Memory** — Remembers context across conversations (SQLite)
- 🛠️ **Built-in Tools** — File I/O, web search, shell commands, planning, and more (14 tools)
- 🌐 **Web UI** — Clean chat interface served automatically at `localhost:4078`
- 🔄 **Model Switching** — Swap between Ollama models on the fly
- 📡 **Share Mode** — Expose your instance with authentication via `--share`
- ⚡ **Streaming** — Real-time token-by-token responses
- 🎨 **Dark/Light Mode** — Toggle with `Ctrl+T`, persists across sessions
- 📤 **Export** — Download conversations as JSON or Markdown
- 🔍 **Search** — Find conversations by title or content
- 🧙 **Setup Wizard** — Guided first-boot experience for beginners
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

---

## 🛠️ Available Tools

DenAI comes with **14 built-in tools** that the AI can use automatically:

| Tool | Description | Internet? |
|------|-------------|:-:|
| `file_read` | Read files with line numbers (offset/limit for large files) | ❌ |
| `file_write` | Create or overwrite files (auto-creates directories) | ❌ |
| `list_files` | List directory contents with glob patterns | ❌ |
| `file_edit` | Search/replace in files (exact text matching, replace_all) | ❌ |
| `command_exec` | Execute shell commands (sandboxed + filtered) | ❌ |
| `web_search` | Fetch and extract text from any URL | ✅ |
| `memory_save` | Save persistent memory (fact/decision/preference/observation) | ❌ |
| `memory_search` | Search saved memories by keywords and type | ❌ |
| `rag_search` | Search indexed local documents (BM25) | ❌ |
| `rag_index` | Reindex `~/.denai/documents/` | ❌ |
| `rag_stats` | Show RAG index statistics | ❌ |
| `question` | Ask the user a question and wait for the answer | ❌ |
| `plan_create` | Create a multi-step execution plan | ❌ |
| `plan_update` | Mark plan steps as done / in progress | ❌ |

Tools are auto-discovered from `denai/tools/`. Drop a new `.py` file and it just works.

---

## 🧠 AI Models

| Model | Size | RAM | Best For | Recommendation |
|-------|------|-----|----------|:-:|
| `llama3.2:3b` | ~2 GB | 8 GB | Quick questions, light tasks | 🟢 Low-end PCs |
| `llama3.1:8b` | ~4.7 GB | 10 GB | General use, good balance | ⭐ **Recommended** |
| `qwen2.5-coder:7b` | ~4.4 GB | 10 GB | Code generation & debugging | 🔵 Developers |
| `qwen2.5-coder:32b` | ~18 GB | 24 GB | Best tool calling & planning | 🏆 **Power users** |
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

## 🧩 Plugins

Extend DenAI with custom tools by dropping Python files in `~/.denai/plugins/`:

### Single-file plugin

```python
# ~/.denai/plugins/calculator.py
"""Plugin: calculadora."""

SPEC = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Calcula expressões matemáticas.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Ex: '2 + 3 * 4'"}
            },
            "required": ["expression"],
        },
    },
}

async def calculator(args: dict) -> str:
    expr = args.get("expression", "")
    allowed = set("0123456789+-*/.() ")
    if not all(c in allowed for c in expr):
        return "Caracteres não permitidos"
    return f"Resultado: {eval(expr, {'__builtins__': {}}, {})}"

TOOLS = [(SPEC, "calculator")]
```

### Directory plugin

```
~/.denai/plugins/weather/
├── plugin.json    # {"name": "weather", "version": "1.0.0"}
└── main.py        # TOOLS + functions (same format)
```

Plugins are auto-discovered on startup. Use `POST /api/plugins/reload` to reload without restart.

See `examples/plugins/` for ready-to-use examples.

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
│   ├── app.py               # FastAPI app factory
│   ├── config.py            # Settings & env vars
│   ├── db.py                # SQLite (aiosqlite)
│   ├── network.py           # Local IP detection
│   ├── llm/                 # LLM integration
│   │   ├── ollama.py        # Ollama streaming + tool loop
│   │   └── prompt.py        # System prompt builder
│   ├── rag/                 # RAG engine
│   │   └── __init__.py      # BM25 index, tokenizer, chunker
│   ├── routes/              # API endpoints
│   │   ├── chat.py          # POST /api/chat (SSE)
│   │   ├── conversations.py # CRUD conversations
│   │   ├── models.py        # Ollama models
│   │   ├── plugins.py       # Plugin management
│   │   └── rag.py           # RAG endpoints
│   ├── security/            # Security layers
│   │   ├── auth.py          # API key
│   │   ├── sandbox.py       # Path validation
│   │   ├── command_filter.py# Command blocklist
│   │   └── rate_limit.py    # Per-IP rate limiting
│   ├── plugins/             # Plugin autodiscovery
│   ├── static/              # Web UI (SPA)
│   └── tools/               # Auto-discovered tools
│       ├── registry.py      # Tool dispatcher
│       ├── file_ops.py      # file_read, file_write, list_files
│       ├── command_exec.py  # command_exec
│       ├── memory.py        # memory_save, memory_search
│       ├── web_fetch.py     # web_search
│       └── rag_search.py    # rag_search, rag_index, rag_stats
├── tests/                   # 237 tests
├── examples/plugins/        # Example plugins
├── pyproject.toml
├── README.md
├── CHANGELOG.md
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
