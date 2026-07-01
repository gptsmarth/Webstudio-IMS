import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../audit/data/audit_repository.dart';
import '../../../audit/domain/audit_models.dart';
import '../../../auth/presentation/auth_controller.dart';
import '../../domain/inventory_models.dart';
import '../../domain/inventory_permissions.dart' as inv_perms;
import '../inventory_controller.dart';
import 'inventory_action_dialogs.dart';
import 'inventory_status_chip.dart';

class InventoryDetailSheet extends ConsumerStatefulWidget {
  const InventoryDetailSheet({super.key, required this.workspaceProvider});

  final InventoryWorkspaceProvider workspaceProvider;

  @override
  ConsumerState<InventoryDetailSheet> createState() => _InventoryDetailSheetState();
}

class _InventoryDetailSheetState extends ConsumerState<InventoryDetailSheet> {
  List<AuditLogEntry>? _auditEntries;
  bool _auditLoading = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadAudit());
  }

  Future<void> _loadAudit() async {
    final item = ref.read(widget.workspaceProvider).selectedItem;
    if (item == null) return;
    setState(() => _auditLoading = true);
    try {
      final entries = await ref.read(auditRepositoryProvider).listForInventoryItem(item.id);
      if (mounted) {
        setState(() {
          _auditEntries = entries;
          _auditLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _auditLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final workspace = ref.watch(widget.workspaceProvider);
    final item = workspace.selectedItem;
    if (item == null) return const SizedBox.shrink();

    final controller = ref.read(widget.workspaceProvider.notifier);
    final permissions = ref.watch(authControllerProvider).user?.permissions ?? const [];
    final canTransfer = inv_perms.canTransferStockLocation(permissions) &&
        item.status != InventoryStatus.sold &&
        !item.isArchived;
    final canMarkSoldAction = inv_perms.canMarkSold(permissions) &&
        item.status == InventoryStatus.available &&
        !item.isArchived;
    final canEdit = inv_perms.canEditInventory(permissions) && !item.isArchived;
    final canArchive = inv_perms.canArchiveInventory(permissions) && !item.isArchived;
    final canRestore = inv_perms.canRestoreInventory(permissions) && item.isArchived;

    return DraggableScrollableSheet(
      initialChildSize: 0.72,
      minChildSize: 0.45,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) {
        return Material(
          borderRadius: const BorderRadius.vertical(top: Radius.circular(AppSpacing.radiusXl)),
          child: ListView(
            controller: scrollController,
            padding: const EdgeInsets.all(AppSpacing.xl),
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Theme.of(context).dividerColor,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(item.modelName, style: Theme.of(context).textTheme.titleMedium),
                        Text(item.modelNumber, style: Theme.of(context).textTheme.bodySmall),
                      ],
                    ),
                  ),
                  InventoryStatusChip(status: item.status, isArchived: item.isArchived),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(item.serialNumber, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: AppSpacing.lg),
              Wrap(
                spacing: AppSpacing.sm,
                runSpacing: AppSpacing.sm,
                children: [
                  if (canTransfer)
                    OutlinedButton.icon(
                      onPressed: workspace.actionInProgress
                          ? null
                          : () async {
                              final locationId = await showTransferLocationDialog(
                                context,
                                locations: workspace.locations,
                                currentLocationId: item.currentLocationId,
                              );
                              if (locationId != null) await controller.transferSelected(locationId);
                            },
                      icon: const Icon(Icons.swap_horiz, size: 18),
                      label: const Text('Transfer'),
                    ),
                  if (canMarkSoldAction)
                    ElevatedButton.icon(
                      onPressed: workspace.actionInProgress
                          ? null
                          : () async {
                              final request = await showMarkSoldDialog(context, item.serialNumber);
                              if (request != null) await controller.markSelectedSold(request);
                            },
                      icon: const Icon(Icons.point_of_sale, size: 18),
                      label: const Text('Mark sold'),
                    ),
                  if (canEdit)
                    OutlinedButton.icon(
                      onPressed: workspace.actionInProgress
                          ? null
                          : () async {
                              final data = await showEditInventoryDialog(context, item);
                              if (data != null) await controller.updateSelectedItem(data);
                            },
                      icon: const Icon(Icons.edit_outlined, size: 18),
                      label: const Text('Edit'),
                    ),
                  if (canArchive)
                    OutlinedButton.icon(
                      onPressed: workspace.actionInProgress ? null : controller.archiveSelected,
                      icon: const Icon(Icons.archive_outlined, size: 18),
                      label: const Text('Archive'),
                    ),
                  if (canRestore)
                    OutlinedButton.icon(
                      onPressed: workspace.actionInProgress ? null : controller.restoreSelected,
                      icon: const Icon(Icons.unarchive_outlined, size: 18),
                      label: const Text('Restore'),
                    ),
                ],
              ),
              const Divider(height: 32),
              _InfoRow(label: 'Location', value: item.currentLocationName),
              _InfoRow(label: 'Color', value: item.color),
              _InfoRow(label: 'Brand', value: item.brandName),
              _InfoRow(label: 'Specs', value: item.specsLabel),
              _InfoRow(label: 'Added', value: item.createdAt.split('T').first),
              _InfoRow(label: 'Updated', value: item.updatedAt.split('T').first),
              const Divider(height: 32),
              Text('Audit timeline', style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: AppSpacing.sm),
              if (_auditLoading) const LinearProgressIndicator(minHeight: 2),
              if (!_auditLoading && (_auditEntries == null || _auditEntries!.isEmpty))
                Text('No audit entries', style: Theme.of(context).textTheme.bodySmall),
              for (final entry in _auditEntries ?? const <AuditLogEntry>[])
                ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.history, size: 18),
                  title: Text(entry.description),
                  subtitle: Text('${entry.operation} · ${entry.createdAt.split('T').first}'),
                ),
              if (workspace.error != null) ...[
                const SizedBox(height: AppSpacing.md),
                Text(workspace.error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: 110, child: Text(label, style: Theme.of(context).textTheme.bodySmall)),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
