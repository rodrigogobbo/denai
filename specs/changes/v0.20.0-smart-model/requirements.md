# Requirements Document

## Introduction

O DenAI iniciava com `llama3.1:8b` como padrão independente da máquina. Usuários com 8GB RAM travavam. O wizard oferecia 2 cards estáticos sem adaptar ao hardware. Este change adiciona detecção de hardware, tiers de recomendação e wizard dinâmico.

## Requirements

### REQ-1: System Profile API
1.1. `GET /api/system/profile` SHALL return: ram_gb, vram_gb, disk_free_gb, cpu_cores, os, arch, tier, recommendation, installed_models, model_catalog. _(Ubiquitous)_
1.2. THE system SHALL detect RAM cross-platform: /proc/meminfo (Linux), sysctl (macOS), ctypes (Windows). _(Ubiquitous)_
1.3. THE system SHALL attempt VRAM detection via nvidia-smi (Linux/Windows) and system_profiler (macOS Apple Silicon). _(Ubiquitous)_
1.4. IF detection fails, THE system SHALL use 8.0GB as a conservative fallback. _(Unwanted behavior)_

### REQ-2: Hardware Tiers
2.1. THE system SHALL classify hardware into 5 tiers based on RAM: minimal (<6GB), light (6–10GB), mid (10–20GB), high (20–36GB), ultra (>36GB). _(Ubiquitous)_
2.2. Dedicated GPU VRAM SHALL boost the effective RAM for tier calculation (not Apple Silicon unified memory). _(Ubiquitous)_
2.3. THE system SHALL recommend the best already-installed model before suggesting downloads. _(Ubiquitous)_
2.4. IF disk free < model_size + 1GB, THE system SHALL recommend a lighter model. _(Unwanted behavior)_

### REQ-3: Dynamic Wizard
3.1. Wizard Step 3 SHALL call `/api/system/profile` and render model cards dynamically. _(Event-driven)_
3.2. THE recommended model SHALL be visually highlighted with a badge (✅ Recomendado or ⚡ Já instalado). _(Ubiquitous)_
3.3. IF a model exceeds available RAM, THE system SHALL show a ⚠️ warning and reduce opacity. _(Ubiquitous)_
3.4. IF the user selects an installed model, THE button SHALL say "Usar agora" (no download). _(Event-driven)_

### REQ-4: config.py
4.1. `_auto_model()` SHALL use tiers from system_profile instead of a hardcoded threshold. _(Ubiquitous)_
4.2. THE fallback SHALL change from `llama3.1:8b` to `llama3.2:3b` (conservative). _(Ubiquitous)_

### REQ-5: Sidebar Badge
5.1. THE model label in the sidebar SHALL show a weight badge when the selected model is heavy (⚠️) or moderate (〜) for the available RAM. _(Ubiquitous)_
