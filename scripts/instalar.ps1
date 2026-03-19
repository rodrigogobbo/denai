# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DenAI - Instalador PowerShell para Windows                        ║
# ║  Versão robusta com verificações detalhadas e tratamento de erros  ║
# ║  Execute: clique direito → "Executar com PowerShell"              ║
# ╚══════════════════════════════════════════════════════════════════════╝

#Requires -Version 5.1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

# ── Configurações ──────────────────────────────────────────────────────
$Config = @{
    Model             = "llama3.2:3b"
    ServerPort        = 4078
    MinRAMGB          = 8
    MinDiskGB         = 10
    PythonVersion     = "3.12"
    PythonMinor       = 11    # mínimo 3.11
    VenvDir           = ".venv"
    FirewallRuleName  = "DenAI Server (porta 4078)"
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Erros = 0
$Avisos = 0

# ── Funções Auxiliares ─────────────────────────────────────────────────

function Show-Banner {
    Clear-Host
    Write-Host ""
    Write-Host "  ╔═════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "  ║                                                             ║" -ForegroundColor Cyan
    Write-Host "  ║   ████████   ███████  ██    ██    █████   ██                ║" -ForegroundColor Cyan
    Write-Host "  ║   ██    ██   ██       ███   ██   ██   ██  ██                ║" -ForegroundColor Cyan
    Write-Host "  ║   ██    ██   █████    ██ ██ ██   ███████  ██                ║" -ForegroundColor Cyan
    Write-Host "  ║   ██    ██   ██       ██  ████   ██   ██  ██                ║" -ForegroundColor Cyan
    Write-Host "  ║   ████████   ███████  ██    ██   ██   ██  ██                ║" -ForegroundColor Cyan
    Write-Host "  ║                                                             ║" -ForegroundColor Cyan
    Write-Host "  ║          Instalador DenAI para Windows                      ║" -ForegroundColor Cyan
    Write-Host "  ║          Versao 1.0 - PowerShell Edition                    ║" -ForegroundColor Cyan
    Write-Host "  ║                                                             ║" -ForegroundColor Cyan
    Write-Host "  ╚═════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Step, [string]$Message)
    Write-Host "  [$Step] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Ok {
    param([string]$Message)
    Write-Host "         [OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Erro {
    param([string]$Message)
    Write-Host "         [ERRO] " -ForegroundColor Red -NoNewline
    Write-Host $Message
    $script:Erros++
}

function Write-Aviso {
    param([string]$Message)
    Write-Host "         [AVISO] " -ForegroundColor DarkYellow -NoNewline
    Write-Host $Message
    $script:Avisos++
}

function Write-Info {
    param([string]$Message)
    Write-Host "         " -NoNewline
    Write-Host $Message -ForegroundColor Gray
}

function Write-Separator {
    Write-Host ""
    Write-Host "  ─────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host ""
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-CommandExists {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

function Install-WithWinget {
    param(
        [string]$PackageId,
        [string]$DisplayName,
        [string]$FallbackUrl = ""
    )

    # Tentar winget primeiro
    if (Test-CommandExists "winget") {
        Write-Info "Instalando via winget..."
        $process = Start-Process -FilePath "winget" -ArgumentList @(
            "install", $PackageId,
            "--accept-source-agreements",
            "--accept-package-agreements",
            "--silent"
        ) -Wait -PassThru -NoNewWindow

        if ($process.ExitCode -eq 0) {
            Write-Ok "$DisplayName instalado via winget!"
            return $true
        }
        Write-Aviso "Winget falhou (codigo $($process.ExitCode)). Tentando fallback..."
    }

    # Fallback: download direto
    if ($FallbackUrl -ne "") {
        Write-Info "Baixando direto de $FallbackUrl ..."
        $tempFile = Join-Path $env:TEMP "denai_installer_$(Get-Random).exe"
        try {
            $ProgressPreference = 'SilentlyContinue'
            Invoke-WebRequest -Uri $FallbackUrl -OutFile $tempFile -UseBasicParsing
            Write-Info "Executando instalador..."
            $process = Start-Process -FilePath $tempFile -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1" -Wait -PassThru
            if ($process.ExitCode -eq 0) {
                Write-Ok "$DisplayName instalado via download direto!"
                Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
                return $true
            }
        }
        catch {
            Write-Erro "Falha no download: $_"
        }
        finally {
            Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Erro "Nao foi possivel instalar $DisplayName automaticamente."
    return $false
}

function New-DesktopShortcut {
    param(
        [string]$Name,
        [string]$TargetPath,
        [string]$WorkingDir,
        [string]$Description,
        [string]$IconLocation = ""
    )

    try {
        $desktop = [Environment]::GetFolderPath("Desktop")
        $shortcutPath = Join-Path $desktop "$Name.lnk"

        $shell = New-Object -ComObject WScript.Shell
        $shortcut = $shell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $TargetPath
        $shortcut.WorkingDirectory = $WorkingDir
        $shortcut.Description = $Description
        if ($IconLocation -ne "") {
            $shortcut.IconLocation = $IconLocation
        }
        $shortcut.Save()

        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($shell) | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# ══════════════════════════════════════════════════════════════════════
# INÍCIO DA INSTALAÇÃO
# ══════════════════════════════════════════════════════════════════════

Show-Banner

Write-Host "  Bem-vindo! Este script vai instalar e configurar o DenAI." -ForegroundColor White
Write-Host "  Relaxa e acompanha as mensagens abaixo." -ForegroundColor Gray
Write-Separator

# ── PASSO 0: Verificar privilégios de Administrador ──────────────────
Write-Step "0/10" "Verificando privilegios de administrador..."

if (-not (Test-IsAdmin)) {
    Write-Aviso "Este script precisa de permissao de Administrador."
    Write-Info "Relancando com privilegios elevados..."
    Write-Host ""

    try {
        Start-Process PowerShell -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", "`"$($MyInvocation.MyCommand.Path)`""
        ) -Verb RunAs
    }
    catch {
        Write-Erro "Voce precisa permitir a execucao como administrador."
        Write-Host "  Pressione qualquer tecla para sair..." -ForegroundColor Gray
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }
    exit
}
Write-Ok "Rodando como Administrador!"
Write-Separator

# ── PASSO 1: Verificar versão do Windows ─────────────────────────────
Write-Step "1/10" "Verificando versao do Windows..."

$osVersion = [Environment]::OSVersion.Version
$winBuild = $osVersion.Build
$winCaption = (Get-CimInstance Win32_OperatingSystem).Caption

if ($osVersion.Major -lt 10) {
    Write-Erro "Windows 10 ou superior e necessario. Voce tem: $winCaption"
    Write-Host "  Pressione qualquer tecla para sair..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Ok "$winCaption (Build $winBuild)"
Write-Separator

# ── PASSO 2: Verificar hardware (RAM e disco) ───────────────────────
Write-Step "2/10" "Verificando hardware..."

# RAM
$totalRAM = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
if ($totalRAM -lt $Config.MinRAMGB) {
    Write-Aviso "Voce tem ${totalRAM}GB de RAM. Recomendamos ${minRAMGB}GB+."
    Write-Info "O DenAI pode ficar lento, mas vai funcionar."
} else {
    Write-Ok "RAM: ${totalRAM}GB (suficiente!)"
}

# Disco
$drive = (Get-PSDrive -Name ($ScriptDir.Substring(0,1)))
$freeGB = [math]::Round($drive.Free / 1GB, 1)
if ($freeGB -lt $Config.MinDiskGB) {
    Write-Aviso "Espaco livre em disco: ${freeGB}GB. Recomendamos ${minDiskGB}GB+."
    Write-Info "O modelo de IA precisa de ~2GB e as dependencias ~1GB."
} else {
    Write-Ok "Disco livre: ${freeGB}GB (suficiente!)"
}

# CPU
$cpuName = (Get-CimInstance Win32_Processor).Name
Write-Ok "CPU: $cpuName"

Write-Separator

# ── PASSO 3: Verificar/Instalar winget ───────────────────────────────
Write-Step "3/10" "Verificando winget (gerenciador de pacotes)..."

if (-not (Test-CommandExists "winget")) {
    Write-Aviso "winget nao encontrado. Tentando instalar..."

    # Tentar instalar via Microsoft Store (App Installer)
    try {
        Write-Info "Baixando App Installer da Microsoft..."
        $msixUrl = "https://aka.ms/getwinget"
        $msixFile = Join-Path $env:TEMP "Microsoft.DesktopAppInstaller.msixbundle"

        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $msixUrl -OutFile $msixFile -UseBasicParsing

        Add-AppxPackage -Path $msixFile -ErrorAction Stop
        Remove-Item $msixFile -Force -ErrorAction SilentlyContinue

        # Recarregar PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

        if (Test-CommandExists "winget") {
            Write-Ok "winget instalado com sucesso!"
        } else {
            Write-Erro "winget instalado mas nao encontrado no PATH."
            Write-Info "Vou tentar instalar tudo via download direto."
        }
    }
    catch {
        Write-Erro "Nao foi possivel instalar o winget: $_"
        Write-Info "Vou tentar instalar tudo via download direto."
    }
} else {
    $wingetVersion = (winget --version 2>$null)
    Write-Ok "winget $wingetVersion encontrado!"
}

Write-Separator

# ── PASSO 4: Verificar/Instalar Python 3.11+ ────────────────────────
Write-Step "4/10" "Verificando Python..."

$pythonOk = $false
$pythonCmd = "python"

# Tentar python e python3
foreach ($cmd in @("python", "python3", "py")) {
    if (Test-CommandExists $cmd) {
        try {
            $versionOutput = & $cmd --version 2>&1
            if ($versionOutput -match "Python (\d+)\.(\d+)\.(\d+)") {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -ge 3 -and $minor -ge $Config.PythonMinor) {
                    $pythonOk = $true
                    $pythonCmd = $cmd
                    Write-Ok "Python $($Matches[0]) encontrado (comando: $cmd)"
                    break
                }
            }
        }
        catch { }
    }
}

if (-not $pythonOk) {
    Write-Info "Python 3.11+ nao encontrado. Instalando Python $($Config.PythonVersion)..."

    $fallbackUrl = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $installed = Install-WithWinget -PackageId "Python.Python.$($Config.PythonVersion)" `
                                     -DisplayName "Python $($Config.PythonVersion)" `
                                     -FallbackUrl $fallbackUrl

    if ($installed) {
        # Atualizar PATH para esta sessão
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                     [System.Environment]::GetEnvironmentVariable("Path", "User")

        # Adicionar caminhos comuns do Python
        $pythonPaths = @(
            "$env:LocalAppData\Programs\Python\Python312",
            "$env:LocalAppData\Programs\Python\Python312\Scripts",
            "$env:ProgramFiles\Python312",
            "$env:ProgramFiles\Python312\Scripts"
        )
        foreach ($p in $pythonPaths) {
            if (Test-Path $p) {
                $env:Path = "$p;$env:Path"
            }
        }

        Write-Aviso "Se o Python nao for reconhecido, reinicie o computador e rode novamente."
    }
}

Write-Separator

# ── PASSO 5: Verificar/Instalar Ollama ───────────────────────────────
Write-Step "5/10" "Verificando Ollama..."

if (-not (Test-CommandExists "ollama")) {
    Write-Info "Ollama nao encontrado. Instalando..."

    $fallbackUrl = "https://ollama.com/download/OllamaSetup.exe"
    $installed = Install-WithWinget -PackageId "Ollama.Ollama" `
                                     -DisplayName "Ollama" `
                                     -FallbackUrl $fallbackUrl

    if ($installed) {
        # Atualizar PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                     [System.Environment]::GetEnvironmentVariable("Path", "User")

        $ollamaPaths = @(
            "$env:LocalAppData\Programs\Ollama",
            "$env:ProgramFiles\Ollama"
        )
        foreach ($p in $ollamaPaths) {
            if (Test-Path $p) {
                $env:Path = "$p;$env:Path"
            }
        }
    }
} else {
    try {
        $ollamaVersion = (ollama --version 2>&1) | Select-Object -First 1
        Write-Ok "Ollama encontrado: $ollamaVersion"
    }
    catch {
        Write-Ok "Ollama encontrado!"
    }
}

Write-Separator

# ── PASSO 6: Criar ambiente virtual e instalar dependências ─────────
Write-Step "6/10" "Configurando ambiente Python..."

$venvPath = Join-Path $ScriptDir $Config.VenvDir

# Criar venv
if (-not (Test-Path (Join-Path $venvPath "Scripts"))) {
    Write-Info "Criando ambiente virtual em $($Config.VenvDir)\..."
    try {
        & $pythonCmd -m venv $venvPath
        Write-Ok "Ambiente virtual criado!"
    }
    catch {
        Write-Erro "Falha ao criar ambiente virtual: $_"
    }
} else {
    Write-Ok "Ambiente virtual ja existe!"
}

# Instalar pacote DenAI
$pipPath = Join-Path $venvPath "Scripts\pip.exe"
if (Test-Path $pipPath) {
    Write-Info "Instalando DenAI e dependencias (isso pode demorar)..."
    try {
        # Atualizar pip primeiro
        & $pipPath install --upgrade pip 2>&1 | Out-Null

        # Instalar pacote denai
        $pipOutput = & $pipPath install denai 2>&1
        $pipExit = $LASTEXITCODE

        if ($pipExit -eq 0 -or $null -eq $pipExit) {
            Write-Ok "DenAI instalado com sucesso!"
        } else {
            Write-Erro "Falha ao instalar DenAI (codigo $pipExit)"
            Write-Info "Saida do pip:"
            $pipOutput | Select-Object -Last 5 | ForEach-Object { Write-Info "  $_" }
        }
    }
    catch {
        Write-Erro "Erro ao instalar DenAI: $_"
    }
} else {
    Write-Erro "pip nao encontrado em $pipPath"
}

Write-Separator

# ── PASSO 7: Iniciar Ollama e baixar modelo ──────────────────────────
Write-Step "7/10" "Preparando modelo de IA..."

# Iniciar Ollama se não estiver rodando
$ollamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $ollamaRunning) {
    if (Test-CommandExists "ollama") {
        Write-Info "Iniciando servico Ollama..."
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Write-Info "Aguardando 5 segundos para o Ollama iniciar..."
        Start-Sleep -Seconds 5
    } else {
        Write-Erro "Ollama nao encontrado no PATH. Reinicie e tente novamente."
    }
}

# Baixar modelo
if (Test-CommandExists "ollama") {
    Write-Info "Baixando modelo $($Config.Model)..."
    Write-Info "Isso pode demorar 10-30 minutos dependendo da sua internet."
    Write-Info "O modelo tem aproximadamente 2GB."
    Write-Host ""

    $pullProcess = Start-Process -FilePath "ollama" -ArgumentList "pull", $Config.Model `
                                  -NoNewWindow -Wait -PassThru

    if ($pullProcess.ExitCode -eq 0) {
        Write-Ok "Modelo $($Config.Model) baixado com sucesso!"
    } else {
        Write-Erro "Falha ao baixar o modelo. Verifique sua internet."
        Write-Info "Voce pode tentar manualmente depois: ollama pull $($Config.Model)"
    }
} else {
    Write-Erro "Ollama nao disponivel. Modelo nao foi baixado."
}

Write-Separator

# ── PASSO 8: Regra de Firewall ───────────────────────────────────────
Write-Step "8/10" "Configurando firewall..."

try {
    $existingRule = Get-NetFirewallRule -DisplayName $Config.FirewallRuleName -ErrorAction SilentlyContinue

    if ($existingRule) {
        Write-Ok "Regra de firewall ja existe!"
    } else {
        New-NetFirewallRule -DisplayName $Config.FirewallRuleName `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort $Config.ServerPort `
            -Action Allow `
            -RemoteAddress "127.0.0.1" `
            -Profile Private `
            -Description "Permite acesso local ao servidor DenAI na porta $($Config.ServerPort)" `
            -ErrorAction Stop | Out-Null

        Write-Ok "Regra de firewall criada (porta $($Config.ServerPort), apenas localhost)!"
    }
}
catch {
    Write-Aviso "Nao foi possivel criar regra de firewall: $_"
    Write-Info "O DenAI pode funcionar mesmo sem ela."
}

Write-Separator

# ── PASSO 9: Tarefa agendada (Ollama no login) ──────────────────────
Write-Step "9/10" "Inicializacao automatica do Ollama..."

Write-Host ""
Write-Host "         Deseja iniciar o Ollama automaticamente quando" -ForegroundColor White
Write-Host "         voce ligar o computador? (Recomendado)" -ForegroundColor White
Write-Host ""
Write-Host "         [S] Sim  [N] Nao" -ForegroundColor Yellow
Write-Host ""

$resposta = Read-Host "         Sua escolha (S/N)"

if ($resposta -match "^[Ss]") {
    try {
        $taskName = "DenAI - Ollama AutoStart"
        $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

        if ($existingTask) {
            Write-Ok "Tarefa agendada ja existe!"
        } else {
            $ollamaPath = (Get-Command ollama -ErrorAction SilentlyContinue).Path
            if ($ollamaPath) {
                $action = New-ScheduledTaskAction -Execute $ollamaPath -Argument "serve"
                $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
                $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
                    -DontStopIfGoingOnBatteries `
                    -StartWhenAvailable `
                    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

                Register-ScheduledTask -TaskName $taskName `
                    -Action $action `
                    -Trigger $trigger `
                    -Settings $settings `
                    -Description "Inicia o Ollama automaticamente no login para o DenAI" `
                    -ErrorAction Stop | Out-Null

                Write-Ok "Ollama vai iniciar automaticamente no proximo login!"
            } else {
                Write-Aviso "Caminho do Ollama nao encontrado. Configure manualmente depois."
            }
        }
    }
    catch {
        Write-Aviso "Nao foi possivel criar tarefa agendada: $_"
        Write-Info "Voce pode iniciar o Ollama manualmente quando precisar."
    }
} else {
    Write-Info "Ok! Voce pode mudar isso depois se quiser."
}

Write-Separator

# ── PASSO 10: Criar atalho na Área de Trabalho ──────────────────────
Write-Step "10/10" "Criando atalho na Area de Trabalho..."

$iniciarBat = Join-Path $ScriptDir "iniciar.bat"
if (Test-Path $iniciarBat) {
    $created = New-DesktopShortcut -Name "DenAI" `
                                    -TargetPath $iniciarBat `
                                    -WorkingDir $ScriptDir `
                                    -Description "Iniciar DenAI - Seu assistente de IA local"

    if ($created) {
        Write-Ok "Atalho 'DenAI' criado na Area de Trabalho!"
    } else {
        Write-Aviso "Nao foi possivel criar o atalho."
        Write-Info "Voce pode abrir o DenAI rodando iniciar.bat diretamente."
    }
} else {
    Write-Aviso "Arquivo iniciar.bat nao encontrado."
    Write-Info "Certifique-se de que iniciar.bat esta na mesma pasta."
}

Write-Separator

# ══════════════════════════════════════════════════════════════════════
# RESULTADO FINAL
# ══════════════════════════════════════════════════════════════════════

Write-Host ""

if ($Erros -eq 0) {
    Write-Host "  ╔═════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║                                                             ║" -ForegroundColor Green
    Write-Host "  ║      INSTALACAO CONCLUIDA COM SUCESSO!                      ║" -ForegroundColor Green
    Write-Host "  ║                                                             ║" -ForegroundColor Green
    Write-Host "  ╚═════════════════════════════════════════════════════════════╝" -ForegroundColor Green
} else {
    Write-Host "  ╔═════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "  ║                                                             ║" -ForegroundColor Yellow
    Write-Host "  ║      INSTALACAO CONCLUIDA COM $Erros ERRO(S) e $Avisos AVISO(S)          ║" -ForegroundColor Yellow
    Write-Host "  ║                                                             ║" -ForegroundColor Yellow
    Write-Host "  ╚═════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  ┌─────────────────────────────────────────────────────────────┐" -ForegroundColor White
Write-Host "  │  Como usar o DenAI:                                         │" -ForegroundColor White
Write-Host "  │                                                             │" -ForegroundColor White
Write-Host "  │  1. Clique duas vezes no atalho 'DenAI' na Area de          │" -ForegroundColor White
Write-Host "  │     Trabalho, OU rode o arquivo iniciar.bat                 │" -ForegroundColor White
Write-Host "  │                                                             │" -ForegroundColor White
Write-Host "  │  2. Aguarde o navegador abrir automaticamente               │" -ForegroundColor White
Write-Host "  │                                                             │" -ForegroundColor White
Write-Host "  │  3. Comece a conversar com a IA!                            │" -ForegroundColor White
Write-Host "  │                                                             │" -ForegroundColor White
Write-Host "  └─────────────────────────────────────────────────────────────┘" -ForegroundColor White
Write-Host ""

Write-Host "  Resumo da instalacao:" -ForegroundColor Cyan
Write-Host "    • Modelo: $($Config.Model) (leve, funciona com 8GB de RAM)" -ForegroundColor Gray
Write-Host "    • RAM detectada: ${totalRAM}GB" -ForegroundColor Gray
Write-Host "    • Disco livre: ${freeGB}GB" -ForegroundColor Gray
Write-Host "    • Porta do servidor: $($Config.ServerPort)" -ForegroundColor Gray
Write-Host ""

if ($Erros -gt 0) {
    Write-Host "  Para resolver os erros:" -ForegroundColor Yellow
    Write-Host "    1. Reinicie o computador" -ForegroundColor Gray
    Write-Host "    2. Rode este instalador novamente" -ForegroundColor Gray
    Write-Host "    3. Se persistir, instale manualmente:" -ForegroundColor Gray
    Write-Host "       Python:  https://www.python.org/downloads/" -ForegroundColor Gray
    Write-Host "       Ollama:  https://ollama.com/download" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "  Dica: Para um modelo mais inteligente (precisa 16GB+ RAM):" -ForegroundColor DarkCyan
Write-Host "        ollama pull llama3.1:8b" -ForegroundColor Gray
Write-Host ""
Write-Host "  ═════════════════════════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Pressione qualquer tecla para fechar..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
