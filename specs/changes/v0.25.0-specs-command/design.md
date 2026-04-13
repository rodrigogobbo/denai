# Design Document

## Overview
### Change Type: new-feature

### Design Goals
1. Reutilizar context_store — sem nova infraestrutura de indexação
2. Leitura direta de arquivos — sem banco, sem indexação
3. Integração natural com o fluxo /context existente

### References
- REQ-1: Comando /specs
- REQ-2: Conteúdo exibido
- REQ-3: Backend

---

## DES-1: routes/specs.py

```python
# POST /api/specs/list
# Body: {conversation_id}
# → verifica context_store.get_context(conv_id)
# → localiza specs_dir = Path(ctx['path']) / 'specs' / 'changes'
# → retorna lista de slugs ordenados

# POST /api/specs/read
# Body: {conversation_id, slug}
# → lê requirements.md + design.md + tasks.md
# → concatena com separadores markdown
# → retorna como string
```

### DES-2: Frontend — interceptar /specs no chat.js

```js
// Em sendMessage(), antes de enviar para o servidor:
if (text === '/specs') → _handleSpecsList()
if (text.match(/^\/specs\s+(.+)/)) → _handleSpecsRead(slug)
if (text === '/specs help') → _showSpecsHelp()
```

### DES-3: _handleSpecsList()

1. Verifica se há contexto ativo (`window._activeContext`)
2. Chama `POST /api/specs/list`
3. Renderiza no chat como mensagem do assistente:
   ```
   📋 Specs em myproject/specs/changes/:
   [1] v0.12.0-agentic-workflows
   [2] v0.13.0-memory-plans-spec
   ...
   Use /specs <slug> para ver o conteúdo.
   ```

### DES-4: _handleSpecsRead(slug)

1. Chama `POST /api/specs/read`
2. Renderiza o markdown com `renderMarkdown(content)`
3. Longa — usar mensagem colapsável ou scroll

### DES-5: Integração com /api/commands

Adicionar entrada `context` no `discover_commands()` ou registrar `/specs` como comando interno (sem arquivo .md), similar ao `/context`.
