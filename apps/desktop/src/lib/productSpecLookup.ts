import type { ProductModel } from '../services/api/ProductModelService';
import type { InventoryItemDetail } from '../services/api/InventoryService';
import { isRetriableSpecLookupError, ProductSpecService } from '../services/api/ProductSpecService';
import { splitModelNotes } from './modelNotes';
import { fetchAllInventoryForModel } from './productModelSummary';

export interface ExistingModelLookup {
  model: ProductModel;
  availableSerials: InventoryItemDetail[];
  allActiveSerials: InventoryItemDetail[];
}

export interface FetchedProductSpec {
  model_name: string;
  cpu: string;
  gpu: string | null;
  ram_gb: number;
  storage_value: string;
  storage_unit: 'GB' | 'TB';
  storage_type: 'SSD' | 'HDD';
  display: string | null;
  color_options: string | null;
  product_image_url: string | null;
  description: string | null;
  notes: string | null;
  source: 'database' | 'gemini' | 'manual';
}

export function findModelByNumber(
  models: ProductModel[],
  modelNumber: string,
  brandId?: number | null,
): ProductModel | null {
  const normalized = modelNumber.trim().toLowerCase();
  if (!normalized) return null;

  const pool = brandId ? models.filter((model) => model.brand_id === brandId) : models;

  return pool.find((model) => model.model_number.trim().toLowerCase() === normalized) ?? null;
}

export async function lookupExistingModelInventory(
  model: ProductModel,
): Promise<ExistingModelLookup> {
  const items = await fetchAllInventoryForModel(model.id);
  const active = items.filter((item) => !item.is_archived);
  return {
    model,
    availableSerials: active.filter((item) => item.status !== 'sold'),
    allActiveSerials: active,
  };
}

export async function fetchProductSpecFromInternet(
  modelNumber: string,
  options?: { modelName?: string; brandName?: string },
): Promise<FetchedProductSpec | null> {
  const result = await ProductSpecService.lookupSpec({
    model_number: modelNumber.trim(),
    model_name: options?.modelName?.trim() || undefined,
    brand_name: options?.brandName?.trim() || undefined,
  });

  if (!result?.cpu) return null;

  return {
    model_name: result.model_name,
    cpu: result.cpu,
    gpu: result.gpu,
    ram_gb: result.ram_gb,
    storage_value: result.storage_value,
    storage_unit: result.storage_unit,
    storage_type: result.storage_type,
    display: result.display,
    color_options: result.color_options,
    product_image_url: result.product_image_url,
    description: result.description,
    notes: result.notes,
    source: 'gemini',
  };
}

export { isRetriableSpecLookupError };

export function modelToFetchedSpec(model: ProductModel): FetchedProductSpec {
  const { description, specNotes } = splitModelNotes(model.notes);
  return {
    model_name: model.model_name,
    cpu: model.cpu,
    gpu: model.gpu,
    ram_gb: model.ram_gb,
    storage_value: String(model.storage_value),
    storage_unit: model.storage_unit,
    storage_type: model.storage_type,
    display: model.display,
    color_options: model.color_options,
    product_image_url: model.product_image_url,
    description: description || null,
    notes: specNotes || null,
    source: 'database',
  };
}
