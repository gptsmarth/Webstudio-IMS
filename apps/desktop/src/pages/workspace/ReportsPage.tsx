import { AlertCircle, Play } from 'lucide-react';
import { ReportExportBar } from '../../components/reports/ReportExportBar';
import { ReportFiltersForm } from '../../components/reports/ReportFiltersForm';
import { ReportPreviewTable } from '../../components/reports/ReportPreviewTable';
import { ReportTypeSelector } from '../../components/reports/ReportTypeSelector';
import { ReportWorkflowSteps } from '../../components/reports/ReportWorkflowSteps';
import { useReportBuilder } from '../../hooks/useReportBuilder';
import { canExportReports } from '../../services/PermissionService';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';

export function ReportsPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const canExport = session ? canExportReports(session.permissions) : false;
  const builder = useReportBuilder();

  return (
    <div className="reports-page report-center animate-fade-in">
      <header className="reports-page__header">
        <WorkspacePageBack />
        <div>
          <h1 className="reports-page__title">Report Center</h1>
          <p className="reports-page__subtitle">
            Choose a report type, configure filters, preview results, then export. Exports always match the filtered preview.
          </p>
        </div>
      </header>

      <ReportWorkflowSteps hasPreviewed={builder.hasPreviewed} />

      <div className="report-center__stack">
        <ReportTypeSelector value={builder.reportType} onChange={builder.changeReportType} />

        <ReportFiltersForm
          reportType={builder.reportType}
          filters={builder.filters}
          setFilters={builder.setFilters}
          resetFilters={builder.resetFilters}
          brands={builder.brands}
          locations={builder.locations}
          productModels={builder.productModels}
        />

        <div className="report-center__preview-bar">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={builder.loading}
            onClick={() => void builder.runPreview()}
          >
            <Play size={14} aria-hidden />
            {builder.loading ? 'Loading preview…' : 'Preview results'}
          </button>
          {!builder.hasPreviewed && (
            <p className="report-center__preview-hint">Export is disabled until you preview filtered results.</p>
          )}
        </div>

        {builder.error && (
          <div className="alert alert-danger report-builder__alert">
            <AlertCircle size={14} aria-hidden />
            <span>{builder.error}</span>
          </div>
        )}

        <ReportPreviewTable
          reportType={builder.reportType}
          rows={builder.rows}
          loading={builder.loading}
          hasPreviewed={builder.hasPreviewed}
          summary={builder.summary}
          page={builder.page}
          pageSize={builder.pageSize}
          totalItems={builder.totalItems}
          totalPages={builder.totalPages}
          setPage={builder.setPage}
          sortField={builder.sortField}
          sortDirection={builder.sortDirection}
          toggleSort={builder.toggleSort}
        />

        {canExport && (
          <ReportExportBar
            hasPreviewed={builder.hasPreviewed}
            exporting={builder.exporting}
            totalItems={builder.totalItems}
            onExport={(format) => void builder.exportReport(format)}
          />
        )}
      </div>
    </div>
  );
}
