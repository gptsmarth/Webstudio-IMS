import 'package:flutter/material.dart';

import '../../../../core/theme/app_breakpoints.dart';
import '../../../../shared/widgets/brand_logo_image.dart';

/// Small brand logo tile — matches desktop inventory brand grid.
class CompactBrandTile extends StatelessWidget {
  const CompactBrandTile({
    super.key,
    required this.brandName,
    required this.onTap,
    this.logoFilename,
    this.subtitle,
  });

  final String brandName;
  final String? logoFilename;
  final String? subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Material(
      color: colorScheme.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: colorScheme.outlineVariant.withValues(alpha: 0.7)),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(10, 14, 10, 10),
          child: Column(
            children: [
              Expanded(
                child: Center(
                  child: BrandLogoImage(
                    brandName: brandName,
                    logoFilename: logoFilename,
                    height: 52,
                    maxWidth: 92,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                brandName,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
              if (subtitle != null) ...[
                const SizedBox(height: 2),
                Text(
                  subtitle!,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
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

/// Responsive 3-column brand grid for phone (matches desktop compact tiles).
class CompactBrandGrid extends StatelessWidget {
  const CompactBrandGrid({
    super.key,
    required this.itemCount,
    required this.itemBuilder,
    this.padding,
  });

  final int itemCount;
  final Widget Function(BuildContext context, int index) itemBuilder;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final crossAxisCount = AppBreakpoints.gridColumns(context, phone: 3, tablet: 4, desktop: 5);
        return GridView.builder(
          padding: padding ?? const EdgeInsets.fromLTRB(12, 8, 12, 24),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: crossAxisCount,
            mainAxisSpacing: 14,
            crossAxisSpacing: 14,
            childAspectRatio: subtitleAspectRatio,
          ),
          itemCount: itemCount,
          itemBuilder: itemBuilder,
        );
      },
    );
  }

  /// Slightly taller cells when subtitles are shown under brand names.
  static const subtitleAspectRatio = 0.88;
  static const logoOnlyAspectRatio = 0.92;
}
