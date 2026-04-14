# Requirements — /specs analyze

## REQ-1: Análise automática de spec com LLM
- REQ-1.1: `POST /api/specs/analyze` recebe `conversation_id` e `slug`, carrega o conteúdo da spec e envia ao LLM com o contexto do repositório ativo
- REQ-1.2: O LLM deve responder em streaming SSE (mesma interface de `/api/chat`)
- REQ-1.3: A resposta deve indicar: tasks concluídas (✅ [x]) vs pendentes (⬜ [ ]), arquivos relevantes encontrados e um resumo de 2-3 linhas

## REQ-2: Tool para agent loop
- REQ-2.1: Tool `specs_analyze` disponível no agent loop com parâmetros `slug` (obrigatório) e `question` (opcional, default: "qual o status desta implementação?")

## REQ-3: Frontend
- REQ-3.1: Comando `/specs <slug>` exibe o conteúdo atual (comportamento existente)
- REQ-3.2: Botão "🔍 Analisar" ao lado de cada spec na listagem — dispara streaming
- REQ-3.3: Alternativa: `/specs <slug> analyze` como sub-comando
