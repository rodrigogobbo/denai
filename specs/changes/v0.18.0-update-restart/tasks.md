# Implementation Tasks

## Status: ✅ DONE (PR #45 update + PR #46/#47 auto-release)

- [x] 1. `routes/update.py` — install SSE streaming + restart endpoint
  - _Implements: DES-1, REQ-1.1, REQ-1.2, REQ-2.1, REQ-2.2_
- [x] 2. Frontend modal — log em tempo real, botões restart
  - _Implements: DES-2, REQ-4.1, REQ-4.2_
- [x] 3. `_waitForReconnect()` — poll + reload
  - _Implements: REQ-2.3_
- [x] 4. Check periódico 6h
  - _Implements: REQ-4.3_
- [x] 5. `ci.yml` job Auto Release — tag + Release + PyPI trusted publishing
  - _Implements: DES-3, REQ-3.1, REQ-3.2, REQ-3.3_
- [x] 6. 4 novos testes de streaming (871 total), bump 0.18.0
