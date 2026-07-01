import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _themeKey = 'webstudio_theme_mode';

enum AppThemeMode { light, dark, system }

final themeModeProvider = StateNotifierProvider<ThemeModeController, ThemeMode>((ref) {
  throw UnimplementedError('themeModeProvider must be overridden in bootstrap');
});

class ThemeModeController extends StateNotifier<ThemeMode> {
  ThemeModeController(this._prefs) : super(_loadInitial(_prefs));

  final SharedPreferences _prefs;

  static ThemeMode _loadInitial(SharedPreferences prefs) {
    final raw = prefs.getString(_themeKey);
    return switch (raw) {
      'dark' => ThemeMode.dark,
      'light' => ThemeMode.light,
      _ => ThemeMode.system,
    };
  }

  Future<void> setMode(AppThemeMode mode) async {
    final themeMode = switch (mode) {
      AppThemeMode.light => ThemeMode.light,
      AppThemeMode.dark => ThemeMode.dark,
      AppThemeMode.system => ThemeMode.system,
    };
    state = themeMode;
    await _prefs.setString(_themeKey, mode.name);
  }
}
