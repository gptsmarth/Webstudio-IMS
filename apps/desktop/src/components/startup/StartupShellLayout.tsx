import type { ReactNode } from 'react';

interface StartupShellLayoutProps {
  brand: ReactNode;
  children: ReactNode;
}

export function StartupShellLayout({ brand, children }: StartupShellLayoutProps): JSX.Element {
  return (
    <div className="startup-layout animate-fade-in">
      <aside className="startup-layout__brand" aria-hidden="true">
        {brand}
      </aside>
      <main className="startup-layout__main">
        <div className="startup-layout__main-inner">{children}</div>
      </main>
    </div>
  );
}
