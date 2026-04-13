# Design Document

## Overview
### Change Type: new-feature

### Design Goals
1. Zero migration para usuários existentes — perfil `default` usa `~/.denai/` diretamente
2. Isolamento de DB e providers por perfil
3. UI simples — dropdown no header, sem páginas extras

### References
- REQ-1: Estrutura de perfis
- REQ-2: CLI e API
- REQ-3: UI
- REQ-4: Isolamento de dados

---

## DES-1: Estrutura de diretórios

```
~/.denai/                        ← perfil default (dados existentes)
  denai.db
  config.yaml
  providers.yaml
  profiles/
    work/                        ← perfil "work"
      denai.db
      config.yaml
      providers.yaml
    personal/                    ← perfil "personal"
      denai.db
      config.yaml
      providers.yaml
  active_profile                 ← arquivo com nome do perfil ativo
```

### DES-2: profile_manager.py

```python
# denai/profile_manager.py

PROFILES_DIR = DATA_DIR / "profiles"
ACTIVE_PROFILE_FILE = DATA_DIR / "active_profile"

def get_active_profile() -> str:
    """Lê o perfil ativo do arquivo. Default: 'default'."""

def set_active_profile(name: str) -> None:
    """Grava o perfil ativo no arquivo."""

def get_profile_dir(name: str) -> Path:
    """Retorna o diretório do perfil. 'default' → DATA_DIR."""

def list_profiles() -> list[dict]:
    """Lista todos os perfis disponíveis."""

def create_profile(name: str) -> Path:
    """Cria diretório do perfil e retorna o path."""

def delete_profile(name: str) -> bool:
    """Remove o diretório do perfil."""
```

### DES-3: config.py — DATA_DIR e DB_PATH dinâmicos

```python
# Ler perfil ativo no boot (antes de qualquer import de rotas)
from .profile_manager import get_active_profile, get_profile_dir

_active_profile = get_active_profile()
_profile_dir = get_profile_dir(_active_profile)

DATA_DIR = _profile_dir          # ← dinâmico
DB_PATH = DATA_DIR / "denai.db"
CONFIG_YAML_PATH = DATA_DIR / "config.yaml"
```

O perfil `default` retorna `Path.home() / ".denai"` — retrocompatível.

### DES-4: CLI

```python
# __main__.py
parser.add_argument("--profile", default=None, help="Perfil a usar")

if CLI.profile:
    from .profile_manager import set_active_profile
    set_active_profile(CLI.profile)
```

### DES-5: routes/profiles.py

```
GET  /api/profiles          → list_profiles()
POST /api/profiles           → create_profile(name)
POST /api/profiles/{name}/activate → set_active_profile + reload hint
DELETE /api/profiles/{name}  → delete_profile(name)
GET  /api/profiles/active    → get_active_profile()
```

### DES-6: Frontend — seletor no header

```html
<div class="profile-selector" id="profileSelector">
  <span id="activeProfileLabel">default</span>
  <div class="profile-dropdown" id="profileDropdown">
    <!-- lista de perfis + botão + -->
  </div>
</div>
```

Ao trocar de perfil: `POST /api/profiles/{name}/activate` → `window.location.reload()`.

### DES-7: O que é compartilhado vs isolado

| Recurso | Isolado por perfil | Compartilhado |
|---|---|---|
| Conversas + mensagens | ✅ `denai.db` | — |
| Memórias | ✅ `denai.db` | — |
| Providers | ✅ `providers.yaml` | — |
| Config (model, port, etc.) | ✅ `config.yaml` | — |
| Skills | — | ✅ `~/.denai/skills/` |
| Personas | — | ✅ `~/.denai/personas/` |
| RAG documents | — | ✅ `~/.denai/documents/` |
| API key | — | ✅ `~/.denai/api.key` |
| Plugins | — | ✅ `~/.denai/plugins/` |
