# Requirements Document

## Introduction

Sub-agentes com persona permitem que o LLM principal delegue tarefas para agentes especializados. O DenAI tinha agent loop mas sem o conceito de persona — todo agente usava o mesmo system prompt genérico. Este change adiciona personas bundled e a tool `subagent`.

## Requirements

### REQ-1: Personas
1.1. THE system SHALL support personas defined as `.md` files with YAML frontmatter (name, description). _(Ubiquitous)_
1.2. THE system SHALL load bundled personas from `denai/personas_bundled/`: security, reviewer, writer, data. _(Ubiquitous)_
1.3. Custom personas in `~/.denai/personas/*.md` SHALL override bundled personas with the same name. _(Ubiquitous)_
1.4. `GET /api/personas` SHALL list all available personas (bundled + custom) with source field. _(Ubiquitous)_

### REQ-2: subagent Tool
2.1. THE system SHALL provide a `subagent` tool that delegates a goal to an isolated LLM session with a custom system prompt. _(Ubiquitous)_
2.2. THE subagent SHALL accept: `goal` (required), `persona` (optional name), `system_prompt` (optional override), `model` (optional). _(Ubiquitous)_
2.3. THE subagent SHALL NOT have access to the `subagent` tool (no recursion). _(Ubiquitous)_
2.4. THE subagent SHALL be limited to 20 tool calls and 120s timeout. _(Ubiquitous)_
2.5. `stream_chat` SHALL accept a `system_override` parameter to support isolated system prompts. _(Ubiquitous)_
