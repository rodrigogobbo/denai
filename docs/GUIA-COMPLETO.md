# 🐺 DenAI — Guia Completo para Iniciantes

> **Versão:** 1.0  
> **Última atualização:** Julho 2025  
> **Público-alvo:** Pessoas que nunca usaram terminal, programação ou IA local  
> **Sistema:** Windows 10 / Windows 11

---

## 📖 Índice

1. [O que é isso?](#-o-que-é-isso)
2. [Antes de começar](#-antes-de-começar)
3. [Instalação Passo a Passo](#-instalação-passo-a-passo)
4. [Como Usar](#-como-usar)
5. [Resolução de Problemas](#-resolução-de-problemas)
6. [Perguntas Frequentes](#-perguntas-frequentes)
7. [Instalação Manual](#-instalação-manual-se-o-instalador-falhar)
8. [Desinstalação](#-desinstalação)
9. [Glossário](#-glossário)

---

## 🤖 O que é isso?

Imagine ter um **ChatGPT pessoal, de graça, rodando no seu computador**. Sem pagar assinatura. Sem criar conta. Sem mandar seus dados pra ninguém. É exatamente isso que o DenAI faz.

### Em palavras simples:

O DenAI é um programa que roda uma **inteligência artificial** (IA) diretamente no seu computador. Você conversa com ela digitando perguntas, e ela responde — exatamente como o ChatGPT, o Gemini ou o Copilot que você talvez já tenha usado na internet.

**A diferença?**

| | ChatGPT (internet) | 🐺 DenAI (seu PC) |
|---|---|---|
| 💰 Custo | Grátis com limites / Pago ($20/mês) | **100% grátis, pra sempre** |
| 🌐 Precisa de internet? | Sim, sempre | **Não** (só pra instalar) |
| 🔐 Privacidade | Seus dados vão pros servidores da OpenAI | **Nada sai do seu computador** |
| 📧 Precisa de conta? | Sim (email, telefone) | **Não** |
| 🔑 Precisa de API key? | Sim, pra uso avançado | **Não** |
| ⚡ Funciona offline? | Não | **Sim!** |

> 💡 **Pense assim:** É como instalar o Word no computador em vez de usar o Google Docs online. O programa roda na sua máquina, os arquivos ficam na sua máquina, e ninguém mais tem acesso.

### O que você pode fazer com o DenAI?

- ✅ **Conversar** — Fazer perguntas sobre qualquer assunto
- ✅ **Escrever textos** — E-mails, redações, resumos, relatórios
- ✅ **Programar** — Pedir ajuda com código, criar scripts
- ✅ **Traduzir** — Textos entre idiomas
- ✅ **Estudar** — A IA explica temas como um professor particular
- ✅ **Analisar arquivos** — Ler e resumir documentos do seu computador
- ✅ **Executar comandos** — Automatizar tarefas no Windows
- ✅ **Pesquisar na web** — Buscar informações atualizadas (precisa de internet pra isso)
- ✅ **Lembrar coisas** — A IA tem memória entre conversas

> 🔒 **Sobre privacidade:** Tudo que você digita fica **apenas no seu computador**. Nenhuma empresa recebe seus dados. Nenhum servidor externo é contatado. É como escrever num caderno que só você tem a chave.

---

## ✅ Antes de começar

Antes de instalar, vamos verificar se o seu computador consegue rodar o DenAI. Não se preocupe — vou te guiar em cada passo!

### 🖥️ Que Windows eu tenho?

Precisamos do **Windows 10** ou **Windows 11**. Veja como descobrir qual é o seu:

1. Aperte as teclas **Windows + I** ao mesmo tempo (a tecla Windows é aquela com o símbolo ⊞ do Windows, geralmente entre Ctrl e Alt)
2. Vai abrir a tela de **Configurações**
3. Clique em **Sistema**
4. Role pra baixo e clique em **Sobre** (ou "Informações do sistema")
5. Procure por **"Edição"** — vai dizer algo como "Windows 11 Home" ou "Windows 10 Pro"

> ⚠️ **Se você tem Windows 7 ou 8:** Infelizmente não é compatível. Você precisaria atualizar para o Windows 10 ou 11 primeiro.

### 💾 Quanta memória RAM eu tenho?

**O que é RAM?** RAM é a "memória de trabalho" do computador. É como a mesa onde você coloca os papéis que está usando agora. Quanto maior a mesa, mais coisas você consegue fazer ao mesmo tempo. A IA precisa de bastante "espaço na mesa" pra funcionar.

**Como verificar:**

1. Aperte **Ctrl + Shift + Esc** ao mesmo tempo (isso abre o "Gerenciador de Tarefas")
2. Se aparecer uma janela simples, clique em **"Mais detalhes"** na parte de baixo
3. Clique na aba **"Desempenho"** (ou "Performance")
4. Clique em **"Memória"** no menu da esquerda
5. No canto superior direito, vai aparecer algo como **"8,0 GB"** ou **"16,0 GB"**

**Requisitos de RAM:**

| RAM do seu PC | Funciona? | O que esperar |
|---|---|---|
| 4 GB ou menos | ❌ Não | Muito pouca memória pra rodar IA |
| 8 GB | ✅ Básico | Modelos 3-4B. Conversas simples, texto, perguntas. Não vai editar arquivos ou executar planos sozinho de forma confiável |
| 16 GB | ⭐ Recomendado | Modelos 7-8B. Conversa boa, gera código, usa tools (ler/escrever arquivos, executar comandos). Acerta na maioria das vezes |
| 32 GB+ | 🏆 Ideal | Modelos 14-32B. Tool calling preciso, planning multi-step, edita vários arquivos em sequência. Experiência mais próxima de ChatGPT/Copilot |

> 💡 **Traduzindo:** Se seu computador tem **8 GB de RAM**, você consegue rodar. Com **16 GB**, roda muito bem. Se não sabe o que significa "3B" ou "7B", não se preocupe — vou explicar mais adiante!

### 💿 Espaço em disco

Você precisa de **10 a 20 GB livres** no disco. Parece muito, mas a IA precisa de espaço pro "cérebro" dela (o modelo).

**Como verificar espaço livre:**

1. Abra o **Explorador de Arquivos** (aquele ícone de pasta amarela na barra de tarefas, ou aperte **Windows + E**)
2. No lado esquerdo, clique em **"Este Computador"** (ou "Meu Computador")
3. Você vai ver seus discos (geralmente **C:**)
4. Embaixo de cada disco, tem uma barra mostrando quanto espaço está usado
5. Precisa ter pelo menos **15 GB livres** (idealmente 20 GB)

> ⚠️ **Disco cheio?** Antes de instalar, esvazie a Lixeira (clique com o botão direito no ícone da Lixeira na área de trabalho → "Esvaziar Lixeira") e delete arquivos que não precisa mais. Isso pode liberar vários GBs!

### 🌐 Conexão com a internet

Você precisa de internet **apenas para a instalação**. Depois que tudo estiver instalado, a IA funciona **100% offline** (sem internet).

- A instalação vai baixar uns **5-10 GB** de arquivos
- Se sua internet for lenta, pode demorar — mas é só uma vez!
- Depois, a única coisa que precisa de internet é a função de "pesquisa na web" (que é opcional)

### 🎮 Placa de vídeo (GPU) — Opcional mas recomendado

**O que é GPU?** É a "placa de vídeo" do computador. Normalmente é usada pra jogos e vídeos, mas a IA também consegue usar ela pra pensar muito mais rápido.

**Você NÃO precisa de GPU pra usar o DenAI!** Ele funciona só com o processador (CPU). Mas se você tiver uma placa de vídeo NVIDIA (como GTX 1060, RTX 3060, RTX 4070, etc.), a IA vai ser **muito mais rápida** — automaticamente, sem configurar nada.

**Como verificar se você tem GPU NVIDIA:**

1. Aperte **Windows + R** (abre a janela "Executar")
2. Digite `dxdiag` e aperte Enter
3. Clique na aba **"Exibição"** (ou "Display")
4. Procure por **"Nome"** — se disser algo com "NVIDIA", ótimo!

> 💡 **Resumo rápido dos requisitos:**
> - ✅ Windows 10 ou 11
> - ✅ 8 GB de RAM (16 GB ideal)
> - ✅ 15-20 GB livres no disco
> - ✅ Internet pra instalar
> - ⭐ GPU NVIDIA (opcional, mas deixa tudo mais rápido)

---

## 📦 Instalação Passo a Passo

Agora vamos ao que interessa! Siga cada passo com calma. Se algo der errado, vá pra seção de [Resolução de Problemas](#-resolução-de-problemas).

---

### 📥 Passo 1: Instalar o Python

O DenAI precisa do Python pra funcionar. Se você já tem Python 3.10+ instalado, pode pular este passo.

1. Abra o navegador
2. Acesse: **[python.org/downloads](https://www.python.org/downloads/)**
3. Clique no botão amarelo grande **"Download Python 3.x.x"**
4. Execute o instalador que foi baixado
5. **⚠️ MUITO IMPORTANTE:** Na primeira tela, **marque a caixa "Add python.exe to PATH"** (fica na parte de baixo!)
6. Clique em **"Install Now"**
7. Espere terminar e clique em "Close"

**Verificar se funcionou:**

1. Abra o Prompt de Comando (`Windows + R` → `cmd` → Enter)
2. Digite:
```
python --version
```
3. Deve aparecer algo como `Python 3.12.4`. Se aparecer, sucesso! ✅

> ⚠️ **Se esquecer de marcar "Add Python to PATH"**, o DenAI não vai encontrar o Python. Nesse caso, desinstale o Python e instale novamente, marcando a caixa desta vez.

---

### ⚙️ Passo 2: Instalar o Ollama

O Ollama é o "motor" que roda os modelos de IA no seu computador.

1. Abra o navegador
2. Acesse: **[ollama.com/download](https://ollama.com/download)**
3. Clique em **"Download for Windows"**
4. Execute o instalador baixado (`OllamaSetup.exe`)
5. Siga os passos do instalador (Next → Next → Install → Finish)
6. O Ollama vai iniciar automaticamente (você pode ver o ícone na bandeja do sistema)

**Verificar se funcionou:**

1. Abra o Prompt de Comando
2. Digite:
```
ollama --version
```
3. Deve aparecer a versão. Se aparecer, sucesso! ✅

---

### 🧠 Passo 3: Baixar um Modelo de IA e Instalar o DenAI

Agora vamos baixar o "cérebro" da IA e instalar o DenAI.

#### O que é um "modelo de IA"?

Pense assim: o DenAI é o **corpo** da IA (a interface, os botões, a tela). O **modelo** é o **cérebro**. Existem vários cérebros disponíveis, cada um com habilidades diferentes. Você pode trocar de cérebro a qualquer momento!

> 💡 **Os números no nome (3B, 7B, 8B) significam o tamanho do cérebro.** "B" vem de "billion" (bilhão) — é o número de "neurônios artificiais". Quanto maior, mais inteligente, mas também mais lento e pesado.

#### 📋 Tabela de modelos recomendados:

| Modelo | Tamanho | RAM necessária | Velocidade | Pra que serve | Recomendação |
|---|---|---|---|---|---|
| `llama3.2:3b` | ~2 GB | 8 GB | ⚡⚡⚡ Muito rápido | Conversas simples, perguntas rápidas | 🟢 **PC com pouca memória** |
| `llama3.1:8b` | ~4.7 GB | 10 GB | ⚡⚡ Rápido | Uso geral, bom equilíbrio | ⭐ **Recomendado pra maioria** |
| `qwen2.5-coder:7b` | ~4.4 GB | 10 GB | ⚡⚡ Rápido | Programação e código | 🔵 **Se você programa** |
| `deepseek-r1:8b` | ~4.9 GB | 10 GB | ⚡⚡ Rápido | Raciocínio lógico, matemática | 🟣 **Problemas complexos** |
| `mistral:7b` | ~4.1 GB | 10 GB | ⚡⚡ Rápido | Versátil, bom em português | 🟡 **Boa opção geral** |
| `gemma3:4b` | ~3.3 GB | 8 GB | ⚡⚡⚡ Rápido | Leve e inteligente pra seu tamanho | 🟢 **Alternativa leve** |

> 💡 **Não sabe qual escolher?** Comece com o **`llama3.1:8b`**. É o mais equilibrado — nem muito pesado, nem muito limitado. Funciona bem pra quase tudo.

> 💡 **Se seu PC tem 8 GB de RAM:** Use o **`llama3.2:3b`** ou **`gemma3:4b`**. Modelos maiores podem deixar o computador lento.

#### Baixar o modelo:

1. Abra o **Prompt de Comando** (aperte **Windows + R**, digite `cmd`, aperte Enter)
2. Digite o comando e aperte Enter:

```
ollama pull llama3.1:8b
```

3. Espere o download terminar (barra de progresso vai aparecer)
4. Pronto! O modelo está disponível

#### Instalar o DenAI:

No mesmo Prompt de Comando, digite:

```
pip install denai
```

Ou, se você clonou o repositório:

```
pip install .
```

> 💡 **Você pode ter vários modelos instalados ao mesmo tempo!** Baixe quantos quiser e alterne entre eles no DenAI.

#### Como ver quais modelos você já tem:

1. Abra o Prompt de Comando (`Windows + R` → `cmd` → Enter)
2. Digite:

```
ollama list
```

3. Vai aparecer uma lista com todos os modelos instalados

#### Como remover um modelo que não quer mais:

```
ollama rm nome-do-modelo
```

Por exemplo: `ollama rm llama3.2:3b`

> 💡 **Removendo modelos, você libera espaço no disco.** Cada modelo ocupa de 2 a 5 GB.

---

### 🚀 Passo 4: Iniciar o DenAI

Tudo pronto! Vamos ligar a IA!

1. Abra o **Prompt de Comando** (`Windows + R` → `cmd` → Enter)
2. Digite:

```
denai
```

3. Espere aparecer uma mensagem parecida com:

```
🐺 DenAI rodando!
Acesse: http://localhost:4078
```

4. O seu **navegador** (Chrome, Edge, etc.) vai abrir automaticamente com o DenAI
5. **Pronto! Você já pode conversar com a IA!** 🎉

> A interface web é servida automaticamente pelo DenAI — não precisa abrir nenhum arquivo HTML separado.

> 💡 **O que é "localhost:4078"?** "localhost" significa "este computador aqui". "4078" é o número da "porta" (como o número de um apartamento). Então `localhost:4078` significa "o programa que está rodando neste computador, na porta 4078". Nada sai pra internet — tudo fica aqui.

#### Se o navegador não abrir automaticamente:

1. Abra seu navegador manualmente (Chrome, Edge, Firefox)
2. Na barra de endereço (onde você digita os sites), digite:

```
localhost:4078
```

3. Aperte **Enter**
4. O DenAI vai aparecer!

> ⚠️ **IMPORTANTE:** Não feche a janela do terminal enquanto estiver usando o DenAI! Se fechar, a IA para de funcionar. Pode minimizar a janela (clicar no botão ➖ no canto superior direito), mas não feche.

#### Para parar o DenAI:

1. Clique na janela do terminal
2. Aperte **Ctrl + C** (segure Ctrl e aperte C)
3. Ou simplesmente feche a janela do terminal (clique no ❌)

#### Para usar novamente outro dia:

Basta abrir o Prompt de Comando e digitar `denai` de novo! Não precisa instalar nada novamente. O DenAI abre em segundos.

---

## 💬 Como Usar

O DenAI está aberto no navegador. Agora vamos aprender a usar!

---

### 🗣️ Conversando com a IA

A tela principal tem uma **caixa de texto** na parte de baixo. É ali que você digita.

1. **Clique na caixa de texto**
2. **Digite sua pergunta ou pedido**
3. **Aperte Enter** (ou clique no botão de enviar ➤)
4. A IA começa a responder **em tempo real** — você vai ver o texto aparecendo palavra por palavra

#### Exemplos de coisas que você pode perguntar:

```
Me explique o que é inteligência artificial como se eu tivesse 10 anos
```

```
Escreva um e-mail profissional pedindo férias pro meu chefe
```

```
Qual a diferença entre Windows 10 e Windows 11?
```

```
Me ajude a montar um cardápio saudável pra semana
```

```
Resuma o texto abaixo em 3 parágrafos: [cole o texto aqui]
```

```
Traduza para inglês: "Preciso remarcar a reunião para sexta-feira"
```

> 💡 **A IA responde em "streaming"** — isso significa que o texto vai aparecendo aos poucos, como se alguém estivesse digitando. É normal! Não precisa esperar um tempão — a resposta vai surgindo em tempo real.

---

### 🎯 Dicas para obter respostas melhores

A qualidade da resposta depende muito de **como você pergunta**. Aqui vão algumas dicas:

#### 1. Seja específico

| ❌ Pergunta vaga | ✅ Pergunta específica |
|---|---|
| "Me fala sobre saúde" | "Quais são os 5 melhores exercícios para dor lombar?" |
| "Como cozinhar?" | "Como fazer arroz soltinho na panela comum?" |
| "Me ajuda com trabalho" | "Escreva uma introdução de 3 parágrafos sobre aquecimento global para um trabalho escolar do 9° ano" |

#### 2. Dê contexto

```
Sou professor de matemática do ensino fundamental.
Preciso criar 10 exercícios de fração para alunos do 5° ano.
Os exercícios devem ser progressivos (do mais fácil ao mais difícil).
Inclua o gabarito no final.
```

> 💡 **Quanto mais contexto você der, melhor a resposta.** Diga quem você é, pra quem é o texto, qual o nível de dificuldade, o formato que quer, etc.

#### 3. Peça passo a passo

```
Me ensine a criar uma tabela no Excel, passo a passo,
como se eu nunca tivesse usado o programa antes.
```

#### 4. Peça pra reformular

Se a resposta não ficou boa, você pode pedir ajustes:

```
Ficou muito formal. Reescreva de forma mais casual e divertida.
```

```
Resuma isso em 3 frases.
```

```
Agora explique como se fosse pra uma criança de 8 anos.
```

#### 5. Use a IA como parceira de ideias

```
Estou planejando uma festa de aniversário para 30 pessoas
com orçamento de R$500. Me dê ideias criativas.
```

```
Preciso de um nome para minha loja de roupas femininas online.
Me dê 20 sugestões criativas.
```

---

### ⭐ Funcionalidades Especiais

O DenAI não é só um chat. Ele tem superpoderes!

#### 📁 Ler arquivos do seu computador

Você pode pedir pra IA ler e analisar arquivos que estão no seu computador:

```
Leia o arquivo C:\Users\SeuNome\Documents\relatorio.txt e faça um resumo
```

```
Analise o arquivo C:\Users\SeuNome\Desktop\dados.csv e me diga
quais são os 5 produtos mais vendidos
```

> ⚠️ **O caminho do arquivo precisa estar correto!** Se não souber o caminho, você pode:
> 1. Encontre o arquivo no Explorador de Arquivos
> 2. Clique com o botão direito nele
> 3. Selecione **"Copiar como caminho"** (ou segure Shift + clique com botão direito → "Copiar caminho completo")
> 4. Cole no chat com Ctrl + V

#### 💻 Executar comandos no Windows

A IA pode executar comandos no seu computador (como listar arquivos, verificar informações do sistema, etc.):

```
Liste todos os arquivos da minha pasta Documentos
```

```
Qual o tamanho total da minha pasta Downloads?
```

```
Me mostre as informações do meu computador (processador, RAM, etc.)
```

> ⚠️ **A IA vai pedir sua confirmação antes de executar qualquer comando.** Ela nunca vai fazer nada sem você aprovar. Isso é uma medida de segurança!

> ⚠️ **Cuidado com comandos destrutivos.** Não peça pra IA deletar arquivos importantes ou mexer em configurações do sistema que você não entende. Na dúvida, pergunte o que o comando faz antes de aprovar.

#### 🧠 Memória entre conversas

O DenAI pode **lembrar** de informações entre conversas:

```
Lembre que meu nome é Maria e eu trabalho com contabilidade
```

Na próxima conversa, você pode perguntar:

```
Qual é meu nome?
```

E a IA vai lembrar! Isso é útil para:
- Preferências pessoais
- Contexto de trabalho
- Informações que você usa frequentemente

> 💡 **Tudo fica salvo localmente.** As memórias são armazenadas em `~/.denai/` no seu computador, nunca na internet.

#### 🔍 Pesquisa na Web

Se a IA precisar de informações atualizadas, ela pode pesquisar na internet:

```
Pesquise na web: qual a cotação do dólar hoje?
```

```
Busque as últimas notícias sobre inteligência artificial
```

> ⚠️ **Essa é a única função que precisa de internet.** Todas as outras funcionam offline.

#### 👨‍💻 Ajuda com Programação

Se você programa (ou quer aprender), a IA é ótima pra isso:

```
Crie um script em Python que renomeia todos os arquivos
de uma pasta adicionando a data no nome
```

```
Me explique o que esse código faz: [cole o código]
```

```
Encontre o erro nesse código: [cole o código]
```

> 💡 **Para programação, o modelo `qwen2.5-coder:7b` é o melhor.** Ele foi treinado especificamente pra código.

---

### 📂 Gerenciando Conversas

#### Criar nova conversa

- Clique no botão **"+ Nova Conversa"** (ou **"New Chat"**) no topo da barra lateral (sidebar)
- Ou use o atalho de teclado (geralmente **Ctrl + N**)
- Cada conversa é independente — a IA não mistura os assuntos

> 💡 **Quando criar uma nova conversa?** Sempre que mudar de assunto! Se estava falando sobre receitas e quer perguntar sobre programação, crie uma nova. Isso ajuda a IA a dar respostas melhores.

#### Alternar entre conversas

- Na **barra lateral esquerda**, você vê todas as suas conversas anteriores
- Clique em qualquer uma pra voltar a ela
- As conversas são salvas automaticamente — mesmo se fechar o navegador, elas continuam lá

#### Deletar conversas

- Passe o mouse sobre uma conversa na barra lateral
- Clique no ícone de **lixeira** 🗑️ que aparece
- Confirme a exclusão

> 💡 **Deletar uma conversa é permanente!** Se tem algo importante numa conversa, copie o texto antes de deletar.

---

### 🔄 Trocar o Modelo de IA

Você pode trocar o "cérebro" da IA a qualquer momento, sem perder suas conversas!

1. Na **barra lateral** ou no **topo da tela**, procure um **menu dropdown** (uma caixinha com o nome do modelo atual)
2. Clique nele
3. Selecione outro modelo da lista
4. Pronto! A próxima resposta já vai usar o novo modelo

> 💡 **Dica:** Use modelos diferentes pra tarefas diferentes!
> - Pergunta rápida? → `llama3.2:3b` (responde mais rápido)
> - Texto longo e elaborado? → `llama3.1:8b` (mais inteligente)
> - Código? → `qwen2.5-coder:7b` (especialista)
> - Problema de lógica? → `deepseek-r1:8b` (raciocínio avançado)

---

### ⚙️ Configurações Avançadas

O DenAI funciona sem configurar nada, mas se quiser personalizar, use variáveis de ambiente:

```bash
# Windows (PowerShell)
$env:DENAI_MAX_TOOL_ROUNDS = "50"     # Mais rodadas de ferramentas (padrão: 25)
$env:DENAI_MAX_CONTEXT = "131072"     # Janela de contexto maior (padrão: 65536)
$env:DENAI_MODEL = "qwen2.5-coder:32b"  # Modelo padrão
denai

# Linux / macOS
DENAI_MAX_TOOL_ROUNDS=50 DENAI_MAX_CONTEXT=131072 denai
```

| Variável | Padrão | O que faz |
|----------|--------|-----------|
| `DENAI_MODEL` | `llama3.1:8b` | Modelo que a IA usa |
| `DENAI_PORT` | `4078` | Porta do servidor web |
| `DENAI_MAX_TOOL_ROUNDS` | `25` | Quantas vezes a IA pode usar ferramentas por mensagem |
| `DENAI_MAX_CONTEXT` | `65536` | Tamanho máximo da "memória de curto prazo" (em tokens) |

> 💡 **O que é contexto?** É o quanto a IA consegue "lembrar" da conversa atual. O DenAI ajusta automaticamente de 8k a 64k tokens conforme a conversa cresce. Se a conversa ficar muito longa, ele resume as mensagens antigas automaticamente.

---

## 🔧 Resolução de Problemas

Algo deu errado? Calma! Vamos resolver. Encontre o seu problema abaixo:

---

### ❌ "O Ollama não está respondendo"

**O que é Ollama?** É o programa que roda a IA por baixo dos panos. Se ele parar, a IA para de funcionar.

**Solução passo a passo:**

1. **Verifique se o Ollama está rodando:**
   - Olhe na **bandeja do sistema** (os ícones pequenos no canto inferior direito da tela, perto do relógio)
   - Procure pelo ícone do Ollama (uma alpaca/lhama estilizada)
   - Se não estiver lá, o Ollama não está rodando

2. **Reinicie tudo:**
   - Feche a janela do terminal (se estiver aberta)
   - Feche o navegador
   - Abra o Prompt de Comando e digite `denai` novamente
   - Espere a mensagem "Rodando em http://localhost:4078"
   - Tente de novo

3. **Verifique se o firewall não está bloqueando:**
   - Aperte **Windows + I** (Configurações)
   - Vá em **Privacidade e Segurança** → **Segurança do Windows** → **Firewall e proteção de rede**
   - Clique em **"Permitir um aplicativo pelo firewall"**
   - Verifique se "Ollama" e "Python" estão na lista e estão marcados
   - Se não estiverem, clique em **"Alterar configurações"** → **"Permitir outro aplicativo"** e adicione-os

4. **Reinicie o Ollama manualmente:**
   - Abra o Prompt de Comando (`Windows + R` → `cmd` → Enter)
   - Digite:
   ```
   ollama serve
   ```
   - Se aparecer "Error: listen tcp ... bind: address already in use", o Ollama já está rodando. O problema é outro.
   - Se funcionar, deixe essa janela aberta e tente acessar o DenAI novamente.

---

### 🐌 "O modelo é muito lento"

Se a IA demora muito pra responder ou o texto aparece muito devagar:

#### Solução 1: Use um modelo menor

Modelos menores respondem mais rápido:

```
ollama pull llama3.2:3b
```

Depois, troque pro modelo menor na interface do DenAI.

#### Solução 2: Feche outros programas

A IA usa muita memória e processamento. Feche programas pesados:

- Navegadores com muitas abas (cada aba consome memória!)
- Jogos
- Programas de edição de vídeo/imagem
- Programas de streaming

**Como ver o que está consumindo memória:**

1. Aperte **Ctrl + Shift + Esc** (Gerenciador de Tarefas)
2. Clique na coluna **"Memória"** pra ordenar
3. Feche os programas que estão usando mais memória (clique com botão direito → "Finalizar tarefa")

> ⚠️ **Não feche processos do sistema!** Se não sabe o que um processo faz, não feche. Foque em programas que você reconhece (Chrome, Spotify, Photoshop, etc.).

#### Solução 3: Aproveite sua GPU NVIDIA

Se você tem uma placa de vídeo NVIDIA, o Ollama deve usá-la automaticamente. Para confirmar:

1. Abra o Prompt de Comando
2. Digite:
```
nvidia-smi
```
3. Se aparecer informações da sua placa, ótimo — ela está sendo usada!
4. Se aparecer "não reconhecido", você precisa instalar os **drivers da NVIDIA**:
   - Vá em [nvidia.com.br/drivers](https://www.nvidia.com.br/Download/index.aspx)
   - Baixe o driver mais recente pra sua placa
   - Instale e reinicie o computador

#### Solução 4: Use modelos "quantizados" menores

Modelos quantizados são versões "comprimidas" que usam menos memória:

```
ollama pull llama3.1:8b-instruct-q4_0
```

O `q4_0` significa uma quantização mais agressiva — menor e mais rápido, com uma pequena perda de qualidade.

---

### ❌ "Erro ao instalar"

#### Problema: "Não foi possível baixar..."

- **Verifique sua internet:** Abra o navegador e tente acessar qualquer site
- **Tente novamente:** Às vezes a conexão falha temporariamente. Rode `pip install denai` de novo
- **Use uma conexão estável:** Se estiver no Wi-Fi, tente conectar com cabo de rede

#### Problema: "Acesso negado" ou "Permissão negada"

- Tente rodar com permissões elevadas:
  - Windows: abra o Prompt de Comando como administrador
  - Linux/Mac: use `pip install --user denai`

#### Problema: "Python não encontrado"

1. Abra o navegador
2. Vá em [python.org/downloads](https://www.python.org/downloads/)
3. Clique no botão amarelo grande **"Download Python 3.x.x"**
4. Execute o instalador que foi baixado
5. **⚠️ MUITO IMPORTANTE:** Na primeira tela do instalador, marque a caixa **"Add Python to PATH"** (ela fica na parte de baixo)
6. Clique em **"Install Now"**
7. Espere terminar
8. Rode `pip install denai` novamente

> ⚠️ **Se esquecer de marcar "Add Python to PATH"**, o DenAI não vai encontrar o Python. Nesse caso, desinstale o Python (Configurações → Aplicativos → Python → Desinstalar) e instale novamente, marcando a caixa desta vez.

---

### ❌ "denai não é reconhecido como comando"

Você instalou com `pip install denai`, deu tudo certo, mas ao digitar `denai` aparece:

```
'denai' não é reconhecido como um comando interno ou externo,
programa operável ou arquivo em lotes.
```

**Por que isso acontece?** O `pip install` coloca o executável `denai.exe` na pasta `Scripts/` do Python. Se essa pasta não está no PATH do Windows, o terminal não encontra o comando.

#### Solução 1: Usar `python -m denai` (mais fácil)

Em vez de digitar `denai`, digite:

```
python -m denai
```

Isso funciona **sempre**, independente do PATH. Se funcionar, use esse comando!

#### Solução 2: Descobrir onde o `denai.exe` foi instalado

1. Abra o Prompt de Comando
2. Digite:
```
pip show denai
```
3. Procure a linha **"Location:"** — algo como `c:\users\seunome\appdata\local\programs\python\python312\lib\site-packages`
4. O executável está em uma pasta vizinha chamada `Scripts`. No exemplo acima, seria:
```
c:\users\seunome\appdata\local\programs\python\python312\Scripts\denai.exe
```
5. Tente rodar o caminho completo:
```
c:\users\seunome\appdata\local\programs\python\python312\Scripts\denai.exe
```

#### Solução 3: Adicionar Scripts ao PATH (definitivo)

1. Descubra o caminho da pasta Scripts (veja Solução 2)
2. Aperte **Windows + R**, digite `sysdm.cpl` e aperte Enter
3. Clique na aba **"Avançado"** (ou "Advanced")
4. Clique em **"Variáveis de Ambiente"** (ou "Environment Variables")
5. Na seção **"Variáveis do usuário"**, encontre **Path** e clique em **"Editar"**
6. Clique em **"Novo"**
7. Cole o caminho da pasta Scripts (ex: `C:\Users\SeuNome\AppData\Local\Programs\Python\Python312\Scripts`)
8. Clique **OK** em todas as janelas
9. **Feche e reabra** o Prompt de Comando (o PATH só atualiza em janelas novas)
10. Agora `denai` vai funcionar! ✅

> 💡 **Dica:** Se você usou `pip install --user denai`, o executável pode estar em `C:\Users\SeuNome\AppData\Roaming\Python\Python312\Scripts`. Use `pip show denai` pra descobrir onde ficou.

#### Solução 4: Reinstalar o Python marcando "Add to PATH"

Se nada funciona, a forma mais simples é reinstalar o Python:

1. Desinstale o Python (Configurações → Aplicativos → Python → Desinstalar)
2. Baixe novamente em [python.org/downloads](https://www.python.org/downloads/)
3. Ao instalar, **marque "Add python.exe to PATH"**
4. Clique em **"Install Now"**
5. Abra um **novo** Prompt de Comando
6. Rode `pip install denai` novamente
7. Agora `denai` deve funcionar!

---

### ❌ "O servidor não inicia"

#### Problema: "Porta 4078 já em uso"

Isso significa que outro programa está usando a mesma "porta" que o DenAI precisa.

1. Abra o Prompt de Comando **como administrador**:
   - Aperte **Windows + R**
   - Digite `cmd`
   - Aperte **Ctrl + Shift + Enter** (isso abre como administrador)
   - Clique "Sim" no popup

2. Digite:
```
netstat -ano | findstr :4078
```

3. Se aparecer algo, anote o número final (PID). Por exemplo:
```
TCP    0.0.0.0:4078    0.0.0.0:0    LISTENING    12345
```
O PID é `12345`.

4. Feche o processo com:
```
taskkill /PID 12345 /F
```

5. Tente iniciar o DenAI novamente.

> 💡 **Traduzindo:** "Porta" é como o número de um apartamento. Dois moradores não podem usar o mesmo apartamento. Se outro programa já está na "porta 4078", precisamos tirar ele de lá primeiro.

#### Problema: "Python não encontrado" ao iniciar

1. Abra o Prompt de Comando
2. Digite:
```
python --version
```
3. Se aparecer "não reconhecido como comando", o Python não está instalado ou não está no PATH
4. Veja a solução em [Problema: "Python não encontrado"](#problema-python-não-encontrado)

#### Problema: Reinstalar do zero

Se nada funciona, tente uma instalação limpa:

1. Desinstale o DenAI:
```
pip uninstall denai
```
2. Reinstale:
```
pip install denai
```
3. Isso vai recriar o ambiente limpo

---

### ❌ "A IA dá respostas estranhas ou sem sentido"

Isso pode acontecer por alguns motivos:

1. **O modelo é muito pequeno** — Modelos 3B são mais propensos a erros. Tente um modelo maior (7B ou 8B)
2. **A pergunta é muito longa** — Modelos locais têm um limite de "memória" na conversa. Se a conversa ficou muito longa, comece uma nova
3. **O modelo não foi feito pra isso** — O `qwen2.5-coder` é ótimo pra código, mas pode não ser ideal pra receitas de bolo. Use o modelo certo pra cada tarefa

> 💡 **Dica:** Se a IA parece "confusa", comece uma nova conversa. Às vezes o histórico muito longo atrapalha.

---

### ❌ "O DenAI travou / não responde"

1. **Espere 30 segundos** — Às vezes a IA está processando algo pesado
2. **Atualize a página** — Aperte **F5** ou **Ctrl + R** no navegador
3. **Reinicie tudo:**
   - Feche a janela do terminal
   - Feche o navegador
   - Abra o Prompt de Comando e digite `denai` novamente
4. Se o problema persistir, **reinicie o computador** e tente novamente

---

### ❌ "Não consigo acessar de outro computador"

Se quer acessar o DenAI de outro computador na mesma rede (ex: do celular ou notebook):

1. **Descubra o IP do computador que roda o DenAI:**
   - Abra o Prompt de Comando
   - Digite: `ipconfig`
   - Procure por **"Endereço IPv4"** (algo como `192.168.1.100`)

2. **No outro dispositivo**, abra o navegador e digite:
```
http://192.168.1.100:4078
```
(troque pelo IP que você encontrou)

3. **Se não funcionar**, o firewall pode estar bloqueando. Você precisa liberar a porta 4078:
   - Configurações → Segurança do Windows → Firewall → Configurações avançadas
   - Regras de Entrada → Nova Regra → Porta → TCP 4078 → Permitir
   - Dê um nome como "DenAI" e salve

> ⚠️ **Isso só funciona na mesma rede!** Ou seja, ambos os dispositivos precisam estar no mesmo Wi-Fi ou na mesma rede do escritório.

---

## ❓ Perguntas Frequentes

### "É seguro usar?"

**Sim!** O DenAI roda 100% no seu computador. Seus dados nunca saem da sua máquina. É como usar o Bloco de Notas ou o Word — tudo fica local. Nenhuma empresa recebe suas conversas, e nenhuma informação é enviada pela internet (exceto se você usar a função de pesquisa na web, que é opcional).

---

### "Precisa de internet?"

**Só pra instalar.** Depois que tudo está instalado, o DenAI funciona **100% offline** — pode até desconectar o cabo de rede ou desligar o Wi-Fi. A única exceção é a função de **pesquisa na web**, que obviamente precisa de internet.

---

### "Quanto custa?"

**Nada. Zero. Grátis. Pra sempre.** 🎉

Todos os componentes são software livre (open source):
- O DenAI é gratuito
- O Ollama é gratuito
- Os modelos de IA são gratuitos
- O Python é gratuito

Não tem assinatura, não tem período de teste, não tem versão "premium". É de graça e ponto.

---

### "Posso usar no trabalho?"

**Sim!** Na verdade, é **ideal** para o trabalho, justamente porque nada é enviado pra fora do computador. Você pode conversar sobre documentos confidenciais, contratos, dados financeiros — tudo fica no seu PC. Nenhum dado corporativo vai parar nos servidores de uma big tech.

> 💡 **Dica para empresas:** Se sua empresa tem políticas de segurança rígidas, o DenAI é uma ótima opção porque atende ao requisito de não enviar dados para terceiros.

---

### "Como atualizar o DenAI?"

```
pip install --upgrade denai
```

Seus modelos e conversas **não são afetados** — eles ficam em pastas separadas (`~/.denai/` e a pasta do Ollama).

> 💡 Os modelos de IA ficam na pasta do Ollama (`C:\Users\SeuNome\.ollama`), não na pasta do DenAI. Então atualizar o DenAI nunca deleta seus modelos.

---

### "Posso rodar vários modelos ao mesmo tempo?"

Sim e não:
- Você pode **ter** vários modelos instalados ao mesmo tempo ✅
- Mas o Ollama só **usa** um modelo por vez ❌
- Trocar de modelo é instantâneo — basta selecionar outro na interface
- Se precisar baixar um novo, use: `ollama pull nome-do-modelo`

---

### "E se meu PC for fraco?"

Mesmo com um PC modesto, dá pra usar! Dicas:

1. **8 GB de RAM:** Use `llama3.2:3b` ou `gemma3:4b`. São leves e respondem rápido
2. **Sem GPU:** Funciona 100% na CPU, só é mais lento. Um `llama3.2:3b` na CPU responde em 5-15 segundos
3. **SSD vs HD:** SSD faz MUITA diferença na hora de carregar o modelo. Se seu PC tem HD, considere trocar por SSD (~R$150 pra 240 GB)
4. **Feche outros programas:** Chrome com muitas abas consome RAM. Feche o que não precisa antes de usar o DenAI

**Quer investir pra melhorar?** A melhor upgrade custo-benefício é:
- **RAM:** Adicionar mais RAM (de 8→16 GB custa ~R$150-300)
- **SSD:** Trocar HD por SSD (se ainda não tem)
- **GPU:** Uma RTX 3060 usada (~R$1.200) acelera os modelos 5-10x

---

### "Funciona sem placa de vídeo (GPU)?"

**Sim!** O DenAI funciona perfeitamente usando apenas o processador (CPU). A diferença é na **velocidade**:

| | Com GPU NVIDIA | Sem GPU (só CPU) |
|---|---|---|
| Velocidade de resposta | ⚡⚡⚡ Muito rápido | ⚡ Mais lento |
| Qualidade da resposta | Igual | Igual |
| Funciona? | Sim | Sim |

A GPU não muda a **qualidade** das respostas — só a **velocidade**. Se você não tem GPU, a IA funciona igualzinho, só demora um pouquinho mais.

---

### "Posso acessar de outro computador na rede?"

**Sim!** Veja as instruções na seção [Não consigo acessar de outro computador](#-não-consigo-acessar-de-outro-computador).

---

### "Funciona no Mac ou Linux?"

**Sim!** O DenAI funciona em qualquer sistema operacional que rode Python 3.10+ e Ollama:

```bash
# macOS / Linux
pip install denai
denai
```

Este guia foca no Windows, mas a experiência é a mesma em todos os sistemas.

---

### "A IA é tão boa quanto o ChatGPT?"

Resposta honesta — **depende do modelo e da sua RAM:**

| O que vc quer fazer | ChatGPT/Copilot | DenAI com 8B (16 GB RAM) | DenAI com 32B (32 GB RAM) |
|---|---|---|---|
| Conversar, tirar dúvidas | ⭐⭐⭐⭐⭐ Excelente | ⭐⭐⭐ Bom | ⭐⭐⭐⭐ Muito bom |
| Escrever textos/e-mails | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Gerar código | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Ler e editar seus arquivos | ⭐⭐⭐⭐⭐ (Copilot/Cursor) | ⭐⭐ Erra às vezes | ⭐⭐⭐⭐ Confiável |
| Executar planos complexos | ⭐⭐⭐⭐⭐ | ⭐⭐ Perde o fio | ⭐⭐⭐ Funciona |
| Privacidade | ❌ Dados na nuvem | ✅ 100% local | ✅ 100% local |
| Custo | R$100-1000/mês | **Grátis** | **Grátis** |
| Funciona sem internet | ❌ | ✅ | ✅ |

**Resumo prático:**
- Com **16 GB de RAM** (modelo 7-8B): é um ótimo assistente pra conversa e código. Pra uso do dia a dia, resolve 80% do que vc precisa.
- Com **32 GB de RAM** (modelo 32B): chega perto do ChatGPT em qualidade. Tool calling funciona bem, consegue planejar e executar tarefas em sequência.
- O gap principal era o **tamanho do contexto**, mas agora o DenAI escala automaticamente de 8k a 64k tokens e sumariza mensagens antigas quando necessário. Ainda fica abaixo dos 128k+ do cloud, mas a diferença é bem menor.

> 💡 **Dica:** Se vc já tem um PC com 16 GB, comece com o `qwen2.5-coder:7b`. Se quiser investir, 32 GB de RAM é a melhor upgrade — custa ~R$300-500 e desbloqueia modelos muito melhores.

---

### "Posso criar imagens com a IA?"

Os modelos de texto do DenAI **não geram imagens** — eles trabalham apenas com texto. Para gerar imagens localmente, você precisaria de software separado (como Stable Diffusion), que tem seus próprios requisitos.

---

### "Meus dados podem ser roubados?"

Seus dados ficam no **seu computador**. O DenAI não abre portas para a internet (a menos que você configure acesso pela rede local). Os riscos são os mesmos de qualquer arquivo no seu PC — se alguém tiver acesso físico ao seu computador, pode ver suas conversas. Mas nada é enviado para servidores externos. Nunca.

---

## 🔩 Instalação Manual (se o instalador falhar)

Se `pip install denai` deu erro e você não conseguiu resolver, siga estes passos manuais. É mais trabalhoso, mas funciona!

---

### Etapa 1: Instalar o Python

1. Abra o navegador
2. Acesse: **[python.org/downloads](https://www.python.org/downloads/)**
3. Clique no botão amarelo **"Download Python 3.x.x"** (a versão mais recente)
4. Execute o arquivo baixado (ex: `python-3.12.x-amd64.exe`)
5. **⚠️ IMPORTANTÍSSIMO:** Na primeira tela, **marque a caixa "Add python.exe to PATH"** (fica na parte de baixo!)
6. Clique em **"Install Now"**
7. Espere terminar e clique em "Close"

**Verificar se funcionou:**
1. Abra o Prompt de Comando (`Windows + R` → `cmd` → Enter)
2. Digite:
```
python --version
```
3. Deve aparecer algo como `Python 3.12.4`. Se aparecer, sucesso! ✅
4. Se aparecer "não reconhecido", desinstale o Python e instale novamente, desta vez marcando "Add to PATH".

---

### Etapa 2: Instalar o Ollama

1. Abra o navegador
2. Acesse: **[ollama.com/download](https://ollama.com/download)**
3. Clique em **"Download for Windows"**
4. Execute o instalador baixado (`OllamaSetup.exe`)
5. Siga os passos do instalador (Next → Next → Install → Finish)
6. O Ollama vai iniciar automaticamente (você pode ver o ícone na bandeja do sistema)

**Verificar se funcionou:**
1. Abra o Prompt de Comando
2. Digite:
```
ollama --version
```
3. Deve aparecer a versão. Se aparecer, sucesso! ✅

---

### Etapa 3: Baixar um modelo de IA

1. No Prompt de Comando, digite:
```
ollama pull llama3.1:8b
```
2. Espere o download terminar (vai baixar ~4.7 GB)
3. A barra de progresso mostra o andamento
4. Quando terminar, teste com:
```
ollama run llama3.1:8b "Olá, tudo bem?"
```
5. Se a IA responder, o modelo está funcionando! ✅

---

### Etapa 4: Instalar o DenAI a partir do código-fonte

1. Abra o Prompt de Comando
2. Clone o repositório:
```
git clone https://github.com/your-org/denai.git
cd denai
```

3. Crie o ambiente virtual do Python:
```
python -m venv .venv
```

4. Ative o ambiente virtual:
```
.venv\Scripts\activate
```

5. Instale o DenAI:
```
pip install .
```

6. Espere terminar (pode levar alguns minutos)

---

### Etapa 5: Iniciar o DenAI manualmente

1. Abra o Prompt de Comando
2. Se instalou do código-fonte, ative o ambiente virtual:
```
.venv\Scripts\activate
```

3. Inicie o servidor:
```
python -m denai
```

4. Espere aparecer "Rodando em http://localhost:4078"
5. Abra o navegador e acesse `localhost:4078`

> 💡 A interface web é servida automaticamente pelo DenAI — não precisa abrir nenhum arquivo separado.

---

## 🗑️ Desinstalação

Se quiser remover tudo do computador:

### Remover o DenAI

```
pip uninstall denai
```

E, opcionalmente, delete a pasta de dados:

1. Aperte **Windows + R**
2. Digite `%USERPROFILE%\.denai` e aperte Enter
3. Delete a pasta inteira (isso remove conversas e memórias)

### Remover os modelos de IA

1. Abra o Prompt de Comando
2. Veja os modelos instalados:
```
ollama list
```
3. Remova cada um:
```
ollama rm llama3.1:8b
ollama rm llama3.2:3b
```
(repita para cada modelo)

Ou delete a pasta de modelos diretamente:
1. Aperte **Windows + R**
2. Digite `%USERPROFILE%\.ollama` e aperte Enter
3. Delete a pasta `models` (isso apaga TODOS os modelos de uma vez)

### Remover o Ollama

1. Aperte **Windows + I** (Configurações)
2. Vá em **Aplicativos** → **Aplicativos instalados** (ou "Aplicativos e recursos")
3. Procure por **"Ollama"**
4. Clique nele → **"Desinstalar"**
5. Confirme

### Remover o Python (opcional)

> ⚠️ **Cuidado:** Se você usa Python pra outras coisas (programação, outros programas), **NÃO desinstale!**

1. Configurações → Aplicativos → Aplicativos instalados
2. Procure por **"Python"**
3. Clique → **"Desinstalar"**

### Verificar se tudo foi removido

Depois de desinstalar tudo, essas pastas podem ter sobrado (pode deletar):
- `C:\Users\SeuNome\.ollama` — Dados do Ollama
- `C:\Users\SeuNome\.denai` — Dados do DenAI (conversas, memórias)
- `C:\Users\SeuNome\AppData\Local\Programs\Python` — Python (se desinstalou)
- `C:\Users\SeuNome\AppData\Local\Ollama` — Cache do Ollama

> 💡 **Como acessar AppData:** Aperte **Windows + R**, digite `%LOCALAPPDATA%` e aperte Enter. Isso abre a pasta AppData\Local.

---

## 📚 Glossário

Termos técnicos explicados de forma simples:

---

### 🤖 IA (Inteligência Artificial)
Um programa de computador que consegue "pensar" — responder perguntas, escrever textos, resolver problemas. Não é um robô físico — é um software, como o Word ou o Chrome, mas que conversa com você.

### 🧠 Modelo (ou Modelo de IA)
O "cérebro" da IA. É um arquivo grande (vários GB) que contém tudo que a IA "aprendeu". Existem vários modelos diferentes, cada um com habilidades diferentes. Pense como cérebros de tamanhos diferentes: um cérebro maior é mais inteligente, mas precisa de mais energia.

### 📖 LLM (Large Language Model)
"Modelo de Linguagem Grande" — é o nome técnico para o tipo de IA que o DenAI usa. É uma IA especializada em **entender e gerar texto**. O ChatGPT, o Gemini e os modelos do DenAI são todos LLMs.

### 🦙 Ollama
O programa que roda os modelos de IA no seu computador. Pense no Ollama como o **motor** e no modelo como o **combustível**. O Ollama é gratuito e de código aberto. O nome é um trocadilho com "llama" (lhama), que é o nome de uma famosa família de modelos de IA.

### 🐍 Python
Uma **linguagem de programação** — é a "língua" em que o DenAI foi escrito. Você não precisa saber programar em Python! Só precisa ter ele instalado no computador pra que o DenAI funcione. Pense como o Java que muitos programas pedem: você instala e esquece.

### ⬛ Terminal (ou Prompt de Comando, ou CMD)
Aquela **janela preta** onde você digita comandos em texto. É a forma "raiz" de falar com o computador — sem clicar em botões, sem interface gráfica, só texto. Parece assustador, mas pra nossa instalação você só precisa digitar alguns comandos simples que eu vou te dar prontos.

### 🖥️ Servidor
Um programa que fica "rodando" e **esperando** que alguém se conecte a ele. O DenAI roda um servidor no seu computador — o navegador se conecta a esse servidor. Mas é tudo local! Não é um servidor na internet — é o seu próprio PC servindo o DenAI pra... seu próprio PC. É como um restaurante onde o cozinheiro e o cliente são a mesma pessoa.

### 🔌 API (Interface de Programação)
Uma "porta" por onde programas conversam entre si. O DenAI usa a API do Ollama pra pedir respostas da IA. Você não precisa se preocupar com isso — é tudo automático e acontece por baixo dos panos.

### 📡 Streaming
Quando a IA manda a resposta **aos poucos**, palavra por palavra, em vez de esperar terminar tudo pra mostrar de uma vez. É como assistir um vídeo ao vivo (streaming de vídeo) vs. baixar o vídeo inteiro antes de assistir.

### 🎮 GPU (Unidade de Processamento Gráfico)
A **placa de vídeo** do computador. Foi inventada pra processar gráficos de jogos, mas por coincidência ela também é ótima pra rodar IA (os cálculos são parecidos). Se você tem uma GPU NVIDIA, a IA roda **muito mais rápido**. Se não tem, funciona igual — só mais devagar. GPUs AMD e Intel ainda não são tão bem suportadas pelo Ollama.

### ⚙️ CPU (Unidade Central de Processamento)
O **processador** — o "cérebro" do computador. É ele que faz todos os cálculos. Se você não tem GPU, a CPU faz o trabalho da IA sozinha (só que mais devagar). Marcas comuns: Intel (Core i3, i5, i7, i9) e AMD (Ryzen 3, 5, 7, 9).

### 💾 RAM (Memória de Acesso Aleatório)
A **memória temporária** do computador — o "espaço de trabalho". Quando você abre um programa, ele vai pra RAM. Quando desliga o PC, a RAM é apagada. A IA precisa de bastante RAM pra funcionar, porque o modelo inteiro precisa ser carregado nela. É medida em **GB** (gigabytes): 8 GB, 16 GB, 32 GB.

### 🪙 Token
A menor unidade de texto que a IA processa. Uma palavra pode ser 1 ou mais tokens. Por exemplo, "computador" pode ser 2 tokens: "compu" + "tador". Quando falamos que um modelo aceita "8K tokens de contexto", significa que ele consegue "lembrar" de aproximadamente 6.000 palavras de conversa. O DenAI escala automaticamente a janela de contexto de 8k a 64k tokens conforme a conversa cresce, e sumariza mensagens antigas quando necessário.

### 📦 Quantização
Uma técnica pra **comprimir** modelos de IA, tornando-os menores e mais rápidos, com uma leve perda de qualidade. É como converter um CD (alta qualidade, grande) pra MP3 (qualidade menor, mas pequeno e prático). Modelos com `q4` ou `q5` no nome são quantizados.

### 🔀 PATH
Uma **lista de pastas** que o Windows procura quando você digita um comando no terminal. Se o Python não está no PATH, o Windows não sabe onde encontrá-lo. É por isso que, ao instalar o Python, precisamos marcar "Add to PATH" — pra dizer ao Windows: "ei, o Python está nesta pasta aqui!".

### 🏠 Localhost
Significa **"este computador aqui"**. Quando você acessa `localhost:4078` no navegador, está dizendo: "me mostre o que está rodando neste computador, na porta 4078". Nada passa pela internet. É como ligar de um telefone pra ele mesmo.

### 🚪 Porta (Port)
Um **número** que identifica qual programa recebe uma conexão. É como o número de um apartamento num prédio. O computador é o prédio, e cada programa usa um apartamento (porta) diferente. O DenAI usa a porta 4078. O Chrome usa a porta 443 pra sites HTTPS. Etc.

### 🔒 Offline
**Sem internet.** Quando dizemos que o DenAI funciona "offline", significa que ele funciona mesmo se você desconectar a internet. Tudo roda no seu computador, sem precisar falar com nenhum servidor externo.

### 📁 .venv (Ambiente Virtual)
Uma pasta que isola as dependências do Python. É como uma "bolha" onde o DenAI instala suas bibliotecas sem bagunçar o resto do seu sistema. Se algo der errado, basta deletar a pasta `.venv` e recriar. O resto do computador não é afetado.

### 🧩 Open Source (Código Aberto)
Software cujo **código-fonte é público** — qualquer pessoa pode ver como funciona, modificar e distribuir. O Ollama, os modelos de IA e o DenAI são todos open source. Isso significa que não tem "pegadinha" — você pode verificar que o programa realmente não envia seus dados pra lugar nenhum.

---

## 🎯 Resumo Rápido

| O que | Como |
|---|---|
| **Instalar** | `pip install denai` |
| **Iniciar** | `denai` no terminal |
| **Usar** | Abrir `localhost:4078` no navegador |
| **Parar** | Ctrl + C no terminal |
| **Trocar modelo** | Menu dropdown na interface |
| **Baixar modelo** | `ollama pull nome-do-modelo` no terminal |
| **Ver modelos** | `ollama list` no terminal |
| **Remover modelo** | `ollama rm nome-do-modelo` no terminal |
| **Atualizar** | `pip install --upgrade denai` |
| **Desinstalar** | `pip uninstall denai` + desinstalar Ollama |

---

## 💌 Palavras Finais

Parabéns por chegar até aqui! 🎉

Você agora tem uma **inteligência artificial pessoal, privada e gratuita** rodando no seu computador. Sem assinaturas, sem limites, sem ninguém espionando suas conversas.

Use e abuse:
- Pergunte qualquer coisa
- Peça ajuda com textos, e-mails, relatórios
- Estude com ela como um tutor particular
- Explore, experimente, divirta-se!

> 🐺 **O DenAI está aqui pra te ajudar. Sempre que precisar, é só chamar.**

---

> **Criado com 🐺 por DenAI**  
> Guia versão 1.0 — Julho 2025  
> Licença: MIT — Livre para uso, cópia e distribuição.
ll denai` + desinstalar Ollama |

---

## 💌 Palavras Finais

Parabéns por chegar até aqui! 🎉

Você agora tem uma **inteligência artificial pessoal, privada e gratuita** rodando no seu computador. Sem assinaturas, sem limites, sem ninguém espionando suas conversas.

Use e abuse:
- Pergunte qualquer coisa
- Peça ajuda com textos, e-mails, relatórios
- Estude com ela como um tutor particular
- Explore, experimente, divirta-se!

> 🐺 **O DenAI está aqui pra te ajudar. Sempre que precisar, é só chamar.**

---

> **Criado com 🐺 por DenAI**  
> Guia versão 1.0 — Julho 2025  
> Licença: MIT — Livre para uso, cópia e distribuição.
