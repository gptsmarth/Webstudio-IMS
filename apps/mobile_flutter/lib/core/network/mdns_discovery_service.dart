import 'dart:async';

import 'package:bonsoir/bonsoir.dart';

import '../../features/connection/domain/server_models.dart';

const discoveryServiceType = '_webstudio-ims._tcp';
const discoveryTimeout = Duration(milliseconds: 4500);

class MdnsDiscoveryService {
  BonsoirDiscovery? _discovery;
  final _servers = <String, DiscoveredServer>{};

  Future<List<DiscoveredServer>> discover({Duration timeout = discoveryTimeout}) async {
    _servers.clear();
    _discovery = BonsoirDiscovery(type: discoveryServiceType);
    await _discovery!.ready;

    final subscription = _discovery!.eventStream?.listen((event) {
      final service = event.service;
      if (service == null) return;

      switch (event.type) {
        case BonsoirDiscoveryEventType.discoveryServiceFound:
          unawaited(service.resolve(_discovery!.serviceResolver));
        case BonsoirDiscoveryEventType.discoveryServiceResolved:
          final mapped = _mapService(service);
          if (mapped != null) {
            _servers[mapped.id] = mapped;
          }
        case BonsoirDiscoveryEventType.discoveryServiceLost:
          _servers.removeWhere((key, _) => key.contains(service.name));
        default:
          break;
      }
    });

    await _discovery!.start();
    await Future<void>.delayed(timeout);
    await subscription?.cancel();
    await stop();
    return _servers.values.toList()
      ..sort((a, b) => a.companyName.compareTo(b.companyName));
  }

  Future<void> stop() async {
    await _discovery?.stop();
    _discovery = null;
  }

  DiscoveredServer? _mapService(BonsoirService service) {
    final host = service is ResolvedBonsoirService ? service.host : null;
    if (host == null || host.isEmpty) return null;
    final attributes = service.attributes;
    final port = service.port;
    final serverName = attributes['server_name'] ?? service.name.split('.').first;
    final companyName = attributes['company_name'] ?? 'WEBSTUDIO';
    final id = '${service.name}-$host-$port';
    return DiscoveredServer(
      id: id,
      serverName: serverName,
      companyName: companyName,
      backendVersion: attributes['backend_version'] ?? 'unknown',
      apiVersion: attributes['api_version'] ?? '1.0',
      buildVersion: attributes['build_version'] ?? '',
      environment: attributes['environment'] ?? 'production',
      port: port,
      host: host,
      url: 'http://$host:$port',
      lastSeen: DateTime.now(),
      status: 'online',
    );
  }
}
