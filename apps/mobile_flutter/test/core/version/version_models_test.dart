import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/version/version_models.dart';

void main() {
  group('Version compare', () {
    test('detects optional update when latest is newer', () {
      const remote = MobileVersionInfo(
        latestVersion: '0.2.0',
        minSupportedVersion: '0.1.0',
        backendVersion: '0.2.0',
      );
      expect(
        resolveUpdateKind(installedVersion: '0.1.0', remote: remote),
        VersionUpdateKind.optionalUpdate,
      );
    });

    test('detects mandatory update below minimum supported', () {
      const remote = MobileVersionInfo(
        latestVersion: '0.3.0',
        minSupportedVersion: '0.2.0',
        backendVersion: '0.3.0',
      );
      expect(
        resolveUpdateKind(installedVersion: '0.1.0', remote: remote),
        VersionUpdateKind.mandatoryUpdate,
      );
    });

    test('reports up to date when installed matches latest', () {
      const remote = MobileVersionInfo(
        latestVersion: '0.1.0',
        minSupportedVersion: '0.1.0',
        backendVersion: '0.1.0',
      );
      expect(
        resolveUpdateKind(installedVersion: '0.1.0', remote: remote),
        VersionUpdateKind.upToDate,
      );
    });

    test('parses mobile payload from version API', () {
      final remote = MobileVersionInfo.fromPayload({
        'backend_version': '0.2.0',
        'min_mobile_version': '0.1.0',
        'mobile': {
          'latest_version': '0.2.0',
          'min_supported_version': '0.1.0',
          'release_date': '2026-07-01',
          'release_notes': 'Stability fixes',
          'apk_download_url': 'https://example.com/app.apk',
          'release_channel': 'beta',
        },
      });
      expect(remote.latestVersion, '0.2.0');
      expect(remote.releaseChannel, 'beta');
      expect(remote.apkDownloadUrl, 'https://example.com/app.apk');
    });
  });
}
