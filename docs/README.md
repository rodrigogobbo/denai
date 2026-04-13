# DenAI — Documentação

> **Versão:** 0.25.0 | [GitHub](https://github.com/rodrigogobbo/denai) | [PyPI](https://pypi.org/project/denai/)

## Documentos disponíveis

| Documento | Público | Descrição |
|---|---|---|
| [GUIA-COMPLETO.md](./GUIA-COMPLETO.md) | Iniciantes | Instalação passo a passo no Windows, sem experiência técnica |
| [INSTALLATION.md](./INSTALLATION.md) | Todos | Requisitos de sistema, modelos, Docker, desinstalação |
| [CONFIGURATION.md](./CONFIGURATION.md) | Usuários | Share mode, MCP, segurança, config.yaml |
| [API.md](./API.md) | Desenvolvedores | Referência completa de todos os endpoints REST |
| [TOOLS.md](./TOOLS.md) | Usuários avançados | Referência de todas as 26 tools disponíveis para o LLM |
| [PROVIDERS.md](./PROVIDERS.md) | Usuários avançados | Como configurar OpenAI, Anthropic, Gemini, Groq e outros |
| [PERSONAS.md](./PERSONAS.md) | Usuários avançados | Sub-agentes especializados e como criar personas customizadas |
| [SECURITY.md](./SECURITY.md) | Desenvolvedores / DevSec | Modelo de segurança, sandbox, SSRF protection, autenticação |

---

## Início Rápido

```bash
# Instalar
pip install denai

# Iniciar (abre no browser em http://localhost:4078)
python -m denai

# Com modelo específico
python -m denai --model llama3.2:3b

# Compartilhar na rede local
python -m denai --compartilhar
```

---

## Arquitetura em uma página

```
~/.denai/
├── denai.db          # Conversas e memórias (SQLite)
├── api.key           # API key de autenticação
├── config.yaml       # Configuração principal
├── providers.yaml    # Providers LLM adicionais (chmod 600)
├── permissions.yaml  # Permissões de tools
├── plans/            # Spec documents (~/<slug>.md)
├── todos.db          # Todo list atual
├── personas/         # Personas customizadas (*.md)
├── skills/           # Skills customizadas (*.md)
├── documents/        # Documentos para RAG
├── plugins/          # Plugins customizados (*.py)
├── projects/         # Contextos de projeto persistidos
└── logs/             # Logs com rotação (5 MB x 3)
```

---

## Funcionalidades por versão

| Versão | Data | Feature |
|---|---|---|
| v0.25.0 | Abr/2026 | Múltiplos perfis isolados + comando `/specs` para specs SDS |
| v0.24.1 | Abr/2026 | Remoção de CSS legacy — Tailwind como único CSS servido |
| v0.24.0 | Abr/2026 | macOS x64 + `/context` busca automática no índice da sessão |
| v0.23.0 | Abr/2026 | Tailwind CSS + comando `/context` para perguntas sobre repositórios |
| v0.22.0 | Abr/2026 | Changelog in-app no modal de update + instaladores Electron menores |
| v0.21.0 | Abr/2026 | Desktop App — Electron + uv bundled (.exe/.dmg/.zip) + specs SDS retroativas |
| v0.20.0 | Abr/2026 | Smart Model Selection — tiers de hardware + wizard dinâmico |
| v0.19.0 | Abr/2026 | Feedback in-app: reportar bugs e sugerir melhorias pelo DenAI |
| v0.18.0 | Abr/2026 | Update com streaming SSE + reinicialização automática + auto-release pipeline |
| v0.17.0 | Abr/2026 | Providers: persistência, UI modal, 8 templates, SSRF protection |
| v0.16.0 | Abr/2026 | Sugestões proativas de skills e plugins |
| v0.15.0 | Abr/2026 | Sub-agentes com persona (security, reviewer, writer, data) |
| v0.14.0 | Abr/2026 | `todowrite` — todo list com substituição total e prioridade |
| v0.13.0 | Mar/2026 | `memory_list` + `plans_spec` (spec documents markdown) |
| v0.12.0 | Mar/2026 | Agentic Workflows, Git Tool, Persistent Project Context |
| v0.11.0 | Mar/2026 | HTML Export, MCP Support |
| v0.10.0 | Mar/2026 | Project /init, Permissões Granulares, Skills |
| v0.8.0  | Mar/2026 | Voice Input, Multi-model, Plugin Marketplace |
| v0.6.0  | Mar/2026 | SSE streaming fix, Docker, CI/CD, PyPI |

---

## Links úteis

- **CHANGELOG completo:** [../CHANGELOG.md](../CHANGELOG.md)
- **Contribuição:** [../CONTRIBUTING.md](../CONTRIBUTING.md)
- **Segurança (vulnerabilidades):** [../SECURITY.md](../SECURITY.md)
- **PyPI:** https://pypi.org/project/denai/
- **GitHub Issues:** https://github.com/rodrigogobbo/denai/issues
