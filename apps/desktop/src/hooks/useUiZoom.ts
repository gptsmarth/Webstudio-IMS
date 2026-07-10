import { useCallback, useEffect, useState } from 'react';

const FALLBACK_ZOOM = 1;

async function invokeZoom(
  action: 'get' | 'in' | 'out' | 'reset' | 'set',
  factor?: number,
): Promise<number> {
  const controls = window.windowControls;
  if (!controls) return FALLBACK_ZOOM;
  try {
    if (action === 'get') return await controls.getZoomFactor();
    if (action === 'in') return await controls.zoomIn();
    if (action === 'out') return await controls.zoomOut();
    if (action === 'reset') return await controls.resetZoom();
    if (action === 'set' && typeof factor === 'number') {
      return await controls.setZoomFactor(factor);
    }
  } catch {
    return FALLBACK_ZOOM;
  }
  return FALLBACK_ZOOM;
}

export function formatZoomPercent(factor: number): string {
  return `${Math.round(factor * 100)}%`;
}

/** Electron zoom factor controls — scales the whole UI proportionally (layout-safe). */
export function useUiZoom(): {
  zoomFactor: number;
  zoomPercentLabel: string;
  zoomIn: () => Promise<void>;
  zoomOut: () => Promise<void>;
  resetZoom: () => Promise<void>;
  setZoomFactor: (factor: number) => Promise<void>;
  available: boolean;
} {
  const [zoomFactor, setZoomFactorState] = useState(FALLBACK_ZOOM);
  const available = typeof window !== 'undefined' && Boolean(window.windowControls);

  useEffect(() => {
    if (!available) return;
    void invokeZoom('get').then(setZoomFactorState);
  }, [available]);

  const zoomIn = useCallback(async () => {
    setZoomFactorState(await invokeZoom('in'));
  }, []);

  const zoomOut = useCallback(async () => {
    setZoomFactorState(await invokeZoom('out'));
  }, []);

  const resetZoom = useCallback(async () => {
    setZoomFactorState(await invokeZoom('reset'));
  }, []);

  const setZoomFactor = useCallback(async (factor: number) => {
    setZoomFactorState(await invokeZoom('set', factor));
  }, []);

  return {
    zoomFactor,
    zoomPercentLabel: formatZoomPercent(zoomFactor),
    zoomIn,
    zoomOut,
    resetZoom,
    setZoomFactor,
    available,
  };
}
