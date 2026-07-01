import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Typography aligned with desktop (Lato 13px body, 600 headings).
abstract final class AppTypography {
  static TextTheme textTheme(Brightness brightness) {
    final base = GoogleFonts.latoTextTheme();
    final color = brightness == Brightness.dark
        ? const Color(0xFFE6EDF3)
        : const Color(0xFF1A2332);

    return base.copyWith(
      bodyLarge: base.bodyLarge?.copyWith(fontSize: 15, height: 1.6, color: color),
      bodyMedium: base.bodyMedium?.copyWith(fontSize: 13, height: 1.6, color: color),
      bodySmall: base.bodySmall?.copyWith(fontSize: 12, height: 1.5, color: color),
      titleLarge: base.titleLarge?.copyWith(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.01,
        color: color,
      ),
      titleMedium: base.titleMedium?.copyWith(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.01,
        color: color,
      ),
      titleSmall: base.titleSmall?.copyWith(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: color,
      ),
      labelLarge: base.labelLarge?.copyWith(fontSize: 13, fontWeight: FontWeight.w600),
      labelMedium: base.labelMedium?.copyWith(fontSize: 12, fontWeight: FontWeight.w600),
      labelSmall: base.labelSmall?.copyWith(
        fontSize: 10,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.08,
      ),
    );
  }
}
