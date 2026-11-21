import { useState, type FormEvent } from 'react';
import { Download } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/shell/TopToolbar';
import { parseApiError } from '../../lib/apiError';
import { ReportService, type AsusWeeklyProducts } from '../../services/api/ReportService';

function lastCompletedWeek() {
  // Start with today's Indian calendar date, then do the calendar math in UTC.
  const today = new Date(Date.now() + 5.5 * 60 * 60 * 1000);
  const currentTuesday = new Date(today);
  currentTuesday.setUTCDate(today.getUTCDate() - ((today.getUTCDay() + 5) % 7));
  const from = new Date(currentTuesday);
  const to = new Date(currentTuesday);
  from.setUTCDate(from.getUTCDate() - 7);
  to.setUTCDate(to.getUTCDate() - 1);
  return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) };
}

export function AsusWeeklyReportPage(): JSX.Element {
  const [dates, setDates] = useState(lastCompletedWeek);
  const [products, setProducts] = useState<AsusWeeklyProducts>('laptops');
  const [downloading, setDownloading] = useState(false);
  const [downloadStarted, setDownloadStarted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const invalidRange = Boolean(dates.from && dates.to && dates.from > dates.to);

  async function download(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!dates.from || !dates.to || invalidRange || downloading) return;
    setDownloading(true);
    setDownloadStarted(false);
    setError(null);
    try {
      await ReportService.downloadAsusWeeklyReport({
        date_from: dates.from,
        date_to: dates.to,
        products,
      });
      setDownloadStarted(true);
    } catch (err) {
      setError(parseApiError(err, 'Could not download the ASUS weekly report.'));
    } finally {
      setDownloading(false);
    }
  }

  return (
    <PageContainer>
      <PageHeader
        title="ASUS Weekly Report"
        description="Download the ASUS sell-out workbook for a date range."
      />
      <form
        className="report-builder__filters asus-weekly-report"
        onSubmit={(event) => void download(event)}
      >
        <fieldset disabled={downloading} className="report-builder__filters-grid">
          <label>
            <span className="form-label">From date</span>
            <input
              className="input"
              type="date"
              required
              value={dates.from}
              onChange={(event) => {
                setDates({ ...dates, from: event.target.value });
                setDownloadStarted(false);
                setError(null);
              }}
            />
          </label>
          <label>
            <span className="form-label">To date</span>
            <input
              className="input"
              type="date"
              required
              value={dates.to}
              onChange={(event) => {
                setDates({ ...dates, to: event.target.value });
                setDownloadStarted(false);
                setError(null);
              }}
            />
          </label>
          <label>
            <span className="form-label">Products</span>
            <select
              className="input"
              value={products}
              onChange={(event) => {
                setProducts(event.target.value as AsusWeeklyProducts);
                setDownloadStarted(false);
                setError(null);
              }}
            >
              <option value="laptops">Laptops only</option>
              <option value="accessories">Accessories only</option>
              <option value="both">Laptops and accessories</option>
            </select>
          </label>
        </fieldset>
        <div className="report-builder__filters-actions">
          <button type="submit" className="btn btn-primary" disabled={downloading || invalidRange}>
            <Download size={16} aria-hidden />
            {downloading ? 'Preparing Excel…' : 'Download Excel'}
          </button>
        </div>
        {(invalidRange || error) && (
          <p className="alert alert-danger" role="alert">
            {invalidRange ? 'From date must be on or before To date.' : error}
          </p>
        )}
        {downloadStarted && (
          <p className="alert alert-success" role="status">
            Excel download started.
          </p>
        )}
      </form>
    </PageContainer>
  );
}
