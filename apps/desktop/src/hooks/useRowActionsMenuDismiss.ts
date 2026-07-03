import { useEffect, type RefObject } from 'react';

/** Close row action menus on Escape and outside click (deferred capture phase). */
export function useRowActionsMenuDismiss(
  menuRef: RefObject<HTMLElement | null>,
  onClose: () => void,
): void {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    const onClickOutside = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) onClose();
    };

    window.addEventListener('keydown', onKeyDown);
    const timer = window.setTimeout(() => {
      document.addEventListener('click', onClickOutside, true);
    }, 0);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('click', onClickOutside, true);
    };
  }, [menuRef, onClose]);
}

export function rowMenuPosition(
  anchorRect: DOMRect,
  menuHeight = 280,
): { top: number; left: number } {
  return {
    top: Math.min(anchorRect.bottom + 4, window.innerHeight - menuHeight),
    left: Math.min(anchorRect.left, window.innerWidth - 220),
  };
}
