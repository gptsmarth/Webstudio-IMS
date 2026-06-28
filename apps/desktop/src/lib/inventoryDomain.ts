import type { InventoryItemDetail, InventoryStatus } from '../services/api/InventoryService';
import type { ProductModel } from '../services/api/ProductModelService';

/** Fields owned by the physical inventory item (serial-tracked unit). */
export type InventoryItemFields = Pick<
  InventoryItemDetail,
  | 'id'
  | 'serial_number'
  | 'status'
  | 'is_archived'
  | 'current_location_id'
  | 'current_location_name'
  | 'color'
  | 'created_at'
  | 'updated_at'
  | 'product_model_id'
>;

/** Catalogue specifications inherited from the parent product model. */
export type ProductModelInheritedFields = Pick<
  InventoryItemDetail,
  | 'brand_id'
  | 'brand_name'
  | 'model_number'
  | 'model_name'
  | 'cpu'
  | 'gpu'
  | 'ram_gb'
  | 'storage_value'
  | 'storage_unit'
  | 'storage_type'
>;

export function saleStatusLabel(status: InventoryStatus, isArchived: boolean): string {
  if (isArchived) return 'Archived';
  if (status === 'sold') return 'Sold';
  return 'Not sold';
}

export function saleStatusBadgeClass(status: InventoryStatus, isArchived: boolean): string {
  if (isArchived) return 'badge-neutral';
  if (status === 'sold') return 'badge-danger';
  return 'badge-success';
}

export function colorVariantsLabel(model: ProductModel | null): string {
  if (!model?.color_options?.trim()) return '—';
  return model.color_options;
}

export function modelDisplayName(item: Pick<InventoryItemDetail, 'model_number' | 'model_name'>): string {
  return `${item.model_number} — ${item.model_name}`;
}
