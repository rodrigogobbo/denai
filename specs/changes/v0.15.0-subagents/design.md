# Design Document

## Overview
### Change Type: new-feature

### DES-1: Personas
`denai/personas.py` — discover_personas() lê bundled + `~/.denai/personas/`. Custom sobrescreve pelo nome.

### DES-2: subagent tool
`denai/tools/subagent.py` — chama `stream_chat` com `system_override=persona.system_prompt` e `tools_spec` sem `subagent`. Coleta chunks SSE e retorna string final.

### DES-3: system_override em stream_chat
`llm/ollama.py` — novo parâmetro `system_override: str | None`. Quando presente, substitui `build_system_prompt()`.
