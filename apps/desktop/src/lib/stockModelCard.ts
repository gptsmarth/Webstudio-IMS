import type { ProductModel } from '../services/api/ProductModelService';
import { formatStorage } from './inventory';
import { splitModelNotes } from './modelNotes';
import { accessoryKindLabel, isAccessoryModel } from './productCategory';

export interface StockModelSpecLine {
  label: string;
  value: string;
}

/** Parse structured Gemini extras stored in product model notes (before ---). */
export function parseNotesSpecLines(notes: string | null | undefined): StockModelSpecLine[] {
  const { specNotes } = splitModelNotes(notes);
  if (!specNotes.trim()) return [];

  const structured = specNotes.split(/\n---\n/)[0]?.trim() ?? specNotes.trim();
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

function pushIfPresent(
  lines: StockModelSpecLine[],
  label: string,
  value: string | null | undefined,
): void {
  const trimmed = value?.trim();
  if (trimmed) {
    lines.push({ label, value: trimmed });
  }
}

/** Bulleted configuration lines for stock model cards (retailer-style layout). */
export function buildStockModelSpecLines(model: ProductModel): StockModelSpecLine[] {
  const lines: StockModelSpecLine[] = [];

  if (isAccessoryModel(model)) {
    lines.push({ label: 'Type', value: accessoryKindLabel(model.accessory_kind) });
    pushIfPresent(lines, 'Part number', model.part_number);
    pushIfPresent(lines, 'Model number', model.model_number);
    pushIfPresent(lines, 'Colors', model.color_options);
    const noteLines = parseNotesSpecLines(model.notes);
    lines.push(...noteLines);
    return lines;
  }

  lines.push({ label: 'Processor', value: model.cpu?.trim() || 'Standard Processor' });
  lines.push({ label: 'Graphics', value: model.gpu?.trim() || 'Integrated Graphics' });
  lines.push({ label: 'Memory', value: `${model.ram_gb || 16} GB RAM` });
  if (model.storage_value && model.storage_unit && model.storage_type) {
    lines.push({
      label: 'Storage',
      value: formatStorage(model.storage_value, model.storage_unit, model.storage_type),
    });
  }
  lines.push({ label: 'Display', value: model.display?.trim() || '15.6" Standard Display' });

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

/** Leading screen size hint for retailer-style cards (e.g. 15.6" or 40.64cm (16)). */
export function displayScreenHint(display: string | null | undefined): string | null {
  if (!display?.trim()) return null;
  const text = display.trim();
  const inch = text.match(/(\d+(?:\.\d+)?)\s*(?:inch|inches|")\b/i);
  if (inch) {
    return `${inch[1]}"`;
  }
  const cm = text.match(/(\d+(?:\.\d+)?)\s*cm\s*\((\d+(?:\.\d+)?)\)/i);
  if (cm) {
    return `${cm[1]}cm (${cm[2]})`;
  }
  const segment = text.split(/[,;]/)[0]?.trim();
  return segment && segment.length <= 28 ? segment : null;
}

const RETAILER_SPEC_ORDER = [
  'operating system',
  'os',
  'processor',
  'graphics',
  'memory',
  'memory type',
  'storage',
  'display',
  'colors',
  'battery',
  'weight',
  'connectivity',
  'keyboard',
  'webcam',
  'audio',
  'charger',
  'warranty',
] as const;

export function orderStockCardSpecLines(lines: StockModelSpecLine[]): StockModelSpecLine[] {
  const rank = new Map<string, number>(RETAILER_SPEC_ORDER.map((label, index) => [label, index]));
  return [...lines].sort((left, right) => {
    const leftRank = rank.get(left.label.toLowerCase()) ?? 99;
    const rightRank = rank.get(right.label.toLowerCase()) ?? 99;
    if (leftRank !== rightRank) return leftRank - rightRank;
    return left.label.localeCompare(right.label);
  });
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
