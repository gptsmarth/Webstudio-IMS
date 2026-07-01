import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';

class WebstudioLogo extends StatelessWidget {
  const WebstudioLogo({
    super.key,
    this.height = 40,
    this.forDarkBackground = false,
  });

  final double height;
  final bool forDarkBackground;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final asset = (forDarkBackground || !isDark)
        ? 'assets/images/logo-dark.svg'
        : 'assets/images/logo.svg';

    return SvgPicture.asset(
      asset,
      height: height,
      semanticsLabel: 'WEBSTUDIO IMS',
      placeholderBuilder: (_) => _FallbackLogo(height: height),
    );
  }
}

class _FallbackLogo extends StatelessWidget {
  const _FallbackLogo({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(Icons.inventory_2_outlined, size: height, color: AppColors.brandCoral),
        const SizedBox(width: AppSpacing.sm),
        Text(
          'WEBSTUDIO',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
                letterSpacing: 0.04,
              ),
        ),
      ],
    );
  }
}
