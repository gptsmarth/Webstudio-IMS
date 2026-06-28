/** Future-ready saved report definitions — not persisted in v1. */

export interface SavedReportDefinition {
  id: string;
  name: string;
  reportType: 'inventory' | 'sales' | 'audit' | 'tally';
  filters: Record<string, unknown>;
  isFavourite: boolean;
  lastUsedAt: string | null;
}

export interface SavedReportsState {
  saved: SavedReportDefinition[];
  favourites: SavedReportDefinition[];
  recent: SavedReportDefinition[];
}

export const EMPTY_SAVED_REPORTS: SavedReportsState = {
  saved: [],
  favourites: [],
  recent: [],
};
