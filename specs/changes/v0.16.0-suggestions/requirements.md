# Requirements Document

## Introduction

Sugestões proativas permitem que o LLM sugira skills e plugins relevantes sem o usuário pedir. O mecanismo usa um prefixo especial no resultado da tool que o SSE stream intercepta e converte em evento `suggestion` para o frontend renderizar como card interativo.

## Requirements

1.1. THE system SHALL provide `suggest_skill` and `suggest_plugin` tools with `skill_name`/`plugin_id` and `reason` parameters. _(Ubiquitous)_
1.2. WHEN a suggestion tool is called, THE system SHALL emit an SSE event `{"suggestion": {"type": "skill"|"plugin", "id": "...", "reason": "..."}}` instead of a `tool_result` event. _(Event-driven)_
1.3. THE frontend SHALL render suggestion cards with a 1-click install button and a dismiss button. _(Ubiquitous)_
1.4. THE install button SHALL call `/api/skills/install` or `/api/marketplace/install` respectively. _(Event-driven)_
1.5. Suggestion tools SHALL NOT be available in Plan mode. _(Ubiquitous)_
1.6. THE system prompt SHALL instruct the LLM to suggest proactively (max 1-2 per response) when relevant. _(Ubiquitous)_
