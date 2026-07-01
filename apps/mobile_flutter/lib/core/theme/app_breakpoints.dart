import 'package:flutter/material.dart';

/// Layout breakpoints aligned with desktop shell + Material adaptive guidance.
abstract final class AppBreakpoints {
  static const double phone = 600;
  static const double tablet = 840;
  static const double desktop = 1200;

  /// Max content width on tablet/desktop for readable line length.
  static const double maxContentWidth = 960;

  static bool isTablet(BuildContext context) =>
      MediaQuery.sizeOf(context).width >= tablet;

  static bool isPhone(BuildContext context) =>
      MediaQuery.sizeOf(context).width < tablet;

  static EdgeInsets pagePadding(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    if (width >= desktop) {
      return const EdgeInsets.symmetric(horizontal: 32, vertical: 24);
    }
    if (width >= tablet) {
      return const EdgeInsets.symmetric(horizontal: 24, vertical: 20);
    }
    return const EdgeInsets.symmetric(horizontal: 16, vertical: 16);
  }

  static int gridColumns(BuildContext context, {int phone = 2, int tablet = 3, int desktop = 4}) {
    final width = MediaQuery.sizeOf(context).width;
    if (width >= AppBreakpoints.desktop) return desktop;
    if (width >= AppBreakpoints.tablet) return tablet;
    return phone;
  }
}
