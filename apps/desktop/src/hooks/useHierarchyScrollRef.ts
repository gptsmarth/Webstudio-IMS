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

  const saveScrollNow = useCallback(() => {
    const element = ref.current;
    if (!element) return;
    const offset = element.scrollTop;
    lastOffsetRef.current = offset;
    setScrollTop(scrollKey, offset);
  }, [scrollKey, setScrollTop]);

  useEffect(() => {
    const element = ref.current;
    if (!element || !isActive) return;

    const save = () => {
      lastOffsetRef.current = element.scrollTop;
      setScrollTop(scrollKey, element.scrollTop);
    };
    save();
    element.addEventListener('scroll', save, { passive: true });
    return () => {
      element.removeEventListener('scroll', save);
      setScrollTop(scrollKey, lastOffsetRef.current);
    };
  }, [isActive, scrollKey, setScrollTop]);

  const restoreScroll = useCallback(() => {
    const element = ref.current;
    if (!element || !isActive || !ready) return;
    const saved = getScrollTop(scrollKey);
    if (saved == null || saved <= 0) return;
    if (Math.abs(element.scrollTop - saved) < 1) return;
    element.scrollTop = saved;
  }, [getScrollTop, isActive, ready, scrollKey]);

  useLayoutEffect(() => {
    if (!isActive || !ready) return;
    restoreScroll();
    let frame1 = 0;
    let frame2 = 0;
    frame1 = requestAnimationFrame(() => {
      restoreScroll();
      frame2 = requestAnimationFrame(restoreScroll);
    });
    return () => {
      cancelAnimationFrame(frame1);
      cancelAnimationFrame(frame2);
    };
  }, [isActive, ready, restoreScroll, scrollKey]);

  return { ref, saveScrollNow };
}
