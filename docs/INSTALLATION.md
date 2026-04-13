# DenAI — Instalação e Requisitos

> **Versão:** 0.24.1

---

## 💻 System Requirements

| Tier | RAM | Storage | GPU | Experience |
|------|-----|---------|-----|------------|
| 🟢 **Mínimo** | 8 GB | 10 GB livre | Não precisa | Modelos 3B — respostas simples, sem tool calling confiável |
| ⭐ **Recomendado** | 16 GB | 20 GB livre | Não precisa | Modelos 7-8B — bom tool calling, respostas consistentes |
| 🏆 **Ideal** | 32 GB+ | 40 GB livre | Qualquer GPU com 8GB+ VRAM | Modelos 14-32B — tool calling preciso, planning multi-step |

### "Consigo fazer o mesmo que o ChatGPT/Copilot?"

Resposta honesta:

| Capacidade | Cloud (GPT-4, Claude) | DenAI 8B | DenAI 32B |
|------------|----------------------|----------|-----------|
| Conversa geral | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Gerar código | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Tool calling (ler/editar/executar) | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Planning multi-step | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Contexto longo (100k+ tokens) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (auto 8-32k with LLM summarization) | ⭐⭐⭐⭐ (auto 32-64k with LLM summarization) |
| Privacidade | ❌ Dados vão pra nuvem | ✅ 100% local | ✅ 100% local |
| Custo | $20-200/mês | **Grátis** | **Grátis** |
| Funciona offline | ❌ | ✅ | ✅ |

> 💡 **Resumo prático:** Com **8 GB RAM + modelo 8B**, o DenAI é um bom assistente de conversa e código, mas erra em tool calling complexo. Com **32 GB RAM + qwen2.5-coder:32b**, chega perto da experiência de cloud — tool calling confiável, planning, edição de arquivos em sequência. O contexto agora escala automaticamente de 8k a 64k tokens, com sumarização automática de mensagens antigas para sessões longas.

### Qual computador comprar?

Se está pensando em montar/comprar um PC pra rodar IA local:

- **Orçamento mínimo (~R$2.500):** PC usado com 16 GB RAM + SSD. Roda modelos 7-8B bem.
- **Orçamento ideal (~R$5.000-8.000):** 32 GB RAM + GPU com 8 GB VRAM (RTX 3060/4060). Roda modelos 14-32B com velocidade.
- **Notebook:** MacBook com Apple Silicon (M1/M2/M3 com 16 GB+) é excelente pra IA local — memória unificada beneficia muito os modelos.

---

---

## 🧠 AI Models

| Model | Size | RAM | What it can do | Recommendation |
|-------|------|-----|----------------|:-:|
| `llama3.2:3b` | ~2 GB | 8 GB | Conversa, Q&A, texto simples | 🟢 PCs fracos |
| `gemma3:4b` | ~3.3 GB | 8 GB | Conversa, código básico | 🟢 Alternativa leve |
| `llama3.1:8b` | ~4.7 GB | 10 GB | Conversa + tool calling básico | ⭐ **Recomendado** |
| `qwen2.5-coder:7b` | ~4.4 GB | 10 GB | Código + tools, bom em programação | 🔵 Devs |
| `mistral:7b` | ~4.1 GB | 10 GB | Versátil, multilingual | 🟡 All-rounder |
| `deepseek-r1:8b` | ~4.9 GB | 10 GB | Raciocínio, matemática, lógica | 🟣 Problemas complexos |
| `qwen2.5-coder:14b` | ~9 GB | 16 GB | Tool calling confiável, planning | 🔵 Devs com 16 GB |
| `qwen2.5-coder:32b` | ~18 GB | 24 GB | Melhor tool calling + planning multi-step | 🏆 **Power users** |

> 💡 DenAI auto-detects your RAM and picks the best default model: `llama3.2:3b` for <12 GB, `llama3.1:8b` for 12 GB+.

```bash
# Install any model
ollama pull <model-name>

# List installed models
ollama list
```

---

---

## 🐳 Docker

Run DenAI + Ollama without installing anything on your machine.

### Quick start

```bash
# Clone the repo
git clone https://github.com/rodrigogobbo/denai.git
cd denai

# Start everything
docker compose up -d

# Pull a model (first time only)
docker compose exec ollama ollama pull llama3.2:3b

# Open http://localhost:8080
```

### What gets created

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `denai-app` | Built from Dockerfile | 8080 | DenAI web UI + API |
| `denai-ollama` | `ollama/ollama:latest` | 11434 | LLM runtime |

| Volume | Purpose |
|--------|---------|
| `ollama_models` | Persists downloaded models between restarts |

### GPU support (NVIDIA)

Edit `docker-compose.yml` and uncomment the `deploy` block under `ollama`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

Requires [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) on the host.

### Custom configuration

```bash
# Use a different model
docker compose exec denai-app env DENAI_MODEL=qwen2.5-coder:7b python -m denai

# Mount your own config
# Add to docker-compose.yml under denai > volumes:
#   - ~/.denai/config.yaml:/home/denai/.denai/config.yaml
```

### Useful commands

```bash
# View logs
docker compose logs -f denai

# Stop everything
docker compose down

# Rebuild after code changes
docker compose build denai && docker compose up -d denai

# Remove everything (containers, volumes, models)
docker compose down -v
```

---

---

## 🗑️ Complete Uninstall

Remove DenAI and all its data from your machine.

### Quick (DenAI only)

```bash
pip uninstall denai -y
```

### Full cleanup (everything)

```bash
# 1. Uninstall the Python package
pip uninstall denai -y

# 2. Remove DenAI data (conversations, memory, config, plugins, skills, logs)
# Linux / macOS
rm -rf ~/.denai

# Windows (PowerShell)
Remove-Item -Recurse -Force "$env:USERPROFILE\.denai"

# Windows (CMD)
rmdir /s /q "%USERPROFILE%\.denai"

# 3. Remove Ollama models (optional — frees 5-50 GB)
ollama list                    # see what's installed
ollama rm llama3.1:8b          # remove one by one
# Or delete all models at once:
# Linux / macOS
rm -rf ~/.ollama/models
# Windows
rmdir /s /q "%USERPROFILE%\.ollama\models"

# 4. Uninstall Ollama (optional)
# Linux
sudo rm /usr/local/bin/ollama
# macOS
brew uninstall ollama   # or delete the app from /Applications
# Windows — Settings → Apps → Ollama → Uninstall

# 5. Docker cleanup (if used)
docker compose down -v         # removes containers + volumes (models)
docker rmi denai-denai         # remove the built image
```

### What gets deleted

| Item | Path | Content |
|------|------|---------|
| DenAI package | pip site-packages | Python code |
| DenAI data | `~/.denai/` | Conversations, memory, config, logs, plugins, skills, backups |
| Ollama models | `~/.ollama/models/` | Downloaded AI models (5-50 GB) |
| Ollama binary | `/usr/local/bin/ollama` | The Ollama runtime |
| Docker volumes | `ollama_models` | Models downloaded inside Docker |

> ⚠️ **Deleting `~/.denai/` is irreversible.** All your conversations, memories, and configs will be lost. Back up anything important first.
> 
> 💡 **Uninstalling DenAI does NOT delete Ollama or its models.** They are separate programs. Remove them separately if you want a clean slate.

---
