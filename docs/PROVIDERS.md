# Providers — Guia Completo

> **DenAI v0.17.0** · Documentação de configuração de LLM providers

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Providers suportados](#2-providers-suportados)
3. [Como adicionar via UI](#3-como-adicionar-via-ui)
4. [Como configurar via config.yaml](#4-como-configurar-via-configyaml)
5. [Persistência e localização dos dados](#5-persistência-e-localização-dos-dados)
6. [API REST](#6-api-rest)
7. [Providers locais — LM Studio e LocalAI](#7-providers-locais--lm-studio-e-localai)
8. [Providers de nuvem](#8-providers-de-nuvem)
9. [Segurança — proteção contra SSRF](#9-segurança--proteção-contra-ssrf)

---

## 1. Visão geral

Um **provider** é uma origem de modelos de linguagem (LLM) que o DenAI pode usar para responder mensagens e executar ferramentas. O sistema suporta dois tipos de provider:

| Tipo | Descrição |
|------|-----------|
| `ollama` | Protocolo nativo Ollama — listagem via `/api/tags`, streaming via `/api/chat` |
| `openai` | API compatível com OpenAI — `/v1/chat/completions`, `/v1/models` |

### Ollama como provider padrão

O **Ollama** é o provider padrão e é inicializado automaticamente na porta `http://localhost:11434`. Ele não precisa ser configurado e não pode ser removido — existe sempre que o DenAI está rodando.

```
Provider padrão: Ollama
URL:             http://localhost:11434  (configurável via ollama_url no config.yaml)
Autenticação:    nenhuma
```

Todos os outros providers são **adicionais** — podem coexistir com o Ollama e os modelos de todos eles aparecem juntos na seleção da UI.

---

## 2. Providers suportados

O DenAI inclui 8 templates pré-configurados que simplificam o cadastro dos providers mais comuns.

| # | Nome | Tipo | URL base | Autenticação | Modelos padrão |
|---|------|------|----------|--------------|----------------|
| 1 | **OpenAI** | `openai` | `https://api.openai.com` | API key (`sk-...`) | gpt-4o, gpt-4o-mini, gpt-4-turbo, o1-mini |
| 2 | **Anthropic (Claude)** | `openai` | `https://api.anthropic.com/v1` | API key (`sk-ant-...`) | claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022, claude-3-opus-20240229 |
| 3 | **Google Gemini** | `openai` | `https://generativelanguage.googleapis.com/v1beta/openai` | API key | gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash |
| 4 | **OpenRouter** | `openai` | `https://openrouter.ai/api/v1` | API key | meta-llama/llama-3.1-70b-instruct, mistralai/mistral-large, anthropic/claude-3.5-sonnet, openai/gpt-4o |
| 5 | **Groq** | `openai` | `https://api.groq.com/openai/v1` | API key (`gsk_...`) | llama-3.1-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768 |
| 6 | **LM Studio** | `openai` | `http://localhost:1234` | Nenhuma | — (detectados automaticamente) |
| 7 | **LocalAI** | `openai` | `http://localhost:8080` | Nenhuma | — (detectados automaticamente) |
| 8 | **Ollama (remoto)** | `ollama` | `http://localhost:11434` | Nenhuma | — (detectados automaticamente) |

> **Nota sobre Anthropic:** apesar de ser uma API proprietária, o endpoint do Claude expõe compatibilidade com o formato OpenAI. O DenAI envia automaticamente o header `anthropic-version: 2023-06-01` exigido pela API.

---

## 3. Como adicionar via UI

O modal de providers fica acessível pelo ícone de configurações na barra lateral ou pelo menu **Settings → Providers**.

### Passo a passo

**1. Abrir o modal**
Clique em **"Add Provider"** (ou no ícone `+` na seção Providers do menu lateral).

**2. Escolher um template**
O dropdown de templates pré-popula os campos com a URL base correta e os modelos padrão do provider escolhido. Selecionar um template é opcional — você pode preencher tudo manualmente.

**3. Preencher os campos**

| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| **Name** | Sim | Nome de identificação do provider (ex: `OpenAI`, `Meu Groq`) |
| **Kind** | Sim | `openai` ou `ollama` |
| **Base URL** | Sim | URL base da API, sem barra final |
| **API Key** | Depende | Obrigatória para providers de nuvem; deixe em branco para locais |
| **Models** | Não | Lista de modelos (um por linha). Se vazio, o DenAI consulta `/v1/models` dinamicamente |
| **Default Model** | Não | Modelo selecionado por padrão ao usar este provider |

**4. Testar a conexão**
Clique em **"Test Connection"** antes de salvar. O DenAI faz uma requisição real para o provider, mede a latência e lista os modelos encontrados. O resultado aparece logo abaixo do botão.

**5. Salvar**
Clique em **"Save"**. O provider é registrado na memória e persistido em `~/.denai/providers.yaml`.

**6. Editar ou remover**
Cada provider na lista tem botões de **edição** (reabre o modal preenchido) e **remoção** (exclui do arquivo de persistência e da memória). O provider Ollama padrão não pode ser removido.

---

## 4. Como configurar via config.yaml

Providers podem ser pré-configurados via arquivo, útil em dotfiles, ambientes de CI/CD ou máquinas sem acesso à UI.

Copie o `config.example.yaml` para `~/.denai/config.yaml` e descomente a seção `providers`:

### OpenAI

```yaml
providers:
  - name: OpenAI
    kind: openai
    base_url: https://api.openai.com
    api_key: sk-...          # nunca commite com a key real
    models:
      - gpt-4o
      - gpt-4o-mini
    default_model: gpt-4o
```

### Anthropic (Claude)

```yaml
providers:
  - name: Anthropic
    kind: openai             # usa o endpoint OpenAI-compat do Claude
    base_url: https://api.anthropic.com/v1
    api_key: sk-ant-...
    models:
      - claude-3-5-sonnet-20241022
      - claude-3-5-haiku-20241022
      - claude-3-opus-20240229
    default_model: claude-3-5-sonnet-20241022
```

### Google Gemini

```yaml
providers:
  - name: Gemini
    kind: openai
    base_url: https://generativelanguage.googleapis.com/v1beta/openai
    api_key: AIza...
    models:
      - gemini-2.0-flash
      - gemini-1.5-pro
    default_model: gemini-2.0-flash
```

### OpenRouter

```yaml
providers:
  - name: OpenRouter
    kind: openai
    base_url: https://openrouter.ai/api/v1
    api_key: sk-or-...
    models:
      - meta-llama/llama-3.1-70b-instruct
      - mistralai/mistral-large
      - anthropic/claude-3.5-sonnet
      - openai/gpt-4o
```

### Groq

```yaml
providers:
  - name: Groq
    kind: openai
    base_url: https://api.groq.com/openai/v1
    api_key: gsk_...
    models:
      - llama-3.1-70b-versatile
      - llama-3.1-8b-instant
      - mixtral-8x7b-32768
    default_model: llama-3.1-70b-versatile
```

### LM Studio (local)

```yaml
providers:
  - name: LM Studio
    kind: openai
    base_url: http://localhost:1234
    # api_key não necessário
```

### LocalAI (local)

```yaml
providers:
  - name: LocalAI
    kind: openai
    base_url: http://localhost:8080
```

### Ollama remoto

```yaml
providers:
  - name: Ollama Servidor
    kind: ollama
    base_url: http://192.168.1.100:11434
    default_model: llama3.1:70b
```

### Múltiplos providers juntos

```yaml
providers:
  - name: OpenAI
    kind: openai
    base_url: https://api.openai.com
    api_key: sk-...
    models: [gpt-4o, gpt-4o-mini]

  - name: Groq
    kind: openai
    base_url: https://api.groq.com/openai/v1
    api_key: gsk_...
    models: [llama-3.1-70b-versatile]

  - name: LM Studio
    kind: openai
    base_url: http://localhost:1234
```

> **Prioridade de carregamento:** providers do `config.yaml` são carregados no boot. Providers adicionados pela UI (salvos em `~/.denai/providers.yaml`) também são carregados no boot e têm precedência em caso de nome duplicado.

---

## 5. Persistência e localização dos dados

### Onde ficam os dados

| Arquivo | Conteúdo |
|---------|----------|
| `~/.denai/providers.yaml` | Providers adicionados via UI |
| `~/.denai/config.yaml` | Configuração geral, incluindo providers via arquivo |

### Formato do arquivo de persistência

O `~/.denai/providers.yaml` tem estrutura simples:

```yaml
providers:
  - name: OpenAI
    kind: openai
    base_url: https://api.openai.com
    api_key: sk-proj-xxxxxx   # armazenado localmente, nunca enviado via API
    models:
      - gpt-4o
      - gpt-4o-mini
    default_model: gpt-4o

  - name: Groq
    kind: openai
    base_url: https://api.groq.com/openai/v1
    api_key: gsk_xxxxxx
    models: []
    default_model: ""
```

### Segurança do arquivo

- O arquivo é criado com **permissão `600`** (leitura e escrita apenas para o dono), tanto na criação quanto em cada gravação.
- Em sistemas Windows, a permissão POSIX não é suportada — o arquivo é criado normalmente sem essa restrição.

### API keys nunca são expostas

As API keys são armazenadas em disco mas **nunca retornadas via API REST**. Todas as respostas que incluem informação de provider retornam:

- `has_key: true/false` — indica se uma key existe
- `api_key_masked` — versão mascarada no formato `sk-p***ey` (4 primeiros + `***` + 2 últimos caracteres)

A função responsável pelo mascaramento (`mask_api_key`) garante que keys com 8 caracteres ou menos são completamente substituídas por `***`.

---

## 6. API REST

Todos os endpoints ficam em `/api/providers`.

### `GET /api/providers`

Lista todos os providers registrados (Ollama padrão + providers adicionados).

```bash
curl http://localhost:4078/api/providers
```

Resposta:

```json
{
  "providers": [
    {
      "name": "Ollama",
      "kind": "ollama",
      "base_url": "http://localhost:11434",
      "has_key": false,
      "api_key_masked": "",
      "models": [],
      "default_model": "",
      "is_default": true
    },
    {
      "name": "OpenAI",
      "kind": "openai",
      "base_url": "https://api.openai.com",
      "has_key": true,
      "api_key_masked": "sk-p***ey",
      "models": ["gpt-4o", "gpt-4o-mini"],
      "default_model": "gpt-4o",
      "is_default": false
    }
  ]
}
```

---

### `GET /api/providers/templates`

Retorna os 8 templates pré-configurados.

```bash
curl http://localhost:4078/api/providers/templates
```

Resposta (resumida):

```json
{
  "templates": [
    {
      "id": "openai",
      "label": "OpenAI",
      "description": "GPT-4o, GPT-4o mini, o1 — API oficial da OpenAI",
      "kind": "openai",
      "base_url": "https://api.openai.com",
      "requires_key": true,
      "default_models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-mini"]
    }
    // ...
  ]
}
```

---

### `POST /api/providers`

Adiciona ou atualiza um provider. Persiste em `~/.denai/providers.yaml`.

```bash
curl -X POST http://localhost:4078/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Groq",
    "kind": "openai",
    "base_url": "https://api.groq.com/openai/v1",
    "api_key": "gsk_...",
    "models": ["llama-3.1-70b-versatile", "llama-3.1-8b-instant"],
    "default_model": "llama-3.1-70b-versatile"
  }'
```

Resposta (a API key não é retornada):

```json
{
  "ok": true,
  "provider": {
    "name": "Groq",
    "kind": "openai",
    "base_url": "https://api.groq.com/openai/v1",
    "has_key": true
  }
}
```

**Campos do body:**

| Campo | Tipo | Obrigatório | Padrão | Descrição |
|-------|------|-------------|--------|-----------|
| `name` | string | Sim | — | Nome do provider |
| `kind` | string | Não | `"openai"` | `"openai"` ou `"ollama"` |
| `base_url` | string | Sim | — | URL base da API |
| `api_key` | string | Não | `""` | Chave de autenticação |
| `models` | array | Não | `[]` | Lista de modelos disponíveis |
| `default_model` | string | Não | `""` | Modelo padrão do provider |

> O provider com `name: "ollama"` (case-insensitive) é reservado e retorna erro `400` se você tentar sobrescrevê-lo.

---

### `DELETE /api/providers/{name}`

Remove um provider pelo nome. O nome é case-insensitive.

```bash
curl -X DELETE http://localhost:4078/api/providers/Groq
```

Resposta:

```json
{ "ok": true }
```

Erro se não encontrado:

```json
{ "error": "Provider 'Groq' não encontrado." }
```

> O provider `ollama` não pode ser removido e retorna `400`.

---

### `POST /api/providers/test`

Testa a conectividade com um provider **antes de salvá-lo**. Mede latência e lista os modelos disponíveis.

```bash
curl -X POST http://localhost:4078/api/providers/test \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "openai",
    "base_url": "https://api.groq.com/openai/v1",
    "api_key": "gsk_..."
  }'
```

Resposta de sucesso:

```json
{
  "ok": true,
  "latency_ms": 312,
  "models_found": 8,
  "models": [
    "llama-3.1-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768"
  ]
}
```

Resposta de falha (key inválida):

```json
{
  "ok": false,
  "error": "API key inválida ou ausente.",
  "latency_ms": null
}
```

Resposta de falha (sem conectividade):

```json
{
  "ok": false,
  "error": "Não foi possível conectar. Verifique a URL.",
  "latency_ms": null
}
```

**Campos do body:**

| Campo | Tipo | Obrigatório | Padrão | Descrição |
|-------|------|-------------|--------|-----------|
| `kind` | string | Não | `"openai"` | `"openai"` ou `"ollama"` |
| `base_url` | string | Sim | — | URL base a testar |
| `api_key` | string | Não | `""` | Chave de autenticação |

> Este endpoint aplica validação anti-SSRF na URL recebida (veja [seção 9](#9-segurança--proteção-contra-ssrf)). URLs inválidas ou bloqueadas retornam `400` com a mensagem de erro correspondente.

---

### `GET /api/models`

Lista modelos de todos os providers registrados (ou de um específico via query param `?provider=`).

```bash
# Todos os providers
curl http://localhost:4078/api/models

# Provider específico
curl "http://localhost:4078/api/models?provider=Groq"
```

---

## 7. Providers locais — LM Studio e LocalAI

Providers locais rodam inteiramente na sua máquina e não enviam dados para a internet.

### LM Studio

O [LM Studio](https://lmstudio.ai) oferece uma interface gráfica para baixar e rodar modelos GGUF localmente. Ele expõe um servidor OpenAI-compatible na porta `1234` por padrão.

**Setup:**

1. Instale o LM Studio em [lmstudio.ai](https://lmstudio.ai)
2. Baixe um modelo (ex: `Llama-3.1-8B-Instruct-GGUF`)
3. Vá em **Local Server** → clique em **Start Server**
4. O servidor ficará disponível em `http://localhost:1234`

**Configuração no DenAI:**

Via UI: selecione o template **"LM Studio"** — a URL já vem preenchida, sem precisar de API key.

Via `config.yaml`:
```yaml
providers:
  - name: LM Studio
    kind: openai
    base_url: http://localhost:1234
```

Via curl:
```bash
curl -X POST http://localhost:4078/api/providers \
  -H "Content-Type: application/json" \
  -d '{"name": "LM Studio", "kind": "openai", "base_url": "http://localhost:1234"}'
```

Os modelos carregados no LM Studio aparecem automaticamente na seleção — não é preciso listá-los manualmente.

---

### LocalAI

O [LocalAI](https://localai.io) é uma alternativa open-source que roda modelos GGUF, GPTQ e outros formatos via Docker ou binário, sem GPU obrigatória. Expõe um servidor OpenAI-compatible na porta `8080` por padrão.

**Setup com Docker:**

```bash
docker run -p 8080:8080 \
  -v $HOME/.localai/models:/models \
  localai/localai:latest
```

**Setup com binário:**

```bash
# macOS/Linux
curl -Lo localai https://github.com/mudler/LocalAI/releases/latest/download/local-ai-$(uname -s)-$(uname -m)
chmod +x localai
./localai --models-path ~/.localai/models
```

**Configuração no DenAI:**

Via UI: selecione o template **"LocalAI"** — URL `http://localhost:8080`, sem API key.

Via `config.yaml`:
```yaml
providers:
  - name: LocalAI
    kind: openai
    base_url: http://localhost:8080
```

> **Porta diferente?** Se você subiu o LocalAI em outra porta, ajuste a `base_url` adequadamente, por exemplo `http://localhost:9090`.

---

## 8. Providers de nuvem

### OpenAI

**Onde obter a API key:** [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

**Formato da key:** `sk-proj-...` ou `sk-...`

```bash
curl -X POST http://localhost:4078/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenAI",
    "kind": "openai",
    "base_url": "https://api.openai.com",
    "api_key": "sk-proj-...",
    "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-mini"],
    "default_model": "gpt-4o"
  }'
```

**Modelos notáveis:**
- `gpt-4o` — modelo principal, multimodal
- `gpt-4o-mini` — mais rápido e barato, ideal para tarefas simples
- `gpt-4-turbo` — contexto de 128k tokens
- `o1-mini` — raciocínio avançado

---

### Anthropic (Claude)

**Onde obter a API key:** [console.anthropic.com](https://console.anthropic.com)

**Formato da key:** `sk-ant-api03-...`

O DenAI usa o endpoint OpenAI-compatible do Claude e envia automaticamente o header `anthropic-version: 2023-06-01`.

```bash
curl -X POST http://localhost:4078/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Anthropic",
    "kind": "openai",
    "base_url": "https://api.anthropic.com/v1",
    "api_key": "sk-ant-...",
    "models": [
      "claude-3-5-sonnet-20241022",
      "claude-3-5-haiku-20241022",
      "claude-3-opus-20240229"
    ],
    "default_model": "claude-3-5-sonnet-20241022"
  }'
```

**Modelos notáveis:**
- `claude-3-5-sonnet-20241022` — melhor custo-benefício, janela de 200k tokens
- `claude-3-5-haiku-20241022` — mais rápido, ideal para tarefas simples
- `claude-3-opus-20240229` — mais capaz para raciocínio complexo

---

### Google Gemini

**Onde obter a API key:** [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

**Formato da key:** `AIzaSy...`

```bash
curl -X POST http://localhost:4078/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Gemini",
    "kind": "openai",
    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
    "api_key": "AIzaSy...",
    "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    "default_model": "gemini-2.0-flash"
  }'
```

**Modelos notáveis:**
- `gemini-2.0-flash` — mais recente, rápido e eficiente
- `gemini-1.5-pro` — contexto de 1 milhão de tokens
- `gemini-1.5-flash` — versão rápida do 1.5

---

### OpenRouter

O OpenRouter funciona como um proxy que agrega centenas de modelos de diferentes provedores (OpenAI, Anthropic, Meta, Mistral, etc.) via uma única API key.

**Onde obter a API key:** [openrouter.ai/keys](https://openrouter.ai/keys)

**Formato da key:** `sk-or-v1-...`

```bash
curl -X POST http://localhost:4078/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenRouter",
    "kind": "openai",
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "sk-or-v1-...",
    "models": [
      "meta-llama/llama-3.1-70b-instruct",
      "mistralai/mistral-large",
      "anthropic/claude-3.5-sonnet",
      "openai/gpt-4o"
    ]
  }'
```

> Todos os modelos disponíveis na sua conta OpenRouter também podem ser descobertos via `GET /api/models?provider=OpenRouter`.

---

### Groq

O Groq oferece inferência de LLMs de código aberto com latência muito baixa (hardware proprietário LPU).

**Onde obter a API key:** [console.groq.com/keys](https://console.groq.com/keys)

**Formato da key:** `gsk_...`

```bash
curl -X POST http://localhost:4078/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Groq",
    "kind": "openai",
    "base_url": "https://api.groq.com/openai/v1",
    "api_key": "gsk_...",
    "models": [
      "llama-3.1-70b-versatile",
      "llama-3.1-8b-instant",
      "mixtral-8x7b-32768"
    ],
    "default_model": "llama-3.1-70b-versatile"
  }'
```

**Modelos notáveis:**
- `llama-3.1-70b-versatile` — maior e mais capaz
- `llama-3.1-8b-instant` — ultra-rápido para tarefas simples
- `mixtral-8x7b-32768` — contexto de 32k tokens

---

## 9. Segurança — proteção contra SSRF

O endpoint `POST /api/providers/test` aceita URLs fornecidas pelo usuário e as usa para fazer requisições HTTP. Para evitar ataques de **Server-Side Request Forgery (SSRF)**, toda URL passa pelo validador `denai/security/url_validator.py` antes de ser utilizada.

### O que é verificado

**1. Esquema HTTP**
Apenas `http` e `https` são aceitos. Qualquer outro esquema (ex: `file://`, `ftp://`, `gopher://`) é rejeitado imediatamente.

**2. Presença de hostname**
URLs sem hostname (ex: `http://`) são rejeitadas.

**3. Endereços bloqueados por padrão**

| Bloco | Motivo |
|-------|--------|
| `127.0.0.0/8` (loopback) | Acesso ao localhost do servidor |
| `169.254.0.0/16` (link-local) | Metadata servers de cloud (AWS IMDSv1/v2, GCP, Azure) |
| `100.64.0.0/10` | Shared address space (RFC 6598) |
| `192.0.0.0/24` | IETF Protocol Assignments |
| `192.0.2.0/24` | TEST-NET-1 (RFC 5737) |
| `198.51.100.0/24` | TEST-NET-2 (RFC 5737) |
| `203.0.113.0/24` | TEST-NET-3 (RFC 5737) |
| `240.0.0.0/4` | Reserved (RFC 1112) |
| `0.0.0.0/8` | "This" network |
| Multicast | Endereços multicast |

**4. Localhost (comportamento especial)**
O endpoint de teste passa `allow_localhost=True`, o que **permite** `localhost`, `127.0.0.1` e `::1`. Isso é intencional para suportar LM Studio e LocalAI em desenvolvimento. Em outros contextos internos do DenAI, localhost permanece bloqueado.

**5. Resolução DNS (prevenção de DNS rebinding)**
Se o hostname não é um IP literal, o validador resolve o DNS e verifica **cada IP resultante** contra os blocos acima. Isso impede ataques onde um domínio externo aponta para um IP interno.

**6. Reconstrução da URL**
Após validação, a URL é reconstruída a partir dos componentes parseados (não do input original). Isso quebra o *taint* e previne bypass via URLs malformadas — a técnica é reconhecida pelo CodeQL como mitigação segura de SSRF.

### Exemplos de URLs rejeitadas

```bash
# Metadata server AWS — bloqueado (169.254.x.x)
curl -X POST http://localhost:4078/api/providers/test \
  -d '{"base_url": "http://169.254.169.254/latest/meta-data"}'
# → {"ok": false, "error": "Endereço bloqueado: link-local address não permitido (inclui metadata server)"}

# Hostname que resolve para IP privado — bloqueado via DNS
curl -X POST http://localhost:4078/api/providers/test \
  -d '{"base_url": "http://internal.corp"}'
# → {"ok": false, "error": "Hostname 'internal.corp' resolve para endereço bloqueado: ..."}

# Esquema inválido — bloqueado
curl -X POST http://localhost:4078/api/providers/test \
  -d '{"base_url": "file:///etc/passwd"}'
# → {"ok": false, "error": "Scheme 'file' não permitido. Use http ou https."}
```

### Importante

A proteção SSRF se aplica **somente ao endpoint de teste** — que é o único ponto onde o DenAI faz requisições baseadas em input do usuário sem autenticação prévia. URLs de providers já salvos (adicionados via UI autenticada ou config.yaml) são usadas diretamente pelo runtime de inferência, que opera em contexto confiável.
