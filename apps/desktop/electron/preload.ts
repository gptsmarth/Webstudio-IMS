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

contextBridge.exposeInMainWorld('network', {
  startDiscovery: () => ipcRenderer.invoke('network:startDiscovery'),
  stopDiscovery: () => ipcRenderer.invoke('network:stopDiscovery'),
  getDiscoveredServers: () => ipcRenderer.invoke('network:getDiscoveredServers'),
  resolveHost: (host: string) => ipcRenderer.invoke('network:resolveHost', host),
});

contextBridge.exposeInMainWorld('update', {
  downloadArtifact: (request: { url: string; fileName: string; expectedSha256?: string }) =>
    ipcRenderer.invoke('update:downloadArtifact', request),
  installAndRestart: (installerPath: string) =>
    ipcRenderer.invoke('update:installAndRestart', installerPath),
});

contextBridge.exposeInMainWorld('windowControls', {
  getZoomFactor: () => ipcRenderer.invoke('window:getZoomFactor') as Promise<number>,
  setZoomFactor: (factor: number) =>
    ipcRenderer.invoke('window:setZoomFactor', factor) as Promise<number>,
  zoomIn: () => ipcRenderer.invoke('window:zoomIn') as Promise<number>,
  zoomOut: () => ipcRenderer.invoke('window:zoomOut') as Promise<number>,
  resetZoom: () => ipcRenderer.invoke('window:resetZoom') as Promise<number>,
});
