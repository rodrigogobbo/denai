'use strict';

// Receber atualizações de status do main process
if (window.electronAPI) {
  window.electronAPI.onSplashStatus((msg) => {
    const el = document.getElementById('status');
    if (el) el.textContent = msg;
  });

  window.electronAPI.getVersion().then((v) => {
    const el = document.getElementById('version');
    if (el) el.textContent = `v${v}`;
  }).catch(() => {});
}
