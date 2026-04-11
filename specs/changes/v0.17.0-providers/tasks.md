# Implementation Tasks

## Status: ✅ DONE (PR #36 providers + PR #37 CodeQL+docs + PR #38/#39 path-injection fixes)

- [x] 1. `denai/providers_store.py` — YAML persistence, mask_api_key, 8 templates
  - _Implements: DES-1, REQ-1.1, REQ-1.3, REQ-2.1, REQ-2.2_
- [x] 2. `app.py` — load_providers_from_store() no boot
  - _Implements: REQ-1.2_
- [x] 3. `routes/models.py` — CRUD completo + POST /api/providers/test
  - _Implements: DES-2, REQ-3.1, REQ-3.2, REQ-3.3_
- [x] 4. `security/url_validator.py` — validate_provider_url() anti-SSRF
  - _Implements: DES-3, REQ-4.1, REQ-4.2, REQ-4.3_
- [x] 5. Frontend modal — template dropdown, test connection, edit/remove
  - _Implements: DES-4, REQ-5.1, REQ-5.2_
- [x] 6. config.example.yaml documentado
- [x] 7. 25 novos testes (867 total), bump 0.17.0/0.17.1
