import { app, BrowserWindow, crashReporter, ipcMain, screen, shell } from 'electron';
import crypto from 'node:crypto';
import dns from 'node:dns/promises';
import fs from 'node:fs';
import http from 'node:http';
import https from 'node:https';
import path from 'node:path';
import { spawn } from 'node:child_process';

import { APP_INDEX_URL, registerAppProtocol, registerAppScheme } from './app-protocol';
import { MdnsBrowser } from './mdns-discovery';
import { configureApplicationMenu, shouldAutoHideMenuBar } from './menu';

registerAppScheme();

const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  let mainWindow: BrowserWindow | null = null;
  const mdnsBrowser = new MdnsBrowser();
  let discoveredServers: unknown[] = [];
  const API_BASE_URL = process.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';
  const APP_MODE = (process.env.NODE_ENV as 'development' | 'production' | 'test') ?? 'development';

  if (APP_MODE === 'production') {
    crashReporter.start({
      productName: 'WEBSTUDIO Desktop',
      companyName: 'WEBSTUDIO',
      submitURL: '',
      uploadToServer: false,
    });
  }

  // --- Centralized Logging Architecture ---
  const getLogPath = (): string => path.join(app.getPath('userData'), 'webstudio-client.log');
  const getCrashReportsPath = (): string => path.join(app.getPath('userData'), 'crash-reports');

  const writeLog = (
    channel: string,
    level: string,
    message: string,
    meta?: Record<string, unknown>,
  ): void => {
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
    try {
      fs.mkdirSync(getCrashReportsPath(), { recursive: true });
      const crashFile = path.join(getCrashReportsPath(), `crash-${Date.now()}.log`);
      fs.writeFileSync(crashFile, `${error.stack ?? error.message}\n`, 'utf-8');
    } catch {
      // Ignore crash file write failures
    }
  });

  process.on('unhandledRejection', (reason) => {
    writeLog('Main', 'error', `Unhandled Rejection: ${String(reason)}`);
  });

  // --- File Persistence Helpers ---
  const getConfigPath = (): string => path.join(app.getPath('userData'), 'webstudio_config.json');
  const getStoragePath = (): string => path.join(app.getPath('userData'), 'webstudio_storage.json');
  const getWindowStatePath = (): string =>
    path.join(app.getPath('userData'), 'webstudio_window_state.json');

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

  const ZOOM_MIN = 0.75;
  const ZOOM_MAX = 1.25;
  const ZOOM_STEP = 0.05;
  const ZOOM_DEFAULT = 1;

  const clampZoomFactor = (value: number): number => {
    const rounded = Math.round(value * 100) / 100;
    return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, rounded));
  };

  const readZoomFactor = (): number => {
    const config = readJson(getConfigPath());
    const raw = config.uiZoomFactor;
    return typeof raw === 'number' && Number.isFinite(raw) ? clampZoomFactor(raw) : ZOOM_DEFAULT;
  };

  const persistZoomFactor = (factor: number): number => {
    const clamped = clampZoomFactor(factor);
    const config = readJson(getConfigPath());
    config.uiZoomFactor = clamped;
    writeJson(getConfigPath(), config);
    return clamped;
  };

  const applyZoomFactor = (factor: number): number => {
    const clamped = persistZoomFactor(factor);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.setZoomFactor(clamped);
    }
    return clamped;
  };

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

  /** Keep the window fully inside the display work area (above the taskbar/dock). */
  const fitWindowStateToWorkArea = (
    state: WindowState,
  ): WindowState & { minWidth: number; minHeight: number } => {
    const anchorX =
      typeof state.x === 'number' ? state.x : screen.getPrimaryDisplay().workArea.x + 40;
    const anchorY =
      typeof state.y === 'number' ? state.y : screen.getPrimaryDisplay().workArea.y + 40;
    const { workArea } = screen.getDisplayNearestPoint({ x: anchorX, y: anchorY });

    // Never force a minimum larger than the usable desktop (14" + taskbar often < 768px tall).
    const minWidth = Math.max(800, Math.min(1024, workArea.width));
    const minHeight = Math.max(560, Math.min(700, workArea.height));

    const width = Math.min(Math.max(state.width, minWidth), workArea.width);
    const height = Math.min(Math.max(state.height, minHeight), workArea.height);

    let x =
      typeof state.x === 'number'
        ? state.x
        : workArea.x + Math.max(0, Math.floor((workArea.width - width) / 2));
    let y =
      typeof state.y === 'number'
        ? state.y
        : workArea.y + Math.max(0, Math.floor((workArea.height - height) / 2));

    x = Math.min(Math.max(x, workArea.x), workArea.x + workArea.width - width);
    y = Math.min(Math.max(y, workArea.y), workArea.y + workArea.height - height);

    return {
      width,
      height,
      x,
      y,
      isMaximized: state.isMaximized,
      minWidth,
      minHeight,
    };
  };

  const ensureWindowInWorkArea = (): void => {
    if (!mainWindow || mainWindow.isDestroyed() || mainWindow.isMaximized()) return;
    const fitted = fitWindowStateToWorkArea({
      ...mainWindow.getBounds(),
      isMaximized: false,
    });
    mainWindow.setMinimumSize(fitted.minWidth, fitted.minHeight);
    mainWindow.setBounds({
      x: fitted.x,
      y: fitted.y,
      width: fitted.width,
      height: fitted.height,
    });
  };

  const saveWindowState = (): void => {
    if (!mainWindow) return;
    const isMaximized = mainWindow.isMaximized();
    // Persist normal bounds so restore after maximize does not keep oversized taskbar-overlapping size.
    const bounds = isMaximized ? mainWindow.getNormalBounds() : mainWindow.getBounds();
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

  const resolveBrandingIcon = (): string | undefined => {
    const candidates = [
      path.join(
        process.resourcesPath,
        'assets',
        'webstudio',
        process.platform === 'darwin' ? 'icon.icns' : 'icon.ico',
      ),
      path.join(
        __dirname,
        '../public/assets/webstudio',
        process.platform === 'darwin' ? 'icon.icns' : 'icon.ico',
      ),
    ];
    for (const candidate of candidates) {
      if (fs.existsSync(candidate)) {
        return candidate;
      }
    }
    return undefined;
  };

  function createWindow(): void {
    const fitted = fitWindowStateToWorkArea(getSavedWindowState());
    const brandingIcon = resolveBrandingIcon();

    mainWindow = new BrowserWindow({
      width: fitted.width,
      height: fitted.height,
      x: fitted.x,
      y: fitted.y,
      minWidth: fitted.minWidth,
      minHeight: fitted.minHeight,
      show: false,
      title: 'WEBSTUDIO Desktop',
      icon: brandingIcon,
      autoHideMenuBar: shouldAutoHideMenuBar(),
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
        webSecurity: true,
      },
    });

    if (fitted.isMaximized) {
      mainWindow.maximize();
    }

    mainWindow.once('ready-to-show', () => {
      ensureWindowInWorkArea();
      applyZoomFactor(readZoomFactor());
      mainWindow?.show();
    });

    mainWindow.on('resize', saveWindowState);
    mainWindow.on('move', saveWindowState);
    mainWindow.on('close', saveWindowState);

    screen.on('display-metrics-changed', () => {
      ensureWindowInWorkArea();
    });

    if (process.env.VITE_DEV_SERVER_URL) {
      void mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    } else {
      writeLog('Main', 'info', `Loading renderer from ${APP_INDEX_URL}`);
      void mainWindow.loadURL(APP_INDEX_URL);
    }

    mainWindow.webContents.on('did-finish-load', () => {
      applyZoomFactor(readZoomFactor());
      writeLog('Main', 'info', `Renderer loaded: ${mainWindow?.webContents.getURL()}`);
    });

    mainWindow.webContents.on(
      'did-fail-load',
      (_event, errorCode, errorDescription, validatedURL) => {
        writeLog(
          'Main',
          'error',
          `Renderer failed to load ${validatedURL}: ${errorDescription} (${errorCode})`,
        );
      },
    );

    mainWindow.webContents.on('render-process-gone', (_event, details) => {
      writeLog('Main', 'error', `Renderer process gone: ${details.reason}`);
    });
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

  ipcMain.handle('config:getEnv', () => {
    const config = readJson(getConfigPath());
    const saved =
      typeof config.apiBaseUrl === 'string' ? config.apiBaseUrl.trim().replace(/\/$/, '') : '';
    return {
      mode: APP_MODE,
      // Prefer the URL saved from Connection setup so LAN clients keep
      // http://<server-ip>:8000 across restarts (default 127.0.0.1 only works on the server PC).
      apiBaseUrl: saved || API_BASE_URL,
    };
  });

  ipcMain.handle('window:getZoomFactor', () => readZoomFactor());
  ipcMain.handle('window:setZoomFactor', (_event, factor: unknown) => {
    const numeric = typeof factor === 'number' ? factor : Number(factor);
    return applyZoomFactor(Number.isFinite(numeric) ? numeric : ZOOM_DEFAULT);
  });
  ipcMain.handle('window:zoomIn', () => applyZoomFactor(readZoomFactor() + ZOOM_STEP));
  ipcMain.handle('window:zoomOut', () => applyZoomFactor(readZoomFactor() - ZOOM_STEP));
  ipcMain.handle('window:resetZoom', () => applyZoomFactor(ZOOM_DEFAULT));

  ipcMain.handle('system:getVersionInfo', () => {
    let webstudioMeta: {
      buildNumber?: number;
      releaseChannel?: string;
      releaseDate?: string;
      gitCommit?: string;
    } = {};
    try {
      const pkgPath = path.join(app.getAppPath(), 'package.json');
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8')) as {
        webstudio?: {
          buildNumber?: number;
          releaseChannel?: string;
          releaseDate?: string;
          gitCommit?: string;
        };
      };
      webstudioMeta = pkg.webstudio ?? {};
    } catch {
      // Fall back to environment metadata when package.json is unavailable.
    }

    return {
      appVersion: app.getVersion(),
      buildNumber: webstudioMeta.buildNumber ?? Number(process.env.WEBSTUDIO_BUILD_NUMBER ?? 1),
      buildVersion: process.env.WEBSTUDIO_BUILD_VERSION ?? app.getVersion(),
      gitCommit:
        webstudioMeta.gitCommit?.trim() ||
        process.env.VITE_GIT_COMMIT ||
        process.env.WEBSTUDIO_GIT_COMMIT ||
        'dev-local',
      buildDate: webstudioMeta.releaseDate?.trim() || new Date().toISOString().split('T')[0],
      releaseChannel:
        webstudioMeta.releaseChannel ?? process.env.WEBSTUDIO_RELEASE_CHANNEL ?? 'development',
      electronVersion: process.versions.electron ?? 'unknown',
      chromiumVersion: process.versions.chrome ?? 'unknown',
      nodeVersion: process.versions.node ?? 'unknown',
    };
  });

  ipcMain.handle(
    'system:log',
    (
      _event,
      {
        channel,
        level,
        message,
        meta,
      }: { channel: string; level: string; message: string; meta?: Record<string, unknown> },
    ) => {
      writeLog(channel, level, message, meta);
    },
  );

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

  const downloadFile = (url: string, destination: string): Promise<void> =>
    new Promise((resolve, reject) => {
      const client = url.startsWith('https://') ? https : http;
      const request = client.get(url, (response) => {
        if (
          response.statusCode &&
          response.statusCode >= 300 &&
          response.statusCode < 400 &&
          response.headers.location
        ) {
          downloadFile(response.headers.location, destination).then(resolve).catch(reject);
          return;
        }
        if (response.statusCode !== 200) {
          reject(new Error(`Download failed with status ${response.statusCode ?? 'unknown'}`));
          return;
        }
        const file = fs.createWriteStream(destination);
        response.pipe(file);
        file.on('finish', () => file.close(() => resolve()));
        file.on('error', reject);
      });
      request.on('error', reject);
    });

  const verifySha256 = (filePath: string, expected: string): boolean => {
    const digest = crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
    return digest.toLowerCase() === expected.trim().toLowerCase();
  };

  ipcMain.handle(
    'update:downloadArtifact',
    async (_event, request: { url: string; fileName: string; expectedSha256?: string }) => {
      const updatesDir = path.join(app.getPath('userData'), 'updates');
      fs.mkdirSync(updatesDir, { recursive: true });
      const destination = path.join(updatesDir, request.fileName);
      writeLog('Main', 'info', `Downloading client update artifact from ${request.url}`);
      await downloadFile(request.url, destination);
      if (request.expectedSha256 && !verifySha256(destination, request.expectedSha256)) {
        fs.unlinkSync(destination);
        throw new Error('Downloaded artifact failed SHA256 verification');
      }
      return destination;
    },
  );

  ipcMain.handle('update:installAndRestart', async (_event, installerPath: string) => {
    writeLog('Main', 'info', `Installing client update from ${installerPath}`);
    if (process.platform === 'win32') {
      spawn(installerPath, ['/S'], { detached: true, stdio: 'ignore' }).unref();
      app.quit();
      return;
    }
    if (process.platform === 'darwin') {
      await shell.openPath(installerPath);
      app.quit();
      return;
    }
    await shell.openPath(installerPath);
    app.quit();
  });

  app.whenReady().then(() => {
    registerAppProtocol();
    configureApplicationMenu({
      zoomIn: () => {
        applyZoomFactor(readZoomFactor() + ZOOM_STEP);
      },
      zoomOut: () => {
        applyZoomFactor(readZoomFactor() - ZOOM_STEP);
      },
      resetZoom: () => {
        applyZoomFactor(ZOOM_DEFAULT);
      },
    });
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
