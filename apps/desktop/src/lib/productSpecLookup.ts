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

export type ModelNumberMatchKind = 'exact' | 'segment';

export interface ModelNumberMatch {
  model: ProductModel;
  kind: ModelNumberMatchKind;
}

function normalizeModelNumberForMatch(value: string): string {
  return value
    .trim()
    .toUpperCase()
    .replace(/[‐‑‒–—−]/g, '-')
    .replace(/\s+/g, '');
}

function modelNumberParts(value: string): string[] {
  return normalizeModelNumberForMatch(value)
    .split(/[/\\|]+/)
    .map((part) => part.trim())
    .filter((part) => part.length >= 5);
}

export function findModelNumberMatches(
  models: ProductModel[],
  modelNumber: string,
  brandId?: number | null,
): ModelNumberMatch[] {
  const normalized = normalizeModelNumberForMatch(modelNumber);
  if (!normalized) return [];

  const pool = brandId ? models.filter((model) => model.brand_id === brandId) : models;
  const exact = pool.find(
    (model) => normalizeModelNumberForMatch(model.model_number) === normalized,
  );
  if (exact) return [{ model: exact, kind: 'exact' }];

  const enteredParts = new Set(modelNumberParts(modelNumber));
  if (enteredParts.size === 0) return [];
  return pool
    .filter((model) => modelNumberParts(model.model_number).some((part) => enteredParts.has(part)))
    .map((model) => ({ model, kind: 'segment' as const }));
}

export function findModelByNumber(
  models: ProductModel[],
  modelNumber: string,
  brandId?: number | null,
): ProductModel | null {
  return (
    findModelNumberMatches(models, modelNumber, brandId).find((match) => match.kind === 'exact')
      ?.model ?? null
  );
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

const inflightSpecLookups = new Map<string, Promise<FetchedProductSpec | null>>();

export async function fetchProductSpecFromInternet(
  modelNumber: string,
  options?: { modelName?: string; brandName?: string; forceRefresh?: boolean },
): Promise<FetchedProductSpec | null> {
  const normalizedModel = modelNumber.trim();
  const normalizedBrand = options?.brandName?.trim().toLowerCase() ?? '';
  const inflightKey = `${normalizedModel.toLowerCase()}|${normalizedBrand}${options?.forceRefresh ? '|refresh' : ''}`;
  const existing = inflightSpecLookups.get(inflightKey);
  if (existing) {
    return existing;
  }

  const lookupPromise = (async (): Promise<FetchedProductSpec | null> => {
    const result = await ProductSpecService.lookupSpec({
      model_number: normalizedModel,
      model_name: options?.modelName?.trim() || undefined,
      brand_name: options?.brandName?.trim() || undefined,
      force_refresh: options?.forceRefresh ?? false,
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
  })();

  inflightSpecLookups.set(inflightKey, lookupPromise);
  try {
    return await lookupPromise;
  } finally {
    if (inflightSpecLookups.get(inflightKey) === lookupPromise) {
      inflightSpecLookups.delete(inflightKey);
    }
  }
}

export { isRetriableSpecLookupError };

export function modelToFetchedSpec(model: ProductModel): FetchedProductSpec {
  const { description, specNotes } = splitModelNotes(model.notes);
  return {
    model_name: model.model_name,
    cpu: model.cpu ?? '',
    gpu: model.gpu,
    ram_gb: model.ram_gb ?? 0,
    storage_value: String(model.storage_value ?? ''),
    storage_unit: model.storage_unit ?? 'GB',
    storage_type: model.storage_type ?? 'SSD',
    display: model.display,
    color_options: model.color_options,
    product_image_url: model.product_image_url,
    description: description || null,
    notes: specNotes || null,
    source: 'database',
  };
}
