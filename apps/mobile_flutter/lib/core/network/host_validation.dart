/// Host validation for IPv4, hostname, and .local mDNS names.
library;

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
    final results = await InternetAddress.lookup(normalized, type: InternetAddressType.IPv4);
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
