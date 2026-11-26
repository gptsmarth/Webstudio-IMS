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

interface ComparisonPagination {
  has_next: boolean;
  has_previous: boolean;
}

export class ComparisonService {
  static async inventory(search: string, page: number) {
    const client = await ApiClientProvider.getClient();
    const response = await client.getRaw<ComparisonLaptop[], ComparisonPagination>(
      '/api/v1/comparison/inventory',
      { search, page, page_size: 8 },
    );
    if (
      !Array.isArray(response.data) ||
      response.data.some((laptop) => !Array.isArray(laptop?.specifications))
    ) {
      throw new Error('The server returned an invalid inventory response.');
    }
    return response;
  }

  static async research(brand: string, modelNumber: string): Promise<ComparisonLaptop> {
    const client = await ApiClientProvider.getClient();
    const laptop = await client.post<ComparisonLaptop>(
      '/api/v1/comparison/external',
      { brand, model_number: modelNumber },
      { timeoutMs: 85000 },
    );
    if (!Array.isArray(laptop?.specifications)) {
      throw new Error('The server returned an invalid laptop research response.');
    }
    return laptop;
  }

  static async savedImage(modelId: string): Promise<Blob> {
    const client = await ApiClientProvider.getClient();
    return client.getBlob('/api/v1/comparison/inventory/' + encodeURIComponent(modelId) + '/image');
  }

  static async processor(modelId: string): Promise<ComparisonSpec[]> {
    const client = await ApiClientProvider.getClient();
    const specs = await client.post<ComparisonSpec[]>(
      '/api/v1/comparison/inventory/' + encodeURIComponent(modelId) + '/processor',
      undefined,
      { timeoutMs: 85000 },
    );
    return Array.isArray(specs) ? specs : [];
  }
}
