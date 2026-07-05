bool canCancelSales(List<String> permissions) => permissions.contains('sales:cancel');

bool canDeleteSale(List<String> permissions, String? inventoryItemId) {
  return canCancelSales(permissions) && inventoryItemId != null && inventoryItemId.isNotEmpty;
}
