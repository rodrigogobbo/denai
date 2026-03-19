@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ╔══════════════════════════════════════════════════════════════════╗
:: ║  DenAI - Instalador para Windows (.bat)                        ║
:: ║  Para iniciantes: basta dar duplo-clique neste arquivo.        ║
:: ║  Ele instala tudo que você precisa automaticamente.            ║
:: ╚══════════════════════════════════════════════════════════════════╝

:: -------------------------------------------------------------------
:: PASSO 0: Verificar se estamos rodando como Administrador.
::          Se não, relançar com privilégios elevados.
:: -------------------------------------------------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] Este instalador precisa de permissao de Administrador.
    echo [!] Vou pedir a permissao agora... Clique "Sim" na janela que aparecer.
    echo.
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

:: -------------------------------------------------------------------
:: Variáveis de configuração
:: -------------------------------------------------------------------
set "INSTALL_DIR=%~dp0"
set "VENV_DIR=%INSTALL_DIR%.venv"
set "MODEL=llama3.2:3b"
set "ERROS=0"

:: Ir para o diretório do instalador
cd /d "%INSTALL_DIR%"

:: -------------------------------------------------------------------
:: BANNER
:: -------------------------------------------------------------------
cls
echo.
echo  ╔═══════════════════════════════════════════════════════════╗
echo  ║                                                           ║
echo  ║   ████████   ███████  ██    ██    █████   ██              ║
echo  ║   ██    ██   ██       ███   ██   ██   ██  ██              ║
echo  ║   ██    ██   █████    ██ ██ ██   ███████  ██              ║
echo  ║   ██    ██   ██       ██  ████   ██   ██  ██              ║
echo  ║   ████████   ███████  ██    ██   ██   ██  ██              ║
echo  ║                                                           ║
echo  ║        Instalador DenAI para Windows                      ║
echo  ║        Versao 1.0 - Para uso domestico                    ║
echo  ║                                                           ║
echo  ╚═══════════════════════════════════════════════════════════╝
echo.
echo  Bem-vindo! Este instalador vai configurar tudo pra voce.
echo  Relaxa e acompanha as mensagens abaixo.
echo.
echo  ─────────────────────────────────────────────────────────────
echo.

:: -------------------------------------------------------------------
:: PASSO 1: Verificar se o winget está disponível
:: -------------------------------------------------------------------
echo [1/8] Verificando se o winget esta disponivel...
where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERRO] O winget nao foi encontrado no seu sistema.
    echo  O winget vem com o Windows 10 ^(versao 1809+^) e Windows 11.
    echo.
    echo  Para instalar manualmente:
    echo  1. Abra a Microsoft Store
    echo  2. Procure por "Instalador de Aplicativo" ^(App Installer^)
    echo  3. Instale/atualize
    echo  4. Rode este instalador novamente
    echo.
    echo  Pressione qualquer tecla para sair...
    pause >nul
    exit /b 1
)
echo        [OK] winget encontrado!
echo.

:: -------------------------------------------------------------------
:: PASSO 2: Verificar/Instalar Python 3.11+
:: -------------------------------------------------------------------
echo [2/8] Verificando Python...

:: Tentar encontrar Python e verificar versão
set "PYTHON_OK=0"
where python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do (
        for /f "tokens=1,2 delims=." %%a in ("%%v") do (
            if %%a geq 3 (
                if %%b geq 11 (
                    set "PYTHON_OK=1"
                    echo        [OK] Python %%v encontrado!
                )
            )
        )
    )
)

if "!PYTHON_OK!"=="0" (
    echo        Python 3.11+ nao encontrado. Instalando Python 3.12...
    echo        Isso pode demorar alguns minutos...
    echo.
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
    if !errorlevel! neq 0 (
        echo.
        echo  [ERRO] Falha ao instalar o Python.
        echo  Tente instalar manualmente: https://www.python.org/downloads/
        set /a ERROS+=1
    ) else (
        echo        [OK] Python 3.12 instalado com sucesso!
        echo.
        echo  [AVISO] Pode ser necessario REINICIAR o terminal para o
        echo          Python ser reconhecido. Se der erro nos proximos
        echo          passos, feche tudo e rode este instalador de novo.

        :: Atualizar PATH para esta sessão
        set "PATH=%LocalAppData%\Programs\Python\Python312;%LocalAppData%\Programs\Python\Python312\Scripts;%PATH%"
    )
)
echo.

:: -------------------------------------------------------------------
:: PASSO 3: Verificar/Instalar Ollama
:: -------------------------------------------------------------------
echo [3/8] Verificando Ollama...
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo        Ollama nao encontrado. Instalando...
    echo        Isso pode demorar alguns minutos...
    echo.
    winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements --silent
    if !errorlevel! neq 0 (
        echo.
        echo  [ERRO] Falha ao instalar o Ollama.
        echo  Tente instalar manualmente: https://ollama.com/download
        set /a ERROS+=1
    ) else (
        echo        [OK] Ollama instalado com sucesso!

        :: Atualizar PATH para esta sessão
        set "PATH=%LocalAppData%\Programs\Ollama;%PATH%"
    )
) else (
    echo        [OK] Ollama ja esta instalado!
)
echo.

:: -------------------------------------------------------------------
:: PASSO 4: Criar ambiente virtual Python (venv)
:: -------------------------------------------------------------------
echo [4/8] Criando ambiente virtual Python...
if exist "%VENV_DIR%" (
    echo        Ambiente virtual ja existe. Pulando criacao.
) else (
    python -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo  [ERRO] Falha ao criar ambiente virtual.
        echo  Verifique se o Python foi instalado corretamente.
        set /a ERROS+=1
    ) else (
        echo        [OK] Ambiente virtual criado em .venv\
    )
)
echo.

:: -------------------------------------------------------------------
:: PASSO 5: Instalar dependências Python (pacote denai)
:: -------------------------------------------------------------------
echo [5/8] Instalando DenAI e dependencias Python...
call "%VENV_DIR%\Scripts\activate.bat"
pip install --upgrade pip >nul 2>&1
pip install denai
if !errorlevel! neq 0 (
    echo  [ERRO] Falha ao instalar o pacote DenAI.
    echo  Verifique sua conexao com a internet.
    set /a ERROS+=1
) else (
    echo        [OK] DenAI instalado com sucesso!
)
call deactivate 2>nul
echo.

:: -------------------------------------------------------------------
:: PASSO 6: Iniciar o Ollama e baixar o modelo
:: -------------------------------------------------------------------
echo [6/8] Iniciando o servico Ollama...

:: Verificar se o Ollama já está rodando
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %errorlevel% neq 0 (
    start /B "" ollama serve >nul 2>&1
    echo        Aguardando o Ollama iniciar...
    timeout /t 5 /nobreak >nul
)
echo        [OK] Ollama esta rodando!
echo.

echo [7/8] Baixando modelo de IA: %MODEL%
echo        Este e o passo mais demorado ^(pode levar 10-30 minutos^).
echo        O modelo tem aproximadamente 2GB de tamanho.
echo        NAO feche esta janela!
echo.
ollama pull %MODEL%
if %errorlevel% neq 0 (
    echo.
    echo  [ERRO] Falha ao baixar o modelo.
    echo  Verifique sua conexao com a internet e tente novamente.
    set /a ERROS+=1
) else (
    echo.
    echo        [OK] Modelo %MODEL% baixado com sucesso!
)
echo.

:: -------------------------------------------------------------------
:: PASSO 7: Criar atalho na Área de Trabalho
:: -------------------------------------------------------------------
echo [8/8] Criando atalho na Area de Trabalho...

set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\DenAI.lnk"
set "TARGET=%INSTALL_DIR%iniciar.bat"

:: Usar PowerShell para criar o atalho .lnk
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $sc = $ws.CreateShortcut('%SHORTCUT%'); ^
     $sc.TargetPath = '%TARGET%'; ^
     $sc.WorkingDirectory = '%INSTALL_DIR%'; ^
     $sc.Description = 'Iniciar DenAI - Seu assistente de IA local'; ^
     $sc.Save()"

if %errorlevel% equ 0 (
    echo        [OK] Atalho criado na Area de Trabalho!
) else (
    echo  [AVISO] Nao consegui criar o atalho automaticamente.
    echo          Voce pode abrir o DenAI rodando iniciar.bat
)
echo.

:: -------------------------------------------------------------------
:: RESULTADO FINAL
:: -------------------------------------------------------------------
echo.
echo  ═══════════════════════════════════════════════════════════════
echo.

if %ERROS% equ 0 (
    echo  ╔═══════════════════════════════════════════════════════════╗
    echo  ║                                                           ║
    echo  ║     INSTALACAO CONCLUIDA COM SUCESSO!                     ║
    echo  ║                                                           ║
    echo  ╚═══════════════════════════════════════════════════════════╝
    echo.
    echo  Como usar o DenAI:
    echo.
    echo    1. Clique duas vezes no atalho "DenAI" na Area de
    echo       Trabalho, OU rode o arquivo iniciar.bat
    echo.
    echo    2. Aguarde o navegador abrir automaticamente
    echo.
    echo    3. Comece a conversar com a IA!
    echo.
    echo  Modelo instalado: %MODEL% ^(leve, funciona com 8GB de RAM^)
    echo.
    echo  Dica: Para usar um modelo mais inteligente ^(precisa de
    echo        mais RAM^), rode: ollama pull llama3.1:8b
    echo.
) else (
    echo  ╔═══════════════════════════════════════════════════════════╗
    echo  ║                                                           ║
    echo  ║   INSTALACAO CONCLUIDA COM %ERROS% ERRO^(S^)                    ║
    echo  ║                                                           ║
    echo  ╚═══════════════════════════════════════════════════════════╝
    echo.
    echo  Alguns componentes nao foram instalados corretamente.
    echo  Revise as mensagens de erro acima e tente:
    echo.
    echo    1. Reiniciar o computador
    echo    2. Rodar este instalador novamente
    echo    3. Instalar manualmente o que faltou
    echo.
    echo  Links uteis:
    echo    Python:  https://www.python.org/downloads/
    echo    Ollama:  https://ollama.com/download
    echo.
)

echo  ═══════════════════════════════════════════════════════════════
echo.
echo  Pressione qualquer tecla para fechar...
pause >nul
exit /b %ERROS%
