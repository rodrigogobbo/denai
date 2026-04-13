# DenAI — Configuração

> **Versão:** 0.25.0

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
