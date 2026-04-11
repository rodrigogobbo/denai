# Design Document

## Overview
### Change Type: new-feature

### DES-1: system_profile.py
- `MODEL_CATALOG`: lista de ModelOption com name, size_gb, ram_min_gb, description, emoji
- `TIERS`: lista de (threshold, tier_name)
- `TIER_DEFAULTS`: dict tier → model name
- `_get_ram_gb()`, `_get_vram_gb()`, `_get_disk_free_gb()`, `_get_cpu_cores()`, `_get_installed_models()`
- `_get_tier(ram_gb, vram_gb)`: considera VRAM boost (não ARM)
- `_best_installed(installed, tier, ram_gb)`: filtra catálogo por RAM e instalado, retorna mais pesado compatível
- `_recommend(tier, ram_gb, installed)`: installed > tier_default > disk check
- `_alternatives(current, ram_gb)`: até 4 alternativas compatíveis
- `get_system_profile()`: agrega tudo, adiciona compatibility flags por modelo

### DES-2: routes/system.py
`GET /api/system/profile` → `get_system_profile()`.

### DES-3: config.py
`_auto_model()` delega para `_get_ram_gb()` + `_get_tier()` + `TIER_DEFAULTS`. Fallback: `llama3.2:3b`.

### DES-4: Wizard dinâmico
`wizardLoadSystemProfile()` em `ui.js` — spinner → fetch /api/system/profile → `_renderWizardModelCards()`. `wizardSelectModel()` mostra botão contextual. `wizardUseModel()` usa instalado sem download.

### DES-5: Sidebar badge
`updateModelLabel()` em `models.js` — consulta `_systemProfile.model_catalog`, aplica badge heavy/medium/ok.
