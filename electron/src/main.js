'use strict';

const {
  app, BrowserWindow, Tray, Menu, dialog, ipcMain, nativeImage,
  powerMonitor, shell,
} = require('electron');
const { autoUpdater } = require('electron-updater');
const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const os = require('os');

// ─── Constants ────────────────────────────────────────────────────────────────

const IS_DEV = !app.isPackaged;
const DENAI_PORT = 4078;
const DENAI_URL = `http://127.0.0.1:${DENAI_PORT}`;
const HEALTH_URL = `${DENAI_URL}/api/health`;
const WIN_MIN_WIDTH = 900;
const WIN_MIN_HEIGHT = 600;
const MAX_RESTARTS = 3;

// Versão bundled — substituída pelo sync-version.js no build
const BUNDLED_VERSION = require('../package.json').version;

// Caminhos
const VENV_DIR = path.join(os.homedir(), '.denai', 'electron-venv');
const BOUNDS_FILE = path.join(app.getPath('userData'), 'window-bounds.json');

// ─── State ─────────────────────────────────────────────────────────────────────

let mainWindow = null;
let splashWindow = null;
let tray = null;
let backendProcess = null;
let backendRestartCount = 0;
let isQuitting = false;

// ─── Crash handlers ────────────────────────────────────────────────────────────

process.on('uncaughtException', (err) => {
  console.error('[DenAI] Uncaught exception:', err);
});
process.on('unhandledRejection', (reason) => {
  console.error('[DenAI] Unhandled rejection:', reason);
});

// ─── Single instance ──────────────────────────────────────────────────────────

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  console.log('[DenAI] Outra instância já está rodando — focando janela existente.');
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
  main();
}

// ─── uv detection ─────────────────────────────────────────────────────────────

function getUvPath() {
  const platform = process.platform;
  const arch = process.arch;

  let uvName;
  if (platform === 'win32')        uvName = 'uv-win32-x64.exe';
  else if (platform === 'darwin' && arch === 'arm64') uvName = 'uv-darwin-arm64';
  else if (platform === 'darwin')  uvName = 'uv-darwin-x64';
  else                             uvName = 'uv-linux-x64';

  // Em produção: recursos empacotados
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'bin', uvName);
  }

  // Em desenvolvimento: bin/ relativo ao electron/
  const devPath = path.join(__dirname, '..', 'bin', uvName);
  if (fs.existsSync(devPath)) return devPath;

  // Fallback: uv instalado globalmente
  try {
    const which = platform === 'win32'
      ? execSync('where uv', { encoding: 'utf-8' }).trim().split('\n')[0]
      : execSync('which uv', { encoding: 'utf-8' }).trim();
    if (which) return which;
  } catch {}

  return null;
}

// ─── venv bootstrap ──────────────────────────────────────────────────────────

async function ensureVenv(uvPath, sendStatus) {
  const venvExists = fs.existsSync(path.join(VENV_DIR, 'pyvenv.cfg'));

  if (!venvExists) {
    // First run — criar venv e instalar denai
    sendStatus('Configurando Python...');
    await runCommand(uvPath, ['venv', VENV_DIR]);

    sendStatus(`Instalando DenAI ${BUNDLED_VERSION}...`);
    await runCommand(uvPath, [
      'pip', 'install',
      `denai==${BUNDLED_VERSION}`,
      '--python', VENV_DIR,
    ]);
    return;
  }

  // Verificar se a versão instalada está correta
  try {
    const pipShow = await runCommand(uvPath, [
      'pip', 'show', 'denai', '--python', VENV_DIR,
    ], { capture: true });
    const match = pipShow.match(/^Version:\s*(.+)$/m);
    const installed = match ? match[1].trim() : null;

    if (installed !== BUNDLED_VERSION) {
      sendStatus(`Atualizando DenAI ${installed} → ${BUNDLED_VERSION}...`);
      await runCommand(uvPath, [
        'pip', 'install', `denai==${BUNDLED_VERSION}`,
        '--python', VENV_DIR,
      ]);
    }
  } catch {
    // pip show falhou — reinstalar
    sendStatus(`Instalando DenAI ${BUNDLED_VERSION}...`);
    await runCommand(uvPath, [
      'pip', 'install', `denai==${BUNDLED_VERSION}`,
      '--python', VENV_DIR,
    ]);
  }
}

function runCommand(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(cmd, args, {
      stdio: opts.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
    });
    let stdout = '';
    proc.stdout?.on('data', (d) => { stdout += d.toString(); });
    proc.on('error', reject);
    proc.on('exit', (code) => {
      if (code === 0) resolve(stdout);
      else reject(new Error(`${path.basename(cmd)} exited with ${code}`));
    });
  });
}

// ─── Backend spawn ────────────────────────────────────────────────────────────

function spawnBackend(uvPath) {
  console.log('[DenAI] Iniciando servidor...');

  const pythonBin = process.platform === 'win32'
    ? path.join(VENV_DIR, 'Scripts', 'python.exe')
    : path.join(VENV_DIR, 'bin', 'python');

  backendProcess = spawn(uvPath, ['run', '--python', VENV_DIR, 'python', '-m', 'denai'], {
    env: {
      ...process.env,
      DENAI_PORT: String(DENAI_PORT),
      DENAI_HOST: '127.0.0.1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
  });

  backendProcess.stdout?.on('data', (d) => {
    const line = d.toString().trim();
    if (line) console.log(`[DenAI backend] ${line}`);
  });
  backendProcess.stderr?.on('data', (d) => {
    const line = d.toString().trim();
    if (line) console.warn(`[DenAI backend:err] ${line}`);
  });
  backendProcess.on('error', (err) => {
    console.error('[DenAI] Falha ao iniciar backend:', err);
  });
  backendProcess.on('exit', (code, signal) => {
    console.log(`[DenAI] Backend encerrou: code=${code} signal=${signal}`);
    backendProcess = null;

    const unexpected = code !== 0 && code !== null && !isQuitting;
    if (unexpected && backendRestartCount < MAX_RESTARTS) {
      backendRestartCount++;
      const delay = 1500 * Math.pow(2, backendRestartCount - 1);
      console.warn(`[DenAI] Reiniciando backend em ${delay}ms (tentativa ${backendRestartCount}/${MAX_RESTARTS})...`);
      setTimeout(() => spawnBackend(uvPath), delay);
    } else if (unexpected) {
      dialog.showErrorBox(
        'DenAI — Servidor encerrou',
        `O servidor DenAI encerrou inesperadamente após ${MAX_RESTARTS} tentativas.\nReinicie o aplicativo.`,
      );
    }
  });
}

// ─── Health polling ───────────────────────────────────────────────────────────

function waitForService(url, timeoutMs, intervalMs) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;

    function check() {
      const req = http.get(url, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else if (Date.now() < deadline) {
          setTimeout(check, intervalMs);
        } else {
          reject(new Error(`Timeout aguardando ${url}`));
        }
        res.resume();
      });
      req.on('error', () => {
        if (Date.now() < deadline) {
          setTimeout(check, intervalMs);
        } else {
          reject(new Error(`Timeout aguardando ${url}`));
        }
      });
      req.setTimeout(intervalMs, () => req.destroy());
    }

    check();
  });
}

// ─── Process cleanup ──────────────────────────────────────────────────────────

function killProcessCrossPlatform(proc) {
  if (!proc || proc.killed || proc.pid == null) return;
  try {
    if (process.platform === 'win32') {
      execSync(`taskkill /F /T /PID ${proc.pid}`, { stdio: 'ignore' });
    } else {
      proc.kill('SIGTERM');
    }
  } catch {}
}

// ─── Window bounds ────────────────────────────────────────────────────────────

function loadWindowBounds() {
  try {
    const data = JSON.parse(fs.readFileSync(BOUNDS_FILE, 'utf-8'));
    if (data.width >= WIN_MIN_WIDTH && data.height >= WIN_MIN_HEIGHT) return data;
  } catch {}
  return { width: 1200, height: 750 };
}

function saveWindowBounds(win) {
  try {
    fs.writeFileSync(BOUNDS_FILE, JSON.stringify(win.getBounds()));
  } catch {}
}

// ─── Splash window ────────────────────────────────────────────────────────────

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 420,
    height: 280,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    transparent: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  splashWindow.loadFile(path.join(__dirname, 'splash.html'));
}

function sendSplashStatus(msg) {
  splashWindow?.webContents.send('splash-status', msg);
}

function closeSplash() {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.close();
    splashWindow = null;
  }
}

// ─── Main window ──────────────────────────────────────────────────────────────

function createMainWindow() {
  const bounds = loadWindowBounds();

  mainWindow = new BrowserWindow({
    ...bounds,
    minWidth: WIN_MIN_WIDTH,
    minHeight: WIN_MIN_HEIGHT,
    title: 'DenAI',
    icon: path.join(__dirname, '..', 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL(DENAI_URL);

  // Salvar bounds ao redimensionar/mover
  const saveBounds = () => saveWindowBounds(mainWindow);
  mainWindow.on('resize', saveBounds);
  mainWindow.on('move', saveBounds);

  // Fechar → minimizar para tray
  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  // DevTools só em desenvolvimento
  if (IS_DEV) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

// ─── Tray ─────────────────────────────────────────────────────────────────────

function setupTray() {
  const iconPath = path.join(__dirname, '..', 'assets',
    process.platform === 'win32' ? 'icon.ico' : 'icon.png');

  const icon = nativeImage.createFromPath(iconPath);
  tray = new Tray(process.platform === 'darwin' ? icon.resize({ width: 18, height: 18 }) : icon);
  tray.setToolTip('DenAI');

  const updateMenu = (serverOnline = true) => {
    const menu = Menu.buildFromTemplate([
      {
        label: '🐺 Abrir DenAI',
        click: () => {
          if (mainWindow) { mainWindow.show(); mainWindow.focus(); }
        },
      },
      { type: 'separator' },
      {
        label: serverOnline ? '● Servidor: online' : '○ Servidor: offline',
        enabled: false,
      },
      { type: 'separator' },
      {
        label: 'Sair',
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]);
    tray.setContextMenu(menu);
  };

  updateMenu(false);

  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });

  // Atualizar status do servidor periodicamente
  setInterval(() => {
    http.get(HEALTH_URL, (res) => {
      updateMenu(res.statusCode === 200);
      res.resume();
    }).on('error', () => updateMenu(false));
  }, 5000);

  return updateMenu;
}

// ─── Ollama check ─────────────────────────────────────────────────────────────

function checkOllama() {
  const check = () => {
    http.get('http://localhost:11434/api/version', (res) => {
      res.resume();
      if (res.statusCode !== 200) scheduleRetry();
    }).on('error', () => scheduleRetry());
  };

  let notified = false;
  const scheduleRetry = () => {
    if (!notified) {
      notified = true;
      // Notificação não-bloqueante
      const { Notification } = require('electron');
      if (Notification.isSupported()) {
        new Notification({
          title: 'DenAI',
          body: 'Ollama não encontrado. Baixe em ollama.com para usar modelos locais.',
        }).show();
      }
    }
    setTimeout(check, 30000); // retry a cada 30s
  };

  setTimeout(check, 3000); // checar 3s após inicializar
}

// ─── Auto-update ──────────────────────────────────────────────────────────────

function setupAutoUpdate() {
  if (IS_DEV) return;

  autoUpdater.setFeedURL({
    provider: 'github',
    owner: 'rodrigogobbo',
    repo: 'denai',
  });

  autoUpdater.on('update-available', () => {
    dialog.showMessageBox({
      type: 'info',
      title: 'Atualização disponível',
      message: 'Uma nova versão do DenAI está disponível. Deseja baixar?',
      buttons: ['Baixar', 'Agora não'],
    }).then(({ response }) => {
      if (response === 0) autoUpdater.downloadUpdate();
    });
  });

  autoUpdater.on('update-downloaded', () => {
    dialog.showMessageBox({
      type: 'info',
      title: 'Atualização pronta',
      message: 'A atualização foi baixada. Reinicie para aplicar.',
      buttons: ['Reiniciar agora', 'Depois'],
    }).then(({ response }) => {
      if (response === 0) {
        isQuitting = true;
        autoUpdater.quitAndInstall();
      }
    });
  });

  autoUpdater.checkForUpdatesAndNotify().catch(() => {});
}

// ─── powerMonitor ─────────────────────────────────────────────────────────────

function setupPowerMonitor() {
  powerMonitor.on('resume', () => {
    // Despachar evento no frontend para reconectar SSE
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.executeJavaScript(
        'window.dispatchEvent(new CustomEvent("denai:wake"))',
      ).catch(() => {});
    }
  });
}

// ─── IPC handlers ─────────────────────────────────────────────────────────────

function setupIPC() {
  ipcMain.handle('open-external', (_e, url) => shell.openExternal(url));
  ipcMain.handle('get-version', () => app.getVersion());
  ipcMain.handle('get-denai-url', () => DENAI_URL);
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  await app.whenReady();

  setupIPC();
  setupPowerMonitor();
  createSplashWindow();
  setupTray();
  setupAutoUpdate();

  // Detectar uv
  const uvPath = getUvPath();
  if (!uvPath || !fs.existsSync(uvPath)) {
    closeSplash();
    dialog.showErrorBox(
      'DenAI — uv não encontrado',
      IS_DEV
        ? 'Coloque o binário uv em electron/bin/ (ver docs).'
        : 'Instalação corrompida. Reinstale o DenAI.',
    );
    app.quit();
    return;
  }

  // Bootstrap do venv
  try {
    sendSplashStatus('Verificando instalação...');
    await ensureVenv(uvPath, sendSplashStatus);
  } catch (err) {
    closeSplash();
    dialog.showErrorBox(
      'DenAI — Erro na instalação',
      `Não foi possível configurar o ambiente Python:\n${err.message}`,
    );
    app.quit();
    return;
  }

  // Iniciar backend
  sendSplashStatus('Iniciando servidor...');
  spawnBackend(uvPath);

  // Aguardar health
  try {
    await waitForService(HEALTH_URL, 30000, 500);
  } catch {
    closeSplash();
    dialog.showErrorBox(
      'DenAI — Servidor não respondeu',
      'O servidor demorou mais de 30 segundos para iniciar.\nVerifique os logs em ~/.denai/logs/',
    );
    app.quit();
    return;
  }

  // Tudo pronto
  closeSplash();
  createMainWindow();
  checkOllama();
}

// ─── App lifecycle ────────────────────────────────────────────────────────────

app.on('activate', () => {
  // macOS — clique no dock
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }
});

app.on('window-all-closed', (e) => {
  // Não encerrar — manter na tray
  e.preventDefault();
});

app.on('before-quit', () => {
  isQuitting = true;
  killProcessCrossPlatform(backendProcess);
});
