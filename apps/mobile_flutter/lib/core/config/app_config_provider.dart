import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config.dart';

const _apiUrlKey = 'webstudio_api_url';

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden in bootstrap');
});

final appConfigProvider = StateNotifierProvider<AppConfigController, AppConfig>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return AppConfigController(prefs);
});

class AppConfigController extends StateNotifier<AppConfig> {
  AppConfigController(this._prefs)
      : super(
          AppConfig(
            apiBaseUrl: _prefs.getString(_apiUrlKey) ?? AppConfig.defaultApiBaseUrl(),
            clientVersion: '0.1.0',
            clientPlatform: _resolveClientPlatform(),
          ),
        ) {
    _loadPackageInfo();
  }

  final SharedPreferences _prefs;

  Future<void> _loadPackageInfo() async {
    try {
      final info = await PackageInfo.fromPlatform();
      state = state.copyWith(clientVersion: info.version);
    } catch (_) {
      // Tests may run without platform bindings.
    }
  }

  Future<void> setApiBaseUrl(String url) async {
    final normalized = url.trim().replaceAll(RegExp(r'/+$'), '');
    state = state.copyWith(apiBaseUrl: normalized);
    await _prefs.setString(_apiUrlKey, normalized);
  }

  Future<bool> probeHealth(Future<bool> Function(String baseUrl) probe) async {
    for (final candidate in AppConfig.discoveryCandidates()) {
      if (await probe(candidate)) {
        await setApiBaseUrl(candidate);
        return true;
      }
    }
    return false;
  }
}

String _resolveClientPlatform() {
  if (kIsWeb) return 'web_mobile';
  if (Platform.isIOS) return 'ios_mobile';
  if (Platform.isAndroid) return 'android_mobile';
  return 'mobile';
}
