import '../network/json_map.dart';

enum VersionUpdateKind { upToDate, optionalUpdate, mandatoryUpdate }

class ClientUpdateArtifact {
  const ClientUpdateArtifact({
    required this.name,
    required this.downloadUrl,
    this.sha256,
    this.sizeBytes,
  });

  factory ClientUpdateArtifact.fromJson(Map<String, dynamic>? json) {
    if (json == null) {
      return const ClientUpdateArtifact(name: '', downloadUrl: '');
    }
    return ClientUpdateArtifact(
      name: json['name'] as String? ?? '',
      downloadUrl: json['download_url'] as String? ?? '',
      sha256: json['sha256'] as String?,
      sizeBytes: json['size_bytes'] as int?,
    );
  }

  final String name;
  final String downloadUrl;
  final String? sha256;
  final int? sizeBytes;
}

class PlatformVersionIdentity {
  const PlatformVersionIdentity({
    required this.version,
    required this.buildNumber,
    required this.gitCommit,
    required this.releaseChannel,
    required this.databaseRevision,
    this.gitShort,
    this.releaseDate,
  });

  factory PlatformVersionIdentity.fromJson(Map<String, dynamic> payload) {
    return PlatformVersionIdentity(
      version: payload['version'] as String? ?? payload['backend_version'] as String? ?? '0.0.0',
      buildNumber: payload['build_number'] as int? ?? 0,
      gitCommit: payload['git_commit'] as String? ?? '—',
      gitShort: payload['git_short'] as String?,
      releaseDate: payload['release_date'] as String?,
      releaseChannel: payload['release_channel'] as String? ?? 'stable',
      databaseRevision: payload['database_revision'] as String? ?? '—',
    );
  }

  final String version;
  final int buildNumber;
  final String gitCommit;
  final String? gitShort;
  final String? releaseDate;
  final String releaseChannel;
  final String databaseRevision;
}

class MobileVersionInfo {
  const MobileVersionInfo({
    required this.latestVersion,
    required this.minSupportedVersion,
    required this.backendVersion,
    this.releaseDate,
    this.releaseNotes,
    this.apkDownloadUrl,
    this.releaseChannel = 'stable',
    this.distributionMode = 'apk_sideload',
    this.appStoreUrl,
    this.artifact,
    this.updateAvailable = false,
    this.mandatory = false,
  });

  factory MobileVersionInfo.fromClientUpdateCheck(Map<String, dynamic> payload) {
    final artifactJson = asJsonMapOrNull(payload['artifact']);
    final artifact = artifactJson == null ? null : ClientUpdateArtifact.fromJson(artifactJson);
    final downloadUrl = artifact?.downloadUrl ?? payload['apk_download_url'] as String?;
    return MobileVersionInfo(
      latestVersion: payload['latest_version'] as String? ?? '0.0.0',
      minSupportedVersion: payload['min_supported_version'] as String? ?? '0.0.0',
      backendVersion: payload['latest_version'] as String? ?? '0.0.0',
      releaseDate: payload['published_at'] as String?,
      releaseNotes: payload['release_notes'] as String?,
      apkDownloadUrl: downloadUrl,
      releaseChannel: payload['release_channel'] as String? ?? 'stable',
      distributionMode: payload['distribution_mode'] as String? ?? 'apk_sideload',
      appStoreUrl: payload['app_store_url'] as String?,
      artifact: artifact,
      updateAvailable: payload['update_available'] as bool? ?? false,
      mandatory: payload['mandatory'] as bool? ?? false,
    );
  }

  factory MobileVersionInfo.fromPayload(Map<String, dynamic> payload) {
    final mobile = asJsonMapOrNull(payload['mobile']);
    final latest = mobile?['latest_version'] as String? ?? payload['backend_version'] as String? ?? '0.0.0';
    final minSupported =
        mobile?['min_supported_version'] as String? ?? payload['min_mobile_version'] as String? ?? latest;
    return MobileVersionInfo(
      latestVersion: latest,
      minSupportedVersion: minSupported,
      backendVersion: payload['backend_version'] as String? ?? '—',
      releaseDate: mobile?['release_date'] as String?,
      releaseNotes: mobile?['release_notes'] as String?,
      apkDownloadUrl: mobile?['apk_download_url'] as String?,
      releaseChannel: mobile?['release_channel'] as String? ?? 'stable',
      distributionMode: mobile?['ios_distribution'] as String? ?? 'apk_sideload',
      appStoreUrl: mobile?['ios_app_store_url'] as String?,
    );
  }

  final String latestVersion;
  final String minSupportedVersion;
  final String backendVersion;
  final String? releaseDate;
  final String? releaseNotes;
  final String? apkDownloadUrl;
  final String releaseChannel;
  final String distributionMode;
  final String? appStoreUrl;
  final ClientUpdateArtifact? artifact;
  final bool updateAvailable;
  final bool mandatory;

  bool get isAppStoreNotification => distributionMode == 'app_store_notification';
}

class VersionCheckOutcome {
  const VersionCheckOutcome({
    required this.kind,
    required this.installedVersion,
    required this.remote,
    this.errorMessage,
    this.checkedAt,
  });

  const VersionCheckOutcome.upToDate({
    required this.installedVersion,
    required this.remote,
    this.checkedAt,
  })  : kind = VersionUpdateKind.upToDate,
        errorMessage = null;

  const VersionCheckOutcome.error({
    required this.installedVersion,
    required this.errorMessage,
    this.remote,
    this.checkedAt,
  }) : kind = VersionUpdateKind.upToDate;

  final VersionUpdateKind kind;
  final String installedVersion;
  final MobileVersionInfo? remote;
  final String? errorMessage;
  final DateTime? checkedAt;
}

/// Parses dotted numeric semver segments for client-side compatibility checks.
int compareAppVersions(String left, String right) {
  final leftParts = _normalizeVersion(left);
  final rightParts = _normalizeVersion(right);
  final length = leftParts.length > rightParts.length ? leftParts.length : rightParts.length;
  for (var index = 0; index < length; index += 1) {
    final leftValue = index < leftParts.length ? leftParts[index] : 0;
    final rightValue = index < rightParts.length ? rightParts[index] : 0;
    if (leftValue != rightValue) return leftValue.compareTo(rightValue);
  }
  return 0;
}

bool isVersionBelow(String installed, String target) => compareAppVersions(installed, target) < 0;

VersionUpdateKind resolveUpdateKind({
  required String installedVersion,
  required MobileVersionInfo remote,
}) {
  if (remote.mandatory || isVersionBelow(installedVersion, remote.minSupportedVersion)) {
    return VersionUpdateKind.mandatoryUpdate;
  }
  if (remote.updateAvailable || isVersionBelow(installedVersion, remote.latestVersion)) {
    return VersionUpdateKind.optionalUpdate;
  }
  return VersionUpdateKind.upToDate;
}

List<int> _normalizeVersion(String value) {
  final cleaned = value.trim().split('+').first;
  if (cleaned.isEmpty) return [0];
  return cleaned.split('.').map((part) => int.tryParse(part.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0).toList();
}
