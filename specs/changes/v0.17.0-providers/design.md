# Design Document

## Overview
### Change Type: new-feature + security

### DES-1: providers_store.py
CRUD sobre `~/.denai/providers.yaml`. `mask_api_key()` retorna string mascarada. `_ensure_secure_file()` aplica chmod 600.

### DES-2: routes/models.py
CRUD endpoints + `POST /api/providers/test`. Pydantic `ProviderBody` para validação.

### DES-3: security/url_validator.py
`validate_provider_url()` — urlparse + blocklist de IPs + DNS resolution check + urlunparse para quebrar taint no CodeQL. `allow_localhost=True` para LM Studio/LocalAI em dev.

### DES-4: Frontend
`models.js` reescrito — `openProviderModal()`, `_renderModalProviderList()`, `applyTemplate()`, `testProviderConnection()`, `saveProvider()`, `removeProviderUI()`. CSS em `components.css`.
