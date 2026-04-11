'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Versão do app
  getVersion: () => ipcRenderer.invoke('get-version'),

  // URL do backend DenAI
  getDenaiUrl: () => ipcRenderer.invoke('get-denai-url'),

  // Abrir links externos no browser padrão
  openExternal: (url) => ipcRenderer.invoke('open-external', url),

  // Splash screen: receber status
  onSplashStatus: (callback) => {
    ipcRenderer.on('splash-status', (_e, msg) => callback(msg));
  },
});
