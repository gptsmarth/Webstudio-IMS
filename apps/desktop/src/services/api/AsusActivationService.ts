import { triggerBlobDownload } from '../../lib/downloadBlob';
import { ApiClientProvider } from './ApiClientProvider';

export type ClaimStatus = 'pending' | 'received' | 'discrepancy';
export type ClaimFilter = ClaimStatus | 'all';

export interface ActivationScheme {
  id: string;
  date_from: string;
  date_to: string;
  filename: string;
  rule_count: number;
  editable: boolean;
  history: SchemeChange[];
}

export type SchemeImport = ActivationScheme & { matched_sale_count: number };
export type SchemeEditMode = 'dates' | 'replace' | 'supplement';
export interface SchemeChange {
  mode: SchemeEditMode | 'upload' | 'model_cn';
  filename: string;
  date_from: string;
  date_to: string;
  changed_at: string;
  model?: string;
  amount?: string;
  note?: string;
  choices?: Record<string, RateDecision>;
}

interface WorkbookRate {
  cn: string;
  dbp?: string | null;
  srp?: string | null;
  supported_dbp?: string | null;
  support_on_srp?: string | null;
  filename?: string;
}

export interface RateDecision {
  use: 'existing' | 'incoming';
  date_from?: string;
  date_to?: string;
}

export interface SchemeEditPreview {
  preview_id: string;
  model_count: number;
  added_rate_count: number;
  conflicts: {
    model: string;
    incoming: WorkbookRate;
    existing: { date_from: string; date_to: string; rate: WorkbookRate }[];
  }[];
}

export interface ActivationClaim {
  sale_id: number;
  sold_on: string;
  invoice: string;
  customer: string | null;
  serial: string;
  model: string;
  unit_price: string | null;
  nov_t2_dbp: string | null;
  supported_srp: string | null;
  supported_dbp: string | null;
  support_on_srp: string | null;
  date_from: string;
  date_to: string;
  scheme_code: string | null;
  scheme_filename: string;
  source_sheet: string | null;
  scheme_id: string;
  scheme_applies: boolean;
  program_period: string | null;
  status: ClaimStatus;
  cancelled: boolean;
  expected_amount: string;
  scheme_expected: string | null;
  original_expected: string | null;
  manual_expected: boolean;
  expected_note: string | null;
  received_amount: string | null;
  variance: string | null;
  receipt_source: 'manual' | 'excel' | null;
  receipt_filename: string | null;
  receipt_scheme: string | null;
  application_no: string | null;
  release_date: string | null;
  record_note: string | null;
  recorded_at: string | null;
  resolution_note: string | null;
  resolution_current: boolean;
  resolved_at: string | null;
}

export interface ActivationDashboard {
  month: string;
  search: string;
  active_scheme: ActivationScheme | null;
  latest_scheme: ActivationScheme | null;
  schemes: ActivationScheme[];
  claims: ActivationClaim[];
  counts: Partial<Record<ClaimStatus, number>>;
  totals: { expected: string; pending: string; received: string };
}

type Outcome =
  | 'receive'
  | 'discrepancy'
  | 'unmatched'
  | 'ambiguous'
  | 'duplicate'
  | 'already_recorded';

export interface ReceiptPreview {
  preview_id: string;
  filename: string;
  confirmed: boolean;
  counts: Partial<Record<Outcome, number>>;
  received_total: string;
  discrepancy_total: string;
  receivable_total: string;
  rows: {
    sheet: string;
    row: number;
    serial: string;
    model: string;
    amount: string;
    expected_amount: string | null;
    variance: string | null;
    release_date: string;
    outcome: Outcome;
    invoice?: string;
    date_from?: string;
    date_to?: string;
  }[];
}

const ROOT = '/api/v1/asus-activation';

export class AsusActivationService {
  static async dashboard(month: string, search = ''): Promise<ActivationDashboard> {
    const client = await ApiClientProvider.getClient();
    return client.get<ActivationDashboard>(ROOT, { month, search: search || undefined });
  }

  static async editScheme<T extends SchemeEditPreview | SchemeImport>(
    id: string,
    mode: SchemeEditMode,
    dateFrom: string,
    dateTo: string,
    file?: File,
    previewId?: string,
    choices?: Record<string, RateDecision>,
  ): Promise<T> {
    const form = new FormData();
    form.append('mode', mode);
    form.append('date_from', dateFrom);
    form.append('date_to', dateTo);
    if (file) form.append('file', file);
    if (previewId) form.append('preview_id', previewId);
    if (choices) form.append('choices', JSON.stringify(choices));
    const client = await ApiClientProvider.getClient();
    return client.postForm<T>(ROOT + '/schemes/' + id + '/edit', form);
  }

  static async uploadScheme(file: File, dateFrom: string, dateTo: string): Promise<SchemeImport> {
    const form = new FormData();
    form.append('file', file);
    form.append('date_from', dateFrom);
    form.append('date_to', dateTo);
    const client = await ApiClientProvider.getClient();
    return client.postForm<SchemeImport>(ROOT + '/schemes', form);
  }

  static async importReceipts(file: File, previewId?: string): Promise<ReceiptPreview> {
    const form = new FormData();
    form.append('file', file);
    if (previewId) form.append('preview_id', previewId);
    const client = await ApiClientProvider.getClient();
    return client.postForm<ReceiptPreview>(ROOT + '/receipts', form);
  }

  static async updateClaim(
    saleId: number,
    action: 'record' | 'resolve',
    amount: string,
    note: string,
  ) {
    const client = await ApiClientProvider.getClient();
    return client.post<ActivationClaim>(ROOT + '/claims/' + saleId + '/receipt', {
      action,
      amount: action === 'record' ? amount : null,
      note,
    });
  }

  static async correctExpected(
    saleId: number,
    amount: string | null,
    note: string,
    scope: 'sale' | 'model',
  ) {
    const client = await ApiClientProvider.getClient();
    return client.put<ActivationClaim>(ROOT + '/claims/' + saleId + '/expected', {
      amount,
      note,
      scope,
    });
  }

  static async download(
    month: string | undefined,
    status: ClaimFilter,
    search = '',
  ): Promise<void> {
    const client = await ApiClientProvider.getClient();
    const blob = await client.getBlob(ROOT + '/export', {
      month,
      status,
      search: search || undefined,
    });
    triggerBlobDownload(
      blob,
      'ASUS-Activation-' + (search ? 'search' : (month ?? 'all-months')) + '-' + status + '.xlsx',
    );
  }
}
