import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/routing/shell_route_titles.dart';

void main() {
  test('shellRouteContext resolves nested titles', () {
    final reports = shellRouteContext('/more/reports');
    expect(reports.title, 'Reports');
    expect(reports.canPopRoute, isTrue);

    final stock = shellRouteContext('/stock');
    expect(stock.title, 'Stock');
    expect(stock.canPopRoute, isFalse);
  });
}
