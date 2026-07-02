import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/presentation/auth_controller.dart';
import '../../features/catalogue/domain/catalogue_models.dart';
import '../../features/inventory/data/inventory_repository.dart';
import '../../core/offline/offline_providers.dart';
import '../../features/inventory/domain/barcode_field_resolver.dart';
import '../../features/inventory/domain/inventory_models.dart';
import '../../core/device/barcode_scan_launcher.dart';
import '../../features/inventory/presentation/widgets/inventory_action_dialogs.dart';
import '../../features/sales/presentation/sales_controller.dart';

class WorkspaceLookupResult {
  const WorkspaceLookupResult({this.saleId, this.inventoryItem});

  final int? saleId;
  final InventoryItem? inventoryItem;
}

Future<WorkspaceLookupResult?> showWorkspaceLookupSheet(BuildContext context, WidgetRef ref) {
  return showModalBottomSheet<WorkspaceLookupResult>(
    context: context,
    isScrollControlled: true,
    builder: (context) => _WorkspaceLookupSheet(ref: ref),
  );
}

class _WorkspaceLookupSheet extends ConsumerStatefulWidget {
  const _WorkspaceLookupSheet({required this.ref});

  final WidgetRef ref;

  @override
  ConsumerState<_WorkspaceLookupSheet> createState() => _WorkspaceLookupSheetState();
}

class _WorkspaceLookupSheetState extends ConsumerState<_WorkspaceLookupSheet> {
  final _searchController = TextEditingController();
  String? _status;
  bool _busy = false;

  List<String> get _permissions =>
      ref.read(authControllerProvider).user?.permissions ?? const <String>[];

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _salesLookup() async {
    if (!canViewSales(_permissions)) {
      setState(() => _status = 'Requires sales:view permission');
      return;
    }
    final term = _searchController.text.trim();
    if (term.isEmpty) return;
    setState(() { _busy = true; _status = null; });
    try {
      await ref.read(salesWorkspaceProvider.notifier).openSaleBySearch(term);
      final sales = ref.read(salesWorkspaceProvider);
      if (sales.selectedDetail != null) {
        if (mounted) Navigator.pop(context, WorkspaceLookupResult(saleId: sales.selectedDetail!.id));
      } else {
        setState(() => _status = 'No matching sale found');
      }
    } catch (error) {
      setState(() => _status = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _inventoryLookup() async {
    if (!canViewInventory(_permissions)) {
      setState(() => _status = 'Requires inventory:view permission');
      return;
    }
    final term = _searchController.text.trim();
    if (term.isEmpty) return;
    setState(() { _busy = true; _status = null; });
    try {
      final result = await ref.read(offlineInventoryServiceProvider).lookupBySerial(term);
      final item = result.data;
      if (item != null && mounted) {
        Navigator.pop(context, WorkspaceLookupResult(inventoryItem: item));
        return;
      }
      setState(() => _status = result.fromCache
          ? 'No cached inventory item found for that serial'
          : 'No inventory item found for that serial');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _barcodeScan() async {
    final scan = await openBarcodeScanner(context, ref);
    if (scan == null) return;
    _searchController.text = scan.rawValue;
    if (scan.targetField == BarcodeFieldTarget.serialNumber) {
      await _inventoryLookup();
    }
  }

  Future<void> _addInventory() async {
    if (!canCreateInventory(_permissions)) {
      setState(() => _status = 'Requires inventory:create permission');
      return;
    }
    final inventoryRepo = ref.read(inventoryRepositoryProvider);
    final List<ProductModel> models = await inventoryRepo.listProductModels();
    final List<Location> locations = await inventoryRepo.listLocations();
    if (!mounted || models.isEmpty || locations.isEmpty) {
      setState(() => _status = 'Need at least one model and location');
      return;
    }

  final serialController = TextEditingController();
  final colorController = TextEditingController(text: 'Black');
  String modelId = models.first.id;
  int locationId = locations.first.id;

    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Add inventory'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: serialController,
                  decoration: const InputDecoration(labelText: 'Serial number'),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: colorController,
                  decoration: const InputDecoration(labelText: 'Color'),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  // ignore: deprecated_member_use
                  value: modelId,
                  decoration: const InputDecoration(labelText: 'Product model'),
                  items: models
                      .map((m) => DropdownMenuItem(value: m.id, child: Text('${m.modelNumber} · ${m.modelName}')))
                      .toList(),
                  onChanged: (v) => setDialogState(() => modelId = v ?? modelId),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<int>(
                  // ignore: deprecated_member_use
                  value: locationId,
                  decoration: const InputDecoration(labelText: 'Location'),
                  items: locations.map((l) => DropdownMenuItem(value: l.id, child: Text(l.name))).toList(),
                  onChanged: (v) => setDialogState(() => locationId = v ?? locationId),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
            ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Add')),
          ],
        ),
      ),
    );
    if (ok != true) return;

    setState(() { _busy = true; _status = null; });
    try {
      final item = await inventoryRepo.createItem(
        CreateInventoryItemRequest(
          serialNumber: serialController.text.trim(),
          productModelId: modelId,
          color: colorController.text.trim(),
          currentLocationId: locationId,
        ),
      );
      if (mounted) Navigator.pop(context, WorkspaceLookupResult(inventoryItem: item));
    } catch (error) {
      setState(() => _status = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _transfer() async {
    if (!_permissions.contains('inventory:transfer')) {
      setState(() => _status = 'Requires inventory:transfer permission');
      return;
    }
    final term = _searchController.text.trim();
    if (term.isEmpty) {
      setState(() => _status = 'Enter a serial number first');
      return;
    }
    setState(() { _busy = true; _status = null; });
    try {
      final InventoryRepository inventoryRepo = ref.read(inventoryRepositoryProvider);
      final InventoryItem item = await inventoryRepo.getBySerial(term);
      final List<Location> locations = await inventoryRepo.listLocations();
      if (!mounted) return;
      final locationId = await showTransferLocationDialog(
        context,
        locations: locations,
        currentLocationId: item.currentLocationId,
      );
      if (locationId == null) return;
      final updated = await inventoryRepo.transferLocation(item.id, locationId);
      if (mounted) Navigator.pop(context, WorkspaceLookupResult(inventoryItem: updated));
    } catch (error) {
      setState(() => _status = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Workspace lookup', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            TextField(
              controller: _searchController,
              decoration: const InputDecoration(
                labelText: 'Search term or serial',
                prefixIcon: Icon(Icons.search),
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (canViewSales(_permissions))
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _salesLookup,
                    icon: const Icon(Icons.point_of_sale, size: 18),
                    label: const Text('Sales lookup'),
                  ),
                if (canViewInventory(_permissions))
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _inventoryLookup,
                    icon: const Icon(Icons.inventory_2, size: 18),
                    label: const Text('Inventory lookup'),
                  ),
                OutlinedButton.icon(
                  onPressed: _busy ? null : _barcodeScan,
                  icon: const Icon(Icons.qr_code_scanner, size: 18),
                  label: const Text('Barcode scan'),
                ),
                if (canCreateInventory(_permissions))
                  ElevatedButton.icon(
                    onPressed: _busy ? null : _addInventory,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('Add inventory'),
                  ),
                if (_permissions.contains('inventory:transfer'))
                  OutlinedButton.icon(
                    onPressed: _busy ? null : _transfer,
                    icon: const Icon(Icons.swap_horiz, size: 18),
                    label: const Text('Transfer'),
                  ),
              ],
            ),
            if (_busy) const Padding(
              padding: EdgeInsets.only(top: 16),
              child: LinearProgressIndicator(),
            ),
            if (_status != null) Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(_status!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          ],
        ),
      ),
    );
  }
}
