@echo off
chcp 65001 >nul 2>&1
title DenAI - Modo Compartilhado

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  🐺 DenAI — Modo Compartilhado                  ║
echo  ║                                                  ║
echo  ║  Inicia o DenAI aberto pra rede local.           ║
echo  ║  Qualquer pessoa na sua rede WiFi poderá         ║
echo  ║  acessar usando a chave de acesso.               ║
echo  ╚══════════════════════════════════════════════════╝
echo.

REM ── Verificar se a instalação existe ──
if not exist ".venv\Scripts\python.exe" (
    echo  [ERRO] Instalacao nao encontrada!
    echo  Execute primeiro o instalar.bat
    echo.
    pause
    exit /b 1
)

REM ── Iniciar Ollama se não está rodando ──
tasklist /FI "IMAGENAME eq ollama.exe" 2>nul | find /I "ollama.exe" >nul
if errorlevel 1 (
    echo  [*] Iniciando Ollama em background...
    start /B ollama serve >nul 2>&1
    timeout /t 3 /nobreak >nul
)

REM ── Ativar venv ──
call .venv\Scripts\activate.bat

REM ── Mostrar a chave de acesso ──
echo.
echo  ══════════════════════════════════════════════════
echo.
if exist "%USERPROFILE%\.denai\api.key" (
    echo  🔑 CHAVE DE ACESSO ^(passe pra quem for usar^):
    echo.
    echo     %USERPROFILE%\.denai\api.key
    echo.
    type "%USERPROFILE%\.denai\api.key"
    echo.
    echo.
) else (
    echo  [!] Chave será gerada na primeira execução.
    echo.
)
echo  ══════════════════════════════════════════════════
echo.
echo  Abrindo para a rede local...
echo  A URL e a chave vão aparecer no terminal abaixo.
echo  Passe a URL + chave pra sua esposa/familia.
echo.
echo  Ctrl+C para parar o servidor.
echo.

REM ── Iniciar servidor em modo compartilhado ──
python -m denai --compartilhar

echo.
echo  Servidor encerrado.
pause
