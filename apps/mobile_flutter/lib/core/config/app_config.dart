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

  static const defaultAndroidEmulatorUrl = 'http://10.0.2.2:8000';
  static const defaultLocalUrl = 'http://127.0.0.1:8000';

  static List<String> discoveryCandidates() {
    return [
      if (Platform.isAndroid) defaultAndroidEmulatorUrl,
      'http://127.0.0.1:8000',
      'http://localhost:8000',
      'http://192.168.1.100:8000',
      'http://192.168.1.1:8000',
      if (!Platform.isAndroid) defaultLocalUrl,
    ];
  }

  static String defaultApiBaseUrl() {
    if (kIsWeb) return defaultLocalUrl;
    if (Platform.isAndroid) return defaultAndroidEmulatorUrl;
    return defaultLocalUrl;
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
