import { useEffect, useLayoutEffect, useRef } from 'react';

/**
 * Preserves scroll position for hierarchy list panes (brands / models) when
 * drilling into detail and navigating back.
 */
export function useHierarchyScrollRef(
  scrollKey: string,
  isActive: boolean,
  getScrollTop: (key: string) => number | undefined,
  setScrollTop: (key: string, value: number) => void,
) {
  const ref = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    if (!isActive) return;
    const element = ref.current;
    if (!element) return;
    const saved = getScrollTop(scrollKey);
    if (saved != null && saved > 0) {
      element.scrollTop = saved;
    }
  }, [getScrollTop, isActive, scrollKey]);

  useEffect(() => {
    const element = ref.current;
    if (!element || !isActive) return;

    const save = () => setScrollTop(scrollKey, element.scrollTop);
    element.addEventListener('scroll', save, { passive: true });
    return () => {
      element.removeEventListener('scroll', save);
      save();
    };
  }, [isActive, scrollKey, setScrollTop]);

  return ref;
}
