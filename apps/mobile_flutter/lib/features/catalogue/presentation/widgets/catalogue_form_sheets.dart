import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../../shared/widgets/scrollable_bottom_sheet.dart';
import '../../domain/catalogue_models.dart';
import '../catalogue_controller.dart';

Future<void> showEditBrandSheet(BuildContext context, WidgetRef ref, CatalogueBrand brand) async {
  final nameController = TextEditingController(text: brand.name);
  final shortController = TextEditingController(text: brand.shortName ?? '');
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => ScrollableBottomSheetForm(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Edit brand', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: AppSpacing.md),
          TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Name')),
          TextField(controller: shortController, decoration: const InputDecoration(labelText: 'Short name')),
          const SizedBox(height: AppSpacing.lg),
          FilledButton(
            onPressed: () async {
              await ref.read(catalogueWorkspaceProvider.notifier).updateBrand(brand.id, {
                'name': nameController.text.trim(),
                if (shortController.text.trim().isNotEmpty) 'short_name': shortController.text.trim(),
              });
              if (context.mounted) Navigator.pop(context);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    ),
  );
}

Future<void> showEditLocationSheet(
  BuildContext context,
  WidgetRef ref,
  CatalogueLocation location,
  List<CatalogueLocation> allLocations,
) async {
  final nameController = TextEditingController(text: location.name);
  var locationType = location.locationType;
  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (context) => StatefulBuilder(
      builder: (context, setState) => ScrollableBottomSheetForm(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Edit location', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: AppSpacing.md),
            TextField(controller: nameController, decoration: const InputDecoration(labelText: 'Name')),
            DropdownButtonFormField<String>(
              value: locationType,
              decoration: const InputDecoration(labelText: 'Type'),
              items: const [
                DropdownMenuItem(value: 'retail_floor', child: Text('Retail floor')),
                DropdownMenuItem(value: 'warehouse', child: Text('Warehouse')),
                DropdownMenuItem(value: 'other', child: Text('Other')),
              ],
              onChanged: (v) => setState(() => locationType = v ?? locationType),
            ),
            const SizedBox(height: AppSpacing.lg),
            FilledButton(
              onPressed: () async {
                await ref.read(catalogueWorkspaceProvider.notifier).updateLocation(location.id, {
                  'name': nameController.text.trim(),
                  'location_type': locationType,
                });
                if (context.mounted) Navigator.pop(context);
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    ),
  );
}
