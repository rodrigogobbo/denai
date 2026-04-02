# DenAI — Referência da API REST

> **Versão:** 0.19.0  
> **Base URL:** `http://localhost:4078`  
> **Autenticação:** header `X-API-Key: <sua-key>` em todas as rotas (exceto `/` e `/static`)

A API key é gerada automaticamente na primeira execução e armazenada em `~/.denai/api.key`.

```bash
# Descobrir a API key
cat ~/.denai/api.key

# Variável de ambiente para os exemplos abaixo
export KEY=$(cat ~/.denai/api.key)
```

---

## Índice

1. [Chat](#chat)
2. [Conversas](#conversas)
3. [Models & Providers](#models--providers)
4. [Memória](#memória)
5. [Plans (execução)](#plans-execução)
6. [Plans Spec (documentos)](#plans-spec-documentos)
7. [Todo List](#todo-list)
8. [Personas](#personas)
9. [Skills](#skills)
10. [Plugins](#plugins)
11. [MCP](#mcp)
12. [RAG](#rag)
13. [Agent Loop](#agent-loop)
14. [Project Analysis](#project-analysis)
15. [Permissions](#permissions)
16. [Undo / Redo](#undo--redo)
17. [Voice](#voice)
18. [Update](#update)
19. [Feedback]
20. [Diagnósticos](#diagnósticos)
20. [Health](#health)

---

## Chat

### `POST /api/chat`

Envia uma mensagem e recebe resposta em streaming (SSE).

**Body:**
```json
{
  "conversation_id": "uuid-opcional",
  "message": "Como faço um loop em Python?",
  "model": "llama3.1:8b",
  "mode": "build"
}
```

**Campos:**
| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `message` | string | ✅ | Mensagem do usuário |
| `conversation_id` | string | ❌ | ID da conversa (cria nova se ausente) |
| `model` | string | ❌ | Modelo a usar (padrão: config) |
| `mode` | string | ❌ | `build` (padrão) ou `plan` (read-only) |

**Resposta:** Stream SSE com eventos:

```
data: {"content": "Em Python, "}
data: {"content": "você pode usar..."}
data: {"tool_call": {"name": "file_read", "args": {"path": "main.py"}}}
data: {"tool_result": {"name": "file_read", "result": "..."}}
data: {"suggestion": {"type": "skill", "id": "python-basics", "reason": "..."}}
data: {"done": true}
```

**Exemplo:**
```bash
curl -X POST http://localhost:4078/api/chat \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Olá!", "model": "llama3.1:8b"}' \
  --no-buffer
```

---

## Conversas

### `GET /api/conversations`

Lista todas as conversas.

```bash
curl http://localhost:4078/api/conversations -H "X-API-Key: $KEY"
```

**Resposta:**
```json
{
  "conversations": [
    {"id": "uuid", "title": "Como fazer...", "model": "llama3.1:8b",
     "created_at": "2026-03-01T10:00:00Z", "updated_at": "2026-03-01T10:05:00Z"}
  ]
}
```

---

### `POST /api/conversations`

Cria uma nova conversa.

```bash
curl -X POST http://localhost:4078/api/conversations \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "Projeto Python", "model": "llama3.1:8b"}'
```

---

### `GET /api/conversations/{id}/messages`

Retorna mensagens de uma conversa.

```bash
curl http://localhost:4078/api/conversations/uuid/messages -H "X-API-Key: $KEY"
```

---

### `DELETE /api/conversations/{id}`

Deleta uma conversa e suas mensagens.

```bash
curl -X DELETE http://localhost:4078/api/conversations/uuid -H "X-API-Key: $KEY"
```

---

### `GET /api/conversations/search?q=termo`

Busca conversas por título ou conteúdo.

```bash
curl "http://localhost:4078/api/conversations/search?q=python" -H "X-API-Key: $KEY"
```

---

### `GET /api/conversations/{id}/export?format=html`

Exporta conversa como HTML standalone.

```bash
curl "http://localhost:4078/api/conversations/uuid/export?format=html" \
  -H "X-API-Key: $KEY" -o conversa.html
```

---

## Models & Providers

### `GET /api/providers`

Lista providers configurados (API keys mascaradas).

```bash
curl http://localhost:4078/api/providers -H "X-API-Key: $KEY"
```

**Resposta:**
```json
{
  "providers": [
    {"name": "Ollama", "kind": "ollama", "base_url": "http://localhost:11434",
     "has_key": false, "api_key_masked": "", "models": [], "is_default": true},
    {"name": "OpenAI", "kind": "openai", "base_url": "https://api.openai.com",
     "has_key": true, "api_key_masked": "sk-ab***99", "models": ["gpt-4o"], "is_default": false}
  ]
}
```

---

### `GET /api/providers/templates`

Lista templates pré-configurados para novos providers.

```bash
curl http://localhost:4078/api/providers/templates -H "X-API-Key: $KEY"
```

---

### `POST /api/providers`

Adiciona ou atualiza um provider (persiste em `~/.denai/providers.yaml`).

```bash
curl -X POST http://localhost:4078/api/providers \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenAI",
    "kind": "openai",
    "base_url": "https://api.openai.com",
    "api_key": "sk-...",
    "models": ["gpt-4o", "gpt-4o-mini"]
  }'
```

---

### `DELETE /api/providers/{name}`

Remove um provider persistido. O provider Ollama padrão não pode ser removido.

```bash
curl -X DELETE http://localhost:4078/api/providers/OpenAI -H "X-API-Key: $KEY"
```

---

### `POST /api/providers/test`

Testa a conexão com um provider antes de salvar.

```bash
curl -X POST http://localhost:4078/api/providers/test \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"kind": "openai", "base_url": "https://api.openai.com", "api_key": "sk-..."}'
```

**Resposta (sucesso):**
```json
{"ok": true, "latency_ms": 142, "models_found": 8, "models": ["gpt-4o", "gpt-4o-mini"]}
```

**Resposta (falha):**
```json
{"ok": false, "error": "API key inválida ou ausente.", "latency_ms": null}
```

---

### `GET /api/models`

Lista modelos de todos os providers (ou de um específico).

```bash
curl http://localhost:4078/api/models -H "X-API-Key: $KEY"
curl "http://localhost:4078/api/models?provider=OpenAI" -H "X-API-Key: $KEY"
```

---

### `POST /api/models/pull`

Baixa um modelo Ollama (streaming de progresso).

```bash
curl -X POST http://localhost:4078/api/models/pull \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2:3b"}' --no-buffer
```

---

### `DELETE /api/models/{name}`

Deleta um modelo Ollama.

```bash
curl -X DELETE "http://localhost:4078/api/models/llama3.2:3b" -H "X-API-Key: $KEY"
```

---

### `GET /api/ollama/status`

Verifica status do Ollama local.

```bash
curl http://localhost:4078/api/ollama/status -H "X-API-Key: $KEY"
```

---

## Memória

### `GET /api/memories`

Lista memórias persistentes.

```bash
curl http://localhost:4078/api/memories -H "X-API-Key: $KEY"
curl "http://localhost:4078/api/memories?type=fact&limit=10" -H "X-API-Key: $KEY"
```

**Query params:** `type` (fact/decision/preference/observation), `limit` (padrão 50, máx 200)

**Resposta:**
```json
{"memories": [...], "total": 42}
```

---

### `DELETE /api/memories/{id}`

Deleta uma memória pelo ID.

```bash
curl -X DELETE http://localhost:4078/api/memories/123 -H "X-API-Key: $KEY"
```

---

## Plans (execução)

Plans são listas de passos de execução (step-by-step), gerenciados pelas tools `plan_create`/`plan_update`.

### `GET /api/plans`

Lista todos os planos.

### `GET /api/plans/{id}`

Retorna um plano com passos completos.

### `DELETE /api/plans/{id}`

Remove um plano.

---

## Plans Spec (documentos)

Spec documents são arquivos markdown com lifecycle (draft → active → done → archived), diferentes dos plans de execução.

### `GET /api/plans-spec`

Lista todos os spec documents.

```bash
curl http://localhost:4078/api/plans-spec -H "X-API-Key: $KEY"
curl "http://localhost:4078/api/plans-spec?status=active" -H "X-API-Key: $KEY"
```

---

### `POST /api/plans-spec`

Cria um novo spec document.

```bash
curl -X POST http://localhost:4078/api/plans-spec \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Feature: Auth com OAuth",
    "content": "# Auth com OAuth\n\n## Objetivo\n...",
    "status": "draft",
    "tags": "auth,oauth,security"
  }'
```

---

### `GET /api/plans-spec/{id}`

Retorna um spec document com conteúdo markdown.

### `PATCH /api/plans-spec/{id}`

Atualiza title, content, status ou tags.

```bash
curl -X PATCH http://localhost:4078/api/plans-spec/feature-auth-com-oauth \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'
```

### `DELETE /api/plans-spec/{id}`

Move para `.trash/` (soft delete, recuperável).

---

## Todo List

### `GET /api/todos`

Retorna a lista de todos atual.

```bash
curl http://localhost:4078/api/todos -H "X-API-Key: $KEY"
```

---

### `PUT /api/todos`

Substitui a lista inteira de todos.

```bash
curl -X PUT http://localhost:4078/api/todos \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "todos": [
      {"id": "1", "content": "Implementar login", "status": "completed", "priority": "high"},
      {"id": "2", "content": "Escrever testes", "status": "in_progress", "priority": "medium"}
    ]
  }'
```

---

### `DELETE /api/todos`

Limpa toda a lista.

---

## Personas

### `GET /api/personas`

Lista personas disponíveis (bundled + custom de `~/.denai/personas/`).

```bash
curl http://localhost:4078/api/personas -H "X-API-Key: $KEY"
```

**Resposta:**
```json
{
  "personas": [
    {"name": "security", "description": "AppSec specialist...", "source": "bundled"},
    {"name": "reviewer", "description": "Senior code reviewer...", "source": "bundled"},
    {"name": "writer",   "description": "Technical writer...", "source": "bundled"},
    {"name": "data",     "description": "Data analyst...", "source": "bundled"}
  ]
}
```

---

## Skills

### `GET /api/skills`

Lista skills disponíveis e ativas.

### `POST /api/skills/activate`

Ativa uma skill manualmente.

```bash
curl -X POST http://localhost:4078/api/skills/activate \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "python-expert"}'
```

### `POST /api/skills/deactivate`

Desativa uma skill.

### `POST /api/skills/match`

Verifica quais skills fazem match com uma mensagem.

### `POST /api/skills/clear`

Desativa todas as skills.

---

## Plugins

### `GET /api/plugins`

Lista plugins instalados.

### `POST /api/plugins/reload`

Recarrega plugins (sem reiniciar o servidor).

---

## MCP

### `GET /api/mcp/servers`

Lista MCP servers configurados e suas tools.

### `POST /api/mcp/connect`

Conecta a um MCP server.

```bash
curl -X POST http://localhost:4078/api/mcp/connect \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"]
  }'
```

### `POST /api/mcp/disconnect`

Desconecta um servidor MCP pelo nome.

### `POST /api/mcp/disconnect-all`

Desconecta todos os servidores MCP.

### `POST /api/mcp/connect-all`

Conecta todos os servidores configurados no `config.yaml`.

---

## RAG

### `GET /api/rag/stats`

Estatísticas do índice de documentos locais.

### `POST /api/rag/index`

Reindexar `~/.denai/documents/`.

### `POST /api/rag/search`

Busca semântica nos documentos indexados.

```bash
curl -X POST http://localhost:4078/api/rag/search \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "como configurar autenticação", "limit": 5}'
```

### `GET /api/rag/documents`

Lista documentos indexados.

### `POST /api/rag/upload`

Faz upload de um documento para `~/.denai/documents/`.

### `DELETE /api/rag/documents/{filename}`

Remove um documento indexado.

---

## Agent Loop

O agent loop decompõe um goal em passos e executa cada um autonomamente.

### `POST /api/agent/start`

Decompõe um goal em plano (não executa ainda).

```bash
curl -X POST http://localhost:4078/api/agent/start \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Criar um script Python que lê um CSV e gera um gráfico", "model": "llama3.1:8b"}'
```

**Resposta:**
```json
{
  "ok": true,
  "plan": {
    "goal": "Criar um script Python...",
    "status": "draft",
    "steps": [
      {"index": 1, "description": "Criar arquivo script.py", "tool_name": "file_write", "status": "pending"},
      {"index": 2, "description": "Instalar dependências", "tool_name": "command_exec", "status": "pending"}
    ]
  }
}
```

---

### `POST /api/agent/approve`

Aprova e executa o plano (streaming SSE).

```bash
curl -X POST http://localhost:4078/api/agent/approve \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Criar um script Python que lê um CSV e gera um gráfico"}' \
  --no-buffer
```

**Eventos SSE:**
```
data: {"type": "agent_step_start", "step": 1, "description": "Criar arquivo...", "tool": "file_write"}
data: {"type": "agent_step_complete", "step": 1, "result": "✅ Arquivo criado"}
data: {"type": "agent_complete", "plan": {...}}
```

---

### `POST /api/agent/abort`

Aborta o plano em execução.

### `GET /api/agent/status`

Retorna o status do plano atual.

---

## Project Analysis

### `POST /api/project/init`

Analisa um diretório e persiste o contexto para o LLM.

```bash
curl -X POST http://localhost:4078/api/project/init \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"path": "/home/user/meu-projeto"}'
```

**Resposta:**
```json
{
  "ok": true,
  "project": {
    "name": "meu-projeto",
    "languages": ["Python"],
    "frameworks": ["FastAPI", "Docker"],
    "file_count": 42,
    "dir_count": 8,
    "git": {"branch": "main", "remote": "git@github.com:..."}
  },
  "context": "## Projeto: meu-projeto\n..."
}
```

### `GET /api/project/init?path=/caminho`

Variante GET para análise.

### `GET /api/project/context?path=/caminho`

Retorna o contexto persistido anteriormente.

---

## Permissions

### `GET /api/permissions`

Lista permissões atuais de todas as tools.

### `PUT /api/permissions`

Atualiza permissões de uma ou mais tools.

```bash
curl -X PUT http://localhost:4078/api/permissions \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"command_exec": "deny", "file_write": "ask"}'
```

Níveis: `allow` (executa automaticamente), `ask` (pede confirmação), `deny` (bloqueia).

### `POST /api/permissions/reset`

Restaura permissões para os valores padrão.

### `POST /api/permissions/check`

Verifica a permissão de uma tool específica.

---

## Undo / Redo

### `GET /api/undo/status`

Retorna o changeset atual e snapshots disponíveis.

### `POST /api/undo`

Desfaz o último changeset de ferramentas destrutivas.

### `POST /api/redo`

Refaz o último undo.

---

## Voice

### `GET /api/voice/status`

Verifica se o Whisper está disponível.

```bash
curl http://localhost:4078/api/voice/status -H "X-API-Key: $KEY"
# {"available": true, "model": "base"}
```

### `POST /api/voice/transcribe`

Transcreve áudio para texto (requer `pip install denai[voice]`).

```bash
curl -X POST http://localhost:4078/api/voice/transcribe \
  -H "X-API-Key: $KEY" \
  -F "audio=@gravacao.wav"
```

---

## Update

### `GET /api/update/check`

Verifica se há versão mais recente no PyPI.

```bash
curl http://localhost:4078/api/update/check -H "X-API-Key: $KEY"
# {"current_version": "0.19.0", "latest_version": "0.19.0", "update_available": false}
```

---

### `POST /api/update/install`

Instala a versão mais recente via `pip install --upgrade denai`. **Retorna SSE streaming** com progresso em tempo real.

```bash
curl -X POST http://localhost:4078/api/update/install -H "X-API-Key: $KEY" --no-buffer
```

**Eventos SSE:**
```
data: {"type": "progress", "line": "Collecting denai..."}
data: {"type": "progress", "line": "Successfully installed denai-0.19.0"}
data: {"type": "success", "version": "0.19.0", "message": "DenAI 0.19.0 instalado com sucesso!"}
```

---

### `POST /api/update/restart`

Reinicia o servidor DenAI. Inicia nova instância e encerra a atual após 1s.

```bash
curl -X POST http://localhost:4078/api/update/restart -H "X-API-Key: $KEY"
# {"ok": true, "message": "Reinicialização iniciada...", "reconnect_delay_ms": 3000}
```

Após chamar, faça polling de `GET /api/health` para detectar quando o servidor voltou.

---

## Feedback

### `GET /api/feedback/config`

Retorna configuração de feedback disponível.

```bash
curl http://localhost:4078/api/feedback/config -H "X-API-Key: $KEY"
# {"enabled": true, "method": "github", "repo": "rodrigogobbo/denai", "has_token": true}
# ou
# {"enabled": true, "method": "local", "has_token": false}
```

---

### `POST /api/feedback`

Envia feedback como GitHub Issue (se token configurado) ou salva localmente.

```bash
curl -X POST http://localhost:4078/api/feedback \
  -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "bug",
    "title": "Crash ao iniciar com Python 3.12",
    "description": "O DenAI fecha imediatamente ao tentar iniciar. Passos: 1) pip install denai 2) python -m denai",
    "include_context": true
  }'
```

**Campos:**
| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `type` | string | ✅ | `bug` ou `improvement` |
| `title` | string | ✅ | Mínimo 3 caracteres |
| `description` | string | ✅ | Mínimo 10 caracteres |
| `include_context` | boolean | ❌ | Incluir versão, OS, Python, logs (padrão: true) |

**Resposta (GitHub):**
```json
{"method": "github", "issue_number": 42, "issue_url": "https://github.com/.../issues/42", "message": "Issue #42 aberta!"}
```

**Resposta (local):**
```json
{"method": "local", "file": "/home/user/.denai/feedback/20260402_220000_bug.json", "message": "Feedback salvo localmente..."}
```

---

### `GET /api/feedback/list`

Lista feedbacks salvos localmente (fallback quando sem token).

```bash
curl http://localhost:4078/api/feedback/list -H "X-API-Key: $KEY"
```

---

## Diagnósticos

### `GET /logs`

Retorna as últimas linhas do arquivo de log.

```bash
curl "http://localhost:4078/logs?lines=100" -H "X-API-Key: $KEY"
```

### `GET /diagnostics`

Retorna informações de diagnóstico do sistema.

---

## Health

### `GET /api/health`

Endpoint público (sem autenticação). Retorna status do servidor.

```bash
curl http://localhost:4078/api/health
```

**Resposta:**
```json
{
  "status": "ok",
  "version": "0.17.0",
  "ollama": true,
  "ollama_version": "0.5.1",
  "model": "llama3.1:8b",
  "share_mode": false
}
```

---

## Códigos de Status

| Código | Significado |
|---|---|
| 200 | Sucesso |
| 201 | Criado |
| 204 | Sem conteúdo (DELETE bem-sucedido) |
| 400 | Parâmetros inválidos |
| 401 | API key ausente ou inválida |
| 403 | Acesso negado (ex: path fora do sandbox) |
| 404 | Recurso não encontrado |
| 409 | Conflito (ex: plano já em execução) |
| 422 | Erro de validação (Pydantic) |
| 429 | Rate limit excedido |
| 500 | Erro interno |
| 502 | Ollama inacessível |
