# DenAI — Sub-agentes e Personas

> **Versão:** 0.24.1

## O que são sub-agentes?

Sub-agentes permitem que o LLM principal delegue tarefas para agentes especializados que rodam com um **system prompt customizado** (persona). Cada sub-agente tem:

- **Sessão LLM isolada** — sem acesso ao histórico do chat principal
- **Persona especializada** — instruções focadas no domínio da tarefa
- **Escopo controlado** — max 20 tool calls, timeout 120s
- **Sem recursão** — sub-agente não pode chamar `subagent`

### Quando usar sub-agentes?

| Situação | Persona |
|---|---|
| Revisar código em busca de vulnerabilidades | `security` |
| Code review geral (bugs, performance, legibilidade) | `reviewer` |
| Escrever ou melhorar documentação | `writer` |
| Analisar dados, escrever SQL, gerar insights | `data` |
| Qualquer expertise específica | persona customizada via `system_prompt` |

---

## Personas Bundled

### `security` — AppSec Specialist

Mentalidade ofensiva. Pensa como atacante para defender melhor.

**Usa para:**
- Análise de vulnerabilidades (OWASP Top 10)
- SQL Injection, XSS, SSRF, IDOR, Broken Auth, Command Injection
- Classificação por severidade (🔴 Crítica / 🟠 Alta / 🟡 Média / 🟢 Baixa)
- Fix code com explicação do vetor de ataque

**Exemplo:**
```json
{
  "action": "subagent",
  "goal": "Analise o arquivo auth.py em busca de vulnerabilidades de autenticação",
  "persona": "security"
}
```

---

### `reviewer` — Senior Code Reviewer

Code review técnico e objetivo.

**Usa para:**
- Bugs potenciais (null checks, race conditions, edge cases)
- Performance (N+1, loops desnecessários, alocações)
- Legibilidade e complexidade ciclomática
- Consistência com padrões do projeto

**Classifica por:** 🔴 Crítico / 🟡 Importante / 🟢 Sugestão

**Exemplo:**
```json
{
  "action": "subagent",
  "goal": "Faça code review do arquivo payments.py",
  "persona": "reviewer"
}
```

---

### `writer` — Technical Writer

Documentação clara, prática e em português.

**Usa para:**
- READMEs, docstrings, comentários inline
- Guias de uso, ADRs, changelogs
- Exemplos práticos de código (não pseudocódigo)

**Exemplo:**
```json
{
  "action": "subagent",
  "goal": "Escreva o README completo do módulo de autenticação",
  "persona": "writer"
}
```

---

### `data` — Data Analyst

Analista sênior orientado a insights acionáveis.

**Usa para:**
- Queries SQL otimizadas
- Análise de schemas e estruturas de dados
- Insights com contexto (comparação com períodos, benchmarks)
- Recomendações de visualização

**Exemplo:**
```json
{
  "action": "subagent",
  "goal": "Analise estes logs de acesso e identifique padrões suspeitos",
  "persona": "data"
}
```

---

## Criando Personas Customizadas

Crie um arquivo `.md` em `~/.denai/personas/`. Personas customizadas **sobrescrevem** bundled com mesmo nome.

**Formato:**
```markdown
---
name: sre
description: SRE especialista em Kubernetes e observabilidade
---
Você é um SRE sênior com 10 anos de experiência em ambientes Kubernetes.

Ao analisar problemas de infraestrutura:
- Sempre peça os logs relevantes antes de diagnosticar
- Priorize disponibilidade e tempo de recovery (MTTR)
- Sugira tanto o fix imediato quanto a solução definitiva
- Mencione alertas e runbooks que devem ser criados

Ferramentas que domina: kubectl, Prometheus, Grafana, Jaeger, Helm.
```

Após criar o arquivo, a persona fica disponível imediatamente via `GET /api/personas`.

**Frontmatter YAML:**
| Campo | Obrigatório | Descrição |
|---|---|---|
| `name` | ✅ | Identificador da persona (usado no parâmetro `persona`) |
| `description` | ❌ | Descrição curta exibida na listagem |

O conteúdo após o frontmatter é o **system prompt completo** do sub-agente.

---

## API Reference

### Tool `subagent`

```json
{
  "name": "subagent",
  "parameters": {
    "goal": "string (obrigatório) — o que o sub-agente deve fazer",
    "persona": "string (opcional) — nome da persona pré-definida",
    "system_prompt": "string (opcional) — substitui persona se fornecido",
    "model": "string (opcional) — modelo LLM (herda o padrão)"
  }
}
```

### `GET /api/personas`

Lista todas as personas disponíveis.

```bash
curl http://localhost:4078/api/personas -H "X-API-Key: $(cat ~/.denai/api.key)"
```

**Resposta:**
```json
{
  "personas": [
    {"name": "security", "description": "AppSec specialist...", "source": "bundled"},
    {"name": "reviewer", "description": "Senior code reviewer...", "source": "bundled"},
    {"name": "writer",   "description": "Technical writer...", "source": "bundled"},
    {"name": "data",     "description": "Data analyst...", "source": "bundled"},
    {"name": "sre",      "description": "SRE especialista...", "source": "custom"}
  ]
}
```

---

## Limitações

| Limite | Valor | Motivo |
|---|---|---|
| Max tool calls por sub-agente | 20 | Evitar loops infinitos |
| Timeout | 120s | Sessão isolada não pode bloquear indefinidamente |
| Recursão | ❌ Bloqueada | `subagent` não está disponível para o sub-agente |
| Histórico do pai | ❌ Não acessa | Sessão completamente isolada |
| Modo Plan | ❌ Não disponível | É execução, não leitura |
