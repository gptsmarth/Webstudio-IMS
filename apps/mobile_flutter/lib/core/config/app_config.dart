import 'dart:io';

import 'package:flutter/foundation.dart';

/// Runtime configuration — mirrors desktop ConfigService defaults.
class AppConfig {
  const AppConfig({
    required this.apiBaseUrl,
    required this.clientVersion,
    required this.clientPlatform,
  });

  final String apiBaseUrl;
  final String clientVersion;
  final String clientPlatform;

  /// Optional compile-time default for production APK/IPA builds, e.g.
  /// `--dart-define=WEBSTUDIO_DEFAULT_API_URL=http://192.168.29.100:8000`
  static const defaultApiUrlFromBuild = String.fromEnvironment(
    'WEBSTUDIO_DEFAULT_API_URL',
    defaultValue: '',
  );

  static const defaultAndroidEmulatorUrl = 'http://10.0.2.2:8000';
  static const defaultLocalUrl = 'http://127.0.0.1:8000';

  /// Android emulator loopback — never valid on a physical shop phone.
  static bool isEmulatorLoopbackUrl(String url) {
    final normalized = url.trim().toLowerCase();
    return normalized.contains('10.0.2.2');
  }

  static bool get hasConfiguredServerUrl {
    final url = defaultApiUrlFromBuild.trim();
    return url.isNotEmpty;
  }

  static List<String> discoveryCandidates() {
    final candidates = <String>[];

    if (defaultApiUrlFromBuild.isNotEmpty) {
      candidates.add(defaultApiUrlFromBuild);
    }

    // Shop LAN probes first — physical phones must not waste time on localhost.
    candidates.addAll([
      suggestedShopServerUrl,
      'http://192.168.1.100:8000',
      'http://192.168.0.100:8000',
      'http://192.168.1.1:8000',
    ]);

    // Emulator alias — debug / Android Studio only.
    if (Platform.isAndroid && kDebugMode) {
      candidates.add(defaultAndroidEmulatorUrl);
    }

    if (!Platform.isAndroid || kDebugMode) {
      candidates.addAll([
        'http://127.0.0.1:8000',
        'http://localhost:8000',
        defaultLocalUrl,
      ]);
    }

    return _uniqueUrls(candidates);
  }

  static const suggestedShopServerUrl = 'http://192.168.29.100:8000';

  /// Prefill for manual connection when auto-discovery fails (shop LAN default).
  static String suggestedManualServerUrl() {
    if (defaultApiUrlFromBuild.isNotEmpty) {
      return defaultApiUrlFromBuild;
    }
    return suggestedShopServerUrl;
  }

  static String defaultApiBaseUrl() {
    if (defaultApiUrlFromBuild.isNotEmpty) {
      return defaultApiUrlFromBuild;
    }
    if (kIsWeb) return defaultLocalUrl;
    if (Platform.isAndroid) {
      // Physical devices must not default to the emulator alias.
      return kDebugMode ? defaultAndroidEmulatorUrl : '';
    }
    return defaultLocalUrl;
  }

  /// True when bootstrap should skip a single-URL health probe and open connection setup.
  static bool shouldOpenConnectionSetupFirst(String apiBaseUrl) {
    final trimmed = apiBaseUrl.trim();
    if (trimmed.isEmpty) return true;
    if (Platform.isAndroid && !kDebugMode && isEmulatorLoopbackUrl(trimmed)) {
      return true;
    }
    return false;
  }

  static List<String> _uniqueUrls(List<String> urls) {
    final seen = <String>{};
    final unique = <String>[];
    for (final url in urls) {
      final normalized = url.trim();
      if (normalized.isEmpty || seen.contains(normalized)) continue;
      seen.add(normalized);
      unique.add(normalized);
    }
    return unique;
  }

  AppConfig copyWith({
    String? apiBaseUrl,
    String? clientVersion,
    String? clientPlatform,
  }) {
    return AppConfig(
      apiBaseUrl: apiBaseUrl ?? this.apiBaseUrl,
      clientVersion: clientVersion ?? this.clientVersion,
      clientPlatform: clientPlatform ?? this.clientPlatform,
    );
  }
}
