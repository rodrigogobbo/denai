# Requirements — Notificação Electron: agent concluído

## REQ-1: Disparar notificação ao término do agent loop
- REQ-1.1: Quando o agent loop emite evento SSE `agent_complete`, o Electron deve exibir uma notificação nativa
- REQ-1.2: Título: "DenAI — Tarefa concluída"
- REQ-1.3: Corpo: primeiros 60 chars do goal + " · N steps"
- REQ-1.4: A notificação só deve disparar se a janela do DenAI NÃO estiver em foco (para evitar redundância)

## REQ-2: Monitoramento SSE no processo principal
- REQ-2.1: `main.js` deve assinar o SSE de status do agent (`GET /api/agent/status`) quando um agent job é iniciado
- REQ-2.2: Ao receber `agent_complete` ou `agent_aborted`, encerrar o listener SSE
- REQ-2.3: O frontend deve notificar o processo principal via IPC (`ipcRenderer.send('agent-started', {goal, jobId})`) ao iniciar um job

## REQ-3: Sem regressão
- REQ-3.1: Notificações de Ollama offline/online e update disponível não são afetadas
