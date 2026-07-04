/** Extract a safe relative path from app:// requests (shared by Electron main and unit tests). */
export function extractAppRelativePath(requestUrl: string): string | null {
  try {
    const parsed = new URL(requestUrl);
    if (parsed.protocol !== 'app:') {
      return null;
    }

    const segments = decodeURIComponent(parsed.pathname)
      .replace(/^\/+/, '')
      .split('/')
      .filter((part) => part.length > 0);

    const normalized: string[] = [];
    for (const segment of segments) {
      if (segment === '.') {
        continue;
      }
      if (segment === '..') {
        normalized.pop();
        continue;
      }
      normalized.push(segment);
    }

    let relativePath = normalized.join('/');
    if (!relativePath) {
      relativePath = 'index.html';
    }
    if (relativePath.startsWith('..')) {
      return null;
    }
    return relativePath;
  } catch {
    return null;
  }
}
