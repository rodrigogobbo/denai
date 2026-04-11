# Implementation Tasks

## Status: ✅ DONE (PR #33, v0.15.0)

- [x] 1. `denai/personas.py` — discover_personas(), get_persona(), parse YAML frontmatter
  - _Implements: DES-1, REQ-1.1, REQ-1.2, REQ-1.3_
- [x] 2. 4 personas bundled: security, reviewer, writer, data
  - _Implements: REQ-1.2_
- [x] 3. `denai/tools/subagent.py` — tool + mini-loop com system_override
  - _Implements: DES-2, REQ-2.1, REQ-2.2, REQ-2.3, REQ-2.4_
- [x] 4. `llm/ollama.py` — parâmetro system_override
  - _Implements: DES-3, REQ-2.5_
- [x] 5. `GET /api/personas`
  - _Implements: REQ-1.4_
- [x] 6. 29 novos testes (824 total), bump 0.15.0
