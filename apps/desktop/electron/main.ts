import { app, BrowserWindow, ipcMain } from 'electron';
import dns from 'node:dns/promises';
import fs from 'node:fs';
import path from 'node:path';

import { MdnsBrowser } from './mdns-discovery';

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  let mainWindow: BrowserWindow | null = null;
  const mdnsBrowser = new MdnsBrowser();
  let discoveredServers: unknown[] = [];
  const API_BASE_URL = process.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
  const APP_MODE = (process.env.NODE_ENV as 'development' | 'production' | 'test') ?? 'development';

  // --- Centralized Logging Architecture ---
  const getLogPath = (): string => path.join(app.getPath('userData'), 'webstudio-client.log');

  const writeLog = (channel: string, level: string, message: string, meta?: Record<string, unknown>): void => {
    const timestamp = new Date().toISOString();
    const formattedMeta = meta ? ` | Meta: ${JSON.stringify(meta)}` : '';
    const logLine = `[${timestamp}] [${channel}] [${level.toUpperCase()}] ${message}${formattedMeta}\n`;
    
    console.log(logLine.trim());
    try {
      fs.appendFileSync(getLogPath(), logLine, 'utf-8');
    } catch {
      // Ignore file write failures
    }
  };

  process.on('uncaughtException', (error) => {
    writeLog('Main', 'error', `Uncaught Exception: ${error.message}`, { stack: error.stack });
  });

  process.on('unhandledRejection', (reason) => {
    writeLog('Main', 'error', `Unhandled Rejection: ${String(reason)}`);
  });

  // --- File Persistence Helpers ---
  const getConfigPath = (): string => path.join(app.getPath('userData'), 'webstudio_config.json');
  const getStoragePath = (): string => path.join(app.getPath('userData'), 'webstudio_storage.json');
  const getWindowStatePath = (): string => path.join(app.getPath('userData'), 'webstudio_window_state.json');

  const readJson = (filePath: string): Record<string, unknown> => {
    try {
      if (fs.existsSync(filePath)) {
        return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as Record<string, unknown>;
      }
    } catch {
      // Ignore parse errors
    }
    return {};
  };

  const writeJson = (filePath: string, data: Record<string, unknown>): void => {
    try {
      fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
    } catch {
      // Ignore write errors
    }
  };

  // --- Window State Persistence ---
  interface WindowState {
    width: number;
    height: number;
    x?: number;
    y?: number;
    isMaximized: boolean;
  }

  const getSavedWindowState = (): WindowState => {
    const saved = readJson(getWindowStatePath());
    return {
      width: typeof saved.width === 'number' ? saved.width : 1280,
      height: typeof saved.height === 'number' ? saved.height : 800,
      x: typeof saved.x === 'number' ? saved.x : undefined,
      y: typeof saved.y === 'number' ? saved.y : undefined,
      isMaximized: Boolean(saved.isMaximized),
    };
  };

  const saveWindowState = (): void => {
    if (!mainWindow) return;
    const isMaximized = mainWindow.isMaximized();
    const bounds = mainWindow.getBounds();
    writeJson(getWindowStatePath(), {
      width: bounds.width,
      height: bounds.height,
      x: bounds.x,
      y: bounds.y,
      isMaximized,
    });
  };

  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  function createWindow(): void {
    const windowState = getSavedWindowState();

    mainWindow = new BrowserWindow({
      width: windowState.width,
      height: windowState.height,
      x: windowState.x,
      y: windowState.y,
      minWidth: 1024,
      minHeight: 768,
      show: false,
      title: 'WEBSTUDIO IMS',
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
        webSecurity: true,
      },
    });

    if (windowState.isMaximized) {
      mainWindow.maximize();
    }

    mainWindow.once('ready-to-show', () => {
      mainWindow?.show();
    });

    mainWindow.on('resize', saveWindowState);
    mainWindow.on('move', saveWindowState);
    mainWindow.on('close', saveWindowState);

    if (process.env.VITE_DEV_SERVER_URL) {
      void mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    } else {
      void mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }
  }

  // --- IPC Handlers ---
  ipcMain.handle('api:health:check', async () => {
    writeLog('API', 'info', 'Health check requested');
    const response = await fetch(`${API_BASE_URL}/health/live`);
    return response.json();
  });

  ipcMain.handle('config:get', (_event, key: string) => {
    const config = readJson(getConfigPath());
    return config[key];
  });

  ipcMain.handle('config:set', (_event, key: string, value: unknown) => {
    const config = readJson(getConfigPath());
    config[key] = value;
    writeJson(getConfigPath(), config);
  });

  ipcMain.handle('config:getEnv', () => ({
    mode: APP_MODE,
    apiBaseUrl: API_BASE_URL,
  }));

  ipcMain.handle('system:getVersionInfo', () => ({
    appVersion: app.getVersion(),
    buildVersion: '0.1.0-mvp',
    gitCommit: process.env.VITE_GIT_COMMIT ?? 'dev-local',
    buildDate: new Date().toISOString().split('T')[0],
    electronVersion: process.versions.electron ?? 'unknown',
    chromiumVersion: process.versions.chrome ?? 'unknown',
    nodeVersion: process.versions.node ?? 'unknown',
  }));

  ipcMain.handle('system:log', (_event, { channel, level, message, meta }: { channel: string; level: string; message: string; meta?: Record<string, unknown> }) => {
    writeLog(channel, level, message, meta);
  });

  ipcMain.handle('system:reportCrash', (_event, errorDetails: Record<string, unknown>) => {
    writeLog('Renderer', 'error', `Renderer Crash Reported: ${JSON.stringify(errorDetails)}`);
  });

  ipcMain.handle('storage:getItem', (_event, key: string) => {
    const storage = readJson(getStoragePath());
    return storage[key];
  });

  ipcMain.handle('storage:setItem', (_event, key: string, value: unknown) => {
    const storage = readJson(getStoragePath());
    storage[key] = value;
    writeJson(getStoragePath(), storage);
  });

  ipcMain.handle('storage:removeItem', (_event, key: string) => {
    const storage = readJson(getStoragePath());
    delete storage[key];
    writeJson(getStoragePath(), storage);
  });

  ipcMain.handle('network:startDiscovery', () => {
    discoveredServers = [];
    mdnsBrowser.start((servers) => {
      discoveredServers = servers;
    });
  });

  ipcMain.handle('network:stopDiscovery', () => {
    mdnsBrowser.stop();
  });

  ipcMain.handle('network:getDiscoveredServers', () => discoveredServers);

  ipcMain.handle('network:resolveHost', async (_event, host: string) => {
    const trimmed = host.trim();
    try {
      const result = await dns.lookup(trimmed, { family: 4 });
      return {
        host: trimmed,
        resolvedIp: result.address,
        resolved: true,
        message: `Resolved ${trimmed} to ${result.address}.`,
      };
    } catch (error) {
      return {
        host: trimmed,
        resolvedIp: null,
        resolved: false,
        message: error instanceof Error ? error.message : String(error),
      };
    }
  });

  app.whenReady().then(() => {
    writeLog('Main', 'info', 'Application bootstrap started');
    createWindow();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      }
    });
  });

  app.on('window-all-closed', () => {
    writeLog('Main', 'info', 'All windows closed');
    mdnsBrowser.stop();
    if (process.platform !== 'darwin') {
      app.quit();
    }
  });
}
