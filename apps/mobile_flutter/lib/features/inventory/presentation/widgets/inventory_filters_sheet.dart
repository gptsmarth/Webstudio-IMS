import 'package:flutter/material.dart';

import '../../../../shared/widgets/scrollable_bottom_sheet.dart';
import '../../domain/inventory_hierarchy.dart';
import '../../domain/inventory_models.dart';

Future<InventoryListFilters?> showInventoryFiltersSheet(
  BuildContext context, {
  required InventoryListFilters initial,
  required List<Location> locations,
}) {
  return showModalBottomSheet<InventoryListFilters>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => ScrollableBottomSheetForm(
      child: _InventoryFiltersSheet(initial: initial, locations: locations),
    ),
  );
}

class _InventoryFiltersSheet extends StatefulWidget {
  const _InventoryFiltersSheet({required this.initial, required this.locations});

  final InventoryListFilters initial;
  final List<Location> locations;

  @override
  State<_InventoryFiltersSheet> createState() => _InventoryFiltersSheetState();
}

class _InventoryFiltersSheetState extends State<_InventoryFiltersSheet> {
  late InventoryStatus? _status;
  late int? _locationId;
  late final TextEditingController _colorController;

  @override
  void initState() {
    super.initState();
    _status = widget.initial.status;
    _locationId = widget.initial.currentLocationId;
    _colorController = TextEditingController(text: widget.initial.color ?? '');
  }

  @override
  void dispose() {
    _colorController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
          Text('Inventory filters', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          DropdownButtonFormField<InventoryStatus?>(
            // ignore: deprecated_member_use
            value: _status,
            items: [
              const DropdownMenuItem(value: null, child: Text('All statuses')),
              ...InventoryStatus.values.map(
                (status) => DropdownMenuItem(value: status, child: Text(inventoryStatusLabel(status))),
              ),
            ],
            onChanged: (value) => setState(() => _status = value),
            decoration: const InputDecoration(labelText: 'Status'),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<int?>(
            // ignore: deprecated_member_use
            value: _locationId,
            items: [
              const DropdownMenuItem(value: null, child: Text('All locations')),
              ...widget.locations.map((l) => DropdownMenuItem(value: l.id, child: Text(l.name))),
            ],
            onChanged: (value) => setState(() => _locationId = value),
            decoration: const InputDecoration(labelText: 'Location'),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _colorController,
            decoration: const InputDecoration(labelText: 'Color'),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              TextButton(
                onPressed: () => Navigator.pop(
                  context,
                  const InventoryListFilters(),
                ),
                child: const Text('Clear'),
              ),
              const Spacer(),
              ElevatedButton(
                onPressed: () => Navigator.pop(
                  context,
                  widget.initial.copyWith(
                    status: _status,
                    currentLocationId: _locationId,
                    color: _colorController.text.trim().isEmpty ? null : _colorController.text.trim(),
                    clearStatus: _status == null,
                  ),
                ),
                child: const Text('Apply'),
              ),
            ],
          ),
        ],
    );
  }
}

Future<HierarchySearchField?> showSearchFieldSheet(BuildContext context, HierarchySearchField current) {
  return showScrollableBottomSheet<HierarchySearchField>(
    context: context,
    title: 'Search field',
    children: HierarchySearchField.values
        .map(
          (field) => ListTile(
            title: Text(_searchFieldLabel(field)),
            trailing: field == current ? const Icon(Icons.check) : null,
            onTap: () => Navigator.pop(context, field),
          ),
        )
        .toList(),
  );
}

String _searchFieldLabel(HierarchySearchField field) {
  return switch (field) {
    HierarchySearchField.all => 'All fields',
    HierarchySearchField.modelNumber => 'Model number',
    HierarchySearchField.modelName => 'Model name',
    HierarchySearchField.partNumber => 'Part number',
    HierarchySearchField.gpu => 'Graphics (GPU)',
    HierarchySearchField.cpu => 'Processor (CPU)',
    HierarchySearchField.display => 'Display',
    HierarchySearchField.serial => 'Serial number',
  };
}

String hierarchySearchPlaceholder(HierarchySearchField field) {
  return switch (field) {
    HierarchySearchField.modelNumber => 'Enter model number…',
    HierarchySearchField.modelName => 'Enter model name…',
    HierarchySearchField.partNumber => 'Enter part number…',
    HierarchySearchField.gpu => 'Search by graphics card…',
    HierarchySearchField.cpu => 'Search by processor…',
    HierarchySearchField.display => 'Search by display size…',
    HierarchySearchField.serial => 'Search by serial number…',
    HierarchySearchField.all => 'Search model, part number, serial, CPU, GPU…',
  };
}
