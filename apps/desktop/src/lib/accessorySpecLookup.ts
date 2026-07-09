import type { AccessoryKind, AccessoryIdentifierType } from './productCategory';
import type { ProductModel } from '../services/api/ProductModelService';
import { ProductSpecService } from '../services/api/ProductSpecService';

export interface FetchedAccessorySpec {
  model_name: string;
  model_number: string | null;
  part_number: string | null;
  accessory_kind: AccessoryKind | null;
  color_options: string | null;
  product_image_url: string | null;
  description: string | null;
  notes: string | null;
  source: 'database' | 'gemini';
}

const inflightAccessoryLookups = new Map<string, Promise<FetchedAccessorySpec | null>>();

export function findAccessoryByIdentifier(
  models: ProductModel[],
  identifier: string,
  brandId?: number | null,
): ProductModel | null {
  const normalized = identifier.trim().toLowerCase();
  if (!normalized) return null;

  const pool = brandId
    ? models.filter((model) => model.brand_id === brandId && model.category === 'accessory')
    : models.filter((model) => model.category === 'accessory');

  return (
    pool.find((model) => {
      const modelNumber = model.model_number.trim().toLowerCase();
      const partNumber = model.part_number?.trim().toLowerCase();
      return modelNumber === normalized || partNumber === normalized;
    }) ?? null
  );
}

export async function fetchAccessorySpecFromInternet(
  identifier: string,
  options?: {
    identifierType?: AccessoryIdentifierType;
    brandName?: string;
    modelName?: string;
    forceRefresh?: boolean;
  },
): Promise<FetchedAccessorySpec | null> {
  const normalized = identifier.trim();
  const identifierType = options?.identifierType ?? 'model_number';
  const normalizedBrand = options?.brandName?.trim().toLowerCase() ?? '';
  const inflightKey = `${identifierType}:${normalized.toLowerCase()}|${normalizedBrand}${options?.forceRefresh ? '|refresh' : ''}`;
  const existing = inflightAccessoryLookups.get(inflightKey);
  if (existing) {
    return existing;
  }

  const lookupPromise = (async (): Promise<FetchedAccessorySpec | null> => {
    const result = await ProductSpecService.lookupAccessorySpec({
      identifier: normalized,
      identifier_type: identifierType,
      brand_name: options?.brandName?.trim() || undefined,
      model_name: options?.modelName?.trim() || undefined,
      force_refresh: options?.forceRefresh ?? false,
    });

    if (!result?.model_name) return null;

    return {
      model_name: result.model_name,
      model_number: result.model_number,
      part_number: result.part_number,
      accessory_kind: result.accessory_kind,
      color_options: result.color_options,
      product_image_url: result.product_image_url,
      description: result.description,
      notes: result.notes,
      source: 'gemini',
    };
  })();

  inflightAccessoryLookups.set(inflightKey, lookupPromise);
  try {
    return await lookupPromise;
  } finally {
    if (inflightAccessoryLookups.get(inflightKey) === lookupPromise) {
      inflightAccessoryLookups.delete(inflightKey);
    }
  }
}

export function accessoryToDisplaySpec(model: ProductModel): FetchedAccessorySpec {
  return {
    model_name: model.model_name,
    model_number: model.model_number,
    part_number: model.part_number,
    accessory_kind: model.accessory_kind,
    color_options: model.color_options,
    product_image_url: model.product_image_url,
    description: null,
    notes: model.notes,
    source: 'database',
  };
}
