bool canViewInventory(List<String> permissions) => permissions.contains('inventory:view');

bool canCreateInventory(List<String> permissions) => permissions.contains('inventory:create');

bool canEditInventory(List<String> permissions) => permissions.contains('inventory:edit');

bool canArchiveInventory(List<String> permissions) => permissions.contains('inventory:archive');

bool canRestoreInventory(List<String> permissions) => permissions.contains('inventory:restore');

bool canMarkSold(List<String> permissions) => permissions.contains('sales:create');

bool canTransferStockLocation(List<String> permissions) => permissions.contains('inventory:transfer');

bool canCreateProductModels(List<String> permissions) => permissions.contains('product_models:create');

bool canDeleteProductModels(List<String> permissions) =>
    permissions.contains('product_models:delete') || permissions.contains('product_models:archive');

bool canEditProductModels(List<String> permissions) => permissions.contains('product_models:edit');
