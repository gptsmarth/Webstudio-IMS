import { FileSpreadsheet, FileText } from 'lucide-react';
import type { ExportFormat } from '../../services/api/ReportService';

interface ReportExportBarProps {
  hasPreviewed: boolean;
  exporting: boolean;
  totalItems: number;
  onExport: (format: ExportFormat) => void;
}

export function ReportExportBar({
  hasPreviewed,
  exporting,
  totalItems,
  onExport,
}: ReportExportBarProps): JSX.Element {
  return (
    <section className={`report-export ${!hasPreviewed ? 'report-export--locked' : ''}`} aria-label="Export options">
      <div className="report-export__copy">
        <h2 className="report-export__title">Export</h2>
        <p className="report-export__hint">
          {hasPreviewed
            ? `Export ${totalItems.toLocaleString()} filtered row${totalItems === 1 ? '' : 's'} as Excel or PDF. CSV support is prepared in the architecture.`
            : 'Preview results before exporting. Exports always use the active filter set shown in the table.'}
        </p>
      </div>
      <div className="report-export__actions">
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={!hasPreviewed || exporting}
          onClick={() => onExport('xlsx')}
        >
          <FileSpreadsheet size={14} aria-hidden />
          {exporting ? 'Exporting…' : 'Excel'}
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={!hasPreviewed || exporting}
          onClick={() => onExport('pdf')}
        >
          <FileText size={14} aria-hidden />
          PDF
        </button>
        <button type="button" className="btn btn-ghost btn-sm" disabled title="CSV export — architecture ready">
          CSV
        </button>
      </div>
    </section>
  );
}
