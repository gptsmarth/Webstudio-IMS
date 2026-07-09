import type { CreateProductModelRequest } from '../services/api/ProductModelService';

const MAX_IMAGE_URL_LENGTH = 512;

function optionalText(value: string | null | undefined): string | null {
  if (value == null) return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function sanitizeImageUrl(value: string | null | undefined): string | null {
  const trimmed = optionalText(value);
  if (!trimmed) return null;
  if (trimmed.startsWith('/assets/')) return trimmed;
  if (trimmed.startsWith('https://') && trimmed.length <= MAX_IMAGE_URL_LENGTH) {
    return trimmed;
  }
  // Long remote URLs are resolved server-side after create; omit to avoid 422 validation.
  return null;
}

/** Normalize create-model payloads so optional empty strings do not fail API validation. */
export function sanitizeCreateProductModelPayload(
  payload: CreateProductModelRequest,
): CreateProductModelRequest {
  const category = payload.category ?? 'laptop';
  const sanitized: CreateProductModelRequest = {
    ...payload,
    part_number: optionalText(payload.part_number ?? undefined),
    gpu: optionalText(payload.gpu ?? undefined),
    display: optionalText(payload.display ?? undefined),
    color_options: optionalText(payload.color_options ?? undefined),
    search_aliases: optionalText(payload.search_aliases ?? undefined),
    notes: optionalText(payload.notes ?? undefined),
    product_image_url: sanitizeImageUrl(payload.product_image_url),
  };

  if (category === 'laptop') {
    const ram = payload.ram_gb != null ? Number(payload.ram_gb) : NaN;
    const storage = payload.storage_value != null ? Number(payload.storage_value) : NaN;
    return {
      ...sanitized,
      ram_gb: Number.isFinite(ram) && ram > 0 ? ram : payload.ram_gb,
      storage_value:
        Number.isFinite(storage) && storage > 0 ? String(payload.storage_value).trim() : payload.storage_value,
    };
  }

  return sanitized;
}
