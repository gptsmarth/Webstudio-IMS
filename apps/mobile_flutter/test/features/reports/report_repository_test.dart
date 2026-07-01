import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/network/json_map.dart';

void main() {
  test('report preview envelope coerces dynamic maps', () {
    final body = <dynamic, dynamic>{
      'data': <dynamic, dynamic>{
        'rows': [
          <dynamic, dynamic>{'serial_number': 'SN-1', 'brand_name': 'ASUS'},
        ],
        'summary': <dynamic, dynamic>{'available_units': 7},
      },
      'meta': <dynamic, dynamic>{
        'page': 1,
        'page_size': 50,
        'total_items': 1,
        'total_pages': 1,
      },
    };

    final envelope = asJsonMap(body);
    final data = asJsonMap(envelope['data']);
    final meta = asJsonMapOrNull(envelope['meta']) ?? {};
    final rows = asJsonMapList(data['rows']);

    expect(rows, hasLength(1));
    expect(rows.first['serial_number'], 'SN-1');
    expect(meta['total_items'], 1);
    expect(asJsonMapOrNull(data['summary'])?['available_units'], 7);
  });
}
