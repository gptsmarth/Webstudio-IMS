import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_spacing.dart';
import '../../../media/presentation/product_image_sheet.dart';
import '../../domain/inventory_hierarchy.dart';
import '../../domain/stock_model_card_utils.dart';

class StockModelCard extends ConsumerStatefulWidget {
  const StockModelCard({
    super.key,
    required this.row,
    required this.onTap,
    this.brandName,
    this.showPrice = false,
    this.showAdminPrices = false,
  });

  final ModelInventoryRow row;
  final String? brandName;
  final VoidCallback onTap;
  final bool showPrice;
  final bool showAdminPrices;

  @override
  ConsumerState<StockModelCard> createState() => _StockModelCardState();
}

class _StockModelCardState extends ConsumerState<StockModelCard> {
  var _specsExpanded = false;

  @override
  void didUpdateWidget(covariant StockModelCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.row.model.id != widget.row.model.id) {
      _specsExpanded = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final model = widget.row.model;
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final specLines = orderStockCardSpecLines(buildStockModelSpecLines(model));
    final visibleSpecs = _specsExpanded
        ? specLines
        : specLines.take(stockCardCollapsedSpecCount).toList();
    final hasMoreSpecs = specLines.length > stockCardCollapsedSpecCount;
    final screenHint = displayScreenHint(model);
    final available = widget.row.availableUnits;
    final badgeBackground = available > 0 ? const Color(0xFFDCFCE7) : const Color(0xFFF3F4F6);
    final badgeForeground = available > 0 ? const Color(0xFF166534) : const Color(0xFF6B7280);
    final badgeBorder = available > 0 ? const Color(0xFF86EFAC) : const Color(0xFFE5E7EB);

    return Material(
      color: colorScheme.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: colorScheme.outlineVariant.withValues(alpha: 0.65)),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: widget.onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              color: colorScheme.surfaceContainerLow,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Align(
                alignment: Alignment.centerRight,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: badgeBackground,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: badgeBorder),
                  ),
                  child: Text(
                    stockAvailabilityLabel(available),
                    style: theme.textTheme.labelSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: badgeForeground,
                    ),
                  ),
                ),
              ),
            ),
            SizedBox(
              height: 148,
              width: double.infinity,
              child: model.productImageUrl != null && model.productImageUrl!.isNotEmpty
                  ? Padding(
                      padding: const EdgeInsets.fromLTRB(10, 10, 10, 4),
                      child: ProductModelImage(
                        key: ValueKey(model.id),
                        imageUrl: model.productImageUrl!,
                        height: 134,
                        bordered: false,
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                      ),
                    )
                  : ColoredBox(
                      color: colorScheme.surfaceContainerLowest,
                      child: Center(
                        child: Icon(productCategoryPlaceholderIcon(model), size: 52, color: colorScheme.outline),
                      ),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (screenHint != null) ...[
                    Text(
                      screenHint,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                  ],
                  Text(
                    displayModelTitle(widget.brandName ?? '', model.modelName),
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      height: 1.3,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    modelNumberLine(model),
                    style: theme.textTheme.labelMedium?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Divider(height: 1, color: colorScheme.outlineVariant.withValues(alpha: 0.5)),
                  const SizedBox(height: 8),
                  if (widget.showAdminPrices) ...[
                    _AdminPriceLine(
                      label: 'Selling',
                      value: formatCardPrice(model.sellingPrice),
                      emphasized: true,
                    ),
                    const SizedBox(height: 6),
                    _AdminPriceLine(
                      label: 'Purchase',
                      value: formatCardPrice(model.purchasePrice),
                    ),
                    const SizedBox(height: 8),
                    Divider(height: 1, color: colorScheme.outlineVariant.withValues(alpha: 0.5)),
                    const SizedBox(height: 8),
                  ] else if (widget.showPrice) ...[
                    Text(
                      formatCardPrice(model.sellingPrice),
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: model.sellingPrice == null || model.sellingPrice! <= 0
                            ? colorScheme.onSurfaceVariant
                            : const Color(0xFFEA580C),
                        fontWeight: model.sellingPrice == null || model.sellingPrice! <= 0 ? FontWeight.w600 : FontWeight.w800,
                        fontSize: model.sellingPrice == null || model.sellingPrice! <= 0 ? 18 : null,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Divider(height: 1, color: colorScheme.outlineVariant.withValues(alpha: 0.5)),
                    const SizedBox(height: 8),
                  ],
                  if (specLines.isNotEmpty) ...[
                    for (final line in visibleSpecs)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('• ', style: theme.textTheme.bodySmall?.copyWith(height: 1.35)),
                            Expanded(
                              child: Text(
                                formatSpecBullet(line),
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: colorScheme.onSurfaceVariant,
                                  height: 1.35,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    if (hasMoreSpecs)
                      TextButton.icon(
                        onPressed: () => setState(() => _specsExpanded = !_specsExpanded),
                        style: TextButton.styleFrom(
                          padding: EdgeInsets.zero,
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          visualDensity: VisualDensity.compact,
                        ),
                        icon: Icon(
                          _specsExpanded ? Icons.expand_less : Icons.expand_more,
                          size: 16,
                        ),
                        label: Text(_specsExpanded ? 'See less' : 'See more'),
                      ),
                    const SizedBox(height: 8),
                  ],
                  Row(
                    children: [
                      Text(
                        'View units & details',
                        style: theme.textTheme.labelLarge?.copyWith(color: colorScheme.primary),
                      ),
                      const SizedBox(width: 4),
                      Icon(Icons.arrow_forward, size: 16, color: colorScheme.primary),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AdminPriceLine extends StatelessWidget {
  const _AdminPriceLine({
    required this.label,
    required this.value,
    this.emphasized = false,
  });

  final String label;
  final String value;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 72,
          child: Text(
            label,
            style: theme.textTheme.labelMedium?.copyWith(
              color: colorScheme.onSurfaceVariant,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        Expanded(
          child: Text(
            value,
            style: theme.textTheme.titleSmall?.copyWith(
              color: emphasized && value != 'Price on request'
                  ? const Color(0xFFEA580C)
                  : colorScheme.onSurface,
              fontWeight: emphasized ? FontWeight.w800 : FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}
