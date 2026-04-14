# Tasks — Notificação Electron: agent concluído

- [ ] **TASK-1**: Adicionar `_watchAgentJob(goal, jobId)` em `main.js` usando fetch SSE
  _Implements: REQ-2.1, REQ-2.2_
- [ ] **TASK-2**: Registrar `ipcMain.on('agent-started', ...)` em `main.js`
  _Implements: REQ-2.3_
- [ ] **TASK-3**: Expor `agentStarted(goal, jobId)` no `preload.js` via contextBridge
  _Implements: REQ-2.3_
- [ ] **TASK-4**: Chamar `window.electron?.agentStarted(goal, jobId)` no frontend ao receber response de `/api/agent/start`
  _Implements: REQ-1.1_
- [ ] **TASK-5**: Notificação condicional: só disparar se `!mainWindow.isFocused()`
  _Implements: REQ-1.4_
- [ ] **TASK-6**: Testes unitários para `_watchAgentJob` (mock EventSource)
  _Implements: REQ-3.1_
