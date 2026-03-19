@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ╔══════════════════════════════════════════════════════════════════╗
:: ║  DenAI - Script de Inicialização                                ║
:: ║  Duplo-clique neste arquivo para abrir o DenAI.                 ║
:: ║  Ou use o atalho "DenAI" na Área de Trabalho.                   ║
:: ╚══════════════════════════════════════════════════════════════════╝

:: Ir para o diretório onde este arquivo está
cd /d "%~dp0"

:: Variáveis
set "VENV_DIR=.venv"
set "PORT=4078"
set "URL=http://localhost:%PORT%"

:: -------------------------------------------------------------------
:: BANNER
:: -------------------------------------------------------------------
cls
echo.
echo  ╔═══════════════════════════════════════════════════╗
echo  ║                                                   ║
echo  ║          DenAI - Assistente de IA Local           ║
echo  ║                                                   ║
echo  ╚═══════════════════════════════════════════════════╝
echo.

:: -------------------------------------------------------------------
:: PASSO 1: Verificar se a instalação existe
:: -------------------------------------------------------------------
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo  [ERRO] Ambiente virtual nao encontrado!
    echo.
    echo  Parece que o DenAI ainda nao foi instalado.
    echo  Rode o arquivo "instalar.bat" ou "instalar.ps1" primeiro.
    echo.
    echo  Pressione qualquer tecla para sair...
    pause >nul
    exit /b 1
)

:: -------------------------------------------------------------------
:: PASSO 2: Iniciar o Ollama (se não estiver rodando)
:: -------------------------------------------------------------------
echo  [1/4] Verificando servico Ollama...

:: Checar se o Ollama já está rodando
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if %errorlevel% neq 0 (
    echo        Iniciando Ollama em segundo plano...
    where ollama >nul 2>&1
    if %errorlevel% equ 0 (
        start /B "" ollama serve >nul 2>&1
        echo        Aguardando Ollama iniciar...
        timeout /t 3 /nobreak >nul
        echo        [OK] Ollama iniciado!
    ) else (
        echo  [AVISO] Ollama nao encontrado no PATH.
        echo          Se voce acabou de instalar, reinicie o computador.
        echo          Tentando continuar sem ele...
    )
) else (
    echo        [OK] Ollama ja esta rodando!
)
echo.

:: -------------------------------------------------------------------
:: PASSO 3: Ativar ambiente virtual Python
:: -------------------------------------------------------------------
echo  [2/4] Ativando ambiente Python...
call "%VENV_DIR%\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo  [ERRO] Falha ao ativar o ambiente virtual.
    echo  Tente rodar o instalador novamente.
    echo.
    echo  Pressione qualquer tecla para sair...
    pause >nul
    exit /b 1
)
echo        [OK] Ambiente ativado!
echo.

:: -------------------------------------------------------------------
:: PASSO 4: Iniciar o servidor DenAI
:: -------------------------------------------------------------------
echo  [3/4] Iniciando servidor DenAI...
echo.

:: Iniciar o servidor em segundo plano via python -m denai
start /B "" python -m denai

:: Guardar o PID não é trivial em batch, mas vamos continuar
echo        Servidor iniciando na porta %PORT%...
echo.

:: -------------------------------------------------------------------
:: PASSO 5: Aguardar e abrir o navegador
:: -------------------------------------------------------------------
echo  [4/4] Abrindo navegador em 3 segundos...
echo.

:: Esperar o servidor subir
timeout /t 3 /nobreak >nul

:: Tentar verificar se o servidor está respondendo
powershell -NoProfile -Command ^
    "try { $r = Invoke-WebRequest -Uri '%URL%' -TimeoutSec 5 -UseBasicParsing; exit 0 } catch { exit 1 }" >nul 2>&1

if %errorlevel% equ 0 (
    echo        [OK] Servidor esta respondendo!
) else (
    echo        [AVISO] Servidor ainda pode estar carregando...
    echo        O navegador vai abrir mesmo assim.
    echo        Se a pagina nao carregar, espere uns segundos e aperte F5.
)

:: Abrir o navegador padrão
start "" "%URL%"

echo.
echo  ═══════════════════════════════════════════════════════════════
echo.
echo        DenAI esta rodando!
echo.
echo        Acesse: %URL%
echo.
echo        Para parar: feche esta janela ou pressione Ctrl+C
echo.
echo  ═══════════════════════════════════════════════════════════════
echo.

:: -------------------------------------------------------------------
:: Manter o terminal aberto mostrando logs do servidor
:: -------------------------------------------------------------------

:: Loop infinito para manter a janela aberta
:loop
timeout /t 30 /nobreak >nul

:: Verificar se o servidor ainda está rodando
tasklist /FI "IMAGENAME eq python.exe" 2>nul | find /I "python.exe" >nul
if %errorlevel% neq 0 (
    echo.
    echo  [!] O servidor parou de funcionar.
    echo.
    echo  Possíveis causas:
    echo    - Erro no codigo do servidor
    echo    - Porta %PORT% ja esta em uso
    echo    - Falta alguma dependencia
    echo.
    echo  Tente:
    echo    1. Fechar outros programas usando a porta %PORT%
    echo    2. Rodar o instalador novamente
    echo    3. Iniciar manualmente: python -m denai
    echo.
    echo  Pressione qualquer tecla para sair...
    pause >nul
    exit /b 1
)

goto loop
