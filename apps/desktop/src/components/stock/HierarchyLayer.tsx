import type { ReactNode } from 'react';

interface HierarchyLayerProps {
  active: boolean;
  children: ReactNode;
  className?: string;
}

/** Keeps hierarchy panes mounted while inactive so scroll position can be restored. */
export function HierarchyLayer({ active, children, className }: HierarchyLayerProps): JSX.Element {
  return (
    <div
      className={`hierarchy-layer ${active ? 'hierarchy-layer--active' : 'hierarchy-layer--inactive'}${className ? ` ${className}` : ''}`}
      aria-hidden={!active}
    >
      {children}
    </div>
  );
}
