import { useCallback, useEffect, useLayoutEffect, useRef, type RefObject } from 'react';

export interface HierarchyScrollRefOptions {
  /** When false, defer restore until data has finished loading. */
  ready?: boolean;
}

export interface HierarchyScrollRefResult {
  ref: RefObject<HTMLDivElement>;
  /** Persist the current scroll offset immediately (call before drill-down navigation). */
  saveScrollNow: () => void;
}

/**
 * Preserves scroll position for hierarchy list panes (brands / models) when
 * drilling into detail and navigating back.
 *
 * Important: do not persist scrollTop=0 on activate — inactive layers often report
 * 0 before layout restore runs, which previously wiped the saved offset and made
 * the list jump to the top after returning from a model.
 */
export function useHierarchyScrollRef(
  scrollKey: string,
  isActive: boolean,
  getScrollTop: (key: string) => number | undefined,
  setScrollTop: (key: string, value: number) => void,
  options?: HierarchyScrollRefOptions,
): HierarchyScrollRefResult {
  const ref = useRef<HTMLDivElement>(null);
  const lastOffsetRef = useRef(0);
  const ready = options?.ready !== false;

  const persistOffset = useCallback(
    (offset: number, { allowZero = false }: { allowZero?: boolean } = {}) => {
      const normalized = Math.max(0, offset);
      if (normalized <= 0 && !allowZero) {
        // Keep a previously saved positive offset when the DOM temporarily reports 0
        // (hidden layer / layout not ready yet).
        const existing = getScrollTop(scrollKey) ?? lastOffsetRef.current;
        if (existing > 0) return;
      }
      lastOffsetRef.current = normalized;
      setScrollTop(scrollKey, normalized);
    },
    [getScrollTop, scrollKey, setScrollTop],
  );

  const saveScrollNow = useCallback(() => {
    const element = ref.current;
    if (!element) {
      // Pane may already be inactive; keep the last known good offset.
      persistOffset(lastOffsetRef.current, { allowZero: lastOffsetRef.current === 0 });
      return;
    }
    persistOffset(element.scrollTop, { allowZero: true });
  }, [persistOffset]);

  useEffect(() => {
    const element = ref.current;
    if (!element || !isActive) return;

    const onScroll = () => {
      persistOffset(element.scrollTop, { allowZero: true });
    };
    element.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      element.removeEventListener('scroll', onScroll);
      // Prefer the live offset, but never replace a stored positive value with 0
      // from a detaching / hidden pane.
      persistOffset(element.scrollTop);
    };
  }, [isActive, persistOffset]);

  const restoreScroll = useCallback((): boolean => {
    const element = ref.current;
    if (!element || !isActive || !ready) return false;
    const saved = getScrollTop(scrollKey) ?? lastOffsetRef.current;
    if (saved == null || saved <= 0) return true;
    const maxScroll = Math.max(0, element.scrollHeight - element.clientHeight);
    if (maxScroll < 1) return false;
    const target = Math.min(saved, maxScroll);
    if (Math.abs(element.scrollTop - target) < 1) return true;
    element.scrollTop = target;
    return Math.abs(element.scrollTop - target) < 1;
  }, [getScrollTop, isActive, ready, scrollKey]);

  useLayoutEffect(() => {
    if (!isActive || !ready) return;

    let cancelled = false;
    let frame1 = 0;
    let frame2 = 0;
    let timeout1 = 0;
    let timeout2 = 0;
    let attempts = 0;
    const maxAttempts = 12;

    const tryRestore = () => {
      if (cancelled) return;
      if (restoreScroll() || attempts >= maxAttempts) return;
      attempts += 1;
      frame1 = requestAnimationFrame(tryRestore);
    };

    tryRestore();
    frame2 = requestAnimationFrame(() => {
      tryRestore();
      timeout1 = window.setTimeout(tryRestore, 50);
      timeout2 = window.setTimeout(tryRestore, 150);
    });

    const element = ref.current;
    const observer =
      element && typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => {
            tryRestore();
          })
        : null;
    if (element && observer) observer.observe(element);

    return () => {
      cancelled = true;
      cancelAnimationFrame(frame1);
      cancelAnimationFrame(frame2);
      window.clearTimeout(timeout1);
      window.clearTimeout(timeout2);
      observer?.disconnect();
    };
  }, [isActive, ready, restoreScroll, scrollKey]);

  return { ref, saveScrollNow };
}
