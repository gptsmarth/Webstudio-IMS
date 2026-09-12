import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/rbac/mobile_navigation.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../auth/presentation/auth_controller.dart';
import '../../../media/presentation/product_image_sheet.dart';
import '../../../../core/rbac/role_permissions.dart';
import '../../domain/inventory_models.dart';
import '../../domain/inventory_permissions.dart' as inv_perms;
import '../../domain/stock_model_card_utils.dart';
import '../inventory_controller.dart';
import 'inventory_action_dialogs.dart';
import 'inventory_status_chip.dart';
import 'product_model_form_sheet.dart';

class StockModelDetailView extends ConsumerWidget {
  const StockModelDetailView({
    super.key,
    required this.model,
    required this.brandName,
    this.brandLogoFilename,
    required this.units,
    required this.locations,
    required this.onSelectUnit,
    required this.brands,
    required this.workspaceProvider,
    this.actionInProgress = false,
    this.inventoryAdminMode = false,
    this.showSellingPrice = true,
    this.showAsusPrice = false,
  });

  final ProductModel model;
  final String brandName;
  final String? brandLogoFilename;
  final List<InventoryItem> units;
  final List<Location> locations;
  final List<Brand> brands;
  final StateNotifierProvider<InventoryWorkspaceController, InventoryWorkspaceState> workspaceProvider;
  final void Function(InventoryItem item) onSelectUnit;
  final bool actionInProgress;
  final bool inventoryAdminMode;
  final bool showSellingPrice;
  final bool showAsusPrice;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final permissions = effectivePermissions(ref.watch(authControllerProvider).user);
    final canTransfer = inv_perms.canTransferStockLocation(permissions);
    final canMarkSold = inv_perms.canMarkSold(permissions);
    final canDeleteSerial = inv_perms.canArchiveInventory(permissions);
    final canEditFromStock = canEditStockProductModel(permissions);
    final canDeleteModel = inv_perms.canDeleteProductModels(permissions) &&
        ref.watch(workspaceProvider).inventoryAdminMode;
    final activeUnits = units.where((item) => !item.isArchived).toList();
    final available = activeUnits.where((item) => item.status != InventoryStatus.sold).toList();
    final displayUnits = inventoryAdminMode ? activeUnits : available;
    final priceLabel = formatDetailPrice(model.sellingPrice);
    final purchaseLabel = formatCardPrice(model.purchasePrice);
    final sellingLabel = formatCardPrice(model.sellingPrice);
    final isAsusModel = model.isAsusLaptop;
    final asusPriceLabel = isAsusModel ? formatLivePrice(model.livePrice) : null;
    final specLines = buildStockModelSpecLines(model);
    final notesText = modelDescriptionText(model.notes);
    final title = displayModelTitle(brandName, model.modelName);
    const editLabel = 'Edit model & price';

    return ListView(
      padding: const EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.md, AppSpacing.md, 96),
      children: [
        Card(
          clipBehavior: Clip.antiAlias,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.lg, AppSpacing.lg, 0),
                child: model.productImageUrl != null && model.productImageUrl!.isNotEmpty
                    ? ProductModelImage(
                        imageUrl: model.productImageUrl!,
                        height: 220,
                        allowFullscreen: true,
                        modelName: title,
                      )
                    : Container(
                        height: 180,
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surfaceContainerLow,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: Theme.of(context).colorScheme.outlineVariant.withValues(alpha: 0.45),
                          ),
                        ),
                        child: Icon(
                          productCategoryPlaceholderIcon(model),
                          size: 72,
                          color: Theme.of(context).colorScheme.outline,
                        ),
                      ),
              ),
              Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (brandName.isNotEmpty)
                      Text(
                        brandName.toUpperCase(),
                        style: Theme.of(context).textTheme.labelMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.6,
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                      ),
                    if (brandName.isNotEmpty) const SizedBox(height: 8),
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                            height: 1.25,
                          ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      modelNumberLine(model),
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                    ),
                    if (canEditFromStock || canDeleteModel) ...[
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 4,
                        runSpacing: 0,
                        alignment: WrapAlignment.end,
                        children: [
                          if (canEditFromStock)
                            TextButton.icon(
                              onPressed: actionInProgress
                                  ? null
                                  : () => _editFullModel(context, ref),
                              icon: const Icon(Icons.edit_outlined, size: 18),
                              label: const Text(editLabel),
                            ),
                          if (canDeleteModel)
                            TextButton.icon(
                              onPressed: actionInProgress ? null : () => _deleteModel(context, ref),
                              icon: Icon(Icons.delete_outline, size: 18, color: Theme.of(context).colorScheme.error),
                              label: Text('Delete', style: TextStyle(color: Theme.of(context).colorScheme.error)),
                            ),
                        ],
                      ),
                    ],
                    if (inventoryAdminMode) ...[
                      const SizedBox(height: 12),
                      _AdminPricePanel(
                        sellingLabel: sellingLabel,
                        purchaseLabel: purchaseLabel,
                      ),
                    ] else if ((showSellingPrice && priceLabel != null) ||
                        (showAsusPrice && isAsusModel)) ...[
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          if (showSellingPrice && priceLabel != null)
                            _PriceChip(
                              label: 'Selling price',
                              value: priceLabel,
                              valueColor: const Color(0xFFEA580C),
                              background: const Color(0xFFEA580C).withValues(alpha: 0.08),
                              border: const Color(0xFFEA580C).withValues(alpha: 0.2),
                            ),
                          if (showAsusPrice && isAsusModel)
                            _PriceChip(
                              label: 'ASUS price',
                              value: asusPriceLabel ?? 'NA',
                              valueColor: Theme.of(context).colorScheme.onSurface,
                              background: Theme.of(context).colorScheme.surfaceContainerHighest,
                              border: Theme.of(context).dividerColor,
                              subtitle: model.livePriceUpdatedAt != null
                                  ? 'as of ${formatRelativeTime(model.livePriceUpdatedAt!)}'
                                  : null,
                            ),
                        ],
                      ),
                    ],
                    const SizedBox(height: 16),
                    _SpecGrid(lines: specLines),
                    if (notesText.isNotEmpty) ...[
                      const SizedBox(height: 16),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surfaceContainerHighest,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: Theme.of(context).dividerColor),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'ADDITIONAL DETAILS & DESCRIPTION',
                              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 0.4,
                                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                                  ),
                            ),
                            const SizedBox(height: 6),
                            Text(notesText),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 12),
                    Text(
                      '${available.length} unit${available.length == 1 ? '' : 's'} available',
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
        Text('Serial numbers', style: Theme.of(context).textTheme.titleMedium),
        Text(
          inventoryAdminMode
              ? '${activeUnits.length} active unit${activeUnits.length == 1 ? '' : 's'}'
              : '${available.length} active unit${available.length == 1 ? '' : 's'}',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
        const SizedBox(height: AppSpacing.sm),
        if (displayUnits.isEmpty)
          const Card(
            child: Padding(
              padding: EdgeInsets.all(AppSpacing.lg),
              child: Text('No serial numbers for this model.'),
            ),
          )
        else
          Card(
            child: Column(
              children: [
                if (inventoryAdminMode)
                  const Padding(
                    padding: EdgeInsets.fromLTRB(AppSpacing.md, AppSpacing.sm, AppSpacing.md, 0),
                    child: Row(
                      children: [
                        Expanded(flex: 3, child: Text('Serial', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12))),
                        Expanded(flex: 2, child: Text('Status', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12))),
                        Expanded(flex: 2, child: Text('Actions', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12))),
                      ],
                    ),
                  ),
                for (var i = 0; i < displayUnits.length; i++) ...[
                  if (i > 0) const Divider(height: 1),
                  _SerialRow(
                    item: displayUnits[i],
                    inventoryAdminMode: inventoryAdminMode,
                    canTransfer: canTransfer && displayUnits[i].status != InventoryStatus.sold,
                    canMarkSold: canMarkSold && displayUnits[i].status == InventoryStatus.available,
                    canDelete: canDeleteSerial &&
                        displayUnits[i].status != InventoryStatus.sold &&
                        !displayUnits[i].isArchived,
                    actionInProgress: actionInProgress,
                    onTap: () => onSelectUnit(displayUnits[i]),
                    onTransfer: () => _transferUnit(context, ref, displayUnits[i]),
                    onMarkSold: () => _markSoldUnit(context, ref, displayUnits[i]),
                    onDelete: () => _deleteUnit(context, ref, displayUnits[i]),
                  ),
                ],
              ],
            ),
          ),
      ],
    );
  }

  Future<void> _editFullModel(BuildContext context, WidgetRef ref) async {
    await showProductModelFormSheet(
      context,
      ref,
      workspaceProvider: workspaceProvider,
      existing: model,
    );
    // Form already applies an optimistic model update; no full workspace reload.
  }

  Future<void> _deleteModel(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete model?'),
        content: Text(
          'Delete ${model.modelName} and all in-stock serial numbers for this model? '
          'Past sales records are not changed.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    await ref.read(workspaceProvider.notifier).deleteProductModel(model.id);
  }

  Future<void> _transferUnit(BuildContext context, WidgetRef ref, InventoryItem item) async {
    final locationId = await showTransferLocationDialog(
      context,
      locations: locations,
      currentLocationId: item.currentLocationId,
    );
    if (locationId == null) return;
    await ref.read(workspaceProvider.notifier).transferItem(item.id, locationId);
  }

  Future<void> _markSoldUnit(BuildContext context, WidgetRef ref, InventoryItem item) async {
    final request = await showMarkSoldDialog(
      context,
      item.serialNumber,
      defaultSaleAmount: model.sellingPrice,
    );
    if (request == null || !context.mounted) return;
    await ref.read(workspaceProvider.notifier).markItemSold(item.id, request);
    if (!context.mounted) return;
    final error = ref.read(workspaceProvider).error;
    final messenger = ScaffoldMessenger.of(context);
    if (error != null) {
      messenger.showSnackBar(SnackBar(content: Text(error)));
    } else {
      messenger.showSnackBar(SnackBar(content: Text('${item.serialNumber} marked as sold.')));
    }
  }

  Future<void> _deleteUnit(BuildContext context, WidgetRef ref, InventoryItem item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete serial?'),
        content: Text(
          'Remove ${item.serialNumber} from live stock?\n\n'
          'Available count will drop by one. Sales history is not changed — sold units cannot be deleted.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirmed != true || !context.mounted) return;
    await ref.read(workspaceProvider.notifier).deleteInventoryItem(item.id);
    if (!context.mounted) return;
    final error = ref.read(workspaceProvider).error;
    final messenger = ScaffoldMessenger.of(context);
    if (error != null) {
      messenger.showSnackBar(SnackBar(content: Text(error)));
    } else {
      messenger.showSnackBar(SnackBar(content: Text('${item.serialNumber} removed from stock.')));
    }
  }
}

class _PriceChip extends StatelessWidget {
  const _PriceChip({
    required this.label,
    required this.value,
    required this.valueColor,
    required this.background,
    required this.border,
    this.subtitle,
  });

  final String label;
  final String value;
  final Color valueColor;
  final Color background;
  final Color border;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label.toUpperCase(),
            style: theme.textTheme.labelSmall?.copyWith(
              fontWeight: FontWeight.w700,
              letterSpacing: 0.4,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: theme.textTheme.headlineSmall?.copyWith(
              color: valueColor,
              fontWeight: FontWeight.w800,
            ),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 2),
            Text(
              subtitle!,
              style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ],
      ),
    );
  }
}

class _AdminPricePanel extends StatelessWidget {
  const _AdminPricePanel({
    required this.sellingLabel,
    required this.purchaseLabel,
  });

  final String sellingLabel;
  final String purchaseLabel;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: theme.dividerColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'PRICING',
            style: theme.textTheme.labelSmall?.copyWith(
              fontWeight: FontWeight.w700,
              letterSpacing: 0.4,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Selling', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                    const SizedBox(height: 4),
                    Text(
                      sellingLabel,
                      style: theme.textTheme.titleLarge?.copyWith(
                        color: sellingLabel == 'Price on request' ? theme.colorScheme.onSurfaceVariant : const Color(0xFFEA580C),
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Purchase', style: theme.textTheme.labelMedium?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
                    const SizedBox(height: 4),
                    Text(
                      purchaseLabel,
                      style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SpecGrid extends StatelessWidget {
  const _SpecGrid({required this.lines});

  final List<StockModelSpecLine> lines;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: lines
          .map(
            (line) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 100,
                    child: Text(line.label, style: Theme.of(context).textTheme.labelMedium),
                  ),
                  Expanded(child: Text(line.value)),
                ],
              ),
            ),
          )
          .toList(),
    );
  }
}

class _SerialRow extends StatelessWidget {
  const _SerialRow({
    required this.item,
    required this.inventoryAdminMode,
    required this.canTransfer,
    required this.canMarkSold,
    required this.canDelete,
    required this.actionInProgress,
    required this.onTap,
    required this.onTransfer,
    required this.onMarkSold,
    required this.onDelete,
  });

  final InventoryItem item;
  final bool inventoryAdminMode;
  final bool canTransfer;
  final bool canMarkSold;
  final bool canDelete;
  final bool actionInProgress;
  final VoidCallback onTap;
  final VoidCallback onTransfer;
  final VoidCallback onMarkSold;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    if (inventoryAdminMode) {
      return InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                flex: 3,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item.serialNumber,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                    ),
                    const SizedBox(height: 4),
                    Text(item.color.isEmpty ? '—' : item.color),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Icon(Icons.place_outlined, size: 14, color: Theme.of(context).colorScheme.outline),
                        const SizedBox(width: 4),
                        Flexible(child: Text(item.currentLocationName)),
                      ],
                    ),
                  ],
                ),
              ),
              Expanded(
                flex: 2,
                child: Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: InventoryStatusChip(status: item.status, isArchived: item.isArchived),
                ),
              ),
              Expanded(
                flex: 2,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    if (canMarkSold)
                      TextButton(
                        onPressed: actionInProgress ? null : onMarkSold,
                        style: TextButton.styleFrom(
                          padding: EdgeInsets.zero,
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: const Text('Mark sold'),
                      ),
                    if (canTransfer)
                      IconButton(
                        tooltip: 'Transfer location',
                        onPressed: actionInProgress ? null : onTransfer,
                        icon: const Icon(Icons.swap_horiz, size: 20),
                      ),
                    if (canDelete)
                      IconButton(
                        tooltip: 'Delete serial',
                        onPressed: actionInProgress ? null : onDelete,
                        icon: Icon(Icons.delete_outline, size: 20, color: Theme.of(context).colorScheme.error),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
    }

    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.serialNumber,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Text(item.color.isEmpty ? '—' : item.color),
                      const SizedBox(width: 8),
                      Icon(Icons.place_outlined, size: 14, color: Theme.of(context).colorScheme.outline),
                      const SizedBox(width: 4),
                      Flexible(child: Text(item.currentLocationName)),
                    ],
                  ),
                ],
              ),
            ),
            if (canTransfer)
              IconButton(
                tooltip: 'Transfer location',
                onPressed: actionInProgress ? null : onTransfer,
                icon: const Icon(Icons.swap_horiz),
              ),
            if (canDelete)
              IconButton(
                tooltip: 'Delete serial',
                onPressed: actionInProgress ? null : onDelete,
                icon: Icon(Icons.delete_outline, color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      ),
    );
  }
}
