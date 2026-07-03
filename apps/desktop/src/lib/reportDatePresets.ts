export type DatePreset =
  | ''
  | 'today'
  | 'yesterday'
  | 'week'
  | 'month'
  | 'quarter'
  | 'year'
  | 'custom';

function startOfDay(date: Date): Date {
  const copy = new Date(date);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

function endOfDay(date: Date): Date {
  const copy = new Date(date);
  copy.setHours(23, 59, 59, 999);
  return copy;
}

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function isoDateTime(date: Date): string {
  return date.toISOString();
}

export function resolveDatePreset(preset: DatePreset): { from: string; to: string } {
  const today = startOfDay(new Date());
  if (preset === 'today') {
    return { from: isoDateTime(today), to: isoDateTime(endOfDay(today)) };
  }
  if (preset === 'yesterday') {
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    return { from: isoDateTime(yesterday), to: isoDateTime(endOfDay(yesterday)) };
  }
  if (preset === 'week') {
    const start = new Date(today);
    start.setDate(start.getDate() - start.getDay());
    return { from: isoDateTime(start), to: isoDateTime(endOfDay(today)) };
  }
  if (preset === 'month') {
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    return { from: isoDateTime(start), to: isoDateTime(endOfDay(today)) };
  }
  if (preset === 'quarter') {
    const quarter = Math.floor(today.getMonth() / 3);
    const start = new Date(today.getFullYear(), quarter * 3, 1);
    return { from: isoDateTime(start), to: isoDateTime(endOfDay(today)) };
  }
  if (preset === 'year') {
    const start = new Date(today.getFullYear(), 0, 1);
    return { from: isoDateTime(start), to: isoDateTime(endOfDay(today)) };
  }
  return { from: '', to: '' };
}

export function dateInputToRange(from: string, to: string): { from: string; to: string } {
  return {
    from: from ? `${from}T00:00:00.000Z` : '',
    to: to ? `${to}T23:59:59.999Z` : '',
  };
}

export { isoDate };
