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
}

type SchemeImport = ActivationScheme & { matched_sale_count: number };

export interface ActivationClaim {
  sale_id: number;
  sold_on: string;
  invoice: string;
  customer: string | null;
  serial: string;
  model: string;
  unit_price: string | null;
  supported_srp: string | null;
  date_from: string;
  date_to: string;
  scheme_code: string | null;
  scheme_filename: string;
  source_sheet: string;
  program_period: string | null;
  status: ClaimStatus;
  cancelled: boolean;
  expected_amount: string;
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
  resolved_at: string | null;
}

export interface ActivationDashboard {
  month: string;
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
  static async dashboard(month: string): Promise<ActivationDashboard> {
    const client = await ApiClientProvider.getClient();
    return client.get<ActivationDashboard>(ROOT, { month });
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

  static async download(month: string | undefined, status: ClaimFilter): Promise<void> {
    const client = await ApiClientProvider.getClient();
    const blob = await client.getBlob(ROOT + '/export', { month, status });
    triggerBlobDownload(
      blob,
      'ASUS-Activation-' + (month ?? 'all-months') + '-' + status + '.xlsx',
    );
  }
}
