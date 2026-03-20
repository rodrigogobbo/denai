# Implementation Tasks

## Overview

This task breakdown implements DenAI v0.12.0 (Agentic Workflows, Git Tool, Persistent Project Context) with 6 phases:

1. **Persistent Project Context** - Extend project.py with persistence and prompt injection
2. **Git Integration Tool** - New git_ops.py tool with structured output
3. **Agent Loop Core** - Agent orchestrator with plan decomposition and step execution
4. **Agent SSE & Routes** - API routes and progress streaming for agent loop
5. **Acceptance Criteria Testing** - Test coverage for all acceptance criteria
6. **Final Checkpoint** - Validation and version bump

**Estimated Effort**: High (3-4 sessions)

---

## Phase 1: Persistent Project Context

- [ ] 1.1 Add context persistence to project.py
  - Add `save_context(result: dict, project_path: str)` function that writes analysis result to `~/.denai/projects/<hash>/context.yaml`
  - Compute hash as `hashlib.sha256(abs_path.encode()).hexdigest()[:12]`
  - Create directories with `parents=True, exist_ok=True`
  - Add `analyzed_at` timestamp to the saved data
  - _Implements: DES-4, REQ-3.1, REQ-3.3, REQ-3.5_

- [ ] 1.2 Add context loading to project.py
  - Add `load_context(project_path: str) -> dict | None` function that reads the YAML file
  - Add `is_context_stale(context: dict, max_days: int = 7) -> bool` function
  - Handle corrupted/unreadable files gracefully (return None, log warning)
  - _Depends: 1.1_
  - _Implements: DES-4, REQ-3.2, REQ-3.4, REQ-3.6_

- [ ] 1.3 Inject project context into system prompt
  - Modify `denai/llm/prompt.py` to call `load_context()` and append a "Project Context" section to the system prompt when available
  - Add `to_prompt_summary(context: dict) -> str` helper that formats context as concise markdown
  - If context is stale, append a notice line: "⚠️ Project context is X days old. Run /init to refresh."
  - _Depends: 1.2_
  - _Implements: DES-4, REQ-3.2, REQ-3.4_

- [ ] 1.4 Call save_context from /init route
  - Modify `denai/routes/project.py` `init_project` and `init_project_get` to call `save_context()` after successful analysis
  - _Depends: 1.1_
  - _Implements: DES-4, REQ-3.1_

- [ ] 1.5 Add GET /api/project/context endpoint
  - Add new route in `denai/routes/project.py` that loads and returns the current project context, or 404 if not found
  - _Depends: 1.2_
  - _Implements: DES-4, REQ-3.7_

---

## Phase 2: Git Integration Tool

- [ ] 2.1 Create git_ops.py with read operations
  - Create `denai/tools/git_ops.py` with tool decorator
  - Implement `git` tool function with `operation` parameter
  - Implement `status` operation: parse `git status --porcelain=v2 --branch` into structured dict `{branch, staged[], unstaged[], untracked[], ahead, behind}`
  - Implement `diff` operation: parse `git diff` with optional `path` and `ref` parameters, return `{files[{name, added, removed, patch}]}`
  - Implement `log` operation: parse `git log --format` with `limit` parameter (default 10), return `{commits[{hash, author, date, message}]}`
  - Implement `branch` operation: parse `git branch` output, return `{branches[], current}`
  - Add repo validation: check `.git` directory exists before any operation
  - Apply sandbox path validation via `is_path_allowed()`
  - _Implements: DES-3, REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4, REQ-2.7, REQ-2.8_

- [ ] 2.2 Add write operations to git_ops.py
  - Implement `add` operation: run `git add` with paths, return `{added[]}`
  - Implement `commit` operation: run `git commit -m`, return `{hash, message}`
  - Implement `checkout` operation: run `git checkout`, return `{branch}`
  - Implement `stash` operation: run `git stash push/pop/list`, return `{result}`
  - Gate write operations through permissions system (`check_permission("git")`)
  - _Depends: 2.1_
  - _Implements: DES-3, REQ-2.1, REQ-2.5_

- [ ] 2.3 Add git error handling
  - Handle "not a git repository" with clear message and suggestion
  - Handle merge conflicts with file list
  - Handle detached HEAD state
  - Return structured error dict with `{error, stderr, suggestion}`
  - _Depends: 2.1_
  - _Implements: DES-3, REQ-2.6_

---

## Phase 3: Agent Loop Core

- [ ] 3.1 Create agent.py with AgentPlan and AgentStep models
  - Create `denai/agent.py`
  - Define `AgentStep` dataclass: index, description, tool_name, tool_args, status, result, error
  - Define `AgentPlan` dataclass: goal, steps, status, max_tool_calls (default 50), created_at
  - Add status transitions: pending → approved → executing → completed/failed/aborted
  - _Implements: DES-1, REQ-1.3_

- [ ] 3.2 Implement plan decomposition via LLM
  - Add `async decompose_goal(goal: str) -> AgentPlan` function
  - Send goal to LLM with a structured prompt requesting JSON plan output
  - Parse LLM response into AgentPlan with steps
  - Validate plan has at least 1 step and no more than 50 tool calls
  - Handle LLM parse failures gracefully (retry once, then error)
  - _Depends: 3.1_
  - _Implements: DES-1, REQ-1.1_

- [ ] 3.3 Implement step executor
  - Add `async execute_step(step: AgentStep) -> dict` function
  - Call `execute_tool(step.tool_name, step.tool_args)` from registry
  - Create undo snapshot before destructive tool calls (file_write, file_edit, command_exec, git write ops)
  - Check permissions before execution — if tool is "ask", pause and return special status
  - Track total tool calls across all steps, abort if exceeding max_tool_calls
  - _Depends: 3.1_
  - _Implements: DES-1, REQ-1.2, REQ-1.5, REQ-1.8, REQ-1.9_

- [ ] 3.4 Implement agent loop with error handling
  - Add `async run_plan(plan: AgentPlan) -> AsyncGenerator` function
  - Iterate through steps, yielding progress events
  - On step failure: pause, yield error event, wait for user decision (retry/skip/abort)
  - On max tool calls: abort with progress report
  - On plan completion: yield summary event
  - _Depends: 3.2, 3.3_
  - _Implements: DES-1, REQ-1.2, REQ-1.3, REQ-1.6, REQ-1.8_

---

## Phase 4: Agent SSE & Routes

- [ ] 4.1 Create agent routes
  - Create `denai/routes/agent.py` with router
  - `POST /api/agent/start` — receives goal, calls decompose_goal, returns plan via SSE event `agent_plan`
  - `POST /api/agent/approve` — approves plan, starts execution, streams `agent_step_start/complete/error` events
  - `POST /api/agent/abort` — aborts current plan
  - `GET /api/agent/status` — returns current plan status
  - _Depends: 3.4_
  - _Implements: DES-2, REQ-1.4_

- [ ] 4.2 Integrate agent detection in chat route
  - Modify `denai/routes/chat.py` to detect `/agent` prefix in user messages
  - When detected, redirect to agent start flow instead of regular stream_chat
  - _Depends: 4.1_
  - _Implements: DES-2, REQ-1.1_

- [ ] 4.3 Handle user messages during execution
  - Add interrupt mechanism in agent loop: check for incoming messages between steps
  - When user message received during execution, pause current plan, process message, yield `agent_paused` event
  - Offer resume/modify/abort options
  - _Depends: 4.1_
  - _Implements: DES-2, REQ-1.7_

- [ ] 4.4 Register new routes in app.py
  - Add agent router to FastAPI app in `denai/app.py`
  - _Depends: 4.1_
  - _Implements: DES-2_

---

## Phase 5: Acceptance Criteria Testing

- [ ] 5.1 Test: Agent loop creates execution plan from goal
  - Verify that when a goal is provided, the system generates an AgentPlan with numbered steps and presents it before executing
  - Test type: unit
  - _Depends: 3.2_
  - _Implements: REQ-1.1_

- [ ] 5.2 Test: Agent loop executes steps sequentially using existing tools
  - Verify that approved plan steps are executed in order, calling the correct tools with correct arguments
  - Test type: integration
  - _Depends: 3.4_
  - _Implements: REQ-1.2_

- [ ] 5.3 Test: Plan status updates after each step
  - Verify that step status transitions from pending → in_progress → completed as execution progresses
  - Test type: unit
  - _Depends: 3.3_
  - _Implements: REQ-1.3_

- [ ] 5.4 Test: Progress events are streamed during execution
  - Verify that SSE events (agent_step_start, agent_step_complete) are yielded during plan execution
  - Test type: integration
  - _Depends: 4.1_
  - _Implements: REQ-1.4_

- [ ] 5.5 Test: Agent pauses for permission-gated tools
  - Verify that when a tool has "ask" permission, the agent loop pauses and yields a permission request event
  - Test type: unit
  - _Depends: 3.3_
  - _Implements: REQ-1.5_

- [ ] 5.6 Test: Agent handles step failure with retry/skip/abort options
  - Verify that on tool execution error, the loop pauses and offers the three recovery options
  - Test type: unit
  - _Depends: 3.4_
  - _Implements: REQ-1.6_

- [ ] 5.7 Test: Agent pauses when user sends message during execution
  - Verify that an incoming user message during loop execution triggers a pause and agent_paused event
  - Test type: integration
  - _Depends: 4.3_
  - _Implements: REQ-1.7_

- [ ] 5.8 Test: Agent loop enforces 50 tool call limit
  - Verify that the loop aborts when cumulative tool calls exceed max_tool_calls
  - Test type: unit
  - _Depends: 3.4_
  - _Implements: REQ-1.8_

- [ ] 5.9 Test: Undo snapshots are created before destructive steps
  - Verify that undo.create_snapshot is called before file_write, file_edit, command_exec, and git write operations
  - Test type: unit
  - _Depends: 3.3_
  - _Implements: REQ-1.9_

- [ ] 5.10 Test: Git tool returns structured status output
  - Verify that git status returns dict with branch, staged, unstaged, untracked, ahead, behind fields
  - Test type: unit
  - _Depends: 2.1_
  - _Implements: REQ-2.1, REQ-2.2_

- [ ] 5.11 Test: Git diff returns structured diff output
  - Verify that git diff returns files with name, added, removed, patch fields
  - Test type: unit
  - _Depends: 2.1_
  - _Implements: REQ-2.3_

- [ ] 5.12 Test: Git log returns structured commit entries
  - Verify that git log returns commits with hash, author, date, message, defaulting to 10 entries
  - Test type: unit
  - _Depends: 2.1_
  - _Implements: REQ-2.4_

- [ ] 5.13 Test: Git write operations respect permissions
  - Verify that add/commit/checkout/stash check permissions before executing
  - Test type: unit
  - _Depends: 2.2_
  - _Implements: REQ-2.5_

- [ ] 5.14 Test: Git tool handles errors with structured messages
  - Verify that git errors (not a repo, conflict, detached HEAD) return error dict with stderr and suggestion
  - Test type: unit
  - _Depends: 2.3_
  - _Implements: REQ-2.6_

- [ ] 5.15 Test: Git tool validates working directory is a git repo
  - Verify that operations on non-git directories return appropriate error
  - Test type: unit
  - _Depends: 2.1_
  - _Implements: REQ-2.7_

- [ ] 5.16 Test: Git tool uses sandbox path validation
  - Verify that is_path_allowed is called before git operations
  - Test type: unit
  - _Depends: 2.1_
  - _Implements: REQ-2.8_

- [ ] 5.17 Test: Project context is persisted after /init
  - Verify that context.yaml is written to ~/.denai/projects/<hash>/ after successful analysis
  - Test type: integration
  - _Depends: 1.4_
  - _Implements: REQ-3.1_

- [ ] 5.18 Test: Project context is injected into system prompt on new session
  - Verify that when context file exists, its summary appears in the system prompt
  - Test type: unit
  - _Depends: 1.3_
  - _Implements: REQ-3.2_

- [ ] 5.19 Test: Project hash is generated from absolute path
  - Verify that hash is deterministic and uses sha256[:12] of the absolute path
  - Test type: unit
  - _Depends: 1.1_
  - _Implements: REQ-3.3_

- [ ] 5.20 Test: Stale context displays refresh notice
  - Verify that contexts older than 7 days trigger a notice in the prompt summary
  - Test type: unit
  - _Depends: 1.3_
  - _Implements: REQ-3.4_

- [ ] 5.21 Test: Context file stores all required fields
  - Verify YAML contains project_name, languages, frameworks, git_remote, file_count, tree, timestamp
  - Test type: unit
  - _Depends: 1.1_
  - _Implements: REQ-3.5_

- [ ] 5.22 Test: Corrupted context file is handled gracefully
  - Verify that unreadable/corrupted YAML returns None and logs warning without crashing
  - Test type: unit
  - _Depends: 1.2_
  - _Implements: REQ-3.6_

- [ ] 5.23 Test: GET /api/project/context returns context or 404
  - Verify the endpoint returns context when available, 404 when not
  - Test type: integration
  - _Depends: 1.5_
  - _Implements: REQ-3.7_

---

## Phase 6: Final Checkpoint

- [ ] 6.1 Verify all acceptance criteria
  - REQ-1: Confirm agent loop creates plans, executes steps, handles errors, respects permissions and limits
  - REQ-2: Confirm git tool provides all 8 operations with structured output and proper error handling
  - REQ-3: Confirm project context is persisted, loaded, injected, and handles edge cases
  - Run full test suite: `make all`
  - Verify ruff check + format pass
  - Verify coverage >= 75%
  - _Implements: All requirements_

- [ ] 6.2 Bump version to 0.12.0
  - Update `denai/version.py` to `VERSION = "0.12.0"`
  - Update CHANGELOG.md with v0.12.0 entry
  - _Implements: All requirements_
