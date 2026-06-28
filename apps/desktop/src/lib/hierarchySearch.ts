export type HierarchySearchField =
  | 'all'
  | 'model_number'
  | 'model_name'
  | 'gpu'
  | 'cpu'
  | 'serial'
  | 'display';

export const HIERARCHY_SEARCH_FIELDS: { value: HierarchySearchField; label: string }[] = [
  { value: 'all', label: 'All fields' },
  { value: 'model_number', label: 'Model number' },
  { value: 'model_name', label: 'Model name' },
  { value: 'gpu', label: 'Graphics (GPU)' },
  { value: 'cpu', label: 'Processor (CPU)' },
  { value: 'display', label: 'Display' },
  { value: 'serial', label: 'Serial number' },
];

export function hierarchySearchPlaceholder(field: HierarchySearchField): string {
  switch (field) {
    case 'model_number':
      return 'Enter model number…';
    case 'model_name':
      return 'Enter model name…';
    case 'gpu':
      return 'Search by graphics card…';
    case 'cpu':
      return 'Search by processor…';
    case 'display':
      return 'Search by display size…';
    case 'serial':
      return 'Search by serial number…';
    default:
      return 'Search model number, name, GPU, CPU, serial…';
  }
}
