# DenAI — Modelo de Segurança

> **Versão:** 0.19.0

## Princípio Fundamental

O DenAI roda **100% localmente**. Nenhum dado é enviado para servidores externos, exceto:
1. Requisições ao Ollama local (ou provider configurado explicitamente pelo usuário)
2. Busca web quando o usuário pede explicitamente (`web_search`)
3. Testes de conexão com providers quando o usuário aciona via UI

---

## Autenticação

### API Key

Toda requisição à API requer o header `X-API-Key`.

- Gerada automaticamente na primeira execução
- Armazenada em `~/.denai/api.key`
- **Nunca commitar ou compartilhar esta key**

```bash
# Onde encontrar
cat ~/.denai/api.key

# Usar nas requisições
curl http://localhost:4078/api/health -H "X-API-Key: $(cat ~/.denai/api.key)"
```

**Rotas públicas** (sem autenticação): `GET /`, `/static/*`, `GET /api/health`

### Rate Limiting

Limite por IP para prevenir abuso. Retorna `429` quando excedido.

---

## Sandbox de Arquivos

As tools `file_read`, `file_write`, `file_edit`, `list_files` e `git` só operam dentro do **home do usuário**.

### Paths Bloqueados (mesmo dentro do home)

```
.ssh/           — chaves SSH
.gnupg/         — chaves GPG
.aws/           — credenciais AWS
.azure/         — credenciais Azure
.gcloud/        — credenciais Google Cloud
.kube/          — kubeconfig
.docker/config.json
.denai/api.key  — própria API key do DenAI
AppData/Local/Google/Chrome/User Data  (Windows)
Library/Keychains/                     (macOS)
```

### Como funciona

```python
# denai/security/sandbox.py
def is_path_allowed(path_str: str, write: bool = False) -> tuple[bool, str]:
    path = Path(path_str).expanduser().resolve()
    home = Path.home().resolve()
    # Verifica se está dentro do home
    path.relative_to(home)  # ValueError se fora
    # Verifica lista de blocked paths
    ...
```

**Resposta HTTP:** `403 Forbidden` para paths fora do sandbox.

---

## Proteção contra Command Injection

`command_exec` filtra comandos destrutivos antes de executar:

**Comandos bloqueados (exemplos):**
```
rm -rf /
rm -rf ~
dd if=/dev/zero
mkfs
format c:
:(){ :|:& };:    (fork bomb)
```

**Permissão padrão de `command_exec`:** `ask` — o usuário deve confirmar antes de cada execução.

---

## Proteção contra SSRF

O endpoint `POST /api/providers/test` aceita URLs fornecidas pelo usuário. Para prevenir SSRF, toda URL passa por `denai/security/url_validator.py` antes de qualquer requisição HTTP.

### Ranges Bloqueados

| Range | Motivo |
|---|---|
| `169.254.0.0/16` | AWS/GCP/Azure instance metadata |
| `127.0.0.0/8` | Loopback (em produção) |
| `::1/128` | IPv6 loopback |
| `100.64.0.0/10` | Shared address space (RFC 6598) |
| `192.0.0.0/24` | IETF protocol assignments |
| `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` | TEST-NET (documentação) |
| `240.0.0.0/4` | Reservado para uso futuro |
| `0.0.0.0/8` | Rede "this" |
| Multicast, link-local | Vários |

### Verificação DNS

Além de bloquear IPs literais, o validador **resolve o DNS** e verifica os IPs resultantes — prevenindo DNS rebinding:

```
attack.evil.com → resolve para 169.254.169.254 → BLOQUEADO
```

### Exceção: `allow_localhost=True`

Para suportar providers locais (LM Studio na porta 1234, LocalAI na 8080), o teste de conexão usa `allow_localhost=True`. Isso é intencional e esperado — o usuário está explicitamente configurando um provider local.

---

## Segurança de API Keys de Providers

API keys de providers (OpenAI, Anthropic, etc.) nunca são expostas pela API:

### Armazenamento

```
~/.denai/providers.yaml  — permissão 600 (só o dono pode ler/escrever)
```

### Mascaramento

`GET /api/providers` sempre retorna keys mascaradas:

```json
{"api_key_masked": "sk-ab***99", "has_key": true}
```

A key real **nunca aparece** em respostas de API, logs ou exports de conversa.

---

## Proteção contra Path Injection

Paths fornecidos pelo usuário (ex: `POST /api/project/init`) são:

1. Resolvidos via `Path(path).expanduser().resolve()` — elimina `..`, symlinks
2. Validados contra o sandbox via `is_path_allowed()`
3. **Reconstruídos** via `Path(*candidate.parts)` antes de serem usados — quebra o taint no CodeQL

```python
# denai/routes/project.py
def _validate_path(path):
    candidate = Path(path).expanduser().resolve()
    allowed, reason = is_path_allowed(str(candidate))
    if not allowed:
        return None, JSONResponse({"error": reason}, status_code=403)
    # Reconstrução — não reutiliza o input original
    safe_path = str(Path(*candidate.parts))
    return safe_path, None
```

---

## Modo Share (`--compartilhar`)

Quando ativado, o DenAI faz bind em `0.0.0.0` e aceita conexões da rede local.

**Considerações:**
- A API key é **obrigatória** — exibida no banner de startup
- Nunca use em redes públicas sem VPN ou proxy reverso com TLS
- O CORS é restrito ao IP local detectado automaticamente
- Não há autenticação por usuário — qualquer pessoa com a key tem acesso total

**Para produção/compartilhamento real:** coloque um proxy reverso (nginx/caddy) com TLS na frente.

---

## Permissões de Tools

Cada tool tem um nível de permissão configurável:

| Nível | Comportamento |
|---|---|
| `allow` | Executa automaticamente |
| `ask` | Pausa e pede confirmação do usuário |
| `deny` | Bloqueia completamente |

**Padrões:**

| Tool | Padrão |
|---|---|
| `file_read`, `list_files`, `grep` | `allow` |
| `file_write`, `file_edit` | `ask` |
| `command_exec` | `ask` |
| `git` (operações de escrita) | `ask` |
| `memory_save` | `allow` |
| `web_search` | `allow` |

Configure via `~/.denai/permissions.yaml` ou `PUT /api/permissions`.

---

## Logs e Privacidade

- Logs em `~/.denai/logs/` com rotação (5 MB, 3 backups)
- **Não logar** API keys, senhas ou tokens
- **Não logar** conteúdo completo de mensagens do usuário (apenas metadata)
- Conversas ficam em `~/.denai/denai.db` — SQLite local

Para apagar todos os dados:
```bash
rm -rf ~/.denai/
```

---

## Checklist OWASP Top 10 (2021)

| Risco | Status | Mitigação |
|---|---|---|
| A01 Broken Access Control | ✅ | API key obrigatória, sandbox de paths |
| A02 Cryptographic Failures | ✅ | Keys de providers com chmod 600, nunca expostas |
| A03 Injection | ✅ | Command filter, sandbox, path validation |
| A04 Insecure Design | ✅ | Permissões por tool, confirmação para ações destrutivas |
| A05 Security Misconfiguration | ✅ | Bind 127.0.0.1 por padrão, rate limiting |
| A06 Vulnerable Components | 🔄 | Dependabot ativo no repositório |
| A07 Auth Failures | ✅ | API key + rate limit por IP |
| A08 Data Integrity Failures | ✅ | Undo/snapshot para tools destrutivas |
| A09 Logging Failures | ✅ | Logs persistentes, sem dados sensíveis |
| A10 SSRF | ✅ | `validate_provider_url()` com blocklist de IPs |
