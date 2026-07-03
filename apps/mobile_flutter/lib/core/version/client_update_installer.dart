import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';

import '../config/app_config.dart';
import 'version_models.dart';

class ClientUpdateInstaller {
  ClientUpdateInstaller({
    required AppConfig config,
    Dio? dio,
  }) : _config = config,
       _dio = dio ?? Dio();

  final AppConfig _config;
  final Dio _dio;

  Future<void> installAndroidUpdate(MobileVersionInfo remote) async {
    if (kIsWeb || !Platform.isAndroid) {
      throw UnsupportedError('APK installation is only supported on Android.');
    }
    final artifact = remote.artifact;
    if (artifact == null || artifact.downloadUrl.isEmpty) {
      throw StateError('No APK artifact available from the update server.');
    }

    final url = _resolveAbsoluteUrl(artifact.downloadUrl);
    final directory = await getTemporaryDirectory();
    final target = File('${directory.path}/${artifact.name}');
    if (await target.exists()) {
      await target.delete();
    }

    await _dio.download(url, target.path);
    if (artifact.sha256 != null && artifact.sha256!.isNotEmpty) {
      final bytes = await target.readAsBytes();
      final digest = sha256.convert(bytes).toString();
      if (digest.toLowerCase() != artifact.sha256!.toLowerCase()) {
        await target.delete();
        throw StateError('Downloaded APK failed SHA256 verification.');
      }
    }

    final result = await OpenFile.open(target.path);
    if (result.type != ResultType.done) {
      throw StateError(result.message);
    }
  }

  String _resolveAbsoluteUrl(String relativeOrAbsolute) {
    if (relativeOrAbsolute.startsWith('http://') || relativeOrAbsolute.startsWith('https://')) {
      return relativeOrAbsolute;
    }
    final base = _config.apiBaseUrl.replaceAll(RegExp(r'/+$'), '');
    final path = relativeOrAbsolute.startsWith('/') ? relativeOrAbsolute : '/$relativeOrAbsolute';
    return '$base$path';
  }
}
