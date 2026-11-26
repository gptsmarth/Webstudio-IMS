import { ApiClientProvider } from './ApiClientProvider';

export interface ComparisonSpec {
  component: string;
  detail: string;
}

export interface ComparisonLaptop {
  source: 'inventory' | 'external';
  model_id: string | null;
  brand: string;
  model_number: string;
  model_name: string | null;
  image_url: string | null;
  managed_image: boolean;
  available_units: number | null;
  selling_price: string | null;
  saved_notes: string | null;
  specifications: ComparisonSpec[];
}

export class ComparisonService {
  static async inventory(search: string, page: number) {
    const client = await ApiClientProvider.getClient();
    return client.get<{
      data: ComparisonLaptop[];
      meta: { has_next: boolean; has_previous: boolean };
    }>('/api/v1/comparison/inventory', { search, page, page_size: 8 });
  }

  static async research(brand: string, modelNumber: string): Promise<ComparisonLaptop> {
    const client = await ApiClientProvider.getClient();
    const response = await client.post<{ data: ComparisonLaptop }>(
      '/api/v1/comparison/external',
      { brand, model_number: modelNumber },
      { timeoutMs: 85000 },
    );
    return response.data;
  }

  static async savedImage(modelId: string): Promise<Blob> {
    const client = await ApiClientProvider.getClient();
    return client.getBlob('/api/v1/comparison/inventory/' + encodeURIComponent(modelId) + '/image');
  }
}
