import 'package:equatable/equatable.dart';

import '../network/json_map.dart';

class ApiException implements Exception {
  const ApiException({
    required this.code,
    required this.message,
    this.statusCode,
    this.details = const [],
  });

  final String code;
  final String message;
  final int? statusCode;
  final List<dynamic> details;

  @override
  String toString() => 'ApiException($code): $message';
}

class AuthSessionExpiredException extends ApiException {
  const AuthSessionExpiredException()
      : super(code: 'SESSION_EXPIRED', message: 'Your session has expired. Sign in again.');
}

class NetworkException extends ApiException {
  const NetworkException([String message = 'Could not reach the server. Check your connection.'])
      : super(code: 'NETWORK_ERROR', message: message);
}

class ApiEnvelope<T> extends Equatable {
  const ApiEnvelope({
    required this.data,
    this.meta,
    this.requestId,
    this.correlationId,
    this.timestamp,
  });

  final T data;
  final Map<String, dynamic>? meta;
  final String? requestId;
  final String? correlationId;
  final String? timestamp;

  factory ApiEnvelope.fromJson(
    Map<String, dynamic> json,
    T Function(Object? json) fromJsonT,
  ) {
    return ApiEnvelope(
      data: fromJsonT(json['data']),
      meta: asJsonMapOrNull(json['meta']),
      requestId: json['request_id'] as String?,
      correlationId: json['correlation_id'] as String?,
      timestamp: json['timestamp'] as String?,
    );
  }

  @override
  List<Object?> get props => [data, meta, requestId, correlationId, timestamp];
}

class ApiErrorEnvelope extends Equatable {
  const ApiErrorEnvelope({
    required this.code,
    required this.message,
    this.details = const [],
    this.requestId,
    this.correlationId,
    this.timestamp,
  });

  final String code;
  final String message;
  final List<dynamic> details;
  final String? requestId;
  final String? correlationId;
  final String? timestamp;

  factory ApiErrorEnvelope.fromJson(Map<String, dynamic> json) {
    final error = asJsonMapOrNull(json['error']) ?? asJsonMap(json);
    return ApiErrorEnvelope(
      code: error['code'] as String? ?? 'API_ERROR',
      message: error['message'] as String? ?? 'Request failed',
      details: (error['details'] as List<dynamic>?) ?? const [],
      requestId: json['request_id'] as String?,
      correlationId: json['correlation_id'] as String?,
      timestamp: json['timestamp'] as String?,
    );
  }

  ApiException toException({int? statusCode}) => ApiException(
        code: code,
        message: message,
        statusCode: statusCode,
        details: details,
      );

  @override
  List<Object?> get props => [code, message, details, requestId];
}
