enum ProductCategory { laptop, accessory }

enum AccessoryKind {
  mouse,
  keyboard,
  charger,
  headset,
  bag,
  dock,
  cable,
  adapter,
  storage,
  other,
}

enum ProductCategoryFilter { all, laptop, accessory }

enum AccessoryIdentifierType { partNumber, modelNumber }

class AccessoryKindOption {
  const AccessoryKindOption({required this.value, required this.label});

  final AccessoryKind value;
  final String label;
}

const accessoryKindOptions = <AccessoryKindOption>[
  AccessoryKindOption(value: AccessoryKind.mouse, label: 'Mouse'),
  AccessoryKindOption(value: AccessoryKind.keyboard, label: 'Keyboard'),
  AccessoryKindOption(value: AccessoryKind.charger, label: 'Charger / adapter'),
  AccessoryKindOption(value: AccessoryKind.headset, label: 'Headset / audio'),
  AccessoryKindOption(value: AccessoryKind.bag, label: 'Bag / sleeve'),
  AccessoryKindOption(value: AccessoryKind.dock, label: 'Dock / hub'),
  AccessoryKindOption(value: AccessoryKind.cable, label: 'Cable'),
  AccessoryKindOption(value: AccessoryKind.adapter, label: 'Power adapter'),
  AccessoryKindOption(value: AccessoryKind.storage, label: 'Storage device'),
  AccessoryKindOption(value: AccessoryKind.other, label: 'Other accessory'),
];

class ProductCategoryFilterOption {
  const ProductCategoryFilterOption({required this.value, required this.label});

  final ProductCategoryFilter value;
  final String label;
}

const productCategoryFilterOptions = <ProductCategoryFilterOption>[
  ProductCategoryFilterOption(value: ProductCategoryFilter.all, label: 'All products'),
  ProductCategoryFilterOption(value: ProductCategoryFilter.laptop, label: 'Laptops only'),
  ProductCategoryFilterOption(value: ProductCategoryFilter.accessory, label: 'Accessories only'),
];

ProductCategory productCategoryFromString(String? value) {
  if (value == 'accessory') return ProductCategory.accessory;
  return ProductCategory.laptop;
}

String productCategoryToApi(ProductCategory category) {
  return category == ProductCategory.accessory ? 'accessory' : 'laptop';
}

AccessoryKind? accessoryKindFromString(String? value) {
  if (value == null || value.isEmpty) return null;
  for (final kind in AccessoryKind.values) {
    if (kind.name == value) return kind;
  }
  return null;
}

String accessoryKindToApi(AccessoryKind kind) => kind.name;

String accessoryKindLabel(AccessoryKind? kind) {
  if (kind == null) return 'Accessory';
  for (final option in accessoryKindOptions) {
    if (option.value == kind) return option.label;
  }
  return 'Accessory';
}

String productCategoryLabel(ProductCategory? category) {
  return category == ProductCategory.accessory ? 'Accessory' : 'Laptop';
}

String productCategoryFilterLabel(ProductCategoryFilter filter) {
  for (final option in productCategoryFilterOptions) {
    if (option.value == filter) return option.label;
  }
  return 'All products';
}

bool isAccessoryModel({ProductCategory? category}) => category == ProductCategory.accessory;

bool isLaptopModel({ProductCategory? category}) => category != ProductCategory.accessory;

String identifierTypeLabel(AccessoryIdentifierType type) {
  return type == AccessoryIdentifierType.partNumber ? 'Part number' : 'Model number';
}

String identifierTypeToApi(AccessoryIdentifierType type) {
  return type == AccessoryIdentifierType.partNumber ? 'part_number' : 'model_number';
}
