# Requirements Document

## Introduction

DenAI v0.12.0 evolves the assistant from an interactive chat-with-tools into a semi-autonomous agent capable of executing multi-step goals with minimal human intervention. Currently, the LLM processes one user message at a time and calls tools reactively within a 25-round loop, but lacks the ability to take a high-level objective, decompose it into steps, execute them sequentially, and report progress — all while respecting safety boundaries.

This release targets three interconnected capabilities: an **Agent Loop** that orchestrates autonomous multi-step execution with human checkpoints, a **Git Integration Tool** that provides structured git operations instead of relying on raw shell commands, and **Persistent Project Context** that remembers project analysis across sessions to eliminate redundant startup work.

Target users are developers running DenAI locally who want to delegate complex tasks (refactoring a module, implementing a feature from a spec, setting up CI) and have the assistant execute them end-to-end with appropriate guardrails. The scope is limited to local execution — no remote deployment, no multi-user collaboration, no cloud services.

Dependencies: Ollama (or compatible LLM provider), existing DenAI tool infrastructure (file_ops, command_exec, memory, plans), existing permissions system. No new external Python dependencies required.

## Glossary

| Term | Definition |
|------|------------|
| agent_loop | The autonomous execution cycle that processes a goal through plan → execute → verify → report steps |
| goal | A high-level user objective expressed in natural language that the agent decomposes into actionable steps |
| step | A single atomic action within a plan, executed by calling one or more existing tools |
| checkpoint | A pause point where the agent presents progress and waits for human approval before continuing |
| destructive_action | Any tool call that modifies state externally (file_write, file_edit, command_exec) as opposed to read-only operations |
| project_context | A persistent YAML file storing analyzed project metadata (languages, frameworks, structure) that survives across sessions |
| context_injection | The process of automatically loading project_context into the LLM system prompt at session start |
| git_tool | A dedicated tool providing structured git operations with parsed output instead of raw shell commands |

## Requirements

### REQ-1: Agent Loop Orchestration

**User Story:** As a developer, I want to give DenAI a high-level goal and have it autonomously plan and execute the necessary steps, so that I can delegate complex multi-step tasks without manually guiding each tool call.

#### Acceptance Criteria

1.1. WHEN the user sends a message containing a goal prefixed with `/agent` or identified as a multi-step objective, THE system SHALL create an execution plan with numbered steps and present it for approval before executing. _(Event-driven)_

1.2. WHEN the user approves a plan, THE system SHALL execute steps sequentially, calling existing tools (file_read, file_write, file_edit, grep, command_exec, etc.) as needed for each step. _(Event-driven)_

1.3. WHILE executing a plan, THE system SHALL update the plan status after each step completion, marking steps as pending, in_progress, or completed. _(State-driven)_

1.4. WHILE executing a plan, THE system SHALL stream progress messages to the user via SSE, including which step is being executed, tool calls made, and results obtained. _(State-driven)_

1.5. WHERE the permissions system has a tool set to "ask", THE system SHALL pause execution and request explicit user approval before calling that tool. _(Optional)_

1.6. IF a step fails with an error, THEN THE system SHALL pause execution, report the error with context, and ask the user whether to retry, skip, or abort the remaining plan. _(Unwanted behavior)_

1.7. IF the user sends a message while the agent loop is executing, THEN THE system SHALL pause the current execution, process the user message, and then offer to resume, modify, or abort the plan. _(Unwanted behavior)_

1.8. THE system SHALL limit agent loop execution to a maximum of 50 tool calls per plan to prevent runaway execution. _(Ubiquitous)_

1.9. THE system SHALL integrate with the existing undo system, creating a snapshot before each destructive step so the entire plan can be rolled back. _(Ubiquitous)_

### REQ-2: Git Integration Tool

**User Story:** As a developer, I want DenAI to have a dedicated git tool that provides structured output for common git operations, so that git interactions are reliable and parseable instead of depending on raw shell command output.

#### Acceptance Criteria

2.1. THE system SHALL provide a `git` tool that supports the following operations: `status`, `diff`, `log`, `branch`, `add`, `commit`, `checkout`, `stash`. _(Ubiquitous)_

2.2. WHEN the `git status` operation is called, THE system SHALL return a structured object containing staged files, unstaged files, untracked files, current branch, and ahead/behind counts. _(Event-driven)_

2.3. WHEN the `git diff` operation is called with optional file path and ref parameters, THE system SHALL return the diff output with file names, added lines, and removed lines clearly separated. _(Event-driven)_

2.4. WHEN the `git log` operation is called, THE system SHALL return structured entries with hash, author, date, and message, defaulting to the last 10 commits. _(Event-driven)_

2.5. WHEN a write operation (`add`, `commit`, `checkout`, `stash`) is called, THE system SHALL respect the existing permissions system and require "allow" permission for the `git` tool. _(Event-driven)_

2.6. IF a git operation fails (not a git repository, merge conflict, detached HEAD), THEN THE system SHALL return a clear error message with the git stderr output and suggested recovery actions. _(Unwanted behavior)_

2.7. THE system SHALL validate that the working directory is inside a git repository before executing any operation. _(Ubiquitous)_

2.8. THE system SHALL use the existing sandbox/path validation to ensure git operations only affect allowed directories. _(Ubiquitous)_

### REQ-3: Persistent Project Context

**User Story:** As a developer, I want DenAI to remember my project's structure, languages, and frameworks across sessions, so that I don't have to re-explain my project every time I start a new conversation.

#### Acceptance Criteria

3.1. WHEN the `/init` command is executed and completes successfully, THE system SHALL persist the analysis result to `~/.denai/projects/<project_hash>/context.yaml`. _(Event-driven)_

3.2. WHEN a new conversation starts, THE system SHALL check if a context file exists for the current working directory and, if found, inject a summary into the system prompt. _(Event-driven)_

3.3. THE system SHALL generate the project hash from the absolute path of the project root directory to ensure uniqueness. _(Ubiquitous)_

3.4. WHEN the project context file is older than 7 days, THE system SHALL display a notice suggesting the user re-run `/init` to refresh the analysis. _(Event-driven)_

3.5. THE system SHALL store the following in the context file: project name, detected languages with percentages, detected frameworks, git remote URL, directory tree (depth 2), file count, and analysis timestamp. _(Ubiquitous)_

3.6. IF the context file is corrupted or unreadable, THEN THE system SHALL log a warning, ignore the file, and continue without injected context. _(Unwanted behavior)_

3.7. THE system SHALL provide an API endpoint `GET /api/project/context` that returns the current project context if available. _(Ubiquitous)_
