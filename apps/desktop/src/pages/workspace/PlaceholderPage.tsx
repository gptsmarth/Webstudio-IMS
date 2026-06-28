import type { LucideIcon } from 'lucide-react';
import { Construction } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/shell/TopToolbar';

interface PlaceholderPageProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  milestone?: string;
}

export function PlaceholderPage({
  title,
  description,
  icon: Icon = Construction,
  milestone = 'Milestone 3C',
}: PlaceholderPageProps): JSX.Element {
  return (
    <PageContainer>
      <PageHeader title={title} description={description} />
      <div className="app-placeholder-card">
        <div className="app-placeholder-icon-wrap">
          <Icon size={28} aria-hidden style={{ color: 'var(--color-primary-500)' }} />
        </div>
        <h2 className="app-placeholder-title">Module under development</h2>
        <p className="app-placeholder-text">
          This page is a shell placeholder. Business functionality for <strong>{title}</strong> will be implemented in {milestone}.
        </p>
        <div className="app-placeholder-grid">
          <div className="app-placeholder-block skeleton" />
          <div className="app-placeholder-block skeleton" />
          <div className="app-placeholder-block skeleton app-placeholder-block-wide" />
        </div>
      </div>
    </PageContainer>
  );
}
