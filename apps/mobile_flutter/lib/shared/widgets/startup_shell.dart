import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../shared/widgets/webstudio_logo.dart';

class StartupBrandPanel extends StatelessWidget {
  const StartupBrandPanel({
    super.key,
    this.footerRight = 'WEBSTUDIO IMS',
  });

  final String footerRight;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xxl, vertical: AppSpacing.xxxl),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [AppColors.brandNavy, AppColors.brandNavyLight],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Column(
        children: [
          const WebstudioLogo(height: 52, forDarkBackground: true),
          const SizedBox(height: AppSpacing.lg),
          Text(
            'Inventory Management System',
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  color: Colors.white70,
                  letterSpacing: 0.04,
                ),
          ),
          const Spacer(),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'WEBSTUDIO',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: Colors.white54,
                      letterSpacing: 0.12,
                    ),
              ),
              Text(
                footerRight,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: Colors.white70,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.08,
                    ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class StartupShellLayout extends StatelessWidget {
  const StartupShellLayout({
    super.key,
    required this.child,
    this.footerRight = 'SETUP',
  });

  final Widget child;
  final String footerRight;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            SizedBox(
              height: 180,
              child: StartupBrandPanel(footerRight: footerRight),
            ),
            Expanded(child: child),
          ],
        ),
      ),
    );
  }
}
