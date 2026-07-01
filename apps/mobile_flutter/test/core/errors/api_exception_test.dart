import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/errors/api_exception.dart';

void main() {
  group('ApiErrorEnvelope', () {
    test('parses standard backend error envelope', () {
      final envelope = ApiErrorEnvelope.fromJson({
        'error': {
          'code': 'INVALID_CREDENTIALS',
          'message': 'Invalid credentials',
          'details': <dynamic>[],
        },
        'request_id': 'req-1',
      });

      expect(envelope.code, 'INVALID_CREDENTIALS');
      expect(envelope.message, 'Invalid credentials');
      expect(envelope.requestId, 'req-1');
    });

    test('maps to ApiException with status code', () {
      final exception = ApiErrorEnvelope.fromJson({
        'error': {'code': 'NOT_FOUND', 'message': 'Missing'},
      }).toException(statusCode: 404);

      expect(exception.code, 'NOT_FOUND');
      expect(exception.statusCode, 404);
    });

    test('parses error when nested map uses dynamic keys', () {
      final envelope = ApiErrorEnvelope.fromJson({
        'error': <dynamic, dynamic>{
          'code': 'FORBIDDEN',
          'message': 'Permission denied',
        },
      });

      expect(envelope.code, 'FORBIDDEN');
      expect(envelope.message, 'Permission denied');
    });
  });
}
