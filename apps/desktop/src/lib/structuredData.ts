export interface StructuredDataRow {
  key: string;
  label: string;
  value: string;
}

export interface ParsedNotificationContent {
  summary: string;
  details: StructuredDataRow[];
}

const FIELD_LABELS: Record<string, string> = {
  current_location: 'Location',
  location: 'Location',
  location_id: 'Location ID',
  status: 'Status',
  brand_id: 'Brand ID',
  product_model_id: 'Product model ID',
  serial_number: 'Serial number',
  invoice_number: 'Invoice',
  customer_name: 'Customer',
  payment_mode: 'Payment mode',
  sale_amount: 'Sale amount',
  model_number: 'Model number',
  model_name: 'Model name',
  cpu: 'Processor',
  gpu: 'Graphics',
  ram_gb: 'Memory (GB)',
  storage_value: 'Storage',
  is_active: 'Active',
  is_archived: 'Archived',
  name: 'Name',
  id: 'ID',
};

function humanizeKey(key: string): string {
  const normalized = key.trim().toLowerCase();
  if (FIELD_LABELS[normalized]) return FIELD_LABELS[normalized];
  return normalized
    .split(/[._]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatPrimitive(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return String(value);
  if (typeof value === 'string') return value.trim() || '—';
  if (Array.isArray(value)) return value.map((item) => formatPrimitive(item)).join(', ');
  return String(value);
}

function pushRow(rows: StructuredDataRow[], key: string, label: string, value: string): void {
  if (!value || value === '—') return;
  rows.push({ key, label, value });
}

/** Flatten audit JSON into simple label → value rows for non-technical readers. */
export function structuredRowsFromObject(
  value: Record<string, unknown> | null,
  prefix = '',
): StructuredDataRow[] {
  if (!value) return [];

  const rows: StructuredDataRow[] = [];

  for (const [rawKey, rawValue] of Object.entries(value)) {
    const fullKey = prefix ? `${prefix}.${rawKey}` : rawKey;
    const label = humanizeKey(rawKey);

    if (rawValue && typeof rawValue === 'object' && !Array.isArray(rawValue)) {
      const nested = rawValue as Record<string, unknown>;
      if (typeof nested.name === 'string') {
        pushRow(rows, fullKey, label, nested.name);
        continue;
      }
      if (Object.keys(nested).length <= 4) {
        const nestedRows = structuredRowsFromObject(nested, fullKey);
        if (nestedRows.length > 0) {
          rows.push(...nestedRows);
          continue;
        }
      }
    }

    pushRow(rows, fullKey, label, formatPrimitive(rawValue));
  }

  return rows;
}

export function formatStructuredJson(value: Record<string, unknown> | null): string {
  if (!value) return '—';
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

const UUID_PATTERN = /[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}/gi;

function shortenUuid(text: string): string {
  return text.replace(UUID_PATTERN, (uuid) => `${uuid.slice(0, 8)}…`);
}

/** Turn notification body text into a short summary plus optional detail rows. */
export function parseNotificationDescription(
  title: string,
  description: string | null,
): ParsedNotificationContent {
  if (!description?.trim()) {
    return { summary: '', details: [] };
  }

  const text = description.trim();
  const details: StructuredDataRow[] = [];

  const syncMatch = text.match(
    /Synchronization run ([a-f0-9-]{36}) started for (.+?)(?:\s*-\s*\(from|\.\s*$|$)/i,
  );
  if (syncMatch) {
    const company = syncMatch[2].trim().replace(/\s*-\s*$/, '');
    const periods = [...text.matchAll(/\(from ([^)]+)\)/gi)].map((match) => match[1].trim());
    details.push({ key: 'sync_run_id', label: 'Sync run ID', value: syncMatch[1] });
    if (periods.length > 0) {
      details.push({ key: 'periods', label: 'Sync periods', value: periods.join(' · ') });
    }
    return {
      summary: `Tally synchronization started for ${company}.`,
      details,
    };
  }

  const connectionLost = text.match(/Tally connection (?:was )?lost[.:]?\s*(.*)$/i);
  if (connectionLost || title.toLowerCase().includes('connection lost')) {
    return {
      summary: text.length > 120 ? `${text.slice(0, 117)}…` : text,
      details: extractUuidDetails(text),
    };
  }

  const uuidDetails = extractUuidDetails(text);
  if (uuidDetails.length > 0 && text.length > 80) {
    return {
      summary: shortenUuid(text.split('.')[0] ?? text),
      details: uuidDetails,
    };
  }

  return {
    summary: shortenUuid(text),
    details: uuidDetails,
  };
}

function extractUuidDetails(text: string): StructuredDataRow[] {
  const matches = [...text.matchAll(UUID_PATTERN)];
  if (matches.length === 0) return [];
  if (matches.length === 1) {
    return [{ key: 'reference_id', label: 'Reference ID', value: matches[0][0] }];
  }
  return matches.map((match, index) => ({
    key: `reference_id_${index}`,
    label: `Reference ID ${index + 1}`,
    value: match[0],
  }));
}
