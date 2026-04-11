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
- 🛠️ **Built-in Tools** — File I/O, grep, web search, shell commands, planning, and more (26 tools)
- 🌐 **Web UI** — Clean chat interface served automatically at `localhost:4078`
- 🔄 **Model Switching** — Swap between Ollama models on the fly
- 📡 **Share Mode** — Expose your instance with authentication via `--share`
- ⚡ **Streaming** — Real-time token-by-token responses with tool-specific icons
- 🎨 **Dark/Light Mode** — Toggle with `Ctrl+T`, persists across sessions
- 📤 **Export** — Download conversations as JSON, Markdown, or standalone HTML
- 🔌 **MCP Support** — Connect external tools via Model Context Protocol (stdio JSON-RPC 2.0)
- 🔍 **Search** — Find conversations by title or content
- 🧙 **Setup Wizard** — Guided first-boot experience for beginners
- 🧩 **Extensible** — Drop a Python file in `denai/tools/` and it's auto-discovered
- 🧠 **Smart Context** — Dynamic context window (8k→32k→64k) with auto-summarization
- 🔄 **Deep Tool Chains** — Up to 25 tool call rounds per message (configurable)
- ⚡ **Parallel Tools** — Read-only tools run concurrently for faster responses
- 📋 **Plans UI** — Visual plan management with progress tracking in sidebar
- ⚙️ **config.yaml** — Persistent configuration in `~/.denai/config.yaml`
- 🌍 **Offline First** — Works without internet after initial setup
- 📝 **Word & Excel** — Create .docx and .xlsx documents with rich formatting
- 📋 **Logging** — Persistent logs in ~/.denai/logs/ with rotation (5 MB, 3 backups)
- 🔍 **Diagnostics API** — /api/logs and /api/diagnostics for troubleshooting
- 🤖 **Agentic Workflows** — Autonomous multi-step execution with checkpoints and undo
- ✅ **Todo List** — Real-time task tracking with `todowrite` (IDs, priority, status)
- 📋 **Spec Documents** — Persistent markdown specs with lifecycle (draft→active→done)
- 🤝 **Sub-agents** — Delegate to specialized agents with custom personas (security, reviewer, writer, data)
- 💡 **Proactive Suggestions** — LLM suggests relevant skills and plugins with 1-click install
- 🔁 **Auto Update** — Streaming install progress + one-click restart from the UI
- 💬 **In-app Feedback** — Report bugs and suggest improvements without leaving DenAI
- 🚀 **Auto Release** — Every version bump triggers tests → GitHub Release → PyPI automatically
- 🖥️ **Desktop App** — Native installer (.exe/.dmg/.zip) via Electron + uv bundled, no Python required

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│                  Browser                    │
│              localhost:4078                  │
└────────────────────┬────────────────────────┘
                     │ HTTP / SSE
┌────────────────────▼────────────────────────┐
│              DenAI Server                   │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ FastAPI   │ │  Tools   │ │   Memory    │ │
│  │ (20      │ │ (auto-   │ │ (SQLite /   │ │
│  │ routers) │ │ discover)│ │  JSON)      │ │
│  └─────┬────┘ └────┬─────┘ └──────┬──────┘ │
│        │           │              │         │
│        └───────────┼──────────────┘         │
│                    │                        │
└─────────┬──────────┼────────────────────────┘
          │          │ Ollama API (:11434)
          │  ┌───────▼───────────────────────┐
          │  │           Ollama              │
          │  │     LLM Models (local)        │
          │  └───────────────────────────────┘
          │  ┌───────────────────────────────┐
          └──│       MCP Servers             │
             │  (stdio, JSON-RPC 2.0)        │
             └───────────────────────────────┘
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

DenAI comes with **26 built-in tools** that the AI can use automatically:

| Tool | Description | Internet? |
|------|-------------|:-:|
| `file_read` | Read files with line numbers (offset/limit for large files) | ❌ |
| `file_write` | Create or overwrite files (auto-backup + auto-creates directories) | ❌ |
| `list_files` | List directory contents with glob patterns | ❌ |
| `file_edit` | Search/replace in files (exact text matching, auto-backup) | ❌ |
| `grep` | Regex search across files (include filter, skips .git/node_modules) | ❌ |
| `command_exec` | Execute shell commands (sandboxed + filtered) | ❌ |
| `web_search` | Search DuckDuckGo or fetch content from any URL | ✅ |
| `memory_save` | Save persistent memory (fact/decision/preference/observation) | ❌ |
| `memory_search` | Search saved memories by keywords and type | ❌ |
| `memory_list` | List recent memories without a query (limit, type filter) | ❌ |
| `rag_search` | Search indexed local documents (BM25) | ❌ |
| `rag_index` | Reindex `~/.denai/documents/` | ❌ |
| `rag_stats` | Show RAG index statistics | ❌ |
| `question` | Ask the user a question and wait for the answer | ❌ |
| `plan_create` | Create a multi-step execution plan (persisted in SQLite) | ❌ |
| `plan_update` | Mark plan steps as done / in progress | ❌ |
| `todowrite` | Replace the entire todo list (IDs, priority, real-time tracking) | ❌ |
| `todoread` | Read the current todo list | ❌ |
| `plans_spec` | Manage persistent markdown spec documents (draft/active/done/archived) | ❌ |
| `subagent` | Delegate a goal to a specialized agent with custom persona | ❌ |
| `suggest_skill` | Proactively suggest a relevant skill to the user | ❌ |
| `suggest_plugin` | Proactively suggest a relevant plugin to the user | ❌ |
| `think` | Internal reasoning scratchpad (no side-effects) | ❌ |
| `create_document` | Create Word .docx files (headings, paragraphs, bullets, tables) | ❌ |
| `create_spreadsheet` | Create Excel .xlsx files (multiple sheets, auto-width) | ❌ |
| `git` | Git operations: status, diff, log, branch, add, commit, checkout, stash | ❌ |

Tools are auto-discovered from `denai/tools/`. Drop a new `.py` file and it just works.

---

## 💻 System Requirements

| Tier | RAM | Storage | GPU | Experience |
|------|-----|---------|-----|------------|
| 🟢 **Mínimo** | 8 GB | 10 GB livre | Não precisa | Modelos 3B — respostas simples, sem tool calling confiável |
| ⭐ **Recomendado** | 16 GB | 20 GB livre | Não precisa | Modelos 7-8B — bom tool calling, respostas consistentes |
| 🏆 **Ideal** | 32 GB+ | 40 GB livre | Qualquer GPU com 8GB+ VRAM | Modelos 14-32B — tool calling preciso, planning multi-step |

### "Consigo fazer o mesmo que o ChatGPT/Copilot?"

Resposta honesta:

| Capacidade | Cloud (GPT-4, Claude) | DenAI 8B | DenAI 32B |
|------------|----------------------|----------|-----------|
| Conversa geral | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Gerar código | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Tool calling (ler/editar/executar) | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Planning multi-step | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Contexto longo (100k+ tokens) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (auto 8-32k with LLM summarization) | ⭐⭐⭐⭐ (auto 32-64k with LLM summarization) |
| Privacidade | ❌ Dados vão pra nuvem | ✅ 100% local | ✅ 100% local |
| Custo | $20-200/mês | **Grátis** | **Grátis** |
| Funciona offline | ❌ | ✅ | ✅ |

> 💡 **Resumo prático:** Com **8 GB RAM + modelo 8B**, o DenAI é um bom assistente de conversa e código, mas erra em tool calling complexo. Com **32 GB RAM + qwen2.5-coder:32b**, chega perto da experiência de cloud — tool calling confiável, planning, edição de arquivos em sequência. O contexto agora escala automaticamente de 8k a 64k tokens, com sumarização automática de mensagens antigas para sessões longas.

### Qual computador comprar?

Se está pensando em montar/comprar um PC pra rodar IA local:

- **Orçamento mínimo (~R$2.500):** PC usado com 16 GB RAM + SSD. Roda modelos 7-8B bem.
- **Orçamento ideal (~R$5.000-8.000):** 32 GB RAM + GPU com 8 GB VRAM (RTX 3060/4060). Roda modelos 14-32B com velocidade.
- **Notebook:** MacBook com Apple Silicon (M1/M2/M3 com 16 GB+) é excelente pra IA local — memória unificada beneficia muito os modelos.

---

## 🧠 AI Models

| Model | Size | RAM | What it can do | Recommendation |
|-------|------|-----|----------------|:-:|
| `llama3.2:3b` | ~2 GB | 8 GB | Conversa, Q&A, texto simples | 🟢 PCs fracos |
| `gemma3:4b` | ~3.3 GB | 8 GB | Conversa, código básico | 🟢 Alternativa leve |
| `llama3.1:8b` | ~4.7 GB | 10 GB | Conversa + tool calling básico | ⭐ **Recomendado** |
| `qwen2.5-coder:7b` | ~4.4 GB | 10 GB | Código + tools, bom em programação | 🔵 Devs |
| `mistral:7b` | ~4.1 GB | 10 GB | Versátil, multilingual | 🟡 All-rounder |
| `deepseek-r1:8b` | ~4.9 GB | 10 GB | Raciocínio, matemática, lógica | 🟣 Problemas complexos |
| `qwen2.5-coder:14b` | ~9 GB | 16 GB | Tool calling confiável, planning | 🔵 Devs com 16 GB |
| `qwen2.5-coder:32b` | ~18 GB | 24 GB | Melhor tool calling + planning multi-step | 🏆 **Power users** |

> 💡 DenAI auto-detects your RAM and picks the best default model: `llama3.2:3b` for <12 GB, `llama3.1:8b` for 12 GB+.

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

## 🐳 Docker

Run DenAI + Ollama without installing anything on your machine.

### Quick start

```bash
# Clone the repo
git clone https://github.com/rodrigogobbo/denai.git
cd denai

# Start everything
docker compose up -d

# Pull a model (first time only)
docker compose exec ollama ollama pull llama3.2:3b

# Open http://localhost:8080
```

### What gets created

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `denai-app` | Built from Dockerfile | 8080 | DenAI web UI + API |
| `denai-ollama` | `ollama/ollama:latest` | 11434 | LLM runtime |

| Volume | Purpose |
|--------|---------|
| `ollama_models` | Persists downloaded models between restarts |

### GPU support (NVIDIA)

Edit `docker-compose.yml` and uncomment the `deploy` block under `ollama`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

Requires [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) on the host.

### Custom configuration

```bash
# Use a different model
docker compose exec denai-app env DENAI_MODEL=qwen2.5-coder:7b python -m denai

# Mount your own config
# Add to docker-compose.yml under denai > volumes:
#   - ~/.denai/config.yaml:/home/denai/.denai/config.yaml
```

### Useful commands

```bash
# View logs
docker compose logs -f denai

# Stop everything
docker compose down

# Rebuild after code changes
docker compose build denai && docker compose up -d denai

# Remove everything (containers, volumes, models)
docker compose down -v
```

---

## 🔌 MCP (Model Context Protocol)

Connect external tools to DenAI via the [MCP standard](https://modelcontextprotocol.io/).

### Configuration

Add MCP servers to `~/.denai/config.yaml`:

```yaml
mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
    enabled: true
  web_search:
    command: python
    args: ["-m", "web_search_mcp"]
    env:
      API_KEY: "your-key-here"
    enabled: true
```

### API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mcp/servers` | GET | List configured servers and status |
| `/api/mcp/connect` | POST | Connect to a server by name or inline config |
| `/api/mcp/disconnect` | POST | Disconnect a server |
| `/api/mcp/disconnect-all` | POST | Disconnect all servers |
| `/api/mcp/connect-all` | POST | Connect all enabled servers |

Tools discovered from MCP servers are automatically available to the AI — no additional setup needed.

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

Configuration priority: **CLI args > env vars > `~/.denai/config.yaml` > defaults**

### config.yaml (recommended)

Create `~/.denai/config.yaml`:

```yaml
model: llama3.1:8b
ollama_url: http://localhost:11434
port: 4078
share: false
max_tool_rounds: 25
max_context: 65536

mcp_servers:
  filesystem:
    command: npx
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
    enabled: true
```

A `config.example.yaml` is included in the repo as reference.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DENAI_HOST` | `127.0.0.1` | Bind address |
| `DENAI_PORT` | `4078` | Server port |
| `DENAI_MODEL` | `llama3.1:8b` | Default Ollama model |
| `DENAI_OLLAMA_URL` | `http://localhost:11434` | Ollama API endpoint |
| `DENAI_API_KEY` | *(auto-generated)* | API key for share mode |
| `DENAI_MAX_TOOL_ROUNDS` | `25` | Max tool call rounds per message |
| `DENAI_MAX_CONTEXT` | `65536` | Max context window (tokens) |

---

## 🗑️ Complete Uninstall

Remove DenAI and all its data from your machine.

### Quick (DenAI only)

```bash
pip uninstall denai -y
```

### Full cleanup (everything)

```bash
# 1. Uninstall the Python package
pip uninstall denai -y

# 2. Remove DenAI data (conversations, memory, config, plugins, skills, logs)
# Linux / macOS
rm -rf ~/.denai

# Windows (PowerShell)
Remove-Item -Recurse -Force "$env:USERPROFILE\.denai"

# Windows (CMD)
rmdir /s /q "%USERPROFILE%\.denai"

# 3. Remove Ollama models (optional — frees 5-50 GB)
ollama list                    # see what's installed
ollama rm llama3.1:8b          # remove one by one
# Or delete all models at once:
# Linux / macOS
rm -rf ~/.ollama/models
# Windows
rmdir /s /q "%USERPROFILE%\.ollama\models"

# 4. Uninstall Ollama (optional)
# Linux
sudo rm /usr/local/bin/ollama
# macOS
brew uninstall ollama   # or delete the app from /Applications
# Windows — Settings → Apps → Ollama → Uninstall

# 5. Docker cleanup (if used)
docker compose down -v         # removes containers + volumes (models)
docker rmi denai-denai         # remove the built image
```

### What gets deleted

| Item | Path | Content |
|------|------|---------|
| DenAI package | pip site-packages | Python code |
| DenAI data | `~/.denai/` | Conversations, memory, config, logs, plugins, skills, backups |
| Ollama models | `~/.ollama/models/` | Downloaded AI models (5-50 GB) |
| Ollama binary | `/usr/local/bin/ollama` | The Ollama runtime |
| Docker volumes | `ollama_models` | Models downloaded inside Docker |

> ⚠️ **Deleting `~/.denai/` is irreversible.** All your conversations, memories, and configs will be lost. Back up anything important first.
> 
> 💡 **Uninstalling DenAI does NOT delete Ollama or its models.** They are separate programs. Remove them separately if you want a clean slate.

---

## 🧑‍💻 Development

```bash
# Clone the repo
git clone https://github.com/rodrigogobbo/denai.git
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
│   ├── logging_config.py      # Centralized logging (file + console)
│   ├── export_html.py       # Standalone HTML export
│   ├── db.py                # SQLite (aiosqlite)
│   ├── network.py           # Local IP detection
│   ├── llm/                 # LLM integration
│   │   ├── ollama.py        # Ollama streaming + tool loop
│   │   ├── context.py    # Context management + summarization
│   │   └── prompt.py        # System prompt builder
│   ├── mcp/                 # MCP client (Model Context Protocol)
│   │   ├── __init__.py
│   │   ├── protocol.py      # JSON-RPC 2.0 types & messages
│   │   └── client.py        # MCP server connection & tool discovery
│   ├── rag/                 # RAG engine
│   │   └── __init__.py      # BM25 index, tokenizer, chunker
│   ├── routes/              # API endpoints
│   │   ├── chat.py          # POST /api/chat (SSE)
│   │   ├── conversations.py # CRUD conversations
│   │   ├── models.py        # Ollama models
│   │   ├── plugins.py       # Plugin management
│   │   ├── diagnostics.py   # /api/logs, /api/diagnostics
│   │   ├── plans.py         # Plans CRUD
│   │   ├── plans_spec.py    # Spec documents CRUD
│   │   ├── personas.py      # List personas
│   │   ├── todos.py         # Todo list endpoints
│   │   ├── mcp.py           # MCP server management
│   │   └── rag.py           # RAG endpoints
│   ├── security/            # Security layers
│   │   ├── auth.py          # API key
│   │   ├── sandbox.py       # Path validation
│   │   ├── command_filter.py# Command blocklist
│   │   └── rate_limit.py    # Per-IP rate limiting
│   ├── personas_bundled/    # Built-in personas (security, reviewer, writer, data)
│   ├── plugins/             # Plugin autodiscovery
│   ├── static/              # Web UI (SPA)
│   └── tools/               # Auto-discovered tools
│       ├── registry.py      # Tool dispatcher
│       ├── file_ops.py      # file_read, file_write, list_files
│       ├── command_exec.py  # command_exec
│       ├── memory.py        # memory_save, memory_search, memory_list
│       ├── web_fetch.py     # web_search
│       ├── rag_search.py    # rag_search, rag_index, rag_stats
│       ├── documents.py     # create_document, create_spreadsheet
│       ├── planning.py      # plan_create, plan_update
│       ├── plans_spec.py    # plans_spec (spec documents)
│       ├── todowrite.py     # todowrite, todoread
│       ├── subagent.py      # subagent (delegação com persona)
│       ├── suggestions.py   # suggest_skill, suggest_plugin
│       ├── git_ops.py       # git operations
│       ├── grep.py          # grep search
│       ├── think.py         # Internal reasoning
│       └── question.py      # Ask user questions
├── electron/                # Desktop app (Electron + uv)
│   ├── src/main.js          # Main process
│   ├── src/splash.html      # Loading screen
│   ├── assets/              # Icons (png/ico/icns)
│   └── forge.config.js      # Build config
├── specs/changes/           # SDS specs per version
├── tests/                   # 918 tests
├── examples/plugins/        # Example plugins
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── LICENSE
```

---

## 🤝 Contributing

We'd love your help! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Development Setup

```bash
# Clone and install
git clone https://github.com/rodrigogobbo/denai.git
cd denai
python -m venv .venv && source .venv/bin/activate
make install  # installs deps + pre-commit hooks

# Available commands
make help     # show all targets
make test     # run tests with coverage (75% minimum)
make lint     # ruff check + format check
make format   # auto-format code
make clean    # remove build artifacts
make all      # lint + test (CI equivalent)
```

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
