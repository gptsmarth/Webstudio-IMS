import { ChevronRight } from 'lucide-react';
import { PageBackButton } from '../shell/PageBackButton';

interface HierarchyBreadcrumbProps {
  rootLabel: string;
  brandName?: string | null;
  modelLabel?: string | null;
  onRoot: () => void;
  onBrand?: () => void;
  onBack?: () => void;
  backLabel?: string;
  /** When true, only the back button is shown (no All brands > Acer trail). */
  minimal?: boolean;
}

export function HierarchyBreadcrumb({
  rootLabel,
  brandName,
  modelLabel,
  onRoot,
  onBrand,
  onBack,
  backLabel,
  minimal = false,
}: HierarchyBreadcrumbProps): JSX.Element | null {
  const showBack = Boolean(onBack && (brandName || modelLabel));

  if (minimal && !showBack) return null;

  return (
    <div className="hierarchy-breadcrumb-row">
      {showBack && onBack && (
        <PageBackButton label={backLabel ?? 'Back'} onClick={onBack} />
      )}
      {!minimal && (
        <nav className="hierarchy-breadcrumb" aria-label="Breadcrumb">
          <button type="button" className="hierarchy-breadcrumb__link" onClick={onRoot}>
            {rootLabel}
          </button>
          {brandName && (
            <>
              <ChevronRight size={14} aria-hidden />
              <button
                type="button"
                className="hierarchy-breadcrumb__link"
                onClick={onBrand}
                disabled={!onBrand}
              >
                {brandName}
              </button>
            </>
          )}
          {modelLabel && (
            <>
              <ChevronRight size={14} aria-hidden />
              <span className="hierarchy-breadcrumb__current">{modelLabel}</span>
            </>
          )}
        </nav>
      )}
    </div>
  );
}
