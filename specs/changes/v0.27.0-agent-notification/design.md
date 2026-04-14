# Design — Notificação Electron: agent concluído

## Fluxo

```
Frontend (chat.js)
  └─ inicia agent job
  └─ ipcRenderer.send('agent-started', { goal, jobId })
         │
         ▼
main.js
  └─ ipcMain.on('agent-started')
  └─ abre EventSource → GET /api/agent/status?job_id=<jobId>
  └─ ao receber agent_complete:
       if (!mainWindow.isFocused()) → _sendNotification()
  └─ fecha listener SSE
```

## Mudanças por arquivo

| Arquivo | Mudança |
|---|---|
| `electron/src/main.js` | `ipcMain.on('agent-started')` + `_watchAgentJob()` |
| `electron/src/preload.js` | expor `agentStarted(goal, jobId)` via contextBridge |
| `frontend/src/agent.js` (ou chat.js) | chamar `window.electron.agentStarted(goal, jobId)` ao iniciar |

## Notas
- Usar `fetch` nativo do Node.js (já disponível no Electron 22+) para SSE simples
- jobId vem do response de `POST /api/agent/start`
- goal vem do input do usuário — truncar a 60 chars na notificação
