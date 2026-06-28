import type { ProductModel } from '../services/api/ProductModelService';
import { formatStorage } from './inventory';

export interface StockModelSpecLine {
  label: string;
  value: string;
}

/** Parse structured Gemini extras stored in product model notes (before ---). */
export function parseNotesSpecLines(notes: string | null | undefined): StockModelSpecLine[] {
  if (!notes?.trim()) return [];

  const structured = notes.split(/\n---\n/)[0]?.trim() ?? notes.trim();
  const lines: StockModelSpecLine[] = [];

  for (const rawLine of structured.split('\n')) {
    const line = rawLine.trim();
    if (!line) continue;
    const colon = line.indexOf(':');
    if (colon <= 0) continue;
    const label = line.slice(0, colon).trim();
    const value = line.slice(colon + 1).trim();
    if (label && value) {
      lines.push({ label, value });
    }
  }

  return lines;
}

function pushIfPresent(lines: StockModelSpecLine[], label: string, value: string | null | undefined): void {
  const trimmed = value?.trim();
  if (trimmed) {
    lines.push({ label, value: trimmed });
  }
}

/** Bulleted configuration lines for stock model cards (retailer-style layout). */
export function buildStockModelSpecLines(model: ProductModel): StockModelSpecLine[] {
  const lines: StockModelSpecLine[] = [];

  pushIfPresent(lines, 'Processor', model.cpu);
  pushIfPresent(lines, 'Graphics', model.gpu);
  lines.push({ label: 'Memory', value: `${model.ram_gb} GB RAM` });
  pushIfPresent(lines, 'Display', model.display);
  lines.push({
    label: 'Storage',
    value: formatStorage(model.storage_value, model.storage_unit, model.storage_type),
  });
  pushIfPresent(lines, 'Colors', model.color_options);

  const noteLines = parseNotesSpecLines(model.notes);
  const seen = new Set(lines.map((line) => line.label.toLowerCase()));
  for (const line of noteLines) {
    const key = line.label.toLowerCase();
    if (!seen.has(key)) {
      lines.push(line);
      seen.add(key);
    }
  }

  return lines;
}

export function stockAvailabilityLabel(availableUnits: number): string {
  return availableUnits === 1 ? '1 unit available' : `${availableUnits} units available`;
}

const CARD_SPEC_PRIORITY = ['Processor', 'Memory', 'Storage', 'Display', 'Graphics'] as const;

/** Key specs for compact retailer-style product cards (HP / ASUS layout). */
export function pickStockCardHighlightSpecs(
  lines: StockModelSpecLine[],
  max = 4,
): StockModelSpecLine[] {
  const byLabel = new Map(lines.map((line) => [line.label, line]));
  const picked: StockModelSpecLine[] = [];

  for (const label of CARD_SPEC_PRIORITY) {
    const line = byLabel.get(label);
    if (line) {
      picked.push(line);
      if (picked.length >= max) return picked;
    }
  }

  for (const line of lines) {
    if (picked.some((entry) => entry.label === line.label)) continue;
    picked.push(line);
    if (picked.length >= max) break;
  }

  return picked;
}
