# DenAI — Referência de Tools

> **Versão:** 0.25.0

Tools são funções que o LLM pode chamar durante uma conversa. São auto-descobertas em `denai/tools/` — basta criar um `.py` com a lista `TOOLS`.

## Tabela Resumo

| Tool | Categoria | Modo Plan | Descrição resumida |
|---|---|---|---|
| `file_read` | Arquivo | ✅ | Lê conteúdo de um arquivo |
| `file_write` | Arquivo | ❌ | Cria ou sobrescreve um arquivo |
| `file_edit` | Arquivo | ❌ | Edição cirúrgica (busca/substitui) |
| `list_files` | Arquivo | ✅ | Lista arquivos de um diretório |
| `grep` | Busca | ✅ | Busca regex em arquivos |
| `command_exec` | Execução | ❌ | Executa comandos no terminal |
| `web_search` | Web | ✅ | Busca DuckDuckGo ou busca URL |
| `memory_save` | Memória | ❌ | Salva memória persistente |
| `memory_search` | Memória | ✅ | Busca memórias por palavras-chave |
| `memory_list` | Memória | ✅ | Lista memórias recentes |
| `rag_search` | RAG | ✅ | Busca nos documentos indexados |
| `rag_index` | RAG | ❌ | Reindexar documentos |
| `rag_stats` | RAG | ✅ | Estatísticas do índice RAG |
| `question` | Interação | ✅ | Pergunta ao usuário e aguarda resposta |
| `plan_create` | Planejamento | ❌ | Cria plano de execução step-by-step |
| `plan_update` | Planejamento | ❌ | Atualiza status de um passo |
| `todowrite` | Planejamento | ❌ | Substitui a todo list inteira |
| `todoread` | Planejamento | ✅ | Lê a todo list atual |
| `plans_spec` | Planejamento | ❌ | Gerencia spec documents (markdown) |
| `subagent` | Sub-agentes | ❌ | Delega goal para agente especializado |
| `suggest_skill` | Sugestões | ❌ | Sugere skill relevante ao usuário |
| `suggest_plugin` | Sugestões | ❌ | Sugere plugin relevante ao usuário |
| `think` | Utilitários | ✅ | Scratchpad interno sem side effects |
| `create_document` | Documentos | ❌ | Cria arquivo Word (.docx) |
| `create_spreadsheet` | Documentos | ❌ | Cria planilha Excel (.xlsx) |
| `git` | Git | ❌ | Operações git (status, diff, commit...) |

---

## Arquivo

### `file_read`

Lê o conteúdo de um arquivo dentro do sandbox (home do usuário).

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | ✅ | Caminho do arquivo (absoluto ou relativo ao home) |

**Exemplo:**
```json
{"path": "/home/user/projeto/main.py"}
```

---

### `file_write`

Cria ou sobrescreve completamente um arquivo. Para edições cirúrgicas, prefira `file_edit`.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | ✅ | Caminho do arquivo |
| `content` | string | ✅ | Conteúdo completo a escrever |

---

### `file_edit`

Substituição cirúrgica — busca texto exato e substitui. Cria backup automático antes de editar.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | ✅ | Caminho do arquivo |
| `old` | string | ✅ | Texto exato a buscar |
| `new` | string | ✅ | Texto de substituição |

> ⚠️ Use `file_read` antes de `file_edit` para garantir que o texto existe.

---

### `list_files`

Lista arquivos e diretórios.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | ❌ | Diretório a listar (padrão: home) |
| `pattern` | string | ❌ | Glob pattern (ex: `*.py`) |

---

## Busca

### `grep`

Busca por padrão regex em arquivos. Ignora `.git/`, `node_modules/`, `__pycache__/`.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `pattern` | string | ✅ | Regex a buscar |
| `path` | string | ❌ | Diretório (padrão: home) |
| `include` | string | ❌ | Glob de arquivos (ex: `*.py`) |

---

## Execução

### `command_exec`

Executa comandos no terminal dentro do sandbox. Comandos destrutivos são bloqueados automaticamente (`rm -rf /`, `format`, etc.).

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `command` | string | ✅ | Comando a executar |
| `cwd` | string | ❌ | Diretório de trabalho |
| `timeout` | integer | ❌ | Timeout em segundos (padrão: 30) |

> ⚠️ Permissão padrão: `ask` — requer confirmação do usuário.

---

## Web

### `web_search`

Detecta automaticamente se a query é uma URL (busca conteúdo) ou texto (busca DuckDuckGo).

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `query` | string | ✅ | URL ou termo de busca |

---

## Memória

### `memory_save`

Salva uma informação que persiste entre sessões (SQLite).

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `content` | string | ✅ | O que lembrar (seja específico) |
| `type` | string | ❌ | `fact`, `decision`, `preference`, `observation` (padrão: observation) |
| `tags` | string | ❌ | Tags separadas por vírgula |

---

### `memory_search`

Busca memórias por palavras-chave em conteúdo e tags.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `query` | string | ✅ | Palavras-chave |
| `type` | string | ❌ | Filtrar por tipo |
| `limit` | integer | ❌ | Máximo de resultados (padrão: 10) |

---

### `memory_list`

Lista as memórias mais recentes sem precisar de query.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `type` | string | ❌ | Filtrar por tipo |
| `limit` | integer | ❌ | Máximo de resultados (padrão: 20, máx: 50) |

---

## RAG

Documentos devem estar em `~/.denai/documents/`. Formatos: `.txt`, `.md`, `.py`, `.json`, `.csv`, `.yaml`, `.html`, etc.

### `rag_search`

Busca por similaridade nos documentos indexados (BM25 — zero dependências externas).

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `query` | string | ✅ | Texto a buscar |
| `limit` | integer | ❌ | Número de resultados (padrão: 5) |

---

### `rag_index`

Reindexar todos os documentos em `~/.denai/documents/`.

**Parâmetros:** Nenhum.

---

### `rag_stats`

Retorna estatísticas do índice (quantidade de documentos, tamanho, etc.).

**Parâmetros:** Nenhum.

---

## Interação

### `question`

Para o streaming e exibe um prompt para o usuário responder. Suporta opções pré-definidas ou resposta livre. Timeout de 5 minutos.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `question` | string | ✅ | Texto da pergunta |
| `options` | array | ❌ | Opções de resposta (ex: `["Sim", "Não"]`) |

---

## Planejamento

### `plan_create`

Cria um plano de execução com passos numerados. Persiste em SQLite — sobrevive a reinicializações. Use para tarefas longas que podem ser retomadas.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `goal` | string | ✅ | Objetivo do plano |
| `steps` | array[string] | ✅ | Lista de passos |

---

### `plan_update`

Atualiza o status de um passo do plano atual.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `step` | integer | ✅ | Número do passo (1-based) |
| `status` | string | ✅ | `pending`, `in_progress`, `done` |
| `result` | string | ❌ | Observação ou resultado do passo |

---

### `todowrite`

**Substitui a lista inteira** de todos a cada chamada. Ideal para rastreamento em tempo real da sessão atual. Use IDs explícitos.

**Fluxo correto:**
1. Criar todos em `pending`
2. Marcar `in_progress` ao começar cada item
3. Marcar `completed` logo após terminar — nunca em batch

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `todos` | array | ✅ | Lista completa (substitui o estado atual) |

**Campos de cada todo:**
| Campo | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `id` | string | ✅ | ID único (ex: "1", "setup-db") |
| `content` | string | ✅ | Descrição da tarefa |
| `status` | string | ✅ | `pending`, `in_progress`, `completed` |
| `priority` | string | ❌ | `low`, `medium`, `high` (padrão: medium) |

---

### `todoread`

Lê a todo list atual sem modificá-la.

**Parâmetros:** Nenhum.

---

### `plans_spec`

Gerencia spec documents — arquivos markdown persistentes com lifecycle rico. Diferente de `plan_create` (execução), specs são documentos de referência (RFC, ADR, design doc).

**Parâmetro `action`:**
| Ação | Descrição |
|---|---|
| `create` | Cria novo spec (requer `title` e `content`) |
| `update` | Atualiza title, content, status ou tags (requer `id`) |
| `get` | Retorna conteúdo completo (requer `id`) |
| `list` | Lista todos os specs (metadados) |
| `delete` | Move para `.trash/` — soft delete (requer `id`) |

**Status disponíveis:** `draft` → `active` → `done` → `archived`

**Exemplo — criar:**
```json
{
  "action": "create",
  "title": "Feature: Auth com OAuth",
  "content": "# Auth com OAuth\n\n## Objetivo\n...",
  "status": "draft",
  "tags": "auth,security"
}
```

---

## Sub-agentes

### `subagent`

Delega um goal para um agente especializado com persona própria. Roda em sessão LLM isolada — sem acesso ao histórico do pai.

**Proteções:**
- Sem recursão: `subagent` não está disponível para o sub-agente
- Max 20 tool calls por sub-agente
- Timeout de 120s

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `goal` | string | ✅ | O que o sub-agente deve fazer |
| `persona` | string | ❌ | Nome da persona: `security`, `reviewer`, `writer`, `data` |
| `system_prompt` | string | ❌ | System prompt customizado (substitui `persona`) |
| `model` | string | ❌ | Modelo a usar (herda o padrão se ausente) |

**Exemplos:**
```json
// Code review especializado
{"goal": "Revise o arquivo auth.py em busca de vulnerabilidades", "persona": "security"}

// Documentação técnica
{"goal": "Escreva o README do módulo payments.py", "persona": "writer"}

// Persona customizada
{"goal": "Analise os logs de erro", "system_prompt": "Você é um SRE experiente..."}
```

---

## Sugestões

### `suggest_skill`

Sugere proativamente uma skill ao usuário. Exibe card interativo com botão 1-click install. Use quando o tópico da conversa for coberto por uma skill disponível.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `skill_name` | string | ✅ | Nome ou slug da skill |
| `reason` | string | ✅ | Por que esta skill é útil no contexto atual |

---

### `suggest_plugin`

Sugere proativamente um plugin ao usuário. Mesma mecânica de `suggest_skill`.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `plugin_id` | string | ✅ | ID do plugin |
| `reason` | string | ✅ | Por que este plugin é útil no contexto atual |

---

## Utilitários

### `think`

Scratchpad interno sem side effects. Use para raciocinar antes de executar ações complexas — especialmente antes de editar múltiplos arquivos ou planejar sequências de comandos.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `thought` | string | ✅ | Raciocínio, análise ou plano interno |

---

### `create_document`

Cria arquivo Word (.docx) com formatação rica. Requer `python-docx` instalado.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | ✅ | Caminho do arquivo .docx |
| `content` | array | ✅ | Lista de elementos do documento |

**Tipos de elemento:**
```json
{"type": "heading", "text": "Título", "level": 1}
{"type": "paragraph", "text": "Conteúdo..."}
{"type": "bullet", "items": ["Item 1", "Item 2"]}
{"type": "table", "headers": ["Col A", "Col B"], "rows": [["val1", "val2"]]}
```

---

### `create_spreadsheet`

Cria planilha Excel (.xlsx) com múltiplas abas. Requer `openpyxl` instalado.

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `path` | string | ✅ | Caminho do arquivo .xlsx |
| `sheets` | array | ✅ | Lista de abas |

---

## Git

### `git`

Operações git via tool calling. Permissão padrão: `ask` (requer confirmação para operações de escrita).

**Parâmetros:**
| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `operation` | string | ✅ | `status`, `diff`, `log`, `branch`, `add`, `commit`, `checkout`, `stash` |
| `path` | string | ❌ | Repositório (padrão: diretório atual) |
| `args` | object | ❌ | Argumentos específicos por operação |

**Exemplos:**
```json
{"operation": "status", "path": "/home/user/projeto"}
{"operation": "commit", "path": "/home/user/projeto", "args": {"message": "feat: adicionar login"}}
{"operation": "diff", "args": {"staged": true}}
```

---

## Guia de Uso — Quando usar cada tool de planejamento

| Situação | Tool recomendada |
|---|---|
| Tarefa da sessão atual (3+ passos), progresso visível | `todowrite` |
| Plano longo que pode ser retomado em outra sessão | `plan_create` / `plan_update` |
| Documento de arquitetura / RFC / decisão técnica | `plans_spec` |
| Tarefa com expertise específica (segurança, review, docs) | `subagent` |
| Raciocínio interno antes de agir | `think` |

---

## Adicionando Tools Customizadas

Crie um arquivo `.py` em `denai/tools/` ou em `~/.denai/plugins/`:

```python
# ~/.denai/plugins/minha_tool.py

MINHA_TOOL_SPEC = {
    "type": "function",
    "function": {
        "name": "minha_tool",
        "description": "Faz algo útil",
        "parameters": {
            "type": "object",
            "properties": {
                "entrada": {"type": "string", "description": "Valor de entrada"}
            },
            "required": ["entrada"]
        }
    }
}

async def minha_tool(args: dict) -> str:
    entrada = args.get("entrada", "")
    return f"Processado: {entrada}"

TOOLS = [(MINHA_TOOL_SPEC, "minha_tool")]
```

A tool é auto-descoberta na próxima requisição ou após `POST /api/plugins/reload`.

---

## Comandos de Chat

Além das 26 tools, o DenAI suporta comandos slash no chat:

| Comando | Descrição |
|---|---|
| `/context <caminho>` | Indexa diretório e ativa contexto de repositório na sessão |
| `/context off` | Desativa o contexto e limpa o índice |
| `/context` | Mostra o projeto atualmente ativo |

Quando `/context` está ativo, `rag_search` busca automaticamente no índice da sessão (ícone 📁) em vez de `~/.denai/documents/`.

| `/specs` | Lista specs SDS em `specs/changes/` do projeto ativo via `/context`, com botões "📄 Ver" e "🔍 Analisar" |
| `/specs <slug>` | Exibe requirements.md + design.md + tasks.md de uma spec |
| `/specs <slug> analyze` | Analisa status de implementação da spec usando o LLM (streaming) |
