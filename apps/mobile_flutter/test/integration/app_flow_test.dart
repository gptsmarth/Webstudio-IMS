import 'package:flutter_test/flutter_test.dart';

import '../../integration_test/support/app_flow_cases.dart';

void main() {
  setUpAll(initIntegrationHarness);
  registerAppFlowIntegrationTests();
}
