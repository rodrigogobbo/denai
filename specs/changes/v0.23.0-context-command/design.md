# Design Document

## Overview
### Change Type: new-feature

### Design Goals
1. Reutilizar RAG e project.py existentes — zero nova infraestrutura
2. Estado de contexto por conversa, não global
3. Sem persistência — contexto vive na sessão de chat

### References
- REQ-1: Comando /context
- REQ-2: Indexação
- REQ-3: Project summary injection
- REQ-4: UX

---

## DES-1: context_store.py — estado da sessão

```python
# denai/context_store.py
# Estado global de contexto por conversation_id
_active_contexts: dict[str, dict] = {}
# {conv_id: {path, summary, index, file_count, project_name}}
```

Simples dict em memória. Limpo quando o servidor reinicia ou o usuário usa `/context off`.

## DES-2: Indexação — reusar RAG

O RAG existente usa `DOCS_DIR = ~/.denai/documents/`. O contexto de sessão usa um índice separado em memória:

```python
# denai/context_store.py
def index_directory(path: str, conv_id: str) -> dict:
    """Indexa um diretório e salva o estado no contexto da sessão."""
    # 1. analyze_project(path) → project summary
    # 2. Coletar arquivos (respeitando .gitignore, limites)
    # 3. Criar índice BM25 em memória (reusar lógica de rag/__init__.py)
    # 4. Salvar em _active_contexts[conv_id]
    return {"file_count": n, "project_name": name, "summary": summary}
```

## DES-3: Injeção no system prompt — ollama.py

```python
# Em stream_chat(), após build_system_prompt():
context = get_active_context(conversation_id)
if context:
    context_block = f"\n\n## Contexto do Repositório\n{context['summary']}"
    system_content = system_content + context_block
```

O `conversation_id` é passado via parâmetro existente no `POST /api/chat`.

## DES-4: Busca contextual — tool rag_search override

Quando contexto ativo, a tool `rag_search` usa o índice da sessão em vez de `~/.denai/documents/`:

```python
async def rag_search(args: dict) -> str:
    conv_id = args.get("_conv_id")
    if conv_id and has_active_context(conv_id):
        return search_context_index(conv_id, args["query"])
    return search_documents(args["query"])  # comportamento padrão
```

## DES-5: Rota POST /api/context/activate

```
POST /api/context/activate
Body: {path, conversation_id}
Response: {ok, file_count, project_name, summary_preview}
```

## DES-6: Comando /context

Em `denai/commands.py` ou como custom command em `~/.denai/commands/`:

```yaml
name: context
description: "Ativa contexto de repositório para a sessão"
```

O frontend intercepta `/context <path>` → chama `POST /api/context/activate` → injeta mensagem de confirmação no chat.

## DES-7: Badge no chat input

```js
// ui.js — quando contexto ativo na conversa atual
if (activeContext) {
  DOM.inputModelLabel.innerHTML += ` <span class="context-badge">📁 ${activeContext.project_name}</span>`
}
```

## DES-8: Limites de indexação

```python
MAX_FILES = 500
MAX_SIZE_MB = 50
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'dist', 'build', '.next', 'venv', '.venv'}
SKIP_EXTENSIONS = {'.pyc', '.lock', '.ico', '.png', '.jpg', '.whl', '.zip'}
```

Respeitar `.gitignore` via leitura simples do arquivo (sem dep extra).
