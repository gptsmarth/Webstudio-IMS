import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/app_config_provider.dart';
import '../constants/api_paths.dart';
import '../errors/api_exception.dart';
import '../network/api_client.dart';
import '../network/connectivity_provider.dart';
import 'version_models.dart';

const _lastCheckKey = 'webstudio_version_last_check';
const _remindLaterKey = 'webstudio_version_remind_later';

final versionRepositoryProvider = Provider<VersionRepository>((ref) {
  return VersionRepository(
    apiClient: ref.watch(apiClientProvider),
    prefs: ref.watch(sharedPreferencesProvider),
    installedVersion: () => ref.read(appConfigProvider).clientVersion,
    isOnline: () => ref.read(connectivityProvider).maybeWhen(data: (value) => value, orElse: () => true),
  );
});

class VersionRepository {
  VersionRepository({
    required ApiClient apiClient,
    required SharedPreferences prefs,
    required String Function() installedVersion,
    required bool Function() isOnline,
  })  : _api = apiClient,
        _prefs = prefs,
        _installedVersion = installedVersion,
        _isOnline = isOnline;

  final ApiClient _api;
  final SharedPreferences _prefs;
  final String Function() _installedVersion;
  final bool Function() _isOnline;

  DateTime? get lastCheckAt {
    final raw = _prefs.getString(_lastCheckKey);
    return raw == null ? null : DateTime.tryParse(raw);
  }

  DateTime? get remindLaterUntil {
    final raw = _prefs.getString(_remindLaterKey);
    return raw == null ? null : DateTime.tryParse(raw);
  }

  MobileVersionInfo? get cachedRemote {
    final raw = _prefs.getString(_cachedRemoteKey);
    if (raw == null || raw.isEmpty) return null;
    try {
      final parts = raw.split('|');
      if (parts.length < 3) return null;
      return MobileVersionInfo(
        latestVersion: parts[0],
        minSupportedVersion: parts[1],
        backendVersion: parts[2],
        releaseDate: parts.length > 3 && parts[3].isNotEmpty ? parts[3] : null,
        releaseNotes: parts.length > 4 && parts[4].isNotEmpty ? parts[4] : null,
        apkDownloadUrl: parts.length > 5 && parts[5].isNotEmpty ? parts[5] : null,
        releaseChannel: parts.length > 6 && parts[6].isNotEmpty ? parts[6] : 'stable',
      );
    } catch (_) {
      return null;
    }
  }

  Future<VersionCheckOutcome> checkForUpdates({bool force = false}) async {
    final installed = _installedVersion();
    if (!_isOnline()) {
      return VersionCheckOutcome.error(
        installedVersion: installed,
        errorMessage: 'No internet connection.',
        checkedAt: lastCheckAt,
      );
    }

    if (!force && !_shouldCheckNow()) {
      return VersionCheckOutcome.upToDate(
        installedVersion: installed,
        remote: cachedRemote,
        checkedAt: lastCheckAt,
      );
    }

    try {
      final payload = await _api.get<Map<String, dynamic>>(
        ApiPaths.version,
        parser: (json) => Map<String, dynamic>.from(json! as Map),
      );
      final remote = MobileVersionInfo.fromPayload(payload);
      await _prefs.setString(_lastCheckKey, DateTime.now().toIso8601String());
      await _prefs.setString(_cachedRemoteKey, _serializeRemote(remote));
      final kind = resolveUpdateKind(installedVersion: installed, remote: remote);
      return VersionCheckOutcome(
        kind: kind,
        installedVersion: installed,
        remote: remote,
        checkedAt: DateTime.now(),
      );
    } on ApiException catch (error) {
      return VersionCheckOutcome.error(
        installedVersion: installed,
        errorMessage: error.message,
        remote: cachedRemote,
        checkedAt: lastCheckAt,
      );
    } catch (_) {
      return VersionCheckOutcome.error(
        installedVersion: installed,
        errorMessage: 'Could not verify the latest version.',
        remote: cachedRemote,
        checkedAt: lastCheckAt,
      );
    }
  }

  Future<void> remindLater({Duration delay = const Duration(hours: 24)}) async {
    await _prefs.setString(_remindLaterKey, DateTime.now().add(delay).toIso8601String());
  }

  bool shouldSuppressOptionalPrompt() {
    final until = remindLaterUntil;
    return until != null && DateTime.now().isBefore(until);
  }

  bool _shouldCheckNow() {
    final last = lastCheckAt;
    if (last == null) return true;
    return DateTime.now().difference(last) >= const Duration(hours: 24);
  }

  static const _cachedRemoteKey = 'webstudio_version_cached_remote';

  String _serializeRemote(MobileVersionInfo remote) {
    return [
      remote.latestVersion,
      remote.minSupportedVersion,
      remote.backendVersion,
      remote.releaseDate ?? '',
      remote.releaseNotes ?? '',
      remote.apkDownloadUrl ?? '',
      remote.releaseChannel,
    ].join('|');
  }
}
