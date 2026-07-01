import 'package:flutter/material.dart';

/// Desktop-aligned design tokens (see apps/desktop/src/index.css).
abstract final class AppColors {
  // Brand
  static const brandNavy = Color(0xFF1A2F52);
  static const brandNavyLight = Color(0xFF2A4572);
  static const brandCoral = Color(0xFFE8684A);

  // Light surfaces
  static const lightBgApp = Color(0xFFEEF1F6);
  static const lightBgSurface = Color(0xFFFFFFFF);
  static const lightBgRaised = Color(0xFFF7F8FB);
  static const lightBgHover = Color(0xFFEEF2F8);
  static const lightBgMuted = Color(0xFFF4F6FA);

  static const lightBorder = Color(0xFFE4E8EF);
  static const lightBorderStrong = Color(0xFFCDD4DF);

  static const lightTextPrimary = Color(0xFF1A2332);
  static const lightTextSecondary = Color(0xFF5A6578);
  static const lightTextTertiary = Color(0xFF8B95A8);
  static const lightTextDisabled = Color(0xFFB4BCC9);

  static const lightPrimary500 = Color(0xFF2B4C7E);
  static const lightPrimary600 = Color(0xFF243F6A);
  static const lightPrimary700 = Color(0xFF1C3356);

  static const lightSuccess = Color(0xFF1B7A3D);
  static const lightSuccessBg = Color(0xFFEDF9F1);
  static const lightWarning = Color(0xFFC45B00);
  static const lightWarningBg = Color(0xFFFFF8EE);
  static const lightDanger = Color(0xFFC62828);
  static const lightDangerBg = Color(0xFFFFF0F0);

  // Dark surfaces
  static const darkBgApp = Color(0xFF0F1419);
  static const darkBgSurface = Color(0xFF161B22);
  static const darkBgRaised = Color(0xFF1C2128);
  static const darkBgHover = Color(0xFF21262D);
  static const darkBgMuted = Color(0xFF141920);

  static const darkBorder = Color(0xFF30363D);
  static const darkBorderStrong = Color(0xFF484F58);

  static const darkTextPrimary = Color(0xFFE6EDF3);
  static const darkTextSecondary = Color(0xFF9BA4B0);
  static const darkTextTertiary = Color(0xFF6E7681);
  static const darkTextDisabled = Color(0xFF484F58);

  static const darkPrimary500 = Color(0xFF5B8FCE);
  static const darkPrimary600 = Color(0xFF7BA8DB);
  static const darkPrimary700 = Color(0xFF9BBFE8);

  static const darkSuccess = Color(0xFF3FB950);
  static const darkSuccessBg = Color(0xFF12261A);
  static const darkWarning = Color(0xFFD29922);
  static const darkWarningBg = Color(0xFF2A1F0A);
  static const darkDanger = Color(0xFFF85149);
  static const darkDangerBg = Color(0xFF2A1214);
}
