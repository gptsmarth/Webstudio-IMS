import 'package:flutter/material.dart';

import '../../../../shared/widgets/brand_logo_image.dart';
import '../../../../shared/widgets/compact_brand_grid.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../shared/widgets/placeholders.dart';
import '../../domain/inventory_hierarchy.dart';

/// Compact brand tiles with logos — mirrors desktop `StockBrandGrid` (compact).
class StockBrandGrid extends StatelessWidget {
  const StockBrandGrid({
    super.key,
    required this.brands,
    required this.onSelect,
    this.showSoldUnits = false,
  });

  final List<BrandInventorySummary> brands;
  final void Function(BrandInventorySummary brand) onSelect;
  final bool showSoldUnits;

  @override
  Widget build(BuildContext context) {
    if (brands.isEmpty) {
      return const EmptyStateView(
        icon: Icons.inventory_2_outlined,
        title: 'No brands yet',
        message: 'Brands from your catalogue will appear here for stock browsing.',
      );
    }

    return CompactBrandGrid(
      itemCount: brands.length,
      itemBuilder: (context, index) {
        final brand = brands[index];
        final subtitle = showSoldUnits && brand.soldUnits > 0
            ? '${brand.availableUnits} avail · ${brand.soldUnits} sold'
            : '${brand.availableUnits} available';
        return CompactBrandTile(
          brandName: brand.brandName,
          logoFilename: brand.logoFilename,
          subtitle: subtitle,
          onTap: () => onSelect(brand),
        );
      },
    );
  }
}

/// Detailed brand cards for Inventory admin — mirrors desktop `StockBrandGrid` (detailed).
class InventoryBrandCard extends StatelessWidget {
  const InventoryBrandCard({
    super.key,
    required this.brand,
    required this.onTap,
    this.showSoldUnits = true,
  });

  final BrandInventorySummary brand;
  final VoidCallback onTap;
  final bool showSoldUnits;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: theme.dividerColor),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  BrandLogoImage(
                    brandName: brand.brandName,
                    logoFilename: brand.logoFilename,
                    height: 36,
                    maxWidth: 72,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(brand.brandName, style: theme.textTheme.titleMedium),
                  ),
                  Icon(Icons.chevron_right, color: theme.colorScheme.onSurfaceVariant),
                ],
              ),
              const SizedBox(height: 14),
              Row(
                children: [
                  _StatChip(label: 'Available', value: '${brand.availableUnits}'),
                  const SizedBox(width: 8),
                  _StatChip(label: 'Total', value: '${brand.totalUnits}'),
                  if (showSoldUnits && brand.soldUnits > 0) ...[
                    const SizedBox(width: 8),
                    _StatChip(label: 'Sold', value: '${brand.soldUnits}'),
                  ],
                ],
              ),
              if (brand.byLocation.isNotEmpty) ...[
                const SizedBox(height: 12),
                ...brand.byLocation.take(3).map(
                      (row) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: Row(
                          children: [
                            Expanded(child: Text(row.locationName, style: theme.textTheme.bodySmall)),
                            Text('${row.count}', style: theme.textTheme.labelMedium),
                          ],
                        ),
                      ),
                    ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelSmall),
          Text(value, style: Theme.of(context).textTheme.titleSmall),
        ],
      ),
    );
  }
}
