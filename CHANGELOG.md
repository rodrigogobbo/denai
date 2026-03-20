# Changelog

Todas as mudanças notáveis do DenAI serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

## [0.11.0] - 2026-03-20

### Adicionado
- **🎨 Share Session (HTML Export)** — exporte conversas como HTML standalone (#14)
  - `denai/export_html.py` — geração de HTML com tema dark, responsivo
  - Markdown-to-HTML converter leve (zero dependências externas)
  - XSS protection via `html.escape` em todo conteúdo de usuário
  - Tool cards expansíveis com toggle JavaScript inline
  - Endpoint `GET /api/conversations/{id}/export?format=html`
  - Content-Disposition com download automático do `.html`
- **🔌 MCP (Model Context Protocol)** — conecte tools externas via MCP (#14)
  - `denai/mcp/protocol.py` — tipos McpTool, McpServerConfig, mensagens JSON-RPC 2.0
  - `denai/mcp/client.py` — McpConnection via stdio subprocess, handshake, tool discovery
  - `denai/routes/mcp.py` — 5 endpoints (list, connect, disconnect, disconnect-all, connect-all)
  - `refresh_mcp_tools()` no `registry.py` — sincroniza tools MCP com TOOLS_SPEC/_EXECUTORS
  - Auto-refresh automático em connect/disconnect
  - Configuração via `~/.denai/config.yaml` seção `mcp_servers`
- 70 testes novos (39 export + 31 MCP) — 580 testes total
- 20 routers (1 novo: mcp)
- `config.example.yaml` com seção `mcp_servers` documentada

## [0.10.0] - 2026-03-20

### Adicionado
- **🔍 /init — Project Analysis** — analisa diretórios e gera contexto pro LLM (#13)
  - `denai/project.py` — detecta linguagens, frameworks, ecossistemas, git info
  - `POST /api/project/init` e `GET /api/project/init` — endpoints de análise
  - Gera tree de diretórios (2 níveis), conta arquivos, identifica key files
  - Suporta 16+ linguagens (Python, JS/TS, Go, Rust, Java, C#, Ruby, PHP, etc.)
  - Detecta 15+ frameworks (Next.js, FastAPI, Django, Docker, GitHub Actions, etc.)
  - Lê README pra extrair descrição, detecta branch e remote do Git
- **🔐 Permissões Granulares** — controle allow/ask/deny por tool (#13)
  - `denai/permissions.py` — sistema de permissões com 3 camadas de override
  - Defaults sensatos: read tools = allow, write tools = ask
  - Configurável via `~/.denai/config.yaml` seção `permissions`
  - Override dedicado via `~/.denai/permissions.yaml`
  - `GET /api/permissions` — lista permissões atuais
  - `PUT /api/permissions` — altera permissão de uma tool
  - `POST /api/permissions/reset` — volta pros defaults
  - `POST /api/permissions/check` — verifica se tool pode executar
  - Integrado no `registry.py` — tools com "deny" são bloqueadas automaticamente
- **📚 Skills (SKILL.md)** — instruções especializadas carregáveis (#13)
  - `denai/skills.py` — discovery, parsing, trigger matching, ativação manual
  - Skills em `~/.denai/skills/*.md` com frontmatter YAML
  - Triggers automáticos: palavras-chave na mensagem ativam skills relevantes
  - `auto_activate: true` pra skills sempre ativas
  - Injetadas no system prompt do LLM (integrado no `prompt.py` e `ollama.py`)
  - `GET /api/skills` — lista skills disponíveis
  - `POST /api/skills/activate` / `deactivate` — controle manual
  - `POST /api/skills/match` — testa quais skills um texto ativaria
  - 3 skills de exemplo: code-review, debug, git-workflow
- 86 testes novos (510 total)
- 18 routers (3 novos: project, permissions, skills)

### Corrigido
- Build do PyPI agora usa versão dinâmica do `version.py` via hatchling (#12)

## [0.9.0] - 2026-03-20

### Adicionado
- **⚡ Custom Commands** — crie prompts reutilizáveis em `~/.denai/commands/`
  - `denai/commands.py` — discovery e parsing de arquivos `.md` com YAML frontmatter
  - Suporte a `$ARGUMENTS`, `$1`, `$2`... com quoted strings
  - `GET /api/commands` — lista comandos disponíveis
  - `POST /api/commands/run` — renderiza comando com argumentos
  - Autocomplete popup no input ao digitar `/`
  - 3 exemplos bundled: test, review, explain
- **📋 Plan Mode** — modo de análise read-only
  - `denai/modes.py` — filtragem de tools (Build = todas, Plan = read-only)
  - Toggle via click no indicador ou Tab com input vazio
  - System prompt prefixado em modo plano
  - Indicador visual: 🔨 Build (verde) / 📋 Plan (azul)
  - Persiste em `sessionStorage`
- **↩️ Undo/Redo** — reverta alterações do agente
  - `denai/undo.py` — snapshots automáticos antes de cada modificação
  - Agrupamento por turn (undo reverte todas as mudanças de uma resposta)
  - Stack de até 50 níveis com redo invalidado por novas mudanças
  - `POST /api/undo`, `POST /api/redo`, `GET /api/undo/status`
  - Hooks em file_ops.py e documents.py
- 47 testes novos (424 total)

### Corrigido
- `test_update.py` — versão não mais hardcoded (usa `VERSION` importado)

## [0.8.0] - 2026-03-20

### Adicionado
- **🎙️ Voice Input (Whisper)** — transcrição de voz por IA (#7)
  - `denai/voice.py` — módulo de transcrição com lazy-load do modelo Whisper
  - `POST /api/voice/transcribe` — recebe áudio e retorna texto
  - `GET /api/voice/status` — verifica se Whisper está disponível
  - Botão de microfone na UI com MediaRecorder API
  - Pulse animation durante gravação, atalho Ctrl+Shift+M
  - Graceful degradation: sem Whisper instalado, botão fica oculto
  - Dep opcional: `pip install denai[voice]`
- **🔌 Multi-model backends** — suporte a múltiplos provedores de LLM (#8)
  - `denai/llm/providers.py` — registry de providers (Ollama, OpenAI-compatible, GPT4All)
  - Streaming adapter OpenAI SSE → formato Ollama (reutiliza tool-calling existente)
  - `GET /api/providers` — lista providers configurados
  - `POST /api/providers` — adiciona provider OpenAI-compatible (LM Studio, LocalAI, etc.)
  - `GET /api/models` agora lista modelos de todos os providers
  - UI: badges de provider no sidebar, dialog para adicionar endpoints
  - Configurável via `config.yaml` seção `providers`
- **🏪 Plugin Marketplace** — instale plugins pela UI (#10)
  - `denai/marketplace.py` — registry bundled + fetch de GitHub
  - 3 plugins built-in: 🌤️ Weather (Open-Meteo), 🌐 Translator, 🍅 Pomodoro
  - `GET /api/marketplace` — lista plugins disponíveis
  - `POST /api/marketplace/install` / `uninstall` — gerencia plugins
  - UI: modal marketplace com grid de cards, busca, install/remove
  - `registry/plugins.json` — placeholder para plugins da comunidade
- 33 testes novos (377 total)

## [0.7.0] - 2026-03-20

### Adicionado
- **Auto-update** — verifica automaticamente se há versão nova no PyPI
  - `GET /api/update/check` — compara versão local vs PyPI
  - `POST /api/update/install` — executa `pip install --upgrade denai`
  - Toast na UI com botão "Atualizar" quando update disponível (5s após startup)
- **VERSION centralizada** — `denai/version.py` como single source of truth (elimina duplicação entre app.py e pyproject.toml)
- 16 testes novos (auto-update, version parsing)
- 344 testes passando no total

## [0.6.0] - 2026-03-20

### Corrigido
- **Streaming SSE bufferizado pelo middleware HTTP** — Root cause: `@app.middleware('http')` do Starlette bufferizava toda a `StreamingResponse` antes de enviar ao cliente, fazendo o LLM gerar tokens mas a UI não receber nada até o final
- Substituído `@app.middleware` por ASGI middleware puro (`AuthMiddleware`) que repassa bytes diretamente sem bufferizar
- Frontend: `break` do evento `done` agora sai do `while` loop externo corretamente
- Backend: `chunk.replace('data: ')` substituído por slice seguro que não corrompe conteúdo contendo a string literal `"data: "`

### Alterado
- VERSION centralizada em `app.py` (v0.6.0)

### Adicionado
- 7 testes novos para o `AuthMiddleware` (autenticação, rate limit, streaming)
- 328 testes passando no total

## [0.5.1] - 2026-03-19

### Adicionado
- **Criar documentos Word (.docx)** — a IA pode gerar documentos completos com títulos, subtítulos (h1-h3), parágrafos (negrito/itálico), listas com bullets e tabelas com cabeçalho
- **Criar planilhas Excel (.xlsx)** — múltiplas abas, cabeçalhos em negrito, colunas auto-dimensionadas, conversão automática de números
- **Detecção inteligente de RAM** — PCs com menos de 12 GB usam `llama3.2:3b` por padrão; PCs com 12 GB+ usam `llama3.1:8b`; detecção em Linux, Windows e macOS
- **Mensagem amigável de memória insuficiente (OOM)** — em vez do erro críptico do Ollama, mostra explicação clara, sugestão de modelo menor e requisitos de RAM
- **Logging persistente** — logs gravados em arquivo para diagnóstico
- **API de diagnósticos** — endpoint para verificar estado do sistema
- Seção de troubleshooting no guia: _"denai não é reconhecido como comando"_ com 4 soluções para PATH no Windows

### Corrigido
- **Painel de Plans** — correção no carregamento e exibição de planos na sidebar
- Documentação atualizada (README e GUIA-COMPLETO) para refletir v0.5.1

## [0.5.0] - 2026-03-19

### Adicionado
- **Arquitetura de UI modular** — `ui.html` dividido de 4.086 → 291 linhas (shell only)
  - 5 módulos CSS: base, animations, layout, chat, components
  - 7 módulos JS: config, helpers, api, models, conversations, chat, ui
  - Montagem de arquivos estáticos para todos os subdiretórios
- **Sumarização via LLM** — auto-sumarização via Ollama quando contexto excede a janela
- **Janela de contexto dinâmica** — escala de 8k → 32k → 64k baseado no tamanho da conversa
- Fallback gracioso para truncamento quando sumarização falha

### Corrigido
- Consistência de versão — `/api/health` retornava 0.2.0, corrigido para versão atual

### Alterado
- 302 testes passando
- Lint clean (ruff)

## [0.4.0] - 2026-03-19

### Adicionado
- **Ícones e cores por tool** — cada tool tem emoji + cor de destaque na UI
  - Borda lateral colorida por tipo (azul=leitura, verde=escrita, laranja=execução, etc.)
  - Mapa de metadados `TOOL_META` para estilização consistente
- **Think tool inline** — scratchpad de raciocínio com borda tracejada, sempre visível
  - Estilizado como _"Raciocínio interno"_ em itálico com destaque violeta
- **Melhorias nos resultados de tools** — resultados > 2000 chars truncados com toggle "mostrar mais", botão de copiar, scroll limitado a 300px
- **Painel de Plans na UI** — gerenciamento visual de planos na sidebar
  - Seção colapsável "📋 Planos" com badge contador
  - Lista de planos com barras de progresso (percentual concluído/total)
  - Modal click-to-view com ícones de status por etapa
  - API REST: `GET /api/plans`, `GET /api/plans/{id}`, `DELETE /api/plans/{id}`
- **Suporte a config.yaml** — configuração persistente em `~/.denai/config.yaml`
  - Prioridade: CLI args > env vars > config.yaml > defaults
  - Todas as configurações suportadas: model, ollama_url, port, share, max_tool_rounds, max_context
  - Template `config.example.yaml` incluído
  - Fallback gracioso em YAML malformado (warning, não crash)
- **Execução paralela de tools** — tools read-only rodam concorrentemente via `asyncio.gather`
  - `file_read`, `grep`, `think`, `memory_search`, `rag_search`, `web_search` etc.
  - Tools de escrita (`file_write`, `command_exec`, etc.) permanecem sequenciais por segurança
  - Agrupamento inteligente: tools paralelas consecutivas agrupadas automaticamente
  - Integração com circuit breaker
- **Comunidade** — SECURITY.md, CODE_OF_CONDUCT, issue/PR templates, Dependabot
- 13 testes novos (Plans routes + tool batching). Total: 295+

### Alterado
- `renderToolCallCard` completamente reescrito com estilização por tool
- Handler SSE de `tool_result` aprimorado com suporte a copy/truncation
- PyYAML adicionado como dependência
- CI: bump actions/checkout v6, actions/upload-artifact v7, actions/setup-python v6, actions/download-artifact v8

### Corrigido
- Rate limiter resetado nos fixtures de teste (corrige CI flaky)

## [0.3.0] - 2026-03-19

### Adicionado
- **18 tools built-in** que transformam o DenAI de chatbot em assistente real
  - `file_read` — leitura de arquivos com números de linha, offset/limit
  - `file_write` — escrita de arquivos com criação automática de diretórios
  - `file_edit` — search/replace com match exato, opção replace_all, sandbox-safe
  - `list_files` — listagem de diretórios com suporte a glob patterns
  - `command_exec` — execução de comandos shell com sandbox de segurança
  - `memory_save` / `memory_search` — memória persistente entre sessões (SQLite)
  - `web_search` — busca DuckDuckGo real por query + fetch de URLs com proteção SSRF
  - `grep` — busca regex em arquivos com filtro por extensão
  - `think` — scratchpad de raciocínio sem side-effects (melhora qualidade em modelos menores)
  - `question` — pausa o LLM e pede input do usuário (async blocking com timeout de 5min)
  - `plan_create` / `plan_update` — planejamento multi-etapas persistido em SQLite
  - `rag_search` / `rag_index` / `rag_stats` — busca local de documentos
- **RAG local com BM25** — busca em documentos de `~/.denai/documents/`, 30+ formatos, zero dependências externas
  - Chunking inteligente com overlap para arquivos grandes
  - Stop words bilíngues (PT-BR + EN)
  - Auto-injeção de contexto relevante nos prompts do chat
  - API completa: stats, index, search, documents, upload, delete
- **Sistema de plugins** — autodiscovery em `~/.denai/plugins/` (single-file + diretório)
  - API routes para listar e gerenciar plugins
- **Context management dinâmico** — janela de contexto auto-escala 8k→32k→64k
  - Estimativa de tokens por mensagem (~4 chars/token)
  - Auto-sumarização quando contexto excede 60% da capacidade
  - Configurável via `DENAI_MAX_CONTEXT` (default: 65536)
- **25 tool call rounds** por mensagem (era 5) — habilita sessões longas multi-etapa
  - Configurável via `DENAI_MAX_TOOL_ROUNDS` (default: 25)
- **Resiliência para modelos locais**
  - Retry com backoff para erros transientes do Ollama (429, 500-504)
  - Recovery hints injetados quando tools falham
  - Circuit breaker: tool que falha 3x consecutivas é bloqueada
  - Backup automático em `~/.denai/backups/` para `file_write` e `file_edit`
- **System prompt reforçado** — regra "read before edit", guidance de error recovery, instrução para usar `think`
- **Multi-step planning** — `plan_create` e `plan_update` com progresso visual (✅ ⬜ 🔄)
- **Model management na UI** — pull e delete de modelos com streaming de progresso
- **Question UI** — cards interativos com botões de opção ou input livre
- Variáveis de ambiente: `DENAI_MAX_TOOL_ROUNDS`, `DENAI_MAX_CONTEXT`
- `.env.example` com todas as variáveis documentadas
- 282 testes passando

### Alterado
- Sistema de tools completamente refatorado de hardcoded para arquitetura extensível
- Rotas de modelos consolidadas em `models.py`

## [0.2.0] - 2026-03-19

### Adicionado
- **Wizard de primeiro uso** — setup guiado em 4 etapas: Welcome → Instalar Ollama → Pull Model → Pronto
- **Dark/Light mode** — toggle com `Ctrl+T`, persistido em localStorage
- **Exportar conversas** — download como JSON ou Markdown via botão no header
- **Busca de conversas** — barra de busca na sidebar, pesquisa em títulos e conteúdo
- **Badge de status do Ollama** — indicador ao vivo no header (polling a cada 15s)
- **Tratamento de erros** — banners contextuais com botão de retry (classifica network, auth, rate limit, server)
- **Feedback visual de tool calling** — spinner CSS, barra de progresso animada, flash de conclusão, contador multi-tool
- **Workflow de publicação PyPI** — GitHub Actions com OIDC publishing
- MANIFEST.in para arquivos estáticos no sdist
- 23 testes de integração (export, search, Ollama status)

### Alterado
- Startup do FastAPI migrado de `on_event` para `lifespan` (elimina warnings de deprecação)
- Metadados e classificadores do pyproject.toml enriquecidos
- Badge do PyPI adicionado ao README

## [0.1.1] - 2026-03-19

### Corrigido
- Vazamento de conexão DB — async context manager (`get_db()`)
- Dependências CDN empacotadas localmente (marked.js, highlight.js, github-dark-dimmed.css)
- Badges do README apontando para o repo correto
- Separador de path do Windows no check de segurança do sandbox
- Mount de StaticFiles para diretório vendor

### Adicionado
- GitHub Actions CI (Ubuntu + Windows, Python 3.10/3.12)
- Extras `[dev]` no pyproject.toml
- `requirements.txt` fallback para usuários de pip

## [0.1.0] - 2026-03-19

### Adicionado
- Release inicial
- Pacote Python modular (33 arquivos, ~2000 LOC)
- Servidor web FastAPI com streaming SSE
- Integração com Ollama (chat, troca de modelo, pull)
- Memória persistente (SQLite)
- Tools built-in: file I/O, comandos shell, busca web, memória
- Segurança: autenticação por API key, rate limiting, filtragem de comandos, sandboxing de paths
- UI web: interface de chat, gerenciamento de conversas, syntax highlighting
- Modo compartilhado (`--compartilhar`) para acesso na rede local
- Scripts de instalação Windows (BAT/PowerShell)
- 84 testes unitários

[Unreleased]: https://github.com/rodrigogobbo/denai/compare/v0.11.0...HEAD
[0.11.0]: https://github.com/rodrigogobbo/denai/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/rodrigogobbo/denai/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/rodrigogobbo/denai/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/rodrigogobbo/denai/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/rodrigogobbo/denai/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/rodrigogobbo/denai/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/rodrigogobbo/denai/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/rodrigogobbo/denai/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/rodrigogobbo/denai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/rodrigogobbo/denai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rodrigogobbo/denai/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/rodrigogobbo/denai/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rodrigogobbo/denai/releases/tag/v0.1.0
