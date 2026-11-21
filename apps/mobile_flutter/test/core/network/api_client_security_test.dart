import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/config/app_config.dart';
import 'package:webstudio_ims/core/network/api_client.dart';
import 'package:webstudio_ims/core/storage/secure_token_storage.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('connection probes omit session tokens and HTTPS requests refuse redirects', () async {
    FlutterSecureStorage.setMockInitialValues({
      SecureTokenStorage.accessTokenKey: 'synthetic-test-token',
    });
    final dio = Dio();
    addTearDown(() => dio.close(force: true));
    final api = ApiClient(
      config: const AppConfig(
        apiBaseUrl: 'https://ims.example.test',
        clientVersion: '1.0.0',
        clientPlatform: 'ios_mobile',
      ),
      tokenStorage: SecureTokenStorage(),
      dio: dio,
    );
    final requests = <RequestOptions>[];
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          requests.add(options);
          handler.resolve(
            Response(requestOptions: options, statusCode: 200, data: {'data': 'ok'}),
          );
        },
      ),
    );

    expect(await api.checkHealthLiveAt('http://discovered.example.test'), isTrue);
    await api.getAt<String>(
      'https://discovered.example.test',
      '/api/v1/version',
      parser: (json) => json as String,
    );
    await api.get<String>('/api/v1/auth/me', parser: (json) => json as String);

    expect(requests[0].headers['Authorization'], isNull);
    expect(requests[1].headers['Authorization'], isNull);
    expect(requests[1].followRedirects, isFalse);
    expect(requests[2].headers['Authorization'], 'Bearer synthetic-test-token');
    expect(requests[2].followRedirects, isFalse);
  });
}
