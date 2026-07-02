enum VersionUpdateKind { upToDate, optionalUpdate, mandatoryUpdate }

class MobileVersionInfo {
  const MobileVersionInfo({
    required this.latestVersion,
    required this.minSupportedVersion,
    required this.backendVersion,
    this.releaseDate,
    this.releaseNotes,
    this.apkDownloadUrl,
    this.releaseChannel = 'stable',
  });

  factory MobileVersionInfo.fromPayload(Map<String, dynamic> payload) {
    final mobile = payload['mobile'] as Map<String, dynamic>?;
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
    );
  }

  final String latestVersion;
  final String minSupportedVersion;
  final String backendVersion;
  final String? releaseDate;
  final String? releaseNotes;
  final String? apkDownloadUrl;
  final String releaseChannel;
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
  if (isVersionBelow(installedVersion, remote.minSupportedVersion)) {
    return VersionUpdateKind.mandatoryUpdate;
  }
  if (isVersionBelow(installedVersion, remote.latestVersion)) {
    return VersionUpdateKind.optionalUpdate;
  }
  return VersionUpdateKind.upToDate;
}

List<int> _normalizeVersion(String value) {
  final cleaned = value.trim().split('+').first;
  if (cleaned.isEmpty) return [0];
  return cleaned.split('.').map((part) => int.tryParse(part.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0).toList();
}
