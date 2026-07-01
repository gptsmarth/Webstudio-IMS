import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/network/json_map.dart';

void main() {
  group('asJsonMap', () {
    test('returns Map<String, dynamic> unchanged', () {
      final input = <String, dynamic>{'id': 1};
      expect(identical(asJsonMap(input), input), isTrue);
    });

    test('coerces Map<dynamic, dynamic>', () {
      final input = <dynamic, dynamic>{'id': 1, 'name': 'ASUS'};
      final result = asJsonMap(input);
      expect(result, {'id': 1, 'name': 'ASUS'});
    });

    test('asJsonMapList filters non-objects', () {
      final input = [
        <dynamic, dynamic>{'id': 1},
        'skip',
        <String, dynamic>{'id': 2},
      ];
      expect(asJsonMapList(input), [
        {'id': 1},
        {'id': 2},
      ]);
    });
  });
}
