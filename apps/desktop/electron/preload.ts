import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('webstudio', {
  checkHealth: () => ipcRenderer.invoke('health:check'),
});
