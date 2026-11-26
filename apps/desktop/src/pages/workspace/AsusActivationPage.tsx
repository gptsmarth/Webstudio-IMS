import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { CalendarDays, Download, FileUp, RefreshCw, TriangleAlert } from 'lucide-react';
import { PageContainer, PageHeader } from '../../components/shell/TopToolbar';
import { parseApiError } from '../../lib/apiError';
import { canWriteSettings } from '../../lib/settings';
import {
  AsusActivationService,
  type ActivationClaim,
  type ActivationDashboard,
  type ActivationScheme,
  type ClaimFilter,
  type ReceiptPreview,
} from '../../services/api/AsusActivationService';
import { useAuthStore } from '../../store';
import {
  ActivationDialog,
  ActivationHistory,
  ActivationSchemeEditor,
} from './ActivationSchemeEditor';
import './asusActivation.css';

const moneyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
});

const claimTabs: { id: ClaimFilter; label: string }[] = [
  { id: 'pending', label: 'Pending Claims' },
  { id: 'discrepancy', label: 'Discrepancies' },
  { id: 'received', label: 'Received' },
  { id: 'all', label: 'All Claims' },
];

const receiptOutcome = {
  receive: 'Will mark received',
  discrepancy: 'Amount mismatch',
  unmatched: 'No matching claim',
  ambiguous: 'Multiple possible matches',
  duplicate: 'Duplicate',
  already_recorded: 'Receipt already recorded',
};

const PAGE_SIZE = 30;

function localMonth() {
  return new Date(Date.now() + 330 * 60_000).toISOString().slice(0, 7);
}

function monthLabel(month: string) {
  return new Intl.DateTimeFormat('en-IN', {
    year: 'numeric',
    month: 'long',
    timeZone: 'UTC',
  }).format(new Date(month + '-01T00:00:00Z'));
}

function rupees(value: string | null | undefined) {
  return value == null ? '—' : moneyFormatter.format(Number(value));
}

type ClaimDialog = { claim: ActivationClaim; action: 'receipt' | 'expected' };
function Pager({
  page,
  size,
  onChange,
}: {
  page: number;
  size: number;
  onChange: (page: number) => void;
}) {
  if (size <= PAGE_SIZE) return null;
  return (
    <div className="activation__pager">
      <button
        className="btn btn-ghost btn-sm"
        disabled={page === 0}
        onClick={() => onChange(page - 1)}
      >
        Previous
      </button>
      <span>
        {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, size)} of {size}
      </span>
      <button
        className="btn btn-ghost btn-sm"
        disabled={(page + 1) * PAGE_SIZE >= size}
        onClick={() => onChange(page + 1)}
      >
        Next
      </button>
    </div>
  );
}

function ConfirmReceiptPreview({
  preview,
  busy,
  onCancel,
  onConfirm,
}: {
  preview: ReceiptPreview;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const [page, setPage] = useState(0);
  const matched = preview.counts.receive ?? 0;
  const flagged = preview.counts.discrepancy ?? 0;
  const skipped = preview.rows.length - matched - flagged;
  return (
    <section className="card activation__panel" aria-label="Receipt preview">
      <div className="activation__toolbar">
        <div>
          <h2>Review CN receipts</h2>
          <p>{preview.filename}</p>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={onCancel}>
          Close preview
        </button>
      </div>
      <div className="activation__summary">
        <span>
          <strong>{matched}</strong> will move to Received · {rupees(preview.received_total)}
        </span>
        <span>
          <strong>{flagged}</strong> amount mismatches · {rupees(preview.discrepancy_total)}
        </span>
        <span>
          <strong>{skipped}</strong> rows will be skipped
        </span>
      </div>
      <div className="activation__table-wrap" tabIndex={0} aria-label="Credit note workbook rows">
        <table className="activation__table">
          <thead>
            <tr>
              <th>Model / IMEI</th>
              <th>Invoice / scheme dates</th>
              <th>Expected CN</th>
              <th>CN Amt</th>
              <th>Variance</th>
              <th>Release date</th>
              <th>Outcome</th>
            </tr>
          </thead>
          <tbody>
            {preview.rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).map((row) => (
              <tr key={row.sheet + ':' + row.row}>
                <td>
                  <strong>{row.model}</strong>
                  <small>
                    {row.serial} · row {row.row}
                  </small>
                </td>
                <td>
                  {row.invoice ?? '—'}
                  {row.date_from && (
                    <small>
                      {row.date_from} to {row.date_to}
                    </small>
                  )}
                </td>
                <td>{rupees(row.expected_amount)}</td>
                <td>{rupees(row.amount)}</td>
                <td>{rupees(row.variance)}</td>
                <td>{row.release_date}</td>
                <td>
                  <span className="activation__badge" data-status={row.outcome}>
                    {receiptOutcome[row.outcome]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pager page={page} size={preview.rows.length} onChange={setPage} />
      <div className="activation__toolbar">
        <p>All amounts in this preview exclude GST.</p>
        <button
          type="button"
          className="btn btn-primary"
          disabled={busy || matched + flagged === 0}
          onClick={onConfirm}
        >
          {busy ? 'Confirming…' : 'Yes, confirm receipts'}
        </button>
      </div>
    </section>
  );
}

function ClaimTable({
  claims,
  canWrite,
  selectClaim,
}: {
  claims: ActivationClaim[];
  canWrite: boolean;
  selectClaim: (value: ClaimDialog) => void;
}) {
  return (
    <div
      className="activation__table-wrap activation__claims-scroll"
      tabIndex={0}
      aria-label="Scrollable ASUS activation claims"
    >
      <table className="activation__table">
        <thead>
          <tr>
            <th>Model / serial</th>
            <th>Invoice / customer</th>
            <th>Activation dates</th>
            <th>Unit price incl. GST</th>
            <th>NOV T2 DBP</th>
            <th>Supported SRP</th>
            <th>Supported DBP</th>
            <th>Support on SRP</th>
            <th className="activation__expected">CN/Unit (expected)</th>
            <th>Received CN</th>
            <th>Receipt / variance</th>
            {canWrite && <th>Action</th>}
          </tr>
        </thead>
        <tbody>
          {claims.map((claim) => (
            <tr key={claim.sale_id}>
              <td>
                <strong>{claim.model}</strong>
                <small>{claim.serial}</small>
                {claim.cancelled && <small>Sale cancelled</small>}
              </td>
              <td>
                <strong>{claim.invoice}</strong>
                <small>{claim.sold_on}</small>
                {claim.customer && <small>{claim.customer}</small>}
              </td>
              <td>
                {claim.date_from} to {claim.date_to}
                <small title={claim.scheme_filename}>
                  {claim.scheme_code ?? claim.source_sheet ?? claim.scheme_filename}
                </small>
                {claim.scheme_applies === false && (
                  <small>Original receipt period · scheme changed</small>
                )}
              </td>
              <td>
                {rupees(claim.unit_price)}
                {claim.unit_price === null && <small>Price unavailable</small>}
              </td>
              <td className="activation__money">{rupees(claim.nov_t2_dbp)}</td>
              <td className="activation__money">{rupees(claim.supported_srp)}</td>
              <td className="activation__money">{rupees(claim.supported_dbp)}</td>
              <td className="activation__money">{rupees(claim.support_on_srp)}</td>
              <td className="activation__expected activation__money">
                {rupees(claim.expected_amount)}
                {claim.expected_note && <small title={claim.expected_note}>Corrected CN</small>}
              </td>
              <td>{rupees(claim.received_amount)}</td>
              <td>
                <span className="activation__badge" data-status={claim.status}>
                  {claim.status === 'discrepancy'
                    ? 'Amount mismatch'
                    : claim.status === 'pending'
                      ? 'Pending'
                      : 'Received'}
                </span>
                {claim.variance && Number(claim.variance) !== 0 && (
                  <small>Variance {rupees(claim.variance)}</small>
                )}
                {claim.release_date && <small>Released {claim.release_date}</small>}
                {claim.receipt_filename && (
                  <small title={claim.receipt_filename}>{claim.receipt_filename}</small>
                )}
                {claim.receipt_source === 'manual' && <small>Entered manually</small>}
                {claim.record_note && <small>{claim.record_note}</small>}
                {claim.resolution_note && (
                  <small>
                    {claim.resolution_current === false ? 'Previous resolution' : 'Resolved'} ·{' '}
                    {claim.resolution_note}
                  </small>
                )}
              </td>
              {canWrite && (
                <td className="activation__claim-actions">
                  {!claim.cancelled && claim.status !== 'received' && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => selectClaim({ claim, action: 'receipt' })}
                    >
                      {claim.status === 'pending' ? 'Mark received' : 'Resolve'}
                    </button>
                  )}
                  {!claim.cancelled && claim.scheme_applies !== false && (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => selectClaim({ claim, action: 'expected' })}
                    >
                      Edit expected CN
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ManualReceiptForm({
  claim,
  action,
  error,
  allowModelCorrection,
  busy,
  onClose,
  onSubmit,
}: {
  claim: ActivationClaim;
  action: ClaimDialog['action'];
  error: string;
  allowModelCorrection: boolean;
  busy: boolean;
  onClose: () => void;
  onSubmit: (amount: string | null, note: string, scope: 'sale' | 'model') => void;
}) {
  const editing = action === 'expected';
  const [amount, setAmount] = useState(editing ? claim.expected_amount : '');
  const [note, setNote] = useState('');
  const [scope, setScope] = useState<'sale' | 'model'>('sale');
  const [clear, setClear] = useState(false);
  const resolving = !editing && claim.status === 'discrepancy';
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(clear ? null : amount.trim(), note.trim(), scope);
  }
  return (
    <ActivationDialog
      title={editing ? 'Edit expected CN' : resolving ? 'Resolve discrepancy' : 'Mark received'}
      busy={busy}
      onClose={onClose}
    >
      <form className="activation__panel" onSubmit={submit}>
        <p>
          {claim.model} · {claim.serial} · {claim.invoice}
        </p>
        <p>
          Expected {rupees(claim.expected_amount)}
          {resolving &&
            ' · Received ' +
              rupees(claim.received_amount) +
              ' · Variance ' +
              rupees(claim.variance)}{' '}
          before GST
        </p>
        {error && (
          <p className="alert alert-danger" role="alert">
            {error}
          </p>
        )}
        {editing && allowModelCorrection && (
          <label>
            <span className="form-label">Apply correction to</span>
            <select
              className="input"
              value={scope}
              disabled={busy}
              onChange={(event) => {
                setScope(event.target.value as 'sale' | 'model');
                setClear(false);
              }}
            >
              <option value="sale">This sale only</option>
              <option value="model">This model throughout the scheme</option>
            </select>
          </label>
        )}
        {editing && scope === 'model' && (
          <p>
            Applies to qualifying sales of this model in the scheme. Individual sale corrections
            take precedence.
          </p>
        )}
        {editing && scope === 'sale' && claim.manual_expected && (
          <label className="activation__checkbox">
            <input
              type="checkbox"
              checked={clear}
              disabled={busy}
              onChange={(event) => setClear(event.target.checked)}
            />
            Restore scheme amount ({rupees(claim.scheme_expected)})
          </label>
        )}
        <div className="activation__fields">
          {!resolving && !clear && (
            <label>
              <span className="form-label">
                {editing ? 'Corrected CN excluding GST' : 'Received CN excluding GST'}
              </span>
              <input
                type="number"
                className="input"
                min="0"
                step="0.01"
                required
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                disabled={busy}
              />
            </label>
          )}
          <label>
            <span className="form-label">
              {resolving ? 'Resolution note' : editing ? 'Reason for correction' : 'Note'}
            </span>
            <input
              className="input"
              maxLength={2000}
              required={resolving || editing}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={busy}
            />
          </label>
        </div>
        <div className="activation__dialog-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={busy || ((resolving || editing) && !note.trim())}
          >
            {resolving ? 'Resolve and mark received' : 'Save'}
          </button>
        </div>
      </form>
    </ActivationDialog>
  );
}

export function AsusActivationPage(): JSX.Element {
  const permissions = useAuthStore((state) => state.session?.permissions);
  const canWrite = Boolean(permissions && canWriteSettings(permissions));
  const [month, setMonth] = useState(localMonth);
  const [searchText, setSearchText] = useState('');
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState<ClaimFilter>('pending');
  const [page, setPage] = useState(0);
  const [dashboard, setDashboard] = useState<ActivationDashboard>();
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [schemeFile, setSchemeFile] = useState<File>();
  const [receiptFile, setReceiptFile] = useState<File>();
  const [preview, setPreview] = useState<ReceiptPreview>();
  const [selected, setSelected] = useState<ClaimDialog>();
  const [editedScheme, setEditedScheme] = useState<ActivationScheme>();
  const [schemeHistoryOpen, setSchemeHistoryOpen] = useState(false);
  const schemeInput = useRef<HTMLInputElement>(null);
  const receiptInput = useRef<HTMLInputElement>(null);
  const requestSequence = useRef(0);
  const refresh = useCallback(async () => {
    const request = ++requestSequence.current;
    try {
      const result = await AsusActivationService.dashboard(month, search);
      if (request !== requestSequence.current) return;
      setDashboard(result);
      setLoadError('');
    } catch (err) {
      if (request === requestSequence.current)
        setLoadError(parseApiError(err, 'Could not load activation claims.'));
    }
  }, [month, search]);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchText.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [searchText]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => {
      window.clearInterval(timer);
      requestSequence.current++;
    };
  }, [refresh]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await action();
    } catch (err) {
      setError(parseApiError(err, 'The activation action failed.'));
    } finally {
      setBusy(false);
    }
  }

  function uploadScheme(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!schemeFile || !start || !end || start > end) return;
    void run(async () => {
      const scheme = await AsusActivationService.uploadScheme(schemeFile, start, end);
      setMessage(
        'Imported ' +
          scheme.rule_count +
          ' model rates for ' +
          scheme.date_from +
          ' to ' +
          scheme.date_to +
          '. Matched ' +
          scheme.matched_sale_count +
          ' recorded ' +
          (scheme.matched_sale_count === 1 ? 'sale.' : 'sales.'),
      );
      setSchemeFile(undefined);
      if (schemeInput.current) schemeInput.current.value = '';
      setTab('pending');
      setPage(0);
      setSelected(undefined);
      setSearchText('');
      setSearch('');
      const schemeMonth = scheme.date_from.slice(0, 7);
      if (schemeMonth === month) await refresh();
      else setMonth(schemeMonth);
    });
  }

  function importReceipts(confirm: boolean) {
    if (!receiptFile || (confirm && !preview)) return;
    void run(async () => {
      const result = await AsusActivationService.importReceipts(
        receiptFile,
        confirm ? preview?.preview_id : undefined,
      );
      if (!confirm) {
        setPreview(result);
        return;
      }
      setPreview(undefined);
      setReceiptFile(undefined);
      if (receiptInput.current) receiptInput.current.value = '';
      setMessage(
        'Marked ' +
          (result.counts.receive ?? 0) +
          ' received and sent ' +
          (result.counts.discrepancy ?? 0) +
          ' amount mismatches to Discrepancies.',
      );
      await refresh();
    });
  }

  const data =
    dashboard?.month === month && (dashboard.search ?? '') === search ? dashboard : undefined;
  const filtered = data?.claims.filter((claim) => tab === 'all' || claim.status === tab) ?? [];
  const monthSchemes = data?.schemes.filter(
    (scheme) => scheme.date_from.slice(0, 7) <= month && scheme.date_to.slice(0, 7) >= month,
  );
  const currentPage = Math.min(page, Math.max(0, Math.ceil(filtered.length / PAGE_SIZE) - 1));
  const currentTab = claimTabs.find((value) => value.id === tab)?.label ?? 'All Claims';

  return (
    <PageContainer>
      <div className="activation">
        <PageHeader
          title="Asus Activation"
          description="Track expected ASUS credit notes, reconcile receipts, and export by invoice month."
          actions={
            <button
              type="button"
              className="btn btn-secondary"
              disabled={!dashboard}
              onClick={() => setSchemeHistoryOpen(true)}
            >
              {canWrite ? 'Manage schemes' : 'Scheme history'}
            </button>
          }
        />
        {data &&
          (data.active_scheme ? (
            <div className="activation__coverage">
              <CalendarDays size={17} aria-hidden />
              <span>
                Active scheme · {data.active_scheme.date_from} to {data.active_scheme.date_to}
              </span>
              {canWrite && data.active_scheme.editable && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setEditedScheme(data.active_scheme ?? undefined)}
                >
                  Manage active scheme
                </button>
              )}
            </div>
          ) : (
            <div className="alert alert-warning activation__coverage" role="status">
              <TriangleAlert size={17} aria-hidden />
              <span>
                No activation scheme covers today.{' '}
                {data.latest_scheme
                  ? 'Latest uploaded range ' +
                    data.latest_scheme.date_from +
                    ' to ' +
                    data.latest_scheme.date_to +
                    '. '
                  : ''}
                {canWrite
                  ? 'Upload the workbook for the missing dates.'
                  : 'Ask an administrator to upload the workbook.'}
              </span>
            </div>
          ))}
        {error && (
          <p className="alert alert-danger" role="alert">
            {error}
          </p>
        )}
        {message && (
          <p className="alert alert-success" role="status">
            {message}
          </p>
        )}
        {canWrite && (
          <div className="activation__uploads">
            <form className="card activation__panel" onSubmit={uploadScheme}>
              <div>
                <h2>Upload activation scheme</h2>
                <p>
                  Choose the inclusive invoice dates. Sales already recorded within those dates are
                  picked up automatically.
                </p>
              </div>
              <fieldset className="activation__fields" disabled={busy}>
                <label>
                  <span className="form-label">From date</span>
                  <input
                    type="date"
                    className="input"
                    required
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                  />
                </label>
                <label>
                  <span className="form-label">To date</span>
                  <input
                    type="date"
                    className="input"
                    min={start || undefined}
                    required
                    value={end}
                    onChange={(e) => setEnd(e.target.value)}
                  />
                </label>
              </fieldset>
              <label>
                <span className="form-label">Activation workbook</span>
                <input
                  ref={schemeInput}
                  type="file"
                  accept=".xlsx"
                  disabled={busy}
                  required
                  onChange={(e) => setSchemeFile(e.target.files?.[0])}
                />
              </label>
              <div>
                <button
                  type="submit"
                  className="btn btn-secondary"
                  disabled={busy || !schemeFile || !start || !end || start > end}
                >
                  <FileUp size={16} aria-hidden />
                  Upload scheme
                </button>
              </div>
            </form>
            <form
              className="card activation__panel"
              onSubmit={(event) => {
                event.preventDefault();
                importReceipts(false);
              }}
            >
              <div>
                <h2>Upload received CN</h2>
                <p>
                  Preview which claims will be marked received and which amounts need review. Uses
                  CN Amt before GST.
                </p>
              </div>
              <label>
                <span className="form-label">ASUS CN workbook</span>
                <input
                  ref={receiptInput}
                  type="file"
                  accept=".xlsx"
                  disabled={busy}
                  required
                  onChange={(e) => {
                    setReceiptFile(e.target.files?.[0]);
                    setPreview(undefined);
                  }}
                />
              </label>
              <div>
                <button type="submit" className="btn btn-secondary" disabled={busy || !receiptFile}>
                  <FileUp size={16} aria-hidden />
                  Preview receipts
                </button>
              </div>
            </form>
          </div>
        )}
        {preview && canWrite && (
          <ConfirmReceiptPreview
            key={preview.preview_id}
            preview={preview}
            busy={busy}
            onCancel={() => setPreview(undefined)}
            onConfirm={() => importReceipts(true)}
          />
        )}
        {selected && canWrite && (
          <ManualReceiptForm
            key={selected.claim.sale_id + selected.action}
            claim={selected.claim}
            action={selected.action}
            error={error}
            allowModelCorrection={Boolean(
              data?.schemes.some(
                (scheme) => scheme.id === selected.claim.scheme_id && scheme.editable,
              ),
            )}
            busy={busy}
            onClose={() => {
              setSelected(undefined);
              setError('');
            }}
            onSubmit={(amount, note, scope) => {
              void run(async () => {
                if (selected.action === 'expected') {
                  await AsusActivationService.correctExpected(
                    selected.claim.sale_id,
                    amount,
                    note,
                    scope,
                  );
                  setMessage('Expected CN updated. Any recorded receipt was checked again.');
                  setSelected(undefined);
                  await refresh();
                  return;
                }
                const saved = await AsusActivationService.updateClaim(
                  selected.claim.sale_id,
                  selected.claim.status === 'pending' ? 'record' : 'resolve',
                  amount ?? '',
                  note,
                );
                setMessage(
                  saved.status === 'discrepancy'
                    ? 'Receipt recorded. The amount mismatch is under Discrepancies.'
                    : 'Claim marked received.',
                );
                setSelected(undefined);
                await refresh();
              });
            }}
          />
        )}
        {editedScheme && canWrite && (
          <ActivationSchemeEditor
            key={editedScheme.id}
            scheme={editedScheme}
            onClose={() => setEditedScheme(undefined)}
            onApplied={(scheme) => {
              setEditedScheme(undefined);
              setMessage(
                'Scheme updated. Matched ' + scheme.matched_sale_count + ' qualifying sales.',
              );
              setPage(0);
              void refresh();
            }}
          />
        )}
        <section className="card activation__panel" aria-label="Monthly activation claims">
          <div className="activation__toolbar">
            <div>
              <h2>{search ? 'Claim search results' : monthLabel(month)}</h2>
              <p>
                {search ? 'All invoice months' : 'Grouped by invoice month'} · CN amounts exclude
                GST
              </p>
              {!search && monthSchemes && (
                <p>
                  {monthSchemes.length
                    ? monthSchemes
                        .map((scheme) => scheme.date_from + ' to ' + scheme.date_to)
                        .join(' · ')
                    : 'This month has no uploaded scheme.'}
                </p>
              )}
            </div>
            <div className="activation__actions">
              <label>
                <span className="form-label">Search all months</span>
                <input
                  type="search"
                  className="input"
                  placeholder="Serial / IMEI, invoice, or model"
                  maxLength={160}
                  value={searchText}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (!searchText.trim() && value.trim()) setTab('all');
                    setSearchText(value);
                    setPage(0);
                  }}
                />
              </label>
              <label>
                <span className="form-label">Invoice month</span>
                <input
                  type="month"
                  className="input"
                  value={month}
                  disabled={Boolean(searchText.trim())}
                  onChange={(e) => {
                    if (/^\d{4}-\d{2}$/.test(e.target.value)) {
                      setMonth(e.target.value);
                      setPage(0);
                      setSelected(undefined);
                    }
                  }}
                />
              </label>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => void refresh()}
                aria-label="Refresh activation claims"
              >
                <RefreshCw size={16} aria-hidden />
              </button>
            </div>
          </div>
          {data && (
            <div className="activation__summary">
              <span>
                Expected CN <strong>{rupees(data.totals.expected)}</strong>
              </span>
              <span>
                Pending CN <strong>{rupees(data.totals.pending)}</strong>
              </span>
              <span>
                Recorded CN <strong>{rupees(data.totals.received)}</strong>
              </span>
            </div>
          )}
          <div className="activation__toolbar">
            <div className="activation__tabs" aria-label="Claim status">
              {claimTabs.map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  className={'btn btn-sm ' + (tab === id ? 'btn-primary' : 'btn-ghost')}
                  aria-pressed={tab === id}
                  onClick={() => {
                    setTab(id);
                    setPage(0);
                  }}
                >
                  {label}
                  {data
                    ? ' (' + (id === 'all' ? data.claims.length : (data.counts[id] ?? 0)) + ')'
                    : ''}
                </button>
              ))}
            </div>
            <div className="activation__actions">
              {!search && (
                <button
                  className="btn btn-secondary btn-sm"
                  type="button"
                  disabled={busy || !data}
                  title={'Download ' + currentTab + ' for ' + monthLabel(month)}
                  onClick={() => void run(() => AsusActivationService.download(month, tab))}
                >
                  <Download size={15} aria-hidden />
                  Month Excel
                </button>
              )}
              <button
                className="btn btn-secondary btn-sm"
                type="button"
                disabled={busy || !data}
                title={'Download ' + currentTab + ' across all months'}
                onClick={() =>
                  void run(() => AsusActivationService.download(undefined, tab, search))
                }
              >
                <Download size={15} aria-hidden />
                {search ? 'Search results Excel' : 'All months Excel'}
              </button>
            </div>
          </div>
          {loadError && (
            <p role="alert" className="alert alert-danger">
              {loadError}
            </p>
          )}
          {!data && !loadError && <p role="status">Loading activation claims…</p>}
          {data &&
            (filtered.length ? (
              <ClaimTable
                claims={filtered.slice(currentPage * PAGE_SIZE, (currentPage + 1) * PAGE_SIZE)}
                canWrite={canWrite}
                selectClaim={(claim) => {
                  setError('');
                  setSelected(claim);
                }}
              />
            ) : (
              <div className="activation__empty">
                <strong>
                  {search
                    ? 'No matching ' + currentTab.toLowerCase() + '.'
                    : 'No ' + currentTab.toLowerCase() + ' for ' + monthLabel(month) + '.'}
                </strong>
                {!search && (
                  <p>
                    Eligible ASUS sales appear after a scheme covering their invoice date is
                    uploaded.
                  </p>
                )}
              </div>
            ))}
          <Pager page={currentPage} size={filtered.length} onChange={setPage} />
        </section>
        {dashboard && schemeHistoryOpen && !editedScheme && (
          <ActivationDialog
            title="Activation scheme history"
            onClose={() => setSchemeHistoryOpen(false)}
            busy={false}
            side
          >
            <ActivationHistory
              schemes={dashboard.schemes}
              activeId={dashboard.active_scheme?.id}
              onManage={
                canWrite
                  ? (scheme) => {
                      setError('');
                      setMessage('');
                      setEditedScheme(scheme);
                    }
                  : undefined
              }
            />
          </ActivationDialog>
        )}
      </div>
    </PageContainer>
  );
}
