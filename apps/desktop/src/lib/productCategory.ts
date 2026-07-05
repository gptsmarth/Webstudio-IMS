export type ProductCategory = 'laptop' | 'accessory';

export type AccessoryKind =
  | 'mouse'
  | 'keyboard'
  | 'charger'
  | 'headset'
  | 'bag'
  | 'dock'
  | 'cable'
  | 'adapter'
  | 'storage'
  | 'other';

export type ProductCategoryFilter = 'all' | ProductCategory;

export type AccessoryIdentifierType = 'part_number' | 'model_number';

export const ACCESSORY_KINDS: { value: AccessoryKind; label: string }[] = [
  { value: 'mouse', label: 'Mouse' },
  { value: 'keyboard', label: 'Keyboard' },
  { value: 'charger', label: 'Charger / adapter' },
  { value: 'headset', label: 'Headset / audio' },
  { value: 'bag', label: 'Bag / sleeve' },
  { value: 'dock', label: 'Dock / hub' },
  { value: 'cable', label: 'Cable' },
  { value: 'adapter', label: 'Power adapter' },
  { value: 'storage', label: 'Storage device' },
  { value: 'other', label: 'Other accessory' },
];

export const PRODUCT_CATEGORY_FILTERS: { value: ProductCategoryFilter; label: string }[] = [
  { value: 'all', label: 'All products' },
  { value: 'laptop', label: 'Laptops only' },
  { value: 'accessory', label: 'Accessories only' },
];

export function accessoryKindLabel(kind: AccessoryKind | null | undefined): string {
  if (!kind) return 'Accessory';
  return ACCESSORY_KINDS.find((row) => row.value === kind)?.label ?? 'Accessory';
}

export function isAccessoryModel(model: { category?: ProductCategory | null }): boolean {
  return model.category === 'accessory';
}

export function productCategoryLabel(category: ProductCategory | null | undefined): string {
  return category === 'accessory' ? 'Accessory' : 'Laptop';
}
