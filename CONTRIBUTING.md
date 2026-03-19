# 🤝 Contribuindo com o DenAI

Obrigado por querer contribuir! Este guia explica como participar do projeto.

---

## 🚀 Como contribuir

### 1. Fork e clone

```bash
# Fork o repositório no GitHub, depois:
git clone https://github.com/seu-usuario/denai.git
cd denai
```

### 2. Crie uma branch

```bash
git checkout -b feat/minha-feature
# ou: fix/corrige-bug, docs/atualiza-readme, etc.
```

### 3. Configure o ambiente de dev

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 4. Faça suas alterações

Código, testes, documentação — o que fizer sentido.

### 5. Rode os testes

```bash
pytest
```

### 6. Commit e push

```bash
git add .
git commit -m "feat: adiciona ferramenta de tradução"
git push origin feat/minha-feature
```

### 7. Abra um Pull Request

Vá no GitHub e abra um PR da sua branch para `main`. Descreva o que mudou e por quê.

---

## 🛠️ Como criar uma nova Tool

Ferramentas (tools) são auto-descobertas. Basta criar um arquivo em `denai/tools/`:

### 1. Crie o arquivo

```bash
touch denai/tools/minha_tool.py
```

### 2. Siga o padrão

```python
"""Descrição curta da ferramenta."""

from denai.tools import tool


@tool(
    name="minha_tool",
    description="Faz algo útil com o input do usuário",
    parameters={
        "texto": {
            "type": "string",
            "description": "O texto para processar",
            "required": True,
        }
    },
)
def minha_tool(texto: str) -> str:
    """Processa o texto e retorna o resultado."""
    resultado = texto.upper()  # exemplo
    return resultado
```

### 3. Teste

```bash
pytest tests/test_tools.py -k "minha_tool"
```

### 4. Pronto!

A tool é registrada automaticamente na próxima execução do DenAI. Sem config extra.

> 💡 Olhe os arquivos existentes em `denai/tools/` como referência — `file_tools.py` e `web_tools.py` são bons exemplos.

---

## 🧪 Testes

Usamos **pytest**. Rode tudo com:

```bash
# Todos os testes
pytest

# Com cobertura
pytest --cov=denai

# Um arquivo específico
pytest tests/test_chat.py

# Modo verbose
pytest -v
```

Novos PRs **devem** incluir testes para funcionalidades novas.

---

## 🎨 Estilo de código

Usamos **ruff** pra linting e formatação:

```bash
# Checar problemas
ruff check .

# Corrigir automaticamente
ruff check --fix .

# Formatar
ruff format .
```

### Regras principais

- Tamanho máximo de linha: **100 caracteres**
- Docstrings em todas as funções públicas
- Type hints nos parâmetros e retorno
- Imports organizados (ruff cuida disso)

---

## 📝 Commits

Seguimos **Conventional Commits** em português:

| Prefixo | Quando usar |
|---------|-------------|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug |
| `docs:` | Apenas documentação |
| `refactor:` | Refatoração sem mudar comportamento |
| `test:` | Adição ou correção de testes |
| `chore:` | Tarefas de manutenção (deps, CI, configs) |

### Exemplos

```
feat: adiciona ferramenta de pesquisa web
fix: corrige erro de encoding ao ler arquivos UTF-8
docs: atualiza guia de instalação
refactor: simplifica lógica de autodiscovery de tools
test: adiciona testes para memory_search
chore: atualiza dependências do projeto
```

---

## 🤝 Código de Conduta

Resumo: **seja legal.**

- Trate todos com respeito
- Críticas construtivas, não destrutivas
- Sem assédio, discriminação ou comportamento tóxico
- Foque no código e nas ideias, não nas pessoas
- Perguntas são bem-vindas — ninguém nasce sabendo

Se alguém violar essas regras, reporte aos mantenedores. Comportamento tóxico resulta em ban.

---

## ❓ Dúvidas?

Abra uma **issue** no GitHub ou mande uma mensagem. Toda contribuição é bem-vinda, de um typo fix até uma feature completa. 🐺
