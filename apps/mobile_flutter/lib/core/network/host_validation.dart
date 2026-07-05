/// Host validation for IPv4, hostname, and .local mDNS names.
library;

import 'dart:async';
import 'dart:io';

final _hostnamePattern = RegExp(
  r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?))*$',
);
final _ipv4Pattern = RegExp(r'^\d{1,3}(?:\.\d{1,3}){3}$');

class HostValidationException implements Exception {
  HostValidationException(this.message);
  final String message;

  @override
  String toString() => message;
}

String normalizeServerHost(String raw) {
  final host = raw.trim();
  if (host.isEmpty) {
    throw HostValidationException('Host / IP address is required.');
  }
  if (_ipv4Pattern.hasMatch(host)) {
    return host;
  }
  final lowered = host.toLowerCase().replaceAll(RegExp(r'\.$'), '');
  if (!_hostnamePattern.hasMatch(lowered)) {
    throw HostValidationException(
      'Enter a valid IPv4 address, hostname, or mDNS name (for example WEBSTUDIO-SERVER.local).',
    );
  }
  return lowered;
}

String normalizeServerUrl(String raw, {int defaultPort = 8000}) {
  final trimmed = raw.trim();
  if (trimmed.isEmpty) {
    throw HostValidationException('Server address is required.');
  }

  var candidate = trimmed;
  if (!candidate.startsWith('http://') && !candidate.startsWith('https://')) {
    candidate = 'http://$candidate';
  }

  final uri = Uri.parse(candidate);
  final host = normalizeServerHost(uri.host);
  final port = uri.hasPort ? uri.port : defaultPort;
  return Uri(scheme: 'http', host: host, port: port).toString().replaceAll(RegExp(r'/+$'), '');
}

String? extractHostnameFromUrl(String url) {
  try {
    return normalizeServerHost(Uri.parse(url).host);
  } catch (_) {
    return null;
  }
}

Future<HostResolutionResult> resolveServerHost(String host, {int port = 8000}) async {
  try {
    final normalized = normalizeServerHost(host);
    if (_ipv4Pattern.hasMatch(normalized)) {
      return HostResolutionResult(
        configuredHost: normalized,
        resolvedIp: normalized,
        success: true,
        message: 'Using IPv4 address $normalized.',
      );
    }

    final results = await InternetAddress.lookup(
      normalized,
      type: InternetAddressType.IPv4,
    ).timeout(
      const Duration(seconds: 5),
      onTimeout: () => throw TimeoutException('Timed out resolving $normalized.'),
    );
    if (results.isEmpty) {
      return HostResolutionResult(
        configuredHost: normalized,
        resolvedIp: null,
        success: false,
        message: 'Could not resolve $normalized.',
      );
    }
    final ip = results.first.address;
    return HostResolutionResult(
      configuredHost: normalized,
      resolvedIp: ip,
      success: true,
      message: 'Resolved $normalized to $ip.',
    );
  } on TimeoutException catch (error) {
    return HostResolutionResult(
      configuredHost: host.trim(),
      resolvedIp: null,
      success: false,
      message: error.message ?? 'Timed out resolving host.',
    );
  } on HostValidationException catch (error) {
    return HostResolutionResult(
      configuredHost: host.trim(),
      resolvedIp: null,
      success: false,
      message: error.message,
    );
  } on SocketException catch (error) {
    return HostResolutionResult(
      configuredHost: host.trim(),
      resolvedIp: null,
      success: false,
      message: error.message,
    );
  }
}

class HostResolutionResult {
  const HostResolutionResult({
    required this.configuredHost,
    required this.resolvedIp,
    required this.success,
    required this.message,
  });

  final String configuredHost;
  final String? resolvedIp;
  final bool success;
  final String message;
}
