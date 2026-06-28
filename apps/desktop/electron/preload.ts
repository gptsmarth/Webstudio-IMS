import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('api', {
  checkHealth: () => ipcRenderer.invoke('api:health:check'),
});

contextBridge.exposeInMainWorld('config', {
  get: (key: string) => ipcRenderer.invoke('config:get', key),
  set: (key: string, value: unknown) => ipcRenderer.invoke('config:set', key, value),
  getEnv: () => ipcRenderer.invoke('config:getEnv'),
});

contextBridge.exposeInMainWorld('system', {
  getVersionInfo: () => ipcRenderer.invoke('system:getVersionInfo'),
  log: (channel: string, level: string, message: string, meta?: Record<string, unknown>) =>
    ipcRenderer.invoke('system:log', { channel, level, message, meta }),
  reportCrash: (errorDetails: Record<string, unknown>) =>
    ipcRenderer.invoke('system:reportCrash', errorDetails),
});

contextBridge.exposeInMainWorld('storage', {
  getItem: (key: string) => ipcRenderer.invoke('storage:getItem', key),
  setItem: (key: string, value: unknown) => ipcRenderer.invoke('storage:setItem', key, value),
  removeItem: (key: string) => ipcRenderer.invoke('storage:removeItem', key),
});
