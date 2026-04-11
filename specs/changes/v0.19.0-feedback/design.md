# Design Document

## Overview
### Change Type: new-feature

### DES-1: routes/feedback.py
`POST /api/feedback` — valida, coleta contexto, formata issue body em markdown, chama `_submit_to_github()` ou `_save_locally()`.

`_collect_context()` — versão, platform, Python, Ollama status via httpx.
`_format_issue_body()` — markdown com seções Descrição, Contexto, Logs. Footer: "Reportado via DenAI in-app feedback".

### DES-2: Frontend
`feedback.js` — `openFeedbackModal()`, `setFeedbackType()`, `submitFeedback()`, `resetFeedbackForm()`. CSS em `components.css`. Botão 💬 no header antes do Export.

### DES-3: Config
`config.yaml` — seção `feedback.github_token` + `feedback.repo` (default: rodrigogobbo/denai).
