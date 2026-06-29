import { useEffect } from 'react';
import { createPortal } from 'react-dom';

interface ModalPortalProps {
  children: React.ReactNode;
}

/** Renders modals on document.body so fixed overlays are not clipped by scroll containers. */
export function ModalPortal({ children }: ModalPortalProps): JSX.Element | null {
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  return createPortal(children, document.body);
}
