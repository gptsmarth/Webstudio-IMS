import '../../../core/constants/api_paths.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/host_validation.dart';
import '../../features/connection/domain/server_models.dart';

class ConnectionDiagnostics {
  ConnectionDiagnostics(this._api);

  final ApiClient _api;

  static const stageLabels = {
    ConnectionStageId.hostResolution: 'Host Resolution',
    ConnectionStageId.reachability: 'Reachability',
    ConnectionStageId.httpConnection: 'HTTP Connection',
    ConnectionStageId.backendHealth: 'Backend Health',
    ConnectionStageId.apiCompatibility: 'API Compatibility',
    ConnectionStageId.authenticationEndpoint: 'Authentication Endpoint',
  };

  Future<ConnectionTestResult> run(String rawUrl) async {
    final stages = <ConnectionStageResult>[];
    var normalized = rawUrl.trim();

    final hostStage = await _runStage(ConnectionStageId.hostResolution, () async {
      normalized = normalizeServerUrl(rawUrl);
      final hostname = extractHostnameFromUrl(normalized);
      if (hostname == null) {
        throw HostValidationException('Could not parse server hostname.');
      }
      final resolution = await resolveServerHost(hostname);
      if (!resolution.success) {
        throw HostValidationException(resolution.message);
      }
    });
    stages.add(hostStage);
    if (!hostStage.success) {
      return _failure(normalized, stages, hostStage);
    }

    final reachabilityStage = await _runStage(ConnectionStageId.reachability, () async {
      final healthy = await _api.checkHealthLiveAt(normalized);
      if (!healthy) {
        throw Exception('Server did not respond.');
      }
    });
    stages.add(reachabilityStage);

    final httpStage = await _runStage(ConnectionStageId.httpConnection, () async {
      final healthy = await _api.checkHealthLiveAt(normalized);
      if (!healthy) {
        throw Exception('HTTP health check failed.');
      }
    });
    stages.add(httpStage);
    if (!httpStage.success) {
      return _failure(normalized, stages, httpStage);
    }

    final healthStage = await _runStage(ConnectionStageId.backendHealth, () async {
      final ready = await _api.getAt<Map<String, dynamic>>(
        normalized,
        '/health/ready',
        parser: (json) => Map<String, dynamic>.from(json! as Map),
      );
      final checks = ready['checks'] as Map<String, dynamic>?;
      if (checks?['database'] == 'failed') {
        throw Exception('Database is not ready.');
      }
    });
    stages.add(healthStage);
    if (!healthStage.success) {
      return _failure(normalized, stages, healthStage);
    }

    String? backendVersion;
    final apiStage = await _runStage(ConnectionStageId.apiCompatibility, () async {
      final versionData = await _api.getAt<Map<String, dynamic>>(
        normalized,
        ApiPaths.version,
        parser: (json) => Map<String, dynamic>.from(json! as Map),
      );
      backendVersion = versionData['backend_version'] as String?;
      if (versionData['api_version'] == null) {
        throw Exception('API version metadata missing.');
      }
    });
    stages.add(apiStage);
    if (!apiStage.success) {
      return _failure(normalized, stages, apiStage);
    }

    String? companyName;
    final authStage = await _runStage(ConnectionStageId.authenticationEndpoint, () async {
      final setup = await _api.getAt<SetupStatus>(
        normalized,
        ApiPaths.setupStatus,
        parser: (json) => SetupStatus.fromJson(json! as Map<String, dynamic>),
      );
      companyName = setup.companyName;
    });
    stages.add(authStage);
    if (!authStage.success) {
      return _failure(normalized, stages, authStage);
    }

    return ConnectionTestResult(
      success: true,
      url: normalized,
      backendVersion: backendVersion,
      companyName: companyName,
      stages: stages,
    );
  }

  Future<ConnectionStageResult> _runStage(
    ConnectionStageId stage,
    Future<void> Function() action,
  ) async {
    try {
      await action();
      return ConnectionStageResult(
        stage: stage,
        label: stageLabels[stage]!,
        success: true,
        message: 'OK',
      );
    } catch (error) {
      return ConnectionStageResult(
        stage: stage,
        label: stageLabels[stage]!,
        success: false,
        message: error.toString(),
      );
    }
  }

  ConnectionTestResult _failure(
    String url,
    List<ConnectionStageResult> stages,
    ConnectionStageResult failed,
  ) {
    return ConnectionTestResult(
      success: false,
      url: url,
      errorMessage: failed.message,
      stages: stages,
      failedStage: failed.stage,
    );
  }
}
