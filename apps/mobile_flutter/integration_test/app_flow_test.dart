import 'package:integration_test/integration_test.dart';

import 'support/app_flow_cases.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(initIntegrationHarness);
  registerAppFlowIntegrationTests();
}
