import { app, net, protocol } from 'electron';
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

/** Must run before app.whenReady(). */
export function registerAppScheme(): void {
  protocol.registerSchemesAsPrivileged([
    {
      scheme: 'app',
      privileges: {
        secure: true,
        standard: true,
        supportFetchAPI: true,
        corsEnabled: true,
        stream: true,
      },
    },
  ]);
}

function resolveDistRoot(): string {
  return path.join(__dirname, '../dist');
}

function resolveDistFilePath(requestUrl: string): string | null {
  const parsed = new URL(requestUrl);
  let relativePath = decodeURIComponent(parsed.pathname);
  if (relativePath.startsWith('/')) {
    relativePath = relativePath.slice(1);
  }
  if (!relativePath || relativePath === '.') {
    relativePath = 'index.html';
  }

  const distRoot = path.resolve(resolveDistRoot());
  const filePath = path.resolve(distRoot, relativePath);
  if (!filePath.startsWith(distRoot)) {
    return null;
  }
  return filePath;
}

/** Packaged installers also copy static assets to resources/assets/ via extraResources. */
function resolveExtraResourceFilePath(requestUrl: string): string | null {
  const parsed = new URL(requestUrl);
  let relativePath = decodeURIComponent(parsed.pathname);
  if (relativePath.startsWith('/')) {
    relativePath = relativePath.slice(1);
  }
  if (!relativePath.startsWith('assets/')) {
    return null;
  }

  const resourceRoot = path.resolve(path.join(process.resourcesPath, 'assets'));
  const assetTail = relativePath.slice('assets/'.length);
  const filePath = path.resolve(resourceRoot, assetTail);
  if (!filePath.startsWith(resourceRoot)) {
    return null;
  }
  return filePath;
}

function resolvePackagedFilePath(requestUrl: string): string | null {
  const distPath = resolveDistFilePath(requestUrl);
  if (distPath && fs.existsSync(distPath)) {
    return distPath;
  }

  if (app.isPackaged) {
    const resourcePath = resolveExtraResourceFilePath(requestUrl);
    if (resourcePath && fs.existsSync(resourcePath)) {
      return resourcePath;
    }
  }

  return distPath;
}

/** Serve packaged renderer assets over app:// (avoids file:// + crossorigin issues on macOS). */
export function registerAppProtocol(): void {
  protocol.handle('app', async (request) => {
    const filePath = resolvePackagedFilePath(request.url);
    if (!filePath || !fs.existsSync(filePath)) {
      return new Response('Not Found', { status: 404 });
    }
    return net.fetch(pathToFileURL(filePath).href);
  });
}

export const APP_INDEX_URL = 'app://./index.html';
