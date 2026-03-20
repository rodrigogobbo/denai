# Changelog

Todas as mudanças notáveis do DenAI serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Unreleased]

_Nenhuma mudança desde v0.6.0 ainda._

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

[Unreleased]: https://github.com/rodrigogobbo/denai/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/rodrigogobbo/denai/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/rodrigogobbo/denai/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/rodrigogobbo/denai/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/rodrigogobbo/denai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/rodrigogobbo/denai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/rodrigogobbo/denai/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/rodrigogobbo/denai/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/rodrigogobbo/denai/releases/tag/v0.1.0
